# Customer Representative API

RAG (Retrieval-Augmented Generation) based customer representative system. Provides intelligent question-answer system using Gemini AI and ChromaDB.

## Features

- **RAG Pipeline**: Document ingestion and intelligent Q&A
- **Multi-Content Support**: Text, URL and file upload
- **Vector Search**: Fast similarity search with ChromaDB
- **Source Attribution**: Shows which sources the responses come from

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
```

Edit the `.env` file and add the necessary information:

**For Cloud ChromaDB:**
```
GEMINI_API_KEY=your_actual_api_key_here
CHROMA_HOST=your_chroma_cloud_host
CHROMA_PORT=443
CHROMA_API_KEY=your_chroma_api_key
```

**For Local ChromaDB:**
```
GEMINI_API_KEY=your_actual_api_key_here
# Leave CHROMA_HOST variable empty or delete it
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

3. **Start the API:**
```bash
python main.py
```

The API will run at `http://localhost:8000`.

## API Endpoints

### Document Ingestion

- **POST** `/api/ingest/text` - Add text content
- **POST** `/api/ingest/url` - Add URL content  
- **POST** `/api/ingest/file` - Upload file (.txt)

### Chat

- **POST** `/api/chat` - Chat with customer representative

### Management

- **GET** `/api/stats` - System statistics
- **DELETE** `/api/clear` - Clear database
- **GET** `/health` - Health check

## Detailed API Endpoint Usage

### 🏠 Home Page
```bash
GET /
```
**Description**: Checks if the API is running.
```bash
curl http://localhost:8080/
```
**Response**:
```json
{"message": "Welcome to Customer Representative API!"}
```

### 🔍 Health Check
```bash
GET /health
```
**Description**: Shows API status and document count in database.
```bash
curl http://localhost:8080/health
```
**Response**:
```json
{
  "status": "healthy",
  "collection_count": 15
}
```

### 📝 Add Text Content
```bash
POST /api/ingest/text
```
**Description**: Adds plain text content to vector database.

**Request Format**:
```json
{
  "text": "string",
  "metadata": {} // optional
}
```

**Example**:
```bash
curl -X POST "http://localhost:8080/api/ingest/text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Our company provides service Monday-Friday 09:00-18:00, Saturday 10:00-16:00. We are closed on Sundays.",
    "metadata": {
      "category": "working_hours",
      "department": "customer_service",
      "priority": "high"
    }
  }'
```

**Response**:
```json
{
  "message": "Text added successfully",
  "chunks_added": 1,
  "total_documents": 16
}
```

### 🌐 Add URL Content
```bash
POST /api/ingest/url
```
**Description**: Automatically fetches web page content and adds it to database.

**Request Format**:
```json
{
  "url": "string",
  "metadata": {} // optional
}
```

**Example**:
```bash
curl -X POST "http://localhost:8080/api/ingest/url" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/faq",
    "metadata": {
      "source": "company_website",
      "type": "faq",
      "last_updated": "2024-01-15"
    }
  }'
```

**Response**:
```json
{
  "message": "URL content added successfully",
  "url": "https://example.com/faq",
  "chunks_added": 5,
  "total_documents": 21
}
```

### 📄 File Upload
```bash
POST /api/ingest/file
```
**Description**: Uploads text file (.txt) and adds its content to database.

**Example**:
```bash
curl -X POST "http://localhost:8080/api/ingest/file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/document.txt"
```

**Response**:
```json
{
  "message": "File added successfully",
  "filename": "document.txt",
  "chunks_added": 3,
  "total_documents": 24
}
```

### 💬 Customer Chat
```bash
POST /api/chat
```
**Description**: Answers customer questions using RAG system.

**Request Format**:
```json
{
  "message": "string",
  "conversation_id": "string" // optional
}
```

**Example**:
```bash
curl -X POST "http://localhost:8080/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Are you open on Saturdays?",
    "conversation_id": "conv-123"
  }'
```

**Response**:
```json
{
  "response": "Yes, we provide service on Saturdays between 10:00-16:00.",
  "conversation_id": "conv-123",
  "sources": [
    {
      "content": "Our company provides service Monday-Friday 09:00-18:00, Saturday 10:00-16:00...",
      "metadata": {
        "category": "working_hours",
        "chunk_index": 0
      },
      "similarity_score": 0.89
    }
  ]
}
```

### 📊 System Statistics
```bash
GET /api/stats
```
**Description**: Shows database status and statistics.
```bash
curl http://localhost:8080/api/stats
```
**Response**:
```json
{
  "total_documents": 24,
  "collection_name": "customer_support_kb",
  "status": "active"
}
```

### 🗑️ Clear Database
```bash
DELETE /api/clear
```
**Description**: Deletes all documents (USE WITH CAUTION!).
```bash
curl -X DELETE http://localhost:8080/api/clear
```
**Response**:
```json
{
  "message": "Database cleared successfully"
}
```

## Usage Scenarios

### 1. **Creating Knowledge Base**
```bash
# Add working hours
curl -X POST "http://localhost:8080/api/ingest/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "We are open Monday-Friday 09:00-18:00"}'

# Add contact information
curl -X POST "http://localhost:8080/api/ingest/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Call 444-1234 for support"}'

# Add product information
curl -X POST "http://localhost:8080/api/ingest/url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://company.com/products"}'
```

### 2. **Customer Chat**
```bash
# Question 1
curl -X POST "http://localhost:8080/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What time do you open?"}'

# Question 2  
curl -X POST "http://localhost:8080/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your support number?"}'
```

### 3. **System Management**
```bash
# Status check
curl http://localhost:8080/api/stats

# Cleanup (if needed)
curl -X DELETE http://localhost:8080/api/clear
```

## Getting Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key" button
3. Copy the API key and add it to `.env` file

## Technical Details

- **Framework**: FastAPI
- **Vector DB**: ChromaDB
- **AI Model**: Gemini 2.0flash + Embedding-001
- **Chunk Size**: 1000 characters (200 overlap)
- **Similarity Search**: Cosine similarity

## Development

You can access API documentation at `http://localhost:8000/docs`.
