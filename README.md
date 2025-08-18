# Müşteri Temsilcisi API

RAG (Retrieval-Augmented Generation) tabanlı müşteri temsilcisi sistemi. Gemini AI ve ChromaDB kullanarak akıllı soru-cevap sistemi sağlar.

## Özellikler

- **RAG Pipeline**: Döküman ekleme ve akıllı soru-cevap
- **Çoklu İçerik Desteği**: Metin, URL ve dosya yükleme
- **Vektör Arama**: ChromaDB ile hızlı benzerlik araması
- **Türkçe Destek**: Müşteri temsilcisi Türkçe yanıtlar verir
- **Kaynak Gösterimi**: Yanıtların hangi kaynaklardan geldiğini gösterir

## Kurulum

1. **Bağımlılıkları yükleyin:**
```bash
pip install -r requirements.txt
```

2. **Environment variables ayarlayın:**
```bash
cp .env.example .env
```

`.env` dosyasını düzenleyip gerekli bilgileri ekleyin:

**Bulut ChromaDB için:**
```
GEMINI_API_KEY=your_actual_api_key_here
CHROMA_HOST=your_chroma_cloud_host
CHROMA_PORT=443
CHROMA_API_KEY=your_chroma_api_key
```

**Yerel ChromaDB için:**
```
GEMINI_API_KEY=your_actual_api_key_here
# CHROMA_HOST değişkenini boş bırakın veya silin
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

3. **API'yi başlatın:**
```bash
python main.py
```

API `http://localhost:8000` adresinde çalışacaktır.

## API Endpoints

### Döküman Ekleme

- **POST** `/api/ingest/text` - Metin içeriği ekle
- **POST** `/api/ingest/url` - URL içeriğini ekle  
- **POST** `/api/ingest/file` - Dosya yükle (.txt)

### Sohbet

- **POST** `/api/chat` - Müşteri temsilcisi ile sohbet et

### Yönetim

- **GET** `/api/stats` - Sistem istatistikleri
- **DELETE** `/api/clear` - Veritabanını temizle
- **GET** `/health` - Sağlık kontrolü

## API Endpoint'leri Detaylı Kullanım

### 🏠 Ana Sayfa
```bash
GET /
```
**Açıklama**: API'nin çalışıp çalışmadığını kontrol eder.
```bash
curl http://localhost:8080/
```
**Yanıt**:
```json
{"message": "Müşteri Temsilcisi API'sine hoş geldiniz!"}
```

### 🔍 Sağlık Kontrolü
```bash
GET /health
```
**Açıklama**: API durumu ve veritabanındaki döküman sayısını gösterir.
```bash
curl http://localhost:8080/health
```
**Yanıt**:
```json
{
  "status": "healthy",
  "collection_count": 15
}
```

### 📝 Metin İçeriği Ekleme
```bash
POST /api/ingest/text
```
**Açıklama**: Düz metin içeriğini vektör veritabanına ekler.

**İstek Formatı**:
```json
{
  "text": "string",
  "metadata": {} // opsiyonel
}
```

**Örnek**:
```bash
curl -X POST "http://localhost:8080/api/ingest/text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Şirketimiz Pazartesi-Cuma 09:00-18:00, Cumartesi 10:00-16:00 saatleri arasında hizmet vermektedir. Pazar günleri kapalıyız.",
    "metadata": {
      "category": "working_hours",
      "department": "customer_service",
      "priority": "high"
    }
  }'
```

**Yanıt**:
```json
{
  "message": "Metin başarıyla eklendi",
  "chunks_added": 1,
  "total_documents": 16
}
```

### 🌐 URL İçeriği Ekleme
```bash
POST /api/ingest/url
```
**Açıklama**: Web sayfasının içeriğini otomatik olarak çeker ve veritabanına ekler.

**İstek Formatı**:
```json
{
  "url": "string",
  "metadata": {} // opsiyonel
}
```

**Örnek**:
```bash
curl -X POST "http://localhost:8080/api/ingest/url" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/sss",
    "metadata": {
      "source": "company_website",
      "type": "faq",
      "last_updated": "2024-01-15"
    }
  }'
```

**Yanıt**:
```json
{
  "message": "URL içeriği başarıyla eklendi",
  "url": "https://example.com/sss",
  "chunks_added": 5,
  "total_documents": 21
}
```

### 📄 Dosya Yükleme
```bash
POST /api/ingest/file
```
**Açıklama**: Text dosyası (.txt) yükleyerek içeriğini veritabanına ekler.

**Örnek**:
```bash
curl -X POST "http://localhost:8080/api/ingest/file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/document.txt"
```

**Yanıt**:
```json
{
  "message": "Dosya başarıyla eklendi",
  "filename": "document.txt",
  "chunks_added": 3,
  "total_documents": 24
}
```

### 💬 Müşteri Sohbeti
```bash
POST /api/chat
```
**Açıklama**: RAG sistemi kullanarak müşteri sorularını yanıtlar.

**İstek Formatı**:
```json
{
  "message": "string",
  "conversation_id": "string" // opsiyonel
}
```

**Örnek**:
```bash
curl -X POST "http://localhost:8080/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Cumartesi günü açık mısınız?",
    "conversation_id": "conv-123"
  }'
```

**Yanıt**:
```json
{
  "response": "Evet, Cumartesi günleri 10:00-16:00 saatleri arasında hizmet vermekteyiz.",
  "conversation_id": "conv-123",
  "sources": [
    {
      "content": "Şirketimiz Pazartesi-Cuma 09:00-18:00, Cumartesi 10:00-16:00 saatleri arasında...",
      "metadata": {
        "category": "working_hours",
        "chunk_index": 0
      },
      "similarity_score": 0.89
    }
  ]
}
```

### 📊 Sistem İstatistikleri
```bash
GET /api/stats
```
**Açıklama**: Veritabanı durumu ve istatistiklerini gösterir.
```bash
curl http://localhost:8080/api/stats
```
**Yanıt**:
```json
{
  "total_documents": 24,
  "collection_name": "customer_support_kb",
  "status": "active"
}
```

### 🗑️ Veritabanını Temizle
```bash
DELETE /api/clear
```
**Açıklama**: Tüm dökümanları siler (DİKKATLİ KULLANIN!).
```bash
curl -X DELETE http://localhost:8080/api/clear
```
**Yanıt**:
```json
{
  "message": "Veritabanı başarıyla temizlendi"
}
```

## Kullanım Senaryoları

### 1. **Bilgi Bankası Oluşturma**
```bash
# Çalışma saatleri ekle
curl -X POST "http://localhost:8080/api/ingest/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Pazartesi-Cuma 09:00-18:00 açığız"}'

# İletişim bilgileri ekle
curl -X POST "http://localhost:8080/api/ingest/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Destek için 444-1234 numarasını arayın"}'

# Ürün bilgileri ekle
curl -X POST "http://localhost:8080/api/ingest/url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://company.com/products"}'
```

### 2. **Müşteri Sohbeti**
```bash
# Soru 1
curl -X POST "http://localhost:8080/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Kaçta açıksınız?"}'

# Soru 2  
curl -X POST "http://localhost:8080/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Destek numaranız nedir?"}'
```

### 3. **Sistem Yönetimi**
```bash
# Durum kontrol
curl http://localhost:8080/api/stats

# Temizlik (gerekirse)
curl -X DELETE http://localhost:8080/api/clear
```

## Gemini API Key Alma

1. [Google AI Studio](https://makersuite.google.com/app/apikey)'ya gidin
2. "Create API Key" butonuna tıklayın
3. API key'i kopyalayıp `.env` dosyasına ekleyin

## Teknik Detaylar

- **Framework**: FastAPI
- **Vektör DB**: ChromaDB
- **AI Model**: Gemini 1.5 Pro + Embedding-001
- **Chunk Size**: 1000 karakter (200 overlap)
- **Similarity Search**: Cosine similarity

## Geliştirme

API dokümantasyonuna `http://localhost:8000/docs` adresinden erişebilirsiniz.
