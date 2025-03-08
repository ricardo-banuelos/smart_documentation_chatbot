from fastapi import FastAPI, UploadFile, File

import os
import uuid

app = FastAPI()

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