# Smart Documentation Chatbot

A simple yet powerful system for querying PDF documents using large language models (LLMs) and vector databases. Upload your PDFs and ask questions in natural language.

## Features
- 📄 PDF Upload & Management
- 🔍 Natural Language Querying
- 💬 Conversation Memory & Session Management
- 🔄 Persistent Storage with SQLite
- 🐳 Easy Deployment with Docker

## Architecture
This system uses LangChain with OpenAI to process PDF documents and answer questions about their content. Here's how it works:

1. PDF Processing: PDFs are uploaded, split into chunks, and converted to embeddings
2. Vector Storage: Document chunks are stored in a FAISS vector database
3. Querying: Questions are processed with a conversational retrieval chain
4. Persistence: SQLite database stores documents, sessions, and conversations

## Requirements
- Python 3.8+
- OpenAI API Key

## Quick Start with Docker
1. Clone this repository
```bash
git clone https://github.com/yourusername/pdf-query-system.git
cd pdf-query-system
```
2. Create a .env file with your OpenAI API key
```bash
echo "OPEN_AI_API_KEY=your-api-key-here" > .env
```
3. Start the application with Docker Compose
```bash
docker-compose up -d
```
4. Access the API at  http://localhost:8000


## API Endpoints

### Documents
- POST /upload/ - Upload a PDF document
- GET /documents/ - List all uploaded documents
- DELETE /documents/{document_id} - Delete a document

## Local Development
1. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Set environment variables
```bash
# On Linux/Mac
export OPEN_AI_API_KEY=your-api-key-here

# On Windows
set OPEN_AI_API_KEY=your-api-key-here
```
4. Run the application
```bash
uvicorn app.main:app --reload
```

## Acknowledgements
This project uses the following libraries:
- LangChain
- OpenAI
- FastAPI
- SQLAlchemy
- FAISS