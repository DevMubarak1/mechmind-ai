# MechMind AI 🏗️🤖

AI-Powered Construction Equipment Diagnostics via WhatsApp + IoT

## Architecture

```
ESP32 Sensor Node → FastAPI Backend → Ollama AI → Baileys WhatsApp Bot
                         ↓
              PostgreSQL + ChromaDB (Docker)
                         ↓
              Next.js Dashboard (Vercel)
```

## Quick Start

### 1. Start databases
```bash
docker-compose up -d
```

### 2. Start backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 3. Start WhatsApp bot
```bash
cd whatsapp-bot
npm install
node index.js
# Scan QR code with WhatsApp
```

### 4. Start Ollama
```bash
ollama serve
ollama pull llama3.1:8b
```

## Team
- **Mubarak** — AI/Software (Backend, WhatsApp bot, Dashboard)
- **Olawale** — Hardware (ESP32, sensors, firmware, enclosure)
- **Ramadan** — Documentation (Proposal, demo video)

## Tech Stack (Zero Cost)
| Component | Technology |
|-----------|-----------|
| AI/LLM | Ollama (Llama 3.1 8B) |
| WhatsApp | Baileys (open-source) |
| Voice STT | faster-whisper (local) |
| Backend | FastAPI (Python) |
| Database | PostgreSQL (Docker) |
| Vector DB | ChromaDB (Docker) |
| Dashboard | Next.js (Vercel) |

## License
Proprietary — 15th China Innovation & Entrepreneurship Competition
