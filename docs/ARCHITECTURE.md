# Architecture

## System Overview

The CubeSat Digital Twin is a system-level simulation of a 2U CubeSat wildfire smoke detection mission. It implements a complete vertical slice from orbital mechanics through onboard AI inference to ground-station visualization.

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SIMULATION ENGINE                         │
│                                                             │
│  Orbit Service ──→ Spacecraft State ──→ Camera Simulator    │
│       │                   │                    │            │
│       │                   │                    ▼            │
│       │                   │           Image Capture         │
│       │                   │                    │            │
│       │                   │                    ▼            │
│       │                   │          ML Inference Engine    │
│       │                   │                    │            │
│       │                   │                    ▼            │
│       │                   │          Priority Calculator    │
│       │                   │                    │            │
│       │                   │                    ▼            │
│       │                   └────── Observation Record        │
│       │                              │                     │
│       ▼                              ▼                     │
│  TelemetryPacket ──────→ WebSocket ──→ Dashboard            │
└─────────────────────────────────────────────────────────────┘
```

## Backend Layers

```
API Layer (FastAPI Routers)
    ↓
Service Layer (Telemetry, Observation, Priority)
    ↓
Domain Layer (Simulation Engine, Orbit, Camera, ML)
    ↓
Adapter Layer (FIRMS, Weather, CelesTrak, GIBS)
    ↓
Persistence Layer (In-memory → SQLite → PostgreSQL)
```

## Key Interfaces

### InferenceEngine (ABC)

All ML classifiers implement:
- `classify(image_path) -> dict` with smoke_probability, confidence, model metadata
- `get_model_info() -> dict`

Phase 1: MockClassifier (deterministic, hash-based)
Future: MobileNet, ONNX, TensorFlow Lite

### SGP4OrbitService

- Accepts TLE, Keplerian elements, or simple altitude/inclination
- Falls back to analytical circular orbit model
- All parameters labeled as simulation values

### CameraSimulator

- Generates synthetic Earth observation images
- Deterministic based on timestamp and position
- Interface supports real Raspberry Pi camera replacement

## Frontend Architecture

```
Pages (app/page.tsx)
    ↓
Feature Components (Globe, Status, Observations, Controls)
    ↓
State Layer (Zustand store)
    ↓
API/WebSocket Clients (lib/api.ts, lib/websocket.ts)
```

## WebSocket Protocol

```json
{
  "type": "telemetry",
  "payload": {
    "packet_sequence": 1,
    "timestamp": "...",
    "spacecraft_id": "CSAT-001",
    "mission_mode": "IDLE",
    "latitude": 45.2,
    "longitude": -122.5,
    "altitude_km": 500.0,
    "battery_percentage": 85.0,
    "smoke_probability": 0.72,
    "confidence": 0.88,
    "priority": "HIGH"
  }
}
```
