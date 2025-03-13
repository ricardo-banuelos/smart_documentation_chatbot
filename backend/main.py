from fastapi import FastAPI, UploadFile, File, Depends, HTTPException

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from dotenv import load_dotenv

import os
import uuid
import pdfplumber

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Document Model
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    content = Column(Text)

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_file_extension(filename: str):
    parts = os.path.splitext(filename)
    if len(parts) > 1:
        return parts[1]
    return ""

def extract_text_from_pdf(file_path: str):
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
        return text

@app.get("/")
async def root():
    return {
        "message" : "Smart Documentation Chatbot Backend"
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):

    # Get and validate file extension
    file_extension = get_file_extension(file.filename)
    if file_extension != '.pdf':
        raise HTTPException(400, 'File extension must be .pdf')

    # Save file with unique name to avoid duplicates
    unique_file_name = f'{uuid.uuid4()}{file_extension}'
    file_path = os.path.join(UPLOAD_DIR, unique_file_name)
    with open(file_path, 'wb') as buffer:
        buffer.write(await file.read())

    # Extract text from PDF
    text_content = extract_text_from_pdf(file_path)

    # Store content in db
    doc = Document(filename=unique_file_name, content=text_content)
    db.add(doc)
    db.commit()

    return {
        "file_name": unique_file_name,
        "message": "File uploaded successfully!"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)