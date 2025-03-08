from fastapi import FastAPI, UploadFile, File, Depends

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

import os
import uuid

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

@app.get("/")
async def root():
    return {
        "message" : "Smart Documentation Chatbot Backend"
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_extension = get_file_extension(file.filename)
    unique_file_name = f'{uuid.uuid4()}{file_extension}'

    file_path = os.path.join(UPLOAD_DIR, unique_file_name)
    with open(file_path, 'wb') as buffer:
        buffer.write(await file.read())

    return {
        "file_name": unique_file_name,
        "message": "File uploaded successfully!"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)