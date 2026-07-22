# 🛡️ SafetyAI — Industrial Safety Command Centre

**AI-Powered Compound Risk Detection for Industrial Plants**

An intelligent multi-agent system that correlates gas sensor readings, work permit activity, shift patterns, and historical incidents to detect dangerous combinations **before** they become fatal — addressing the root cause behind incidents like the 2025 Vizag Steel Plant tragedy.

## The Problem

Workers die in industrial plants not because safety equipment is missing, but because **signals exist in silos**. Gas sensors, permit systems, SCADA, and shift logs never talk to each other. A single sensor reading may look normal — but combined with an active confined space permit and an upcoming shift changeover, it becomes **lethal**.

> **6,500+ fatal workplace accidents in FY2023 in India alone.**

## The Solution

SafetyAI is a **compound risk detection engine** that fuses multiple data streams in real-time and fires intelligent alerts when dangerous combinations are detected — even when each individual signal appears normal.

### Key Features

- **Compound Risk Detection Engine** — Five specialist agents (Gas, Permit, Shift, Compliance, and a Coordinator that combines them) genuinely reason over separate slices of the data instead of one scoring function
- **Trend-based lead time** — the Gas Agent estimates minutes-to-threshold from the actual recent trend in each sensor's readings, not just whether it's over the line right now
- **Geospatial Safety Heatmap** — Real-time plant map, laid out from `plant.config.yaml`, not hardcoded
- **AI-Powered Alerts** — Claude generates natural language explanations and reports
- **Alerts never wait on AI** — a safety alert fires instantly with deterministic text, then upgrades in place once the Claude explanation is ready, so API latency can never delay the actual notification
- **Compliance Agent (RAG)** — retrieves actual regulation clauses relevant to what's happening, instead of an LLM guessing citations from memory
- **Human-in-the-loop actions** — state-changing actions (suspend a permit, evacuate) are proposed automatically but require one click to confirm; everything else is fully automatic
- **Single-Sensor vs Compound Comparison** — Proves the system catches what traditional monitoring misses
- **Pluggable for any plant** — see `docs/SYSTEM_DESIGN.md` §3: standing up a new plant install is a config file, not a code change

## Architecture

See `docs/SYSTEM_DESIGN.md` for the full architecture and database schema (with diagrams). In short:

```
SCADA / Permit / Shift systems  →  Connector adapters (connectors/)
                                          ↓
                              Postgres + TimescaleDB + pgvector
                                          ↓
     Gas · Permit · Shift · Compliance agents  (agents/*_agent.py)
                                          ↓
                      Coordinator Agent  (agents/coordinator.py)
                                          ↓
                 Automation policy → auto action / human-confirm gate
                                          ↓
              WebSocket  →  React dashboard (geospatial heatmap, alerts)
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Vite + Tailwind | Enterprise dashboard UI |
| Backend | FastAPI (Python) | Async API + WebSocket |
| AI (generation) | Claude API | Alert explanations + incident reports |
| AI (retrieval) | BAAI/bge-small-en-v1.5 (local, via sentence-transformers) | Real embeddings for the Compliance and Incident agents |
| Database | PostgreSQL + TimescaleDB + pgvector | Sensor history, permits/zones, regulation embeddings — one instance (see docs/SYSTEM_DESIGN.md §2) |
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
# Terminal 1 — Database (TimescaleDB + pgvector bundled)
docker run -d --name safety_db -e POSTGRES_USER=safety -e POSTGRES_PASSWORD=safety123 -e POSTGRES_DB=industrial_safety -p 5432:5432 timescale/timescaledb-ha:pg16

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

Everything specific to this plant — zones, sensors, thresholds, connectors, which agents
are enabled — lives in `backend/plant.config.yaml`. It's loaded into the database
automatically on startup (`bootstrap.py`); edit it and restart to change what the app
monitors. See `docs/SYSTEM_DESIGN.md` §3.1 for what onboarding a different plant looks like.

## Demo Scenario

Pick a zone in **Demo Controls** and click **"Trigger Scenario"** to simulate a Vizag-style
compound risk building up in that zone (every sensor ramps toward its own configured
"extreme" threshold over ~3 minutes — this works for any zone, not just one hardcoded case):

1. **T+0:00** — All zones green, normal operations
2. **T+0:30** — Gas readings in the selected zone start rising
3. — A confined-space (or other) permit is already active in that zone
4. — The Gas Agent's trend estimate starts reporting a shrinking lead time
5. — Compound risk crosses `warning`, then `critical` — the Coordinator's explanation cites gas + permit + shift factors together
6. — A state-changing action is proposed (e.g. suspend the permit) and **waits for your confirmation** — nothing fires on its own
7. **Safety officer clicks "Confirm"** — crisis averted

### The Key Insight

A **single gas sensor** at 38 ppm shows "within acceptable range — no alarm."

Our **compound system** at the same 38 ppm + confined space permit + shift changeover = **CRITICAL RISK**.

This directly demonstrates **false negative rate reduction** — the metric that saves lives.

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/health` | Health check |
| GET | `/api/plant` | This install's plant identity (from `plant.config.yaml`) |
| GET | `/api/zones` | All plant zones (config-driven layout) |
| GET | `/api/sensors` | Current sensor readings per zone |
| GET | `/api/permits` | Active work permits |
| POST | `/api/permits/{id}/suspend` | Suspend a permit directly |
| GET | `/api/risks` | Current zone risk scores (Coordinator output) |
| GET | `/api/alerts` | Persisted alert history |
| GET | `/api/actions/pending` | Actions awaiting human confirmation |
| POST | `/api/actions/{id}/confirm` | Human-in-loop gateway — confirms a proposed action |
| GET | `/api/shift` | Current shift info |
| POST | `/api/report/{zone_id}` | Generate AI incident report for a zone |
| POST | `/api/demo/trigger-scenario/{zone_id}` | Ramp a zone's sensors toward their extreme thresholds (demo only) |
| POST | `/api/demo/reset` | Reset to normal |
| WS | `/ws` | Real-time data stream |

## Judging Criteria Alignment

| Criteria | Weight | How We Address It |
|----------|--------|-------------------|
| Innovation | 25% | Compound risk detection — danger isn't one signal, it's a combination; genuine multi-agent reasoning, not one formula |
| Business Impact | 25% | Prevents fatalities, reduces false negatives, deployable to a new plant via config, not a rewrite |
| Technical Excellence | 20% | Real multi-agent pipeline, trend-based lead time, RAG-based compliance retrieval, Timescale + pgvector, human-in-loop actions |
| Scalability | 15% | Config-driven zones/thresholds/connectors — a new plant install is `plant.config.yaml` + secrets, not new code |
| User Experience | 15% | Real-time heatmap, one-click action confirmation, AI-generated reports |

## License

MIT
"# Ai.Sensor" 
