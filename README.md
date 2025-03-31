# Smart Documentation Chatbot

A simple yet powerful system for querying documents using large language models (LLMs) and vector databases. Upload your PDFs, TXT files, or Word documents and ask questions in natural language.

## Features
- 📄 Document Upload & Management (PDF, TXT, DOCX)
- 🔍 Natural Language Querying
- 💬 Conversation Memory & Session Management
- 🔄 Persistent Storage with SQLite
- 🐳 Easy Deployment with Docker

## Architecture
This system uses LangChain with OpenAI to process documents and answer questions about their content. Here's how it works:

1. Document Processing: Files are uploaded, split into chunks, and converted to embeddings
2. Vector Storage: Document chunks are stored in a FAISS vector database
3. Querying: Questions are processed with a conversational retrieval chain
4. Persistence: SQLite database stores documents, sessions, and conversations

## Supported File Types
- PDF files (.pdf)
- Plain text files (.txt)
- Word documents (.docx, .doc)

## Requirements
- Python 3.8+
- OpenAI API Key

## Quick Start with Docker
1. Clone this repository
```bash
git clone https://github.com/yourusername/document-query-system.git
cd document-query-system
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
- POST /upload/ - Upload a document (PDF, TXT, DOCX)
- GET /documents/ - List all uploaded documents
- DELETE /documents/{document_id} - Delete a document

### Querying
- POST /query/{document_id} - Query a document with conversation memory

###