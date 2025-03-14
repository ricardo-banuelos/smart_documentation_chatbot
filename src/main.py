import os
import uuid
import shutil
from typing import Dict, List, Optional
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pdf_query_engine import PDFQueryEngine

from dotenv import load_dotenv

# Initialize FastAPI app
app = FastAPI(title="PDF Query API", description="API for querying PDF documents using LLMs")

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

# In-memory storage for uploaded documents and sessions
documents = {}  # document_id -> {file_path, engine, filename}
sessions = {}   # session_id -> document_id


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


class SessionInfo(BaseModel):
    session_id: str
    document_id: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
    session_id: str


@app.post("/upload/", response_model=DocumentInfo)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF document and prepare it for querying.
    """
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")
        
        # Generate unique ID for this document
        document_id = str(uuid.uuid4())
        
        # Create file path
        filename = file.filename
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
            engine = PDFQueryEngine(OPEN_AI_API_KEY)
            engine.load_pdf(file_path)
            
            # Store in memory
            documents[document_id] = {
                "file_path": file_path,
                "filename": filename,
                "engine": engine
            }
            
            return {"id": document_id, "filename": filename}
        except Exception as e:
            # Clean up the file if engine initialization fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed with error: {str(e)}")


@app.post("/query/{document_id}", response_model=QueryResponse)
async def query_document(document_id: str, query_request: QueryRequest):
    """
    Query a previously uploaded PDF document with conversation memory.
    """
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get or create session ID
    session_id = query_request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        sessions[session_id] = document_id
    elif session_id in sessions and sessions[session_id] != document_id:
        # If session exists but is for a different document, create a new session
        session_id = str(uuid.uuid4())
        sessions[session_id] = document_id
    else:
        sessions[session_id] = document_id
    
    try:
        engine = documents[document_id]["engine"]
        result = engine.query(query_request.question, session_id)
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.get("/documents/", response_model=List[DocumentInfo])
async def list_documents():
    """
    List all uploaded documents.
    """
    return [
        {"id": doc_id, "filename": doc_info["filename"]} 
        for doc_id, doc_info in documents.items()
    ]


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its associated resources.
    """
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = documents[document_id]["file_path"]
    
    # Remove file and document entry
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove associated sessions
        for session_id, doc_id in list(sessions.items()):
            if doc_id == document_id:
                del sessions[session_id]
        
        del documents[document_id]
        return {"status": "success", "message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@app.get("/sessions/history/{session_id}", response_model=ChatHistoryResponse)
async def get_session_history(session_id: str):
    """
    Get the conversation history for a session.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    document_id = sessions[session_id]
    engine = documents[document_id]["engine"]
    
    # Convert LangChain messages to our ChatMessage format
    messages = []
    for msg in engine.get_chat_history():
        role = "user" if msg.type == "human" else "assistant"
        messages.append({"role": role, "content": msg.content})
    
    return {"messages": messages, "session_id": session_id}


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """
    Clear the conversation history for a session.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    document_id = sessions[session_id]
    engine = documents[document_id]["engine"]
    engine.clear_memory()
    
    return {"status": "success", "message": f"Session {session_id} cleared"}


# For development/testing purposes
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)