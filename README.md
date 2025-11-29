# 🚨 Patrol-X

> **Transforming chaotic public messages into clear, structured AI-generated alerts for Haiti**

Patrol-X turns chaotic public messages from WhatsApp, Telegram, and social media into clear, structured AI-generated alerts to help Haitians understand what is happening, where, and how serious it is—instantly.

---

## 🎯 Overview

Patrol-X is an intelligent real-time information analysis system that:
- **Collects** content from multiple sources (WhatsApp, Telegram, Twitter, RSS)
- **Filters** relevance using AI
- **Summarizes** key points
- **Suggests** appropriate actions
- **Helps** users make informed and rapid decisions

---

## 🏗️ Architecture

```
Sources (WhatsApp/Telegram)
    ↓
Ingestion Layer (Webhooks/APIs)
    ↓
Pre-Processing (DeepSeek-V3: Filtering & Normalization)
    ↓
AI Analysis (GPT-OSS-120B: Event Extraction)
    ↓
Decision Engine (Rules + Thresholds)
    ↓
Dashboard + Notifications + Chatbot
    ↓
Storage (MongoDB) + Logs
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- MongoDB Atlas account (or local MongoDB)
- HuggingFace API token

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
   ```bash
   # Create .env file
   export HF_TOKEN=your_huggingface_token
   export DB_USERNAME=your_mongodb_username
   export DB_PASSWORD=your_mongodb_password
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

### Process Messages
```bash
POST /messages
```
Processes raw messages and converts them into structured events.

### Get Latest Events
```bash
GET /events/latest
```
Retrieves the latest events from the database.

### Get Location Summary
```bash
GET /events/location/<location>
```
Gets AI-generated summary for a specific location.

### Chat Assistant
```bash
POST /chat
```
AI assistant that answers questions about events using RAG.

**📖 Full API Documentation**: See [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)

---

## 📁 Project Structure

```
PatrolX/
├── api/                    # API application
│   ├── app.py             # Flask application entry point
│   ├── services.py        # AI services (preprocessing, analysis)
│   ├── utils.py           # Utility functions
│   ├── db/                # Database models
│   │   └── models.py      # MongoDB models
│   └── prompts/           # AI prompts
│       └── system/        # System prompts for AI models
├── docs/                  # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── API_QUICK_REFERENCE.md
│   ├── patrol-x-specification.md
│   └── PatrolX_API.postman_collection.json
├── data/                  # Test data
│   └── whatsapp_*.json    # Sample message files
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment config
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

---

## 🤖 AI Models Used

- **DeepSeek-V3**: Preprocessing and summarization
- **GPT-OSS-120B**: Deep analysis and event extraction

---

## 🧪 Testing

### Using Postman
Import the collection from `docs/PatrolX_API.postman_collection.json`

### Using cURL

**Process messages:**
```bash
curl -X POST http://localhost:5000/messages \
  -H "Content-Type: application/json" \
  -d @data/whatsapp_messages.json
```

**Get location summary:**
```bash
curl http://localhost:5000/events/location/Delmas
```

**Chat:**
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Kisa k ap pase nan Delmas?"}'
```

---

## 🌍 Supported Locations

### Hierarchical (include subdivisions)
- **Delmas** (includes Delmas 1-110, Delmas 19, Delmas 33, etc.)
- **Tabarre**, **Martissant**, **Pelerin**

### Non-Hierarchical (treated separately)
- **Carrefour** ≠ Carrefour Drouillard ≠ Carrefour Feuilles
- **Pétion-Ville**, **Croix-des-Bouquets**, **Kenscoff**, **Thomassin**

---

## 📊 Data Flow

1. **Ingestion**: Raw messages from sources
2. **Preprocessing**: Filter, normalize, extract hints (DeepSeek-V3)
3. **Analysis**: Generate structured events (GPT-OSS-120B)
4. **Storage**: Save to MongoDB
5. **Query**: Retrieve and summarize by location
6. **Chat**: Answer questions using RAG

---

## 🔧 Configuration

### Environment Variables
- `HF_TOKEN`: HuggingFace API token
- `DB_USERNAME`: MongoDB username
- `DB_PASSWORD`: MongoDB password

### MongoDB Collections
- `events`: Structured events
- `processed_messages`: Preprocessed messages

---

## 🚢 Deployment

### Vercel
The project is configured for Vercel deployment. See `vercel.json`.

### Local Development
```bash
cd api
python app.py
```

---

## 📝 License

This project is part of a hackathon submission.

---

## 👥 Team

Patrol-X Team - Hackathon 2025

---

## 🙏 Acknowledgments

Built for the people of Haiti 🇭🇹

**Patrol-X** - Turning chaos into clarity

