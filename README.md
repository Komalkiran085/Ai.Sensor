# 🛡️ SafetyAI — Industrial Safety Command Centre

**AI-Powered Compound Risk Detection for Industrial Plants**

An intelligent multi-agent system that correlates gas sensor readings, work permit activity, shift patterns, and historical incidents to detect dangerous combinations **before** they become fatal — addressing the root cause behind incidents like the 2025 Vizag Steel Plant tragedy.

## The Problem

Workers die in industrial plants not because safety equipment is missing, but because **signals exist in silos**. Gas sensors, permit systems, SCADA, and shift logs never talk to each other. A single sensor reading may look normal — but combined with an active confined space permit and an upcoming shift changeover, it becomes **lethal**.

> **6,500+ fatal workplace accidents in FY2023 in India alone.**

## The Solution

SafetyAI is a **compound risk detection engine** that fuses multiple data streams in real-time and fires intelligent alerts when dangerous combinations are detected — even when each individual signal appears normal.

### Key Features

- **Compound Risk Detection Engine** — Multi-agent system correlating gas sensors, permits, shift patterns
- **Geospatial Safety Heatmap** — Real-time plant map that visualizes risk zones dynamically
- **AI-Powered Alerts** — Claude API generates natural language explanations of compound risks
- **Digital Permit Intelligence** — Flags dangerous simultaneous operations automatically
- **Incident Report Generation** — Auto-generates regulatory-compliant reports (OISD/Factory Act)
- **Single-Sensor vs Compound Comparison** — Proves the system catches what traditional monitoring misses

## Architecture

```
Data Sources (Sensors, Permits, Shifts)
         ↓
   Data Simulator Layer
         ↓
┌──────────────────────────┐
│    INTELLIGENCE ENGINE   │
│  Risk Scorer + Threshold │
│  Compound Risk Detector  │
└──────────────────────────┘
         ↓
   Claude AI (Alert + Report)
         ↓
┌──────────────────────────┐
│   WebSocket Real-Time    │
│   React Dashboard        │
│   Plant Heatmap + Alerts │
└──────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Vite + Tailwind | Enterprise dashboard UI |
| Backend | FastAPI (Python) | Async API + WebSocket |
| AI | Claude API (Anthropic) | Intelligent alerts + reports |
| Database | PostgreSQL | Persistent storage |
| Cache | Redis | Pub/sub + caching |
| Deployment | Docker Compose | One-command startup |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### Run with Docker

```bash
# 1. Clone and enter directory
cd AiSensor

# 2. Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Start everything
docker compose up --build

# 4. Open browser
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

### Run without Docker (Development)

```bash
# Terminal 1 — Database
docker run -d --name safety_db -e POSTGRES_USER=safety -e POSTGRES_PASSWORD=safety123 -e POSTGRES_DB=industrial_safety -p 5432:5432 postgres:15

# Terminal 2 — Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env  # Add your API key
uvicorn main:app --reload --port 8000

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
```

## Demo Scenario

Click **"Trigger Vizag Scenario"** to simulate the 2025 Vizag Steel Plant conditions:

1. **T+0:00** — All zones green, normal operations
2. **T+0:30** — CO in Battery 3 starts rising slowly
3. **T+1:00** — A confined space entry permit is active in Battery 3
4. **T+1:30** — AI flags compound risk: gas + permit + shift changeover
5. **T+2:00** — CO crosses critical threshold
6. **T+2:30** — Full AI alert with explanation fires
7. **Safety officer clicks "Suspend Permit"** — crisis averted

### The Key Insight

A **single gas sensor** at 38 ppm shows "within acceptable range — no alarm."

Our **compound system** at the same 38 ppm + confined space permit + shift changeover = **CRITICAL RISK**.

This directly demonstrates **false negative rate reduction** — the metric that saves lives.

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/health` | Health check |
| GET | `/api/zones` | All plant zones |
| GET | `/api/sensors` | Current sensor readings |
| GET | `/api/permits` | Active work permits |
| GET | `/api/risks` | Current zone risk scores |
| GET | `/api/alerts` | All fired alerts |
| GET | `/api/shift` | Current shift info |
| POST | `/api/permits/{id}/suspend` | Suspend a permit |
| POST | `/api/report/{zone}` | Generate AI incident report |
| POST | `/api/demo/trigger-vizag` | Start Vizag scenario |
| POST | `/api/demo/reset` | Reset to normal |
| WS | `/ws` | Real-time data stream |

## Judging Criteria Alignment

| Criteria | Weight | How We Address It |
|----------|--------|-------------------|
| Business Impact | 25% | Prevents fatalities, reduces false negatives, deployable in real plants |
| Technical Excellence | 25% | Multi-agent architecture, real-time WebSocket, Claude AI integration |
| Scalability | 20% | Docker, PostgreSQL, zone-based architecture scales to any plant size |
| User Experience | 15% | Real-time heatmap, one-click permit suspension, AI-generated reports |
| Innovation | 15% | Compound risk detection — danger isn't one signal, it's a combination |

## License

MIT
"# Ai.Sensor" 
