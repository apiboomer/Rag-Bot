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
    title="Müşteri Temsilcisi API",
    description="RAG tabanlı müşteri temsilcisi sistemi",
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
    return {"message": "Müşteri Temsilcisi API'sine hoş geldiniz!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "collection_count": collection.count()}

@app.post("/api/ingest/text")
async def ingest_text(request: IngestRequest):
    """Metin içeriği veritabanına ekle"""
    try:
        # Text'i chunk'lara böl
        chunks = chunk_text(request.text)
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Embedding oluştur
            embedding = generate_embedding(chunk)
            
            # Metadata hazırla
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
        
        # ChromaDB'ye ekle
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "message": "Metin başarıyla eklendi",
            "chunks_added": len(chunks),
            "total_documents": collection.count()
        }
        
    except Exception as e:
        logger.error(f"Text ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest/url")
async def ingest_url(request: URLIngestRequest):
    """URL içeriğini veritabanına ekle"""
    try:
        # URL'den içerik çek
        content = fetch_url_content(request.url)
        
        # Text'i chunk'lara böl
        chunks = chunk_text(content)
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Embedding oluştur
            embedding = generate_embedding(chunk)
            
            # Metadata hazırla
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
        
        # ChromaDB'ye ekle
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "message": "URL içeriği başarıyla eklendi",
            "url": request.url,
            "chunks_added": len(chunks),
            "total_documents": collection.count()
        }
        
    except Exception as e:
        logger.error(f"URL ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Dosya içeriğini veritabanına ekle"""
    try:
        # Dosya içeriğini oku
        content = await file.read()
        
        # Sadece text dosyalarını destekle
        if file.content_type not in ["text/plain", "application/pdf"]:
            raise HTTPException(
                status_code=400, 
                detail="Sadece text (.txt) dosyaları desteklenmektedir"
            )
        
        # Text'e çevir
        if file.content_type == "text/plain":
            text_content = content.decode('utf-8')
        else:
            # PDF desteği için ek kütüphane gerekir
            raise HTTPException(
                status_code=400, 
                detail="PDF desteği henüz eklenmemiştir"
            )
        
        # Text'i chunk'lara böl
        chunks = chunk_text(text_content)
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Embedding oluştur
            embedding = generate_embedding(chunk)
            
            # Metadata hazırla
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
        
        # ChromaDB'ye ekle
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "message": "Dosya başarıyla eklendi",
            "filename": file.filename,
            "chunks_added": len(chunks),
            "total_documents": collection.count()
        }
        
    except Exception as e:
        logger.error(f"File ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Müşteri ile sohbet et"""
    try:
        # Kullanıcı sorusu için embedding oluştur
        query_embedding = generate_embedding(request.message)
        
        # Benzer dökümanları ara
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=["documents", "metadatas", "distances"]
        )
        
        # Context oluştur
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
        
        # Prompt oluştur
        prompt = f"""Sen bir müşteri temsilcisisin. Aşağıdaki bilgi bankasını kullanarak müşterinin sorusunu yanıtla.
        
Bilgi Bankası:
{context}

Müşteri Sorusu: {request.message}

Lütfen:
1. Türkçe yanıt ver
2. Yardımsever ve profesyonel ol
3. Sadece bilgi bankasındaki bilgileri kullan
4. Eğer bilgi bankasında cevap yoksa, bunu belirt ve yardım için başka bir yol öner
5. Kısa ve net yanıt ver

Yanıt:"""

        # Gemini'den yanıt al
        response_text = generate_response(prompt)
        
        # Conversation ID oluştur
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
    """Sistem istatistikleri"""
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
    """Veritabanını temizle (dikkatli kullanın!)"""
    try:
        # Koleksiyonu sil ve yeniden oluştur
        chroma_client.delete_collection(name="customer_support_kb")
        global collection
        collection = chroma_client.get_or_create_collection(
            name="customer_support_kb",
            metadata={"hnsw:space": "cosine"}
        )
        
        return {"message": "Veritabanı başarıyla temizlendi"}
        
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
