# 2U CubeSat Wildfire Smoke Detection — Digital Twin

System-level digital twin for a 2U CubeSat concept using an RGB camera and onboard AI/ML for probable wildfire/smoke indication and intelligent image prioritisation.

## Scope

This repository is an engineering demonstrator and simulation environment. It is **not** flight-qualified hardware or a definitive autonomous fire-confirmation system.

## Mission Concept

```
Simulated pass → observation → RGB image → onboard inference →
probability/confidence → image priority → telemetry/downlink → ground dashboard
```

The AI system identifies **probable** smoke/wildfire signatures, outputs probability/confidence, and assigns an observation priority. Smoke, clouds, haze, dust, shadows, and atmospheric effects can produce visually similar patterns, so the system reflects uncertainty in all outputs.

## Features

### What Works (Phases 1-5)

- **SGP4 Orbit Propagation** — CelesTrak TLE integration with analytical fallback
- **Camera Simulation** — Synthetic Earth observation image generation
- **ML Pipeline** — Onboard smoke detection (mock + real with training scripts)
- **Live AI Vision** — External vision inference via OpenRouter/Groq with failover
- **FIRMS + Weather Correlation** — Fire detection fusion with weighted probability
- **5-Station Ground Network** — Global coverage with pass detection and visibility
- **Downlink Simulation** — Priority-ordered queue with realistic transfer
- **Autonomous Fault Recovery** — Self-healing with retries and cooldown
- **EPS Model** — Per-subsystem power consumption and load shedding
- **Thermal Model** — 5-node thermal simulation with safe ranges
- **SQLite Persistence** — Full observation/telemetry/event database
- **Replay & Export** — Session recording, playback, and data export
- **3D Dashboard** — CesiumJS globe with ground track, FIRMS overlay, camera footprint

### What's Simulated (Not Real Hardware)

- Orbital mechanics (mathematical models)
- Camera images (gradient + terrain simulation)
- ML classification (mock classifier or trained model inference)
- Ground station passes (geometry-based visibility)
- Power/thermal dynamics (physics-based models)

## Roadmap

| Status | Item |
|--------|------|
| ✅ | Digital twin simulation (Phases 1-5) |
| ✅ | Onboard ML pipeline (mock + real with training scripts) |
| ✅ | Live AI vision analysis (OpenRouter/Groq) |
| ✅ | Persistence, replay, export |
| ✅ | Ground network, downlink simulation |
| ✅ | Fault recovery, EPS, thermal modeling |
| 🔜 | Raspberry Pi 5 deployment |
| 🔜 | Real camera hardware integration |
| 🔜 | Custom trained smoke detection model |
| 🔜 | Actual ground station hardware |

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![CesiumJS](https://img.shields.io/badge/CesiumJS-1.115-blue)
![SQLite](https://img.shields.io/badge/SQLite-3-orange?logo=sqlite)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c?logo=pytorch)

## Project Structure

```
/
├── backend/                  Python FastAPI backend
│   ├── app/
│   │   ├── main.py           Application entry + WebSocket
│   │   ├── core/             Config, database, resource manager
│   │   ├── api/v1/           21 REST route modules
│   │   ├── models/           Pydantic schemas
│   │   ├── services/         17 service modules
│   │   ├── simulation/       Engine, orbit, camera
│   │   ├── ml/               Inference interface + mock
│   │   ├── ai/               Vision AI providers + service
│   │   └── adapters/         External API clients
│   ├── tests/                pytest test suite
│   └── requirements.txt
├── frontend/                 Next.js + CesiumJS dashboard
│   ├── src/
│   │   ├── app/              Pages and layout
│   │   ├── components/       16 mission control panels
│   │   ├── lib/              API + WebSocket clients
│   │   └── stores/           Zustand state management
│   └── package.json
├── simulation/               Shared configurations
├── docs/                     Technical documentation
├── data/                     Observations and persistence
├── scripts/                  ML training pipeline
├── docker-compose.yml
└── .env.example
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` — all external API keys are optional (system degrades gracefully):

| Variable | Description |
|----------|-------------|
| `NASA_FIRMS_MAP_KEY` | NASA FIRMS API key for wildfire hotspot data |
| `NEXT_PUBLIC_CESIUM_TOKEN` | Cesium Ion access token for 3D globe imagery |
| `AI_MODE` | `mock` (local) or `live` (external vision AI) |
| `OPENROUTER_API_KEY` | OpenRouter API key (if `AI_MODE=live`) |
| `GROQ_API_KEY` | Groq API key (if `AI_MODE=live`) |

### 2. Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Access

- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API Base**: http://localhost:8000

### Docker

```bash
docker-compose up --build
```

## API Overview

### Core Simulation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/config` | Spacecraft and simulation config |
| POST | `/api/v1/simulation/start` | Start simulation |
| POST | `/api/v1/simulation/stop` | Stop simulation |
| POST | `/api/v1/simulation/reset` | Reset simulation |

### Observations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/observations/capture` | Trigger observation |
| GET | `/api/v1/observations` | List observations |
| GET | `/api/v1/observations/{id}` | Get observation |

### AI Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ai/status` | AI service status |
| POST | `/api/v1/ai/analyze` | Analyze image |

### Ground Network

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ground-station/network` | Station list |
| GET | `/api/v1/ground-station/visibility` | Visibility windows |
| GET | `/api/v1/ground-station/status` | Current pass status |

### Downlink

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/downlink/status` | Queue status |
| GET | `/api/v1/downlink/queue` | Queue contents |
| POST | `/api/v1/downlink/schedule` | Schedule downlink |

### FIRMS & Correlation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/firms/status` | FIRMS adapter status |
| GET | `/api/v1/correlation/status` | Correlation status |
| POST | `/api/v1/correlation/analyze` | Trigger correlation |

### Recovery & Subsystems

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/recovery/status` | Fault recovery status |
| POST | `/api/v1/recovery/trigger` | Trigger recovery |
| GET | `/api/v1/eps/status` | EPS power status |
| GET | `/api/v1/thermal/status` | Thermal model status |
| GET | `/api/v1/tle/status` | TLE service status |
| POST | `/api/v1/tle/refresh` | Refresh TLE data |

### History & Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/history/observations` | Observation history |
| GET | `/api/v1/history/telemetry` | Telemetry history |
| GET | `/api/v1/history/events` | Event history |
| GET | `/api/v1/export/observations` | Export observations (JSON/CSV) |
| GET | `/api/v1/export/telemetry` | Export telemetry |

### Replay

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/replay/sessions` | List sessions |
| POST | `/api/v1/replay/playback` | Start playback |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/system/resources` | System resource stats |
| WS | `/ws/telemetry` | Live telemetry stream |

## AI Vision Pipeline

```bash
# Mock mode (no API key needed)
AI_MODE=mock

# Live mode with OpenRouter
AI_MODE=live
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...

# Live mode with Groq
AI_MODE=live
AI_PROVIDER=groq
GROQ_API_KEY=gsk_...

# Failover (OpenRouter primary, Groq fallback)
AI_MODE=live
AI_PROVIDER=openrouter
AI_FAILOVER_ENABLED=true
```

The external vision AI returns an **AI Smoke Score** (0-1). This is NOT a calibrated probability of wildfire. It is an AI-generated assessment used for mission decision support.

## ML Training Pipeline

```bash
# Prepare dataset
python scripts/ml/prepare_dataset.py --source <data_path> --output data/raw

# Split dataset
python scripts/ml/split_dataset.py --labels data/labels/labels.json --output data/splits

# Train models
python scripts/ml/train.py --data data/splits/ --model mobilenet_v3_small --epochs 30

# Evaluate
python scripts/ml/evaluate.py --model data/models/best_model.pt --data data/splits/

# Export
python scripts/ml/export.py --model data/models/best_model.pt --format onnx

# Full pipeline
python scripts/ml/run_pipeline.py --source <data_path>
```

Set `ML_MODE=real` in `.env` to use trained model. Default is `ML_MODE=mock`.

## External Integrations

| Service | Purpose | Required? |
|---------|---------|-----------|
| NASA FIRMS | Wildfire hotspot detection | No (graceful fallback) |
| Open-Meteo | Weather and air quality | No (graceful fallback) |
| CelesTrak | Satellite TLE data | No (uses default orbit) |
| OpenRouter | Vision AI inference | No (mock mode) |
| Groq | Vision AI inference | No (mock mode) |

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

88 tests covering:
- Model validation, orbit propagation, ML classification, priority calculation
- API endpoints (all 21 route modules)
- ML pipeline (preprocessing, postprocessing, metrics, model registry)
- AI vision providers (mock, OpenRouter, Groq, preprocessing, failover, rate limiting)
- External adapters (FIRMS, weather, CelesTrak)

## Security

Real credentials must **never** be committed. Store them in a local `.env` file and keep `.env` ignored by Git.

## License

Engineering demonstrator — not for production or flight use.
