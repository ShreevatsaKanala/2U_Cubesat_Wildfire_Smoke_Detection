# Architecture

## System Overview

The CubeSat Digital Twin is a system-level simulation of a 2U CubeSat wildfire smoke detection mission. It implements a complete vertical slice from orbital mechanics through onboard AI inference to ground-station visualization, with persistence, replay, and export capabilities.

## Phase 5 Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          SIMULATION ENGINE                                    │
│                                                                              │
│  TLE Service ──→ SGP4 Orbit ──→ Spacecraft State ──→ Fault Injection         │
│       │                │                │                    │                │
│       │                │                │                    ▼                │
│       │                │                │          EPS Model (per-subsystem)  │
│       │                │                │          Thermal Model (5-node)     │
│       │                │                │                    │                │
│       │                │                │                    ▼                │
│       │                │                │          Camera Simulator           │
│       │                │                │                    │                │
│       │                │                │                    ▼                │
│       │                │                │     ┌──────────────┴─────────────┐  │
│       │                │                │     │                            │  │
│       │                │                │     ▼                            ▼  │
│       │                │                │  ML Pipeline              AI Vision │
│       │                │                │  (mock/real)        (OpenRouter/Groq│
│       │                │                │     │                            │  │
│       │                │                │     └──────────────┬─────────────┘  │
│       │                │                │                    │                │
│       │                │                │                    ▼                │
│       │                │                │          Priority Calculator        │
│       │                │                │                    │                │
│       │                │                │                    ▼                │
│       │                │                │            Observation Record       │
│       │                │                │                    │                │
│       │                │                │                    ▼                │
│       │                │                │       ┌────────────┴────────────┐  │
│       │                │                │       │                         │  │
│       │                │                │       ▼                         ▼  │
│       │                │                │  FIRMS Correlation      Weather    │
│       │                │                │  + Weather Fusion       Adapter   │
│       │                │                │       │                         │  │
│       │                │                │       └────────────┬────────────┘  │
│       │                │                │                    │                │
│       │                │                │                    ▼                │
│       │                │                │          Ground Station Network    │
│       │                │                │          (5 global stations)       │
│       │                │                │                    │                │
│       │                │                │                    ▼                │
│       │                │                │              Downlink Queue        │
│       │                │                │              (priority-ordered)    │
│       │                │                │                    │                │
│       │                │                │                    ▼                │
│       │                │                │           Persistence (SQLite)     │
│       │                │                │                    │                │
│       ▼                ▼                ▼                    ▼                │
│  TelemetryPacket ──→ WebSocket ──→ Dashboard                                  │
│                                                                              │
│  Fault Recovery (autonomous) ──→ Event Log ──→ Events Panel                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Observation → AI/ML Analysis → Priority → Correlation → Persistence → Export
     │              │              │           │              │           │
     │              │              │           │              │           │
     ▼              ▼              ▼           ▼              ▼           ▼
  Camera        Smoke         Weighted    FIRMS+Weather   SQLite DB   JSON/CSV
  Capture       Score         Score       Fusion          Storage     Streaming
```

## Backend Layers

```
┌─────────────────────────────────────────────────────────────┐
│ API Layer (FastAPI — 21 route modules)                      │
│   health, config, spacecraft, telemetry, observations,      │
│   simulation, environment, events, ground_station,          │
│   downlink, faults, ai_status, tle, history, recovery,      │
│   eps, thermal, firms, correlation, replay, export          │
├─────────────────────────────────────────────────────────────┤
│ Service Layer (17 service modules)                          │
│   TelemetryService, ObservationService, PriorityCalculator, │
│   GroundNetworkService, DownlinkScheduler, MissionEvents,   │
│   PersistenceService, ExportService, ReplayService,         │
│   FaultRecoveryService, EPSModel, ThermalModel,             │
│   FireCorrelationService, TLEService, AIService             │
├─────────────────────────────────────────────────────────────┤
│ Domain Layer (Simulation Engine)                            │
│   SGP4OrbitService, CameraSimulator, MockClassifier,        │
│   RealSmokeClassifier, FaultInjection                       │
├─────────────────────────────────────────────────────────────┤
│ Adapter Layer (External APIs)                               │
│   FIRMSAdapter, WeatherAdapter, CelesTrakAdapter, GIBSAdapter│
├─────────────────────────────────────────────────────────────┤
│ Persistence Layer (SQLite via aiosqlite)                    │
│   Observations, Telemetry, Events, Sessions, Exports        │
├─────────────────────────────────────────────────────────────┤
│ Resource Management                                         │
│   BoundedList, TTLCache, ResourceMonitor, DegradationTracker│
└─────────────────────────────────────────────────────────────┘
```

## Key Interfaces

### InferenceEngine (ABC)

All ML classifiers implement:
- `classify(image_path) -> dict` with smoke_probability, confidence, model metadata
- `get_model_info() -> dict`

Modes: MockClassifier (deterministic), RealSmokeClassifier (PyTorch)

### AIService

Live external vision AI via OpenRouter/Groq:
- Structured prompt → JSON response
- Pydantic validation of AI output
- Provider failover (OpenRouter → Groq → Mock)
- Rate limiting and timeout management

### SGP4OrbitService

- Accepts TLE, Keplerian elements, or simple altitude/inclination
- CelesTrak integration for real TLE data
- Falls back to analytical circular orbit model

### CameraSimulator

- Generates synthetic Earth observation images
- Deterministic based on timestamp and position
- Interface supports real Raspberry Pi camera replacement

### SimulationEngine

- Fault injection (battery, camera, ADCS, comms, eclipse)
- Ground station network pass detection
- Downlink queue processing
- FIRMS correlation with weather fusion
- Mission event logging
- Configurable simulation speed

### EPSModel

- Per-subsystem power consumption (OBC, ADCS, Comms, Camera, ML, Thermal)
- Battery SOC tracking (coulomb counting)
- Solar generation vs consumption
- Eclipse detection
- Load shedding with priority-based decisions
- Power budget events (LOW_POWER, CRITICAL, EMERGENCY)

### ThermalModel

- 5-node thermal simulation (OBC, Battery, Camera, Comms, Structure)
- Solar heating, Earth albedo, Earth IR
- Radiative cooling to deep space
- Inter-node conduction
- Safe operating range tracking
- Thermal mode states (NOMINAL, WARMING, COOLING, CRITICAL_HOT, CRITICAL_COLD)

### FaultRecoveryService

- Autonomous recovery handlers per subsystem
- Retry logic with configurable max retries
- Cooldown periods between attempts
- Recovery actions: camera reboot, comm failover, GPS propagate, battery shed, thermal emergency, OBC watchdog

### FireCorrelationService

- Weighted probability fusion (AI: 0.40, FIRMS: 0.35, Weather: 0.25)
- FIRMS hotspot proximity matching
- Weather condition analysis (wind speed, humidity, temperature)
- Priority boost based on fused probability
- Configurable correlation threshold

### GroundNetworkService

- 5 pre-configured global ground stations
- Pass detection with visibility windows
- Link budget calculations (data rate, SNR, link margin)
- Station handoff events
- Elevation and azimuth calculation

## Ground Station Network

| Station | Location | Latitude | Longitude | Data Rate |
|---------|----------|----------|-----------|-----------|
| GS-BOULDER | Boulder, CO | 40.0°N | 105.3°W | 256 kbps |
| GS-FAIRBANKS | Fairbanks, AK | 64.9°N | 147.7°W | 512 kbps |
| GS-SVALBARD | Svalbard, Norway | 78.2°N | 15.6°E | 1024 kbps |
| GS-SINGAPORE | Singapore | 1.3°N | 103.8°E | 256 kbps |
| GS-SANTIAGO | Santiago, Chile | 33.4°S | 70.6°W | 512 kbps |

## Frontend Architecture

```
Pages (app/page.tsx)
    ↓
Feature Components:
    ├── Globe (CesiumJS 3D Earth — ground track, FIRMS, footprint)
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

## WebSocket Protocol

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
    },
    "recent_events": [...],
    "resource_stats": {
      "memory_mb": 45.2,
      "degradation": "none"
    }
  }
}
```

## Persistence Layer

SQLite database (`data/cubesat_twin.db`) stores:

| Table | Contents |
|-------|----------|
| `observations` | All captured observations with metadata |
| `telemetry` | Periodic telemetry snapshots |
| `events` | Mission events with severity levels |
| `sessions` | Replay session metadata |

Resource management ensures bounded memory usage:
- `BoundedList` — Caps in-memory collections with eviction
- `TTLCache` — Time-based cache expiration for FIRMS/TLE data
- `ResourceMonitor` — Tracks memory usage and triggers degradation
- `CleanupScheduler` — Periodic cache cleanup tasks
