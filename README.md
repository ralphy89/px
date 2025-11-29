# Patrol-X

> **Transforming chaotic public messages into clear, structured AI-generated alerts for Haiti**

Patrol-X turns chaotic public messages from WhatsApp, Telegram, and social media into clear, structured AI-generated alerts to help Haitians understand what is happening, where, and how serious it is—instantly.

---

## Overview

Patrol-X is an intelligent real-time information analysis system that:
- **Collects** content from multiple sources (WhatsApp, Telegram, Twitter, RSS)
- **Filters** relevance using Grok AI (xAI)
- **Analyzes** and extracts structured events
- **Summarizes** key points with actionable recommendations
- **Notifies** users about critical events automatically
- **Answers** questions through an AI chat assistant
- **Helps** users make informed and rapid decisions

---

## Architecture

```
Sources (WhatsApp/Telegram/Social Media)
    ↓
Ingestion Layer (POST /messages)
    ↓
Pre-Processing (Grok AI: Filtering & Normalization)
    ↓
AI Analysis (Grok AI: Event Extraction)
    ↓
Storage (MongoDB Production)
    ↓
Notification System (Auto-notify for critical/high events)
    ↓
API Endpoints (Events, Chat, Notifications, Auth)
    ↓
User Interface / Mobile App
```

---

## Quick Start

### Prerequisites

- Python 3.8+
- MongoDB Atlas account (production database)
- Grok AI API key from [xAI Console](https://console.x.ai/)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd PatrolX
   ```

2. **Create virtual environment**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   
   Create a `.env` file or set environment variables:
   ```bash
   # Grok AI (xAI) Configuration
   export GROK_TOKEN=your_grok_api_key_from_xai_console
   
   # MongoDB Configuration
   export DB_USERNAME=your_mongodb_username
   export DB_PASSWORD=your_mongodb_password
   
   # JWT Secret (for authentication)
   export JWT_SECRET=your_secure_random_secret_key
   ```

   **Generate JWT_SECRET:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

5. **Run the server**
   ```bash
   cd api
   python app.py
   # or
   flask run
   ```

The API will be available at `http://localhost:5000`

---

## 📡 API Endpoints

### Authentication

#### Sign Up
```bash
POST /auth/signup
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

#### Sign In
```bash
POST /auth/signin
Content-Type: application/json

{
  "username": "johndoe",  # or "email": "john@example.com"
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "status": "ok",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

#### Get Current User
```bash
GET /auth/me
Authorization: Bearer <token>
```

#### Logout
```bash
POST /auth/logout
Authorization: Bearer <token>
```

---

### Events

#### Process Messages
```bash
POST /messages
Content-Type: application/json

{
  "messages": [
    {
      "text": "Barikad nan Delmas 33, wout bloke!",
      "source": "whatsapp",
      "timestamp": "2025-01-15T10:30:00Z",
      "metadata": {}
    }
  ]
}
```

#### Get Latest Events
```bash
GET /events/latest
```

#### Get Events by Location
```bash
GET /events/location/<location>
# Example: GET /events/location/Delmas
```

---

### Chat Assistant

#### Chat with AI
```bash
POST /chat
Content-Type: application/json

{
  "prompt": "Kisa k ap pase nan Delmas jodi a?"
}
```

**Supported Languages:**
- Haitian Creole (ht)
- French (fr)
- English (en)

**Query Types:**
- Location-based: "Kisa k ap pase nan Delmas?"
- Event-type-based: "Ki aksidan ki genyen?"
- General situation: "Koman laria ye la?"
- Time-based: "Ki evenman ki pase yè?"

---

### Notifications

#### Get Notifications
```bash
GET /notifications?unread_only=true&limit=50
Authorization: Bearer <token>
```

**Query Parameters:**
- `unread_only` (boolean): Filter to unread notifications only
- `limit` (integer): Maximum number of notifications (default: 50)

**Response:**
```json
{
  "status": "ok",
  "notifications": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "user_id": "507f1f77bcf86cd799439011",
      "event_id": "507f191e810c19729de860ea",
      "title": "Shooting in Delmas 33",
      "message": "Des tirs ont été signalés...",
      "location": "Delmas 33",
      "event_type": "shooting",
      "severity": "critical",
      "is_read": false,
      "created_at": "2025-01-15T14:30:00.000Z"
    }
  ],
  "unread_count": 5
}
```

#### Mark Notification as Read
```bash
POST /notifications/<notification_id>/read
Authorization: Bearer <token>
```

#### Mark All Notifications as Read
```bash
POST /notifications/read-all
Authorization: Bearer <token>
```

#### Delete Notification
```bash
DELETE /notifications/<notification_id>
Authorization: Bearer <token>
```

**Full API Documentation**: See [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)

---

## Project Structure

```
PatrolX/
├── api/                    # API application
│   ├── __init__.py
│   ├── app.py             # Flask application entry point
│   ├── auth.py            # Authentication logic (JWT, bcrypt)
│   ├── services.py        # AI services (Grok AI integration)
│   ├── utils.py           # Utility functions
│   ├── db/                # Database models
│   │   ├── __init__.py
│   │   └── models.py      # MongoDB models and queries
│   └── prompts/           # AI prompts
│       └── system/        # System prompts for Grok AI
│           ├── deepseek_for_chat.txt
│           ├── deepseek_pretriage.txt
│           ├── gpt_analysis.txt
│           └── gpt_for_chat.txt
├── docs/                  # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── API_QUICK_REFERENCE.md
│   └── patrol-x-specification.md
├── data/                  # Test data
│   └── whatsapp_*.json    # Sample message files
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment config
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

---

## 🤖 AI Models Used

**Grok AI (xAI)** - All AI operations powered by Grok:
- **`grok-4-1-fast-reasoning`**: Deep analysis and event extraction
- **`grok-4-fast-reasoning`**: Preprocessing, chat, and summarization
- **Embeddings API**: For semantic search and RAG (Retrieval-Augmented Generation)

**API Endpoint**: `https://api.x.ai/v1`

Get your API key from: [https://console.x.ai/](https://console.x.ai/)

---

## 🗄️ Database Structure

### MongoDB Collections

#### `events`
Structured events extracted from messages.
```json
{
  "event_type": "shooting | roadblock | kidnapping | protest | traffic | accident | weather | fire | other",
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

#### `processed_messages`
Preprocessed messages before analysis.
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

#### `users`
User accounts for authentication.
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password_hash": "$2b$12$...",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### `sessions`
Active user sessions (JWT tokens).
```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "token": "...",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": "2025-01-22T10:30:00Z"
}
```

#### `notifications`
User notifications for events.
```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "event_id": "507f191e810c19729de860ea",
  "title": "Shooting in Delmas 33",
  "message": "Des tirs ont été signalés...",
  "location": "Delmas 33",
  "event_type": "shooting",
  "severity": "critical",
  "is_read": false,
  "created_at": "2025-01-15T14:30:00.000Z"
}
```

**Database**: MongoDB Atlas Production (`px-prod.amaelqi.mongodb.net`)

---

## 🌍 Supported Locations

### Hierarchical (include subdivisions)
- **Delmas** (includes Delmas 1-110, Delmas 19, Delmas 33, etc.)
- **Tabarre** (includes Tabarre 19, Tabarre 33, etc.)
- **Pétion-Ville** (includes Petionville, Petyonvil, PV)
- **Croix-des-Bouquets** (includes Kwadebouke, Bon Repos)
- **Pèlerin** (includes Pelerin)
- **Thomassin**
- **Canapé-Vert** (includes Kanapevè)
- **Laboule** (includes Laboul)

### Non-Hierarchical (treated separately)
- **Carrefour** ≠ Carrefour Drouillard ≠ Carrefour Feuilles
- **Martissant**
- **Kenscoff**
- **Okap** (Cap-Haïtien)
- **Jérémie**

---

## Data Flow

1. **Ingestion**: Raw messages received via `POST /messages`
2. **Preprocessing**: Filter, normalize, extract hints using Grok AI
3. **Analysis**: Generate structured events using Grok AI
4. **Storage**: Save events to MongoDB production database
5. **Notification**: Automatically create notifications for critical/high severity events
6. **Query**: Retrieve and summarize by location or query type
7. **Chat**: Answer questions using RAG (Retrieval-Augmented Generation) with Grok AI

---

## Configuration

### Environment Variables

| Variable | Description | Required | Where to Get |
|----------|-------------|----------|--------------|
| `GROK_TOKEN` | Grok AI API key | Yes | [xAI Console](https://console.x.ai/) |
| `DB_USERNAME` | MongoDB Atlas username | Yes | MongoDB Atlas Dashboard |
| `DB_PASSWORD` | MongoDB Atlas password | Yes | MongoDB Atlas Dashboard |
| `JWT_SECRET` | Secret key for JWT tokens | Yes | Generate with: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |

### Database Configuration

- **Cluster**: `px-prod.amaelqi.mongodb.net`
- **Database**: `production`
- **Collections**: `events`, `processed_messages`, `users`, `sessions`, `notifications`

---

## Security

### Authentication
- **JWT Tokens**: 7-day expiration
- **Password Hashing**: bcrypt with salt
- **Session Management**: Active sessions tracked in database

### API Security
- **CORS**: Enabled for all origins (configure for production)
- **Token Validation**: All protected endpoints require valid JWT token
- **Password Requirements**: Should be enforced in frontend

---

## Notification System

### Automatic Notifications
- Notifications are automatically created when events are saved
- Only **critical** and **high** severity events trigger notifications
- All active users receive notifications for matching events

### Notification Features
- Read/unread tracking
- Mark individual or all as read
- Delete notifications
- Filter by unread status
- Limit results with pagination

---

## Testing

### Using Postman

1. **Import Collection**: Use the Postman collection from `docs/`
2. **Set Environment Variables**:
   - `base_url`: `http://localhost:5000`
   - `token`: JWT token from sign-in

3. **Test Flow**:
   - Sign up → Sign in → Get token
   - Process messages → Check events
   - Get notifications → Mark as read
   - Chat with AI

### Using cURL

**Sign Up:**
```bash
curl -X POST http://localhost:5000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"test123"}'
```

**Sign In:**
```bash
curl -X POST http://localhost:5000/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}'
```

**Get Notifications:**
```bash
curl -X GET "http://localhost:5000/notifications?unread_only=true" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Process Messages:**
```bash
curl -X POST http://localhost:5000/messages \
  -H "Content-Type: application/json" \
  -d @data/whatsapp_messages.json
```

**Chat:**
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Kisa k ap pase nan Delmas?"}'
```

---

## Deployment

### Local Development
```bash
cd api
python app.py
# or
flask run
```

### Production Deployment

1. **Set Environment Variables** in your hosting platform:
   - `GROK_TOKEN` (from xAI Console)
   - `DB_USERNAME` (MongoDB Atlas)
   - `DB_PASSWORD` (MongoDB Atlas)
   - `JWT_SECRET` (generate secure random key)

2. **Vercel Deployment**:
   - The project includes `vercel.json` configuration
   - Deploy using Vercel CLI or dashboard

3. **Database**: Ensure MongoDB Atlas cluster is accessible from deployment environment

---

## Troubleshooting

### Common Issues

1. **Grok AI API Error**
   - Verify `GROK_TOKEN` is set correctly
   - Check API key permissions at [console.x.ai](https://console.x.ai/)
   - Verify API quota/limits

2. **MongoDB Connection Error**
   - Check `DB_USERNAME` and `DB_PASSWORD` environment variables
   - Verify MongoDB Atlas IP whitelist
   - Check network connectivity

3. **JWT Token Invalid**
   - Check `JWT_SECRET` is set
   - Verify token hasn't expired (7 days)
   - Ensure token is sent in `Authorization: Bearer <token>` header

4. **Notifications Not Created**
   - Verify events have `severity` of `critical` or `high`
   - Check that users exist and are active
   - Verify database connection

---

## License

This project is part of a hackathon submission.

---

## Team

Patrol-X Team - Hackathon 2025

---

## Acknowledgments

Built for the people of Haiti 🇭🇹

**Patrol-X** - Turning chaos into clarity
