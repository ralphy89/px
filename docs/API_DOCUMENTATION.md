# Patrol-X API Documentation

## 🎯 Overview

Patrol-X transforms chaotic public messages from WhatsApp, Telegram, and social media into clear, structured AI-generated alerts to help Haitians understand what is happening, where, and how serious it is—instantly.

**Base URL**: `http://your-server-url/api`

---

## 📋 Table of Contents

1. [Endpoints](#endpoints)
   - [POST /messages](#post-messages)
   - [GET /events/latest](#get-eventslatest)
   - [GET /events/location/<location>](#get-eventslocationlocation)
   - [POST /chat](#post-chat)
2. [Data Structures](#data-structures)
3. [Error Handling](#error-handling)
4. [Example Workflows](#example-workflows)

---

## 🔌 Endpoints

### POST /messages

Processes raw messages from social media sources and converts them into structured events.

**Request:**
```json
{
  "messages": [
    {
      "text": "Barikad nan Delmas 33, wout bloke!",
      "source": "whatsapp",
      "timestamp": "2025-01-15T10:30:00Z",
      "metadata": {}
    },
    {
      "text": "Yo tire nan Martissant, pran prekosyon!",
      "source": "telegram",
      "timestamp": "2025-01-15T10:35:00Z",
      "metadata": {}
    }
  ]
}
```

**Response (Success):**
```json
{
  "status": "ok",
  "Message": "Event save successfully"
}
```

**Response (Error):**
```json
{
  "error": "Event not saved"
}
```

**Status Codes:**
- `200 OK` - Messages processed and events saved successfully
- `400 Bad Request` - Invalid request format
- `500 Internal Server Error` - Processing or database error

**Processing Flow:**
1. **Preprocessing** (DeepSeek-V3): Filters, normalizes, and extracts hints from messages
2. **Analysis** (GPT-OSS-120B): Generates structured events grouped by cluster_id
3. **Storage**: Saves events to MongoDB

---

### GET /events/latest

Retrieves the latest events from the database.

**Request:**
```
GET /events/latest
```

**Response:**
```json
{
  "status": "ok",
  "Events": [
    {
      "event_type": "roadblock",
      "severity": "high",
      "priority": "urgent",
      "timestamp_start": "2025-01-15T10:30:00Z",
      "timestamp_end": null,
      "probability": 0.9,
      "location": "Delmas 33",
      "summary": "Roadblock reported near Delmas 33, route blocked.",
      "recommended_action": "Evite zòn nan. Pran yon lot traje.",
      "sources_count": 3,
      "messages_used": ["msg1", "msg2", "msg3"],
      "cluster_id": "delmas33_block"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Success
- `404 Not Found` - Invalid method (must be GET)

---

### GET /events/location/<location>

Gets events and generates an AI-powered summary for a specific location.

**Request:**
```
GET /events/location/Delmas
GET /events/location/Martissant
GET /events/location/Pétion-Ville
```

**Response:**
```json
{
  "status": "ok",
  "summary": "État des lieux :\n\nVoici ce qu'il faut retenir :\n\nSelon les informations disponibles, plusieurs événements ont été signalés dans la zone de Delmas au cours des dernières 24 heures. Des barricades ont été signalées à Delmas 33, bloquant la circulation. Des tirs ont été entendus dans la zone de Delmas 19.\n\nZones concernées : Delmas 33, Delmas 19\n\nSources mentionnées : WhatsApp, Telegram"
}
```

**Response (No Events):**
```json
{
  "status": "ok",
  "summary": "No events detected in the last 24 hours for Delmas. The area appears calm."
}
```

**Status Codes:**
- `200 OK` - Success

**Location Rules:**
- Supports hierarchical locations (e.g., "Delmas" includes "Delmas 33", "Delmas 19", etc.)
- Non-hierarchical locations are treated separately (e.g., "Carrefour" ≠ "Carrefour Drouillard")
- Case-insensitive matching

---

### POST /chat

AI chat assistant that answers questions about events using RAG (Retrieval-Augmented Generation).

**Request:**
```json
{
  "prompt": "Kisa k ap pase nan Delmas jodi a?"
}
```

**Response:**
```json
{
  "status": "ok",
  "answer": "Selon les informations disponibles, plusieurs événements ont été signalés dans la zone de Delmas aujourd'hui. Des barricades ont été signalées à Delmas 33, bloquant la circulation. Des tirs ont été entendus dans la zone de Delmas 19. Il est recommandé d'éviter ces zones et de prendre des routes alternatives si possible."
}
```

**Response (Error):**
```json
{
  "status": "error",
  "answer": "Désolé, je n'ai pas pu traiter votre question. Veuillez réessayer."
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid request format

**Supported Languages:**
- Haitian Creole (ht)
- French (fr)
- English (en)

---

## 📊 Data Structures

### Event Object

```json
{
  "event_type": "roadblock | shooting | insecurity | kidnapping | protest | traffic | accident | weather | fire | other",
  "severity": "critical | high | medium | low",
  "priority": "urgent | high | medium | low",
  "timestamp_start": "2025-01-15T10:30:00Z",
  "timestamp_end": "2025-01-15T11:00:00Z | null",
  "probability": 0.9,
  "location": "Delmas 33",
  "summary": "Clear, factual summary",
  "recommended_action": "Evite zòn nan.",
  "sources_count": 3,
  "messages_used": ["msg_id_1", "msg_id_2"],
  "cluster_id": "delmas33_block"
}
```

### Preprocessed Message Object

```json
{
  "original_text": "Barikad nan Delmas 33!",
  "clean_text": "Barikad nan Delmas 33",
  "is_relevant": true,
  "category_hint": "roadblock",
  "location_hint": "Delmas 33",
  "risk_hint": "high",
  "language": "ht",
  "cluster_id": "delmas33_block",
  "timestamp": "2025-01-15T10:30:00Z",
  "source": "whatsapp"
}
```

### Raw Message Object

```json
{
  "text": "Message content here",
  "source": "whatsapp | telegram | twitter | rss | chatbot",
  "timestamp": "2025-01-15T10:30:00Z",
  "metadata": {}
}
```

---

## ⚠️ Error Handling

### Error Response Format

```json
{
  "error": "Error description",
  "description": "Detailed error message"
}
```

### Common Error Codes

- **400 Bad Request**: Invalid request format, missing required fields, or wrong data types
- **404 Not Found**: Endpoint not found or wrong HTTP method
- **500 Internal Server Error**: Server-side error (processing, database, or AI model error)

### Example Error Responses

**Invalid JSON:**
```json
{
  "error": "Expected JSON body"
}
```

**Missing Required Field:**
```json
{
  "error": "'messages' must be a list"
}
```

**Processing Error:**
```json
{
  "error": "Event not saved"
}
```

---

## 🔄 Example Workflows

### Workflow 1: Processing New Messages

```bash
# Step 1: Send raw messages from WhatsApp/Telegram
curl -X POST http://localhost:5000/messages \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "text": "Barikad nan Delmas 33!",
        "source": "whatsapp",
        "timestamp": "2025-01-15T10:30:00Z",
        "metadata": {}
      }
    ]
  }'

# Response: {"status": "ok", "Message": "Event save successfully"}
```

### Workflow 2: Getting Location Summary

```bash
# Step 1: Query events for a location
curl -X GET http://localhost:5000/events/location/Delmas

# Response: AI-generated summary of events in Delmas
```

### Workflow 3: Chat Assistant

```bash
# Step 1: Ask a question about events
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Kisa k ap pase nan Delmas jodi a?"
  }'

# Response: Natural language answer based on database events
```

### Workflow 4: Get Latest Events

```bash
# Step 1: Retrieve latest events
curl -X GET http://localhost:5000/events/latest

# Response: List of recent events
```

---

## 🌍 Supported Locations (Haiti)

### Hierarchical Locations (include subdivisions)
- **Delmas** (includes Delmas 1-110, Delmas 19, Delmas 33, etc.)
- **Tabarre** (includes Tabarre 19, Tabarre 33, etc.)
- **Martissant** (includes Martissant 19, Martissant 33, etc.)
- **Pelerin** (includes Pelerin 19, Pelerin 33, etc.)

### Non-Hierarchical Locations (treated separately)
- **Carrefour** ≠ Carrefour Drouillard ≠ Carrefour Feuilles
- **Pétion-Ville** (standalone)
- **Croix-des-Bouquets** (standalone)
- **Kenscoff** (standalone)
- **Thomassin** (standalone)

### Other Common Locations
- Route Frère
- Silo
- Canapé-Vert
- Nazon
- Okap (Cap-Haïtien)
- Jérémie

---

## 🚀 Quick Start

### 1. Start the Server

```bash
cd api
python app.py
# or
flask run
```

### 2. Test the API

```bash
# Health check
curl http://localhost:5000/

# Process messages
curl -X POST http://localhost:5000/messages \
  -H "Content-Type: application/json" \
  -d @whatsapp_messages.json

# Get location summary
curl http://localhost:5000/events/location/Delmas

# Chat
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Kisa k ap pase?"}'
```

---

## 📝 Notes

- All timestamps are in ISO 8601 format (UTC)
- Location matching is case-insensitive
- The AI models used:
  - **Preprocessing**: DeepSeek-V3
  - **Analysis**: GPT-OSS-120B
  - **Summary/Chat**: DeepSeek-V3
- Events are automatically grouped by `cluster_id` during analysis
- Only messages with `is_relevant: true` are processed into events

---

## 🔐 Security

- CORS is enabled for all origins (`*`)
- In production, use environment variables for:
  - `HF_TOKEN` (HuggingFace API token)
  - `DB_USERNAME` (MongoDB username)
  - `DB_PASSWORD` (MongoDB password)

---

## 📞 Support

For hackathon support or questions, refer to the project repository or contact the development team.

**Patrol-X** - Turning chaos into clarity for Haiti 🇭🇹

