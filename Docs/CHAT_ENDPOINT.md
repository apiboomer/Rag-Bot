# 💬 Chat Endpoint Kullanımı

## Endpoint
```
POST /api/chat
URL: http://localhost:8080/api/chat
```

## İstek Formatı
```json
{
  "message": "Kullanıcının sorusu"
}
```

## Yanıt Formatı
```json
{
  "response": "Müşteri temsilcisinin yanıtı",
  "conversation_id": "sohbet-id",
  "sources": [...]
}
```

## Kullanım Örneği

### Soru Sor
```bash
curl -X POST "http://localhost:8080/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Kaçta açıksınız?"}'
```

### Yanıt
```json
{
  "response": "Pazartesi-Cuma 09:00-18:00 saatleri arasında hizmet vermekteyiz.",
  "conversation_id": "abc-123",
  "sources": [
    {
      "content": "Pazartesi-Cuma 09:00-18:00 açığız",
      "similarity_score": 0.92
    }
  ]
}
```

## Nasıl Çalışır?
1. Sorunuz vektöre çevrilir
2. ChromaDB'de benzer bilgiler aranır
3. Gemini AI yanıt üretir
4. Kaynaklarla birlikte döndürülür
