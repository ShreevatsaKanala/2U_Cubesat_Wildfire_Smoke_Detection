# Development Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/ShreevatsaKanala/2U_Cubesat_Wildfire_Smoke_Detection.git
cd 2U_Cubesat_Wildfire_Smoke_Detection
cp .env.example .env
# Edit .env with your API keys (optional)
```

### 2. Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: http://localhost:8000
API docs at: http://localhost:8000/docs

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: http://localhost:3000

### 4. Docker

```bash
docker-compose up --build
```

## Environment Variables

All variables are configured via `.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `NASA_FIRMS_MAP_KEY` | (empty) | NASA FIRMS API key for wildfire hotspot data |
| `NEXT_PUBLIC_CESIUM_TOKEN` | (empty) | Cesium Ion access token for 3D globe |
| `AI_MODE` | `mock` | `mock` or `live` — vision AI mode |
| `AI_PROVIDER` | `openrouter` | `openrouter` or `groq` — primary AI provider |
| `OPENROUTER_API_KEY` | (empty) | OpenRouter API key |
| `GROQ_API_KEY` | (empty) | Groq API key |
| `OPENROUTER_MODEL` | `google/gemini-2.0-flash-001` | OpenRouter model |
| `GROQ_MODEL` | `qwen/qwen3.6-27b` | Groq model |
| `AI_FAILOVER_ENABLED` | `true` | Enable provider failover |
| `AI_TIMEOUT_SECONDS` | `30` | AI request timeout |
| `AI_MAX_REQUESTS_PER_MINUTE` | `10` | Rate limit for AI requests |
| `ML_MODE` | `mock` | `mock` or `real` — ML classifier mode |
| `ML_MODEL_PATH` | `data/models/best_model.pt` | Path to trained model |
| `ML_SMOKE_THRESHOLD` | `0.5` | Smoke detection threshold |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/cubesat_twin.db` | Database connection |
| `BACKEND_HOST` | `0.0.0.0` | Backend bind address |
| `BACKEND_PORT` | `8000` | Backend port |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend API base URL |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | Frontend WebSocket URL |

External API keys are optional — the system degrades gracefully without them.

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application + WebSocket + simulation loop
│   ├── core/
│   │   ├── config.py        # Settings via env vars
│   │   ├── database.py      # SQLite async database layer
│   │   └── resource_manager.py  # BoundedList, TTLCache, monitoring
│   ├── api/v1/              # REST endpoints (21 routers)
│   │   ├── health.py
│   │   ├── simulation.py
│   │   ├── observations.py
│   │   ├── spacecraft.py
│   │   ├── telemetry.py
│   │   ├── environment.py
│   │   ├── events.py
│   │   ├── ground_station.py
│   │   ├── downlink.py
│   │   ├── faults.py
│   │   ├── ai_status.py
│   │   ├── tle.py
│   │   ├── history.py
│   │   ├── recovery.py
│   │   ├── eps.py
│   │   ├── thermal.py
│   │   ├── firms.py
│   │   ├── correlation.py
│   │   ├── replay.py
│   │   └── export.py
│   ├── models/              # Pydantic schemas
│   │   ├── spacecraft.py    # SpacecraftState, PowerState, ThermalState
│   │   ├── telemetry.py     # TelemetryPacket, MissionEvent
│   │   ├── observation.py   # Observation record
│   │   ├── events.py        # MissionEvent, EventLog
│   │   ├── ground_station.py # GroundStationConfig, GroundPass, Network
│   │   └── downlink.py      # DownlinkItem, DownlinkQueue
│   ├── services/            # Business logic (17 modules)
│   │   ├── telemetry_service.py
│   │   ├── observation_service.py
│   │   ├── priority.py
│   │   ├── ground_network.py
│   │   ├── ground_station.py
│   │   ├── downlink.py
│   │   ├── downlink_scheduler.py
│   │   ├── persistence_service.py
│   │   ├── export_service.py
│   │   ├── replay_service.py
│   │   ├── fault_recovery.py
│   │   ├── eps_model.py
│   │   ├── thermal_model.py
│   │   ├── fire_correlation.py
│   │   └── tle_service.py
│   ├── simulation/          # Engine, orbit, camera
│   │   ├── engine.py        # SimulationEngine (main loop)
│   │   ├── orbit/sgp4_orbit.py  # SGP4 orbit propagation
│   │   └── camera.py        # Synthetic image capture
│   ├── ml/                  # Inference interface + mock
│   ├── ai/                  # Vision AI providers + service
│   └── adapters/            # External API clients (FIRMS, Weather, CelesTrak, GIBS)
├── tests/                   # pytest test suite (88 tests)
└── requirements.txt

frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx         # Main dashboard layout
│   │   ├── layout.tsx       # Root layout
│   │   └── globals.css      # Mission theme styles
│   ├── components/          # 16 React components
│   │   ├── Globe.tsx        # CesiumJS 3D Earth
│   │   ├── SpacecraftStatus.tsx
│   │   ├── MissionControls.tsx
│   │   ├── SimulationClock.tsx
│   │   ├── PowerPanel.tsx
│   │   ├── ThermalPanel.tsx
│   │   ├── HealthPanel.tsx
│   │   ├── FaultInjectionPanel.tsx
│   │   ├── MissionEventsPanel.tsx
│   │   ├── GroundStationPanel.tsx
│   │   ├── DownlinkQueuePanel.tsx
│   │   ├── ObservationCenter.tsx
│   │   ├── ObservationHistoryPanel.tsx
│   │   ├── EnvironmentPanel.tsx
│   │   ├── LiveTelemetry.tsx
│   │   └── ConnectionIndicator.tsx
│   ├── lib/
│   │   ├── api.ts           # REST API client
│   │   └── websocket.ts     # WebSocket client
│   └── stores/
│       └── telemetryStore.ts # Zustand state management
├── package.json
└── tsconfig.json
```

## Running Tests

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

## Database Management

The system uses SQLite via `aiosqlite` for async database access.

### Database Location

```
data/cubesat_twin.db
```

### Tables

| Table | Contents |
|-------|----------|
| `observations` | All captured observations with metadata |
| `telemetry` | Periodic telemetry snapshots |
| `events` | Mission events with severity levels |
| `sessions` | Replay session metadata |

### Reset Database

```bash
rm data/cubesat_twin.db
# Database is recreated on next backend start
```

### Export Data

Use the export API endpoints or access the database directly:

```bash
sqlite3 data/cubesat_twin.db ".dump" > backup.sql
```

## Code Style

- Backend: Python type hints, Pydantic models, async where appropriate
- Frontend: TypeScript strict mode, functional components, Zustand for state
- All external calls behind adapters with timeout and error handling
- No hardcoded secrets or API keys
- Bounded collections to prevent memory leaks
- Graceful degradation for all external services

## Adding a New ML Model

1. Create a new class implementing `InferenceEngine` in `app/ml/`
2. Implement `classify(image_path)` returning the standard dict
3. Update `SimulationEngine` to use your model
4. All observations will use the new model automatically

## Adding a New Adapter

1. Create a new file in `app/adapters/`
2. Use `httpx.AsyncClient` with 10s timeout
3. Return typed dicts
4. Handle all errors gracefully (log + return defaults)
5. Add endpoint in `app/api/v1/environment.py`

## Adding a New API Route

1. Create a new file in `app/api/v1/`
2. Create a `router = APIRouter()` with appropriate prefix and tags
3. Implement endpoints with proper response models
4. Register the router in `app/main.py`:
   ```python
   from app.api.v1.your_module import router as your_router
   app.include_router(your_router)
   ```
