from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uuid
from typing import List, Optional
import aiofiles
import requests
from io import BytesIO
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Customer Representative API",
    description="RAG-based customer representative system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize ChromaDB
chroma_host = os.getenv("CHROMA_HOST")
chroma_port = os.getenv("CHROMA_PORT", "8000")
chroma_api_key = os.getenv("CHROMA_API_KEY")

if chroma_host:
    # Cloud ChromaDB
    if chroma_api_key:
        # Authenticated cloud instance
        chroma_client = chromadb.HttpClient(
            host=chroma_host,
            port=int(chroma_port),
            headers={"Authorization": f"Bearer {chroma_api_key}"}
        )
    else:
        # Non-authenticated cloud instance
        chroma_client = chromadb.HttpClient(
            host=chroma_host,
            port=int(chroma_port)
        )
    logger.info(f"Connected to ChromaDB cloud at {chroma_host}:{chroma_port}")
else:
    # Local ChromaDB
    chroma_client = chromadb.PersistentClient(
        path=os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    )
    logger.info("Using local ChromaDB")

# Get or create collection
collection = chroma_client.get_or_create_collection(
    name="customer_support_kb",
    metadata={"hnsw:space": "cosine"}
)

# Pydantic models
class IngestRequest(BaseModel):
    text: str
    metadata: Optional[dict] = {}

class URLIngestRequest(BaseModel):
    url: str
    metadata: Optional[dict] = {}

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[dict] = []

# Helper functions
def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Gemini AI"""
    try:
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        raise HTTPException(status_code=500, detail="Embedding generation failed")

def generate_response(prompt: str) -> str:
    """Generate response using Gemini AI"""
    try:
        model = genai.GenerativeModel('gemma-3-27b-it')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        raise HTTPException(status_code=500, detail="Response generation failed")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > start + chunk_size // 2:
                chunk = text[start:break_point + 1]
                end = break_point + 1
        
        chunks.append(chunk.strip())
        start = end - overlap
        
        if start >= len(text):
            break
    
    return chunks

def fetch_url_content(url: str) -> str:
    """Fetch content from URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"URL fetch error: {e}")
        raise HTTPException(status_code=400, detail=f"URL fetch failed: {str(e)}")

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to Customer Representative API!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "collection_count": collection.count()}

@app.post("/api/ingest/text")
async def ingest_text(request: IngestRequest):
    """Add text content to database"""
    try:
        # Split text into chunks
        chunks = chunk_text(request.text)
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = generate_embedding(chunk)
            
            # Prepare metadata
            metadata = {
                **request.metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source_type": "text"
            }
            
            documents.append(chunk)
            embeddings.append(embedding)
            metadatas.append(metadata)
            ids.append(str(uuid.uuid4()))
        
        # Add to ChromaDB
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "message": "Text added successfully",
            "chunks_added": len(chunks),
            "total_documents": collection.count()
        }
        
    except Exception as e:
        logger.error(f"Text ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest/url")
async def ingest_url(request: URLIngestRequest):
    """Add URL content to database"""
    try:
        # Fetch content from URL
        content = fetch_url_content(request.url)
        
        # Split text into chunks
        chunks = chunk_text(content)
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = generate_embedding(chunk)
            
            # Prepare metadata
            metadata = {
                **request.metadata,
                "url": request.url,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source_type": "url"
            }
            
            documents.append(chunk)
            embeddings.append(embedding)
            metadatas.append(metadata)
            ids.append(str(uuid.uuid4()))
        
        # Add to ChromaDB
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "message": "URL content added successfully",
            "url": request.url,
            "chunks_added": len(chunks),
            "total_documents": collection.count()
        }
        
    except Exception as e:
        logger.error(f"URL ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Add file content to database"""
    try:
        # Read file content
        content = await file.read()
        
        # Only support text files
        if file.content_type not in ["text/plain", "application/pdf"]:
            raise HTTPException(
                status_code=400, 
                detail="Only text (.txt) files are supported"
            )
        
        # Convert to text
        if file.content_type == "text/plain":
            text_content = content.decode('utf-8')
        else:
            # Additional library needed for PDF support
            raise HTTPException(
                status_code=400, 
                detail="PDF support has not been added yet"
            )
        
        # Split text into chunks
        chunks = chunk_text(text_content)
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = generate_embedding(chunk)
            
            # Prepare metadata
            metadata = {
                "filename": file.filename,
                "content_type": file.content_type,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source_type": "file"
            }
            
            documents.append(chunk)
            embeddings.append(embedding)
            metadatas.append(metadata)
            ids.append(str(uuid.uuid4()))
        
        # Add to ChromaDB
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "message": "File added successfully",
            "filename": file.filename,
            "chunks_added": len(chunks),
            "total_documents": collection.count()
        }
        
    except Exception as e:
        logger.error(f"File ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with customer"""
    try:
        # Generate embedding for user question
        query_embedding = generate_embedding(request.message)
        
        # Search for similar documents
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=["documents", "metadatas", "distances"]
        )
        
        # Create context
        context_docs = []
        sources = []
        
        if results['documents'] and results['documents'][0]:
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                context_docs.append(doc)
                sources.append({
                    "content": doc[:200] + "..." if len(doc) > 200 else doc,
                    "metadata": metadata,
                    "similarity_score": 1 - distance  # Convert distance to similarity
                })
        
        context = "\n\n".join(context_docs)
        
        # Create prompt
        prompt = f"""You are a customer representative. Answer the customer's question using the knowledge base below.
        
Knowledge Base:
{context}

Customer Question: {request.message}

Please:
1. Respond in English
2. Be helpful and professional
3. Only use information from the knowledge base
4. If the answer is not in the knowledge base, state this and suggest another way to get help
5. Give short and clear answers

Response:"""

        # Get response from Gemini
        response_text = generate_response(prompt)
        
        # Create conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """System statistics"""
    try:
        total_docs = collection.count()
        return {
            "total_documents": total_docs,
            "collection_name": collection.name,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/clear")
async def clear_database():
    """Clear database (use with caution!)"""
    try:
        # Delete collection and recreate
        chroma_client.delete_collection(name="customer_support_kb")
        global collection
        collection = chroma_client.get_or_create_collection(
            name="customer_support_kb",
            metadata={"hnsw:space": "cosine"}
        )
        
        return {"message": "Database cleared successfully"}
        
    except Exception as e:
        logger.error(f"Clear database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
