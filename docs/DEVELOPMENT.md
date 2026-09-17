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

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application + WebSocket
│   ├── core/config.py        # Settings via env vars
│   ├── models/               # Pydantic schemas
│   │   ├── spacecraft.py     # SpacecraftState, PowerState, ThermalState, etc.
│   │   ├── telemetry.py      # TelemetryPacket, MissionEvent
│   │   ├── observation.py    # Observation record
│   │   ├── events.py         # MissionEvent, EventLog
│   │   ├── ground_station.py # GroundStationConfig, GroundPass
│   │   └── downlink.py       # DownlinkItem, DownlinkQueue
│   ├── simulation/           # Engine, orbit, camera
│   │   ├── engine.py         # SimulationEngine (fault injection, ground station, downlink)
│   │   ├── orbit/sgp4_orbit.py # Orbit propagation
│   │   └── camera.py         # Synthetic image capture
│   ├── ml/                   # Inference interface + mock
│   ├── services/             # Telemetry, observations, priority, ground station, downlink
│   ├── adapters/             # External API clients (FIRMS, Weather, CelesTrak, GIBS)
│   ├── api/v1/               # REST endpoints (11 routers)
│   └── data/                 # Database layer
├── tests/                    # pytest tests (42 tests)
└── requirements.txt

frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main dashboard layout
│   │   ├── layout.tsx        # Root layout
│   │   └── globals.css       # Mission theme styles
│   ├── components/           # 16 React components
│   │   ├── Globe.tsx         # CesiumJS 3D Earth (ground track, FIRMS, footprint)
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
│   │   ├── api.ts            # REST API client (17 endpoints)
│   │   └── websocket.ts      # WebSocket client
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

42 tests covering:
- Model validation
- Orbit propagation
- ML classification
- Priority calculation
- API endpoints (including Phase 2: events, ground station, downlink, faults)
- External adapters

## Code Style

- Backend: Python type hints, Pydantic models, async where appropriate
- Frontend: TypeScript strict mode, functional components, Zustand for state
- All external calls behind adapters with timeout and error handling
- No hardcoded secrets or API keys

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
