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
- Power model (coulomb counting, eclipse detection)
- Thermal model (multi-node radiative)
- Fault injection system
- Ground station pass detection
- Downlink queue management

### Frontend Stack

- **Next.js 14** with TypeScript
- Tailwind CSS for mission-control dark theme
- CesiumJS for 3D Earth visualisation
- Zustand for state management
- WebSocket client for live telemetry
- 16 mission control panels

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
| `NEXT_PUBLIC_CESIUM_TOKEN` | Cesium Ion access token for 3D globe imagery |

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
| GET | `/api/v1/spacecraft/state` | Full spacecraft state |
| GET | `/api/v1/spacecraft/health` | Subsystem health status |
| GET | `/api/v1/spacecraft/power` | Power subsystem state |
| GET | `/api/v1/spacecraft/thermal` | Thermal node temperatures |
| GET | `/api/v1/spacecraft/attitude` | ADCS attitude state |
| GET | `/api/v1/telemetry/latest` | Latest telemetry packet |
| GET | `/api/v1/observations` | Paginated observation list |
| GET | `/api/v1/observations/{id}` | Get specific observation |
| GET | `/api/v1/events` | Mission event log |
| GET | `/api/v1/ground-station/status` | Ground station pass status |
| GET | `/api/v1/ground-station/config` | Ground station configuration |
| GET | `/api/v1/downlink/status` | Downlink queue status |
| GET | `/api/v1/faults` | Current fault states |
| POST | `/api/v1/faults/inject` | Inject faults |
| POST | `/api/v1/faults/clear` | Clear all faults |
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
- Speed: Configurable via frontend controls (1x, 5x, 10x, 50x)
- Orbit mode: LEO, SSO, GEO presets
- Camera modes: Follow, Top-down, Free

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

62 tests (5 skipped if torch not installed) covering:
- Model validation, orbit propagation, ML classification, priority calculation
- API endpoints (health, config, spacecraft, observations, events, ground station, downlink, faults, simulation, environment)
- ML pipeline (preprocessing, postprocessing, metrics, model registry, classifier integration)
- External adapters

## ML Pipeline

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

# Benchmark
python scripts/ml/benchmark.py --model data/models/best_model.pt

# Full pipeline
python scripts/ml/run_pipeline.py --source <data_path>
```

Set `ML_MODE=real` in `.env` to use trained model. Default is `ML_MODE=mock`.

## External Integrations

| Service | Purpose | Required? |
|---|---|---|
| NASA FIRMS | Wildfire hotspot detection | No (graceful fallback) |
| Open-Meteo | Weather and air quality | No (graceful fallback) |
| CelesTrak | Satellite TLE data | No (uses default orbit) |
| NASA GIBS | Satellite imagery layers | No (URL construction only) |

## Digital Twin Domains

Phase 3 adds real ML inference pipeline:

1. **Mission/Orbit** — SGP4 propagation with configurable orbital parameters
2. **Spacecraft State** — Full state vector with power, thermal, attitude
3. **Power Subsystem** — Coulomb counting, eclipse detection, solar generation
4. **Thermal Subsystem** — Multi-node thermal with safe range tracking
5. **ADCS** — NADIR, SUN_SYNC, INERTIAL attitude modes
6. **Camera/Payload** — Synthetic image generation with terrain simulation
7. **AI/ML Inference** — Pluggable interface: MockClassifier + RealSmokeClassifier
8. **ML Pipeline** — Preprocessing, training, evaluation, threshold calibration, ONNX export
9. **Mission Decision Logic** — Weighted priority calculation (CRITICAL/HIGH/MEDIUM/LOW)
10. **Fault Management** — Inject/clear battery, camera, ADCS, comms, eclipse faults
11. **Ground Station** — Pass detection, visibility, elevation/azimuth calculation
12. **Downlink** — Priority-ordered queue with transmission tracking
13. **Mission Events** — Event logging with severity levels
14. **Telemetry** — Typed packets with live WebSocket streaming
15. **Ground Dashboard** — 3D Cesium globe with ground track, FIRMS, camera footprint

## Roadmap

- [x] Replace mock classifier with real lightweight CNN/MobileNet/ONNX model
- [ ] Add real TLE loading from CelesTrak
- [ ] SQLite/PostgreSQL persistence layer
- [ ] Observation image downlink simulation
- [ ] Multi-station ground network
- [ ] FIRMS hotspot overlay on Cesium globe (live)
- [ ] Autonomous fault recovery logic
- [ ] Subsystem-level EPS depth
- [ ] Detailed thermal model improvement
- [ ] Replay/export functionality
- [ ] Raspberry Pi 5 deployment and benchmarking
- [ ] Real dataset acquisition and training

## Security

Real credentials must **never** be committed. Store them in a local `.env` file and keep `.env` ignored by Git.

## License

Engineering demonstrator — not for production or flight use.
