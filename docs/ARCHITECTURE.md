# Architecture

## System Overview

The CubeSat Digital Twin is a system-level simulation of a 2U CubeSat wildfire smoke detection mission. It implements a complete vertical slice from orbital mechanics through onboard AI inference to ground-station visualization.

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                      SIMULATION ENGINE                           │
│                                                                  │
│  Orbit Service ──→ Spacecraft State ──→ Fault Injection          │
│       │                   │                    │                 │
│       │                   │                    ▼                 │
│       │                   │          Power/Thermal Models        │
│       │                   │                    │                 │
│       │                   │                    ▼                 │
│       │                   │          Camera Simulator            │
│       │                   │                    │                 │
│       │                   │                    ▼                 │
│       │                   │          ML Inference Engine         │
│       │                   │                    │                 │
│       │                   │                    ▼                 │
│       │                   │          Priority Calculator         │
│       │                   │                    │                 │
│       │                   │                    ▼                 │
│       │                   └────── Observation Record             │
│       │                              │                          │
│       │                              ▼                          │
│       │                    Ground Station Pass Check             │
│       │                              │                          │
│       │                              ▼                          │
│       │                        Downlink Queue                    │
│       │                              │                          │
│       ▼                              ▼                          │
│  TelemetryPacket ──────→ WebSocket ──→ Dashboard                 │
│                                                                  │
│  MissionEvents ─────────→ Event Log ──→ Events Panel             │
└──────────────────────────────────────────────────────────────────┘
```

## Backend Layers

```
API Layer (FastAPI Routers: health, config, spacecraft, telemetry,
           observations, simulation, environment, events,
           ground-station, downlink, faults)
    ↓
Service Layer (Telemetry, Observation, Priority, GroundStationPass,
               Downlink, MissionEvents)
    ↓
Domain Layer (Simulation Engine, Orbit, Camera, ML, PowerModel,
              ThermalModel, FaultInjection)
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

Phase 2: MockClassifier (deterministic, hash-based)
Future: MobileNet, ONNX, TensorFlow Lite

### SGP4OrbitService

- Accepts TLE, Keplerian elements, or simple altitude/inclination
- Falls back to analytical circular orbit model
- All parameters labeled as simulation values

### CameraSimulator

- Generates synthetic Earth observation images
- Deterministic based on timestamp and position
- Interface supports real Raspberry Pi camera replacement

### SimulationEngine (Phase 2)

- Fault injection (battery, camera, ADCS, comms, eclipse)
- Ground station pass detection
- Downlink queue processing
- Mission event logging
- Configurable simulation speed

### PowerModel (Phase 2)

- Battery SOC tracking (coulomb counting)
- Solar generation vs consumption
- Eclipse detection
- Power balance monitoring

### ThermalModel (Phase 2)

- Multi-node thermal simulation
- Solar heating, Earth albedo, internal dissipation
- Radiative cooling
- Safe operating range tracking

## Frontend Architecture

```
Pages (app/page.tsx)
    ↓
Feature Components:
    ├── Globe (CesiumJS 3D Earth)
    ├── SpacecraftStatus (position, attitude, power, thermal, health)
    ├── MissionControls (start/stop/reset, speed, orbit mode)
    ├── SimulationClock (elapsed time, steps/sec)
    ├── PowerPanel (battery, solar, consumption, eclipse)
    ├── ThermalPanel (per-node temperatures with safe ranges)
    ├── HealthPanel (subsystem health cards)
    ├── FaultInjectionPanel (toggle switches)
    ├── MissionEventsPanel (scrollable event list)
    ├── GroundStationPanel (pass info, distance, visibility)
    ├── DownlinkQueuePanel (queue items, TX stats)
    ├── ObservationCenter (latest observation detail)
    ├── ObservationHistoryPanel (paginated list with replay)
    ├── EnvironmentPanel (weather, air quality)
    ├── LiveTelemetry (scrolling telemetry log)
    └── ConnectionIndicator (WS status)
    ↓
State Layer (Zustand store with nested telemetry, events, faults, etc.)
    ↓
API/WebSocket Clients (lib/api.ts, lib/websocket.ts)
```

## WebSocket Protocol (Phase 2)

```json
{
  "type": "telemetry",
  "payload": {
    "packet_sequence": 1,
    "timestamp": "...",
    "spacecraft_id": "CSAT-001",
    "mission_mode": "SCIENCE",
    "position": {
      "latitude": 45.2,
      "longitude": -122.5,
      "altitude_km": 500.0,
      "velocity_km_s": 7.5,
      "heading_deg": 90.0
    },
    "attitude": {
      "roll_deg": 0.1,
      "pitch_deg": -0.2,
      "yaw_deg": 45.0,
      "attitude_mode": "NADIR",
      "pointing_error_deg": 0.3
    },
    "power": {
      "battery_soc": 85.5,
      "battery_voltage": 7.4,
      "solar_generation_w": 2.5,
      "power_consumption_w": 1.8,
      "power_balance_w": 0.7,
      "eclipse": false
    },
    "thermal": {
      "nodes": [
        {"name": "solar_panel_plus_y", "temperature_c": 45.0, "min_safe_c": -20.0, "max_safe_c": 60.0}
      ]
    },
    "health": {
      "overall": "NOMINAL",
      "eps": {"status": "NOMINAL", "uptime_s": 1000},
      "obc": {"status": "NOMINAL", "uptime_s": 1000}
    }
  }
}
```
