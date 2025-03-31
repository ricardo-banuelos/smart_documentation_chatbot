import os
import uuid
import shutil
from typing import Dict, List, Optional
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .document_query_engine import QueryEngineFactory
from .document_loaders import DocumentLoaderFactory
from .models import get_db, Document, Session as DBSession, Message

from dotenv import load_dotenv

# Initialize FastAPI app
app = FastAPI(title="Document Query API", description="API for querying documents using LLMs")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

load_dotenv()
OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')

# Store uploads in this directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory storage for query engines
engines = {}  # document_id -> DocumentQueryEngine instance


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str


class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    upload_date: str


class SessionInfo(BaseModel):
    session_id: str
    document_id: str
    created_at: str
    last_activity: str


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
    session_id: str


@app.post("/upload/", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a document (PDF, TXT, DOCX) and prepare it for querying.
    """
    try:
        # Get the file extension and check if it's supported
        filename = file.filename
        _, file_ext = os.path.splitext(filename.lower())
        
        supported_extensions = DocumentLoaderFactory.get_supported_extensions()
        
        if file_ext not in supported_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(supported_extensions)}"
            )
        
        # Generate unique ID for this document
        document_id = str(uuid.uuid4())
        
        # Create file path
        file_path = os.path.join(UPLOAD_DIR, f"{document_id}_{filename}")
        
        # Save uploaded file
        try:
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File write operation failed: {str(e)}")
        finally:
            await file.close()
        
        # Initialize the query engine
        try:
            engine = QueryEngineFactory.create_engine(file_path, OPEN_AI_API_KEY)
            engine.load_document(file_path)
            
            # Store engine in memory
            engines[document_id] = engine
            
            # Store document information in database
            db_document = Document(
                id=document_id,
                filename=filename,
                file_path=file_path,
                file_type=file_ext[1:]  # Store without the leading dot
            )
            db.add(db_document)
            db.commit()
            
            return {
                "id": document_id, 
                "filename": filename,
                "file_type": file_ext[1:],
                "upload_date": db_document.upload_date.isoformat()
            }
        
        except Exception as e:
            # Clean up the file if engine initialization fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
        
    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed with error: {str(e)}")


@app.post("/query/{document_id}", response_model=QueryResponse)
async def query_document(document_id: str, query_request: QueryRequest, db: Session = Depends(get_db)):
    """
    Query a previously uploaded document with conversation memory.
    """
    # Check if document exists in database
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get or initialize engine
    if document_id not in engines:
        try:
            engine = QueryEngineFactory.create_engine(db_document.file_path, OPEN_AI_API_KEY)
            engine.load_document(db_document.file_path)
            engines[document_id] = engine
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize query engine: {str(e)}")
    else:
        engine = engines[document_id]
    
    # Get or create session ID
    session_id = query_request.session_id
    db_session = None
    
    if not session_id:
        # Create new session
        session_id = str(uuid.uuid4())
        db_session = DBSession(
            id=session_id,
            document_id=document_id
        )
        db.add(db_session)
    else:
        # Check if session exists
        db_session = db.query(DBSession).filter(DBSession.id == session_id).first()
        if not db_session:
            # Create new session with the provided ID
            db_session = DBSession(
                id=session_id,
                document_id=document_id
            )
            db.add(db_session)
        elif db_session.document_id != document_id:
            # If session exists but is for a different document, create a new session
            session_id = str(uuid.uuid4())
            db_session = DBSession(
                id=session_id,
                document_id=document_id
            )
            db.add(db_session)
    
    try:
        # Store the question in database
        user_message = Message(
            session_id=session_id,
            role="user",
            content=query_request.question
        )
        db.add(user_message)
        
        # Query the engine
        result = engine.query(query_request.question, session_id)
        
        # Store the answer in database
        assistant_message = Message(
            session_id=session_id,
            role="assistant",
            content=result["answer"]
        )
        db.add(assistant_message)
        
        # Update session last activity
        db_session.last_activity = user_message.timestamp
        
        db.commit()
        
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "session_id": session_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.get("/documents/", response_model=List[DocumentInfo])
async def list_documents(db: Session = Depends(get_db)):
    """
    List all uploaded documents.
    """
    documents = db.query(Document).all()
    return [
        {
            "id": doc.id, 
            "filename": doc.filename,
            "file_type": doc.file_type or "pdf",  # Default to pdf for backward compatibility
            "upload_date": doc.upload_date.isoformat()
        } 
        for doc in documents
    ]


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """
    Delete a document and its associated resources.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = document.file_path
    
    # Remove file and document entry
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove document from database (cascade will remove sessions and messages)
        db.delete(document)
        
        # Remove engine from memory
        if document_id in engines:
            del engines[document_id]
            
        db.commit()
        return {"status": "success", "message": "Document deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@app.get("/sessions/{document_id}", response_model=List[SessionInfo])
async def list_sessions(document_id: str, db: Session = Depends(get_db)):
    """
    List all sessions for a document.
    """
    # Check if document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    sessions = db.query(DBSession).filter(DBSession.document_id == document_id).all()
    return [
        {
            "session_id": session.id,
            "document_id": session.document_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }
        for session in sessions
    ]


@app.get("/sessions/history/{session_id}", response_model=ChatHistoryResponse)
async def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """
    Get the conversation history for a session.
    """
    session = db.query(DBSession).filter(DBSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp).all()
    
    return {
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            } 
            for msg in messages
        ],
        "session_id": session_id
    }


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str, db: Session = Depends(get_db)):
    """
    Clear the conversation history for a session.
    """
    session = db.query(DBSession).filter(DBSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Clear messages from database
    db.query(Message).filter(Message.session_id == session_id).delete()
    
    # Clear memory in engine
    document_id = session.document_id
    if document_id in engines:
        engines[document_id].clear_memory(session_id)
    
    db.commit()
    return {"status": "success", "message": f"Session {session_id} cleared"}


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok", "message": "API is operational"}


# For development/testing purposes
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)