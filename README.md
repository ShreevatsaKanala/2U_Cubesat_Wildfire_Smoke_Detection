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

## Architecture

```
/
├── backend/        Python FastAPI backend + simulation engine
├── frontend/       Next.js + CesiumJS mission-control dashboard
├── simulation/     Shared simulation configurations
├── docs/           Technical documentation
├── data/           Observation images and persistence
├── scripts/        Utility scripts
├── docker-compose.yml
└── .env.example
```

### Backend Stack

- **Python 3.11+** with FastAPI
- Pydantic for typed schemas
- WebSocket for live telemetry
- SGP4 orbit propagation (with analytical fallback)
- Pluggable ML inference interface
- External API adapters (NASA FIRMS, Open-Meteo, CelesTrak, NASA GIBS)

### Frontend Stack

- **Next.js 14** with TypeScript
- Tailwind CSS for mission-control dark theme
- CesiumJS for 3D Earth visualisation
- Zustand for state management
- WebSocket client for live telemetry

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `NASA_FIRMS_MAP_KEY` | NASA FIRMS API key for wildfire hotspot data |
| `CESIUM_ION_TOKEN` | Cesium Ion access token for 3D globe imagery |

The system works **without** external API keys — adapters gracefully degrade.

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker-compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/config` | Spacecraft and simulation configuration |
| GET | `/api/v1/spacecraft/state` | Current spacecraft state |
| GET | `/api/v1/telemetry/latest` | Latest telemetry packet |
| GET | `/api/v1/telemetry/history` | Telemetry history |
| GET | `/api/v1/observations` | List observations |
| GET | `/api/v1/observations/{id}` | Get specific observation |
| POST | `/api/v1/simulation/start` | Start simulation |
| POST | `/api/v1/simulation/stop` | Stop simulation |
| POST | `/api/v1/simulation/reset` | Reset simulation |
| GET | `/api/v1/environment/weather` | Weather data (Open-Meteo) |
| GET | `/api/v1/environment/air-quality` | Air quality data |
| GET | `/api/v1/environment/hotspots` | FIRMS wildfire hotspots |
| WS | `/ws/telemetry` | Live telemetry WebSocket |

## Simulator Controls

- **START** — Begin simulation loop (orbit propagation, observations, telemetry)
- **STOP** — Pause simulation
- **RESET** — Reset to initial state
- Speed: Configurable via simulation config (default 1x)

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

34 tests covering:
- Model validation
- Orbit propagation
- ML classification
- Priority calculation
- API endpoints
- External adapters

## External Integrations

| Service | Purpose | Required? |
|---|---|---|
| NASA FIRMS | Wildfire hotspot detection | No (graceful fallback) |
| Open-Meteo | Weather and air quality | No (graceful fallback) |
| CelesTrak | Satellite TLE data | No (uses default orbit) |
| NASA GIBS | Satellite imagery layers | No (URL construction only) |

## Digital Twin Domains

Phase 1 implements the core vertical slice:

1. **Mission/Orbit** — SGP4 propagation with configurable orbital parameters
2. **Spacecraft State** — Full state vector with power, thermal, attitude
3. **Camera/Payload** — Synthetic image generation with terrain simulation
4. **AI/ML Inference** — Pluggable interface with deterministic mock classifier
5. **Mission Decision Logic** — Weighted priority calculation (CRITICAL/HIGH/MEDIUM/LOW)
6. **Telemetry** — Typed packets with live WebSocket streaming
7. **Ground Station** — 3D Cesium globe with real-time spacecraft tracking

Future phases will add: ADCS, data handling, communications, power subsystem depth, thermal modelling, fault management.

## Roadmap

- [ ] Replace mock classifier with real lightweight CNN/MobileNet/ONNX model
- [ ] Add real TLE loading from CelesTrak
- [ ] SQLite/PostgreSQL persistence layer
- [ ] Observation image downlink simulation
- [ ] Ground station dashboard enhancements
- [ ] FIRMS hotspot overlay on Cesium globe
- [ ] Fault management and safe mode logic
- [ ] Power budget depth (subsystem-level)
- [ ] Thermal model improvement
- [ ] Replay/export functionality

## Security

Real credentials must **never** be committed. Store them in a local `.env` file and keep `.env` ignored by Git.

## License

Engineering demonstrator — not for production or flight use.
