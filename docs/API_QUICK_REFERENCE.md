# Patrol-X API - Quick Reference Card

## 🚀 Endpoints at a Glance

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/messages` | Process raw messages → structured events |
| `GET` | `/events/latest` | Get latest events |
| `GET` | `/events/location/<location>` | Get location summary |
| `POST` | `/chat` | Ask questions about events |

---

## 📤 POST /messages

**Input:** Raw messages from WhatsApp/Telegram  
**Output:** Structured events saved to DB

```bash
curl -X POST http://localhost:5000/messages \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "text": "Barikad nan Delmas 33!",
      "source": "whatsapp",
      "timestamp": "2025-01-15T10:30:00Z"
    }]
  }'
```

---

## 📥 GET /events/location/Delmas

**Input:** Location name  
**Output:** AI-generated summary

```bash
curl http://localhost:5000/events/location/Delmas
```

---

## 💬 POST /chat

**Input:** User question  
**Output:** AI answer based on events

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Kisa k ap pase nan Delmas?"}'
```

---

## 🎯 Hackathon Demo Flow

1. **Ingest Messages** → `POST /messages`
2. **Check Location** → `GET /events/location/Delmas`
3. **Ask Questions** → `POST /chat`

---

## 📍 Common Locations

- `Delmas` (includes all Delmas subdivisions)
- `Martissant`
- `Pétion-Ville`
- `Tabarre`
- `Carrefour`

---

## ⚡ Quick Test

```bash
# 1. Process messages
curl -X POST http://localhost:5000/messages \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"text":"Test","source":"whatsapp","timestamp":"2025-01-15T10:00:00Z"}]}'

# 2. Get summary
curl http://localhost:5000/events/location/Delmas

# 3. Chat
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Kisa k ap pase?"}'
```

