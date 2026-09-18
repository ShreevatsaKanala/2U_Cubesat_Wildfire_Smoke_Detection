# API Reference

Base URL: `http://localhost:8000`

All endpoints are under `/api/v1/` unless noted otherwise. The system returns JSON responses.

---

## Core Simulation

### GET /api/v1/health

Health check endpoint.

```json
{
  "status": "ok",
  "version": "0.3.0",
  "timestamp": "2026-09-18T00:00:00Z",
  "simulation_running": false
}
```

### GET /api/v1/config

Returns spacecraft and simulation configuration.

```json
{
  "spacecraft": {
    "spacecraft_id": "CSAT-001",
    "name": "2U CubeSat Wildfire Twin",
    "mass_kg": 2.6,
    "battery_capacity_wh": 40.0,
    "solar_generation_w": 2.0,
    "power_consumption_w": 1.5
  },
  "simulation": {
    "speed": 1.0,
    "telemetry_frequency_hz": 1.0,
    "observation_interval_s": 30.0,
    "running": false
  }
}
```

### POST /api/v1/simulation/start

Starts the simulation loop.

```json
{ "status": "started", "running": true }
```

### POST /api/v1/simulation/stop

Stops the simulation loop.

```json
{ "status": "stopped", "running": false }
```

### POST /api/v1/simulation/resume

Resumes a paused simulation.

```json
{ "status": "resumed", "running": true }
```

### POST /api/v1/simulation/reset

Resets simulation to initial state.

```json
{ "status": "reset", "running": false }
```

### GET /api/v1/simulation/status

Returns current simulation status including speed and elapsed time.

```json
{
  "running": true,
  "sim_speed": 1.0,
  "elapsed_seconds": 3600.0,
  "step_count": 3600,
  "steps_per_second": 1.0
}
```

---

## Spacecraft State

### GET /api/v1/spacecraft/state

Returns full `SpacecraftState` with nested position, attitude, power, thermal, and health objects.

### GET /api/v1/spacecraft/health

Returns subsystem health status:

```json
{
  "overall": "NOMINAL",
  "eps": {"status": "NOMINAL", "uptime_s": 1000},
  "obc": {"status": "NOMINAL", "uptime_s": 1000},
  "comms": {"status": "NOMINAL", "uptime_s": 1000},
  "adcs": {"status": "NOMINAL", "uptime_s": 1000},
  "camera": {"status": "NOMINAL", "uptime_s": 1000},
  "gps": {"status": "NOMINAL", "uptime_s": 1000}
}
```

### GET /api/v1/spacecraft/power

Returns power subsystem state:

```json
{
  "battery_soc": 85.5,
  "battery_voltage": 7.4,
  "solar_generation_w": 2.5,
  "power_consumption_w": 1.8,
  "power_balance_w": 0.7,
  "eclipse": false,
  "battery_temperature_c": 22.0
}
```

### GET /api/v1/spacecraft/thermal

Returns thermal node temperatures:

```json
{
  "nodes": [
    {"name": "solar_panel_plus_y", "temperature_c": 45.0, "min_safe_c": -20.0, "max_safe_c": 60.0},
    {"name": "battery", "temperature_c": 22.0, "min_safe_c": 0.0, "max_safe_c": 45.0}
  ]
}
```

### GET /api/v1/spacecraft/attitude

Returns ADCS attitude state:

```json
{
  "roll_deg": 0.1,
  "pitch_deg": -0.2,
  "yaw_deg": 45.0,
  "attitude_mode": "NADIR",
  "pointing_error_deg": 0.3,
  "roll_rate_dps": 0.01,
  "pitch_rate_dps": -0.02,
  "yaw_rate_dps": 0.005
}
```

---

## Telemetry

### GET /api/v1/telemetry/latest

Returns latest `TelemetryPacket`.

---

## Observations

### POST /api/v1/observations/capture

Triggers a manual observation capture.

### GET /api/v1/observations?limit=20&offset=0

Returns paginated observations:

```json
{
  "observations": [...],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

### GET /api/v1/observations/{observation_id}

Returns specific observation record. Returns 404 if not found.

---

## AI Analysis

### GET /api/v1/ai/status

Returns AI vision service status:

```json
{
  "mode": "live",
  "provider": "openrouter",
  "model": "google/gemini-2.0-flash-001",
  "failover_enabled": true,
  "failover_provider": "groq",
  "requests_this_minute": 3,
  "max_requests_per_minute": 10,
  "total_analyses": 42
}
```

### POST /api/v1/ai/analyze

Manually trigger AI analysis on the latest observation.

```json
{
  "observation_id": "obs-001",
  "ai_smoke_score": 0.72,
  "ai_confidence": 0.85,
  "provider": "openrouter"
}
```

---

## Ground Stations

### GET /api/v1/ground-station/network

Returns all ground stations in the network:

```json
{
  "stations": [
    {
      "station_id": "GS-BOULDER",
      "name": "Boulder, CO",
      "latitude": 40.0,
      "longitude": -105.3,
      "altitude_m": 1655.0,
      "status": "active",
      "link_budget": {
        "data_rate_kbps": 256.0,
        "snr_db": 18.5,
        "link_margin_db": 6.2,
        "frequency_ghz": 2.2
      }
    }
  ],
  "total_stations": 5
}
```

### GET /api/v1/ground-station/visibility

Returns visibility windows for all stations:

```json
{
  "windows": [
    {
      "station_id": "GS-BOULDER",
      "station_name": "Boulder, CO",
      "aos_time": "2026-09-18T14:30:00Z",
      "los_time": "2026-09-18T14:38:00Z",
      "max_elevation_deg": 65.0,
      "duration_seconds": 480
    }
  ]
}
```

### GET /api/v1/ground-station/status

Returns current ground station pass status:

```json
{
  "distance_km": 1234.5,
  "is_visible": false,
  "next_pass_s": 3600,
  "elevation_deg": 0.0,
  "azimuth_deg": 0.0,
  "closest_station": "GS-BOULDER"
}
```

### GET /api/v1/ground-station/config

Returns primary ground station configuration:

```json
{
  "name": "Primary Ground Station",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "altitude_m": 10.0,
  "min_elevation_deg": 10.0
}
```

---

## Downlink

### GET /api/v1/downlink/status

Returns downlink queue status:

```json
{
  "queue": [
    {
      "id": "dl-001",
      "observation_id": "obs-001",
      "size_bytes": 1024,
      "priority": "HIGH",
      "created_at": "2026-09-18T00:00:00Z",
      "status": "pending"
    }
  ],
  "total_transmitted": 42,
  "total_failed": 2,
  "total_pending": 5
}
```

### GET /api/v1/downlink/queue

Returns current queue contents sorted by priority.

### POST /api/v1/downlink/schedule

Schedule an observation for downlink:

```json
{
  "observation_id": "obs-001",
  "priority": "HIGH"
}
```

---

## FIRMS

### GET /api/v1/firms/status

Returns FIRMS adapter status:

```json
{
  "adapter_status": "configured",
  "api_key_set": true,
  "cache_size": 150,
  "cache_evicted": 12,
  "last_fetch_time": "2026-09-18T00:00:00Z",
  "total_hotspots": 450
}
```

### GET /api/v1/firms/detections

Returns FIRMS hotspot detections:

```json
{
  "hotspots": [
    {
      "latitude": 34.5,
      "longitude": -118.2,
      "brightness": 320.5,
      "frp": 15.2,
      "confidence": 80,
      "timestamp": "2026-09-18T00:00:00Z"
    }
  ],
  "total": 450
}
```

---

## Correlation

### GET /api/v1/correlation/status

Returns correlation service status:

```json
{
  "correlations_performed": 12,
  "last_correlation_time": "2026-09-18T00:00:00Z",
  "fused_events_generated": 3,
  "weights": {
    "ai": 0.40,
    "firms": 0.35,
    "weather": 0.25
  }
}
```

### POST /api/v1/correlation/analyze

Trigger correlation analysis for recent observations:

```json
{
  "observation_id": "obs-001",
  "fused_probability": 0.68,
  "ai_contribution": 0.29,
  "firms_contribution": 0.24,
  "weather_contribution": 0.15,
  "priority_boost": "HIGH"
}
```

---

## Recovery

### GET /api/v1/recovery/status

Returns fault recovery service status:

```json
{
  "handlers": {
    "camera_reboot": {
      "state": "idle",
      "attempts": 0,
      "max_retries": 3
    },
    "comm_failover": {
      "state": "recovered",
      "attempts": 1,
      "last_recovery_time": "2026-09-18T00:00:00Z"
    }
  },
  "total_recoveries": 5,
  "active_recoveries": 0
}
```

### POST /api/v1/recovery/trigger

Manually trigger a recovery action:

```json
{
  "action": "camera_reboot"
}
```

---

## EPS

### GET /api/v1/eps/status

Returns detailed EPS status:

```json
{
  "battery_soc": 85.5,
  "battery_voltage": 7.4,
  "battery_temperature_c": 22.0,
  "solar_generation_w": 2.5,
  "total_consumption_w": 1.8,
  "power_balance_w": 0.7,
  "eclipse": false,
  "subsystems": [
    {
      "name": "obc",
      "nominal_w": 0.5,
      "peak_w": 0.8,
      "is_active": true,
      "duty_cycle": 1.0,
      "is_shed": false
    }
  ],
  "load_shedding_active": false,
  "power_budget_events": []
}
```

---

## Thermal

### GET /api/v1/thermal/status

Returns thermal model status:

```json
{
  "mode": "NOMINAL",
  "nodes": [
    {
      "name": "obc",
      "temperature_c": 28.5,
      "heat_dissipation_w": 0.5,
      "solar_heating_w": 0.1,
      "earth_albedo_w": 0.05,
      "earth_ir_w": 0.1,
      "radiative_cooling_w": -0.3,
      "conduction_w": 0.0,
      "min_safe_c": -40.0,
      "max_safe_c": 70.0
    }
  ],
  "critical_nodes": [],
  "thermal_balance": "stable"
}
```

---

## TLE

### GET /api/v1/tle/status

Returns TLE service status:

```json
{
  "norad_id": "55000",
  "has_tle": true,
  "source": "celestrak",
  "last_refresh": "2026-09-18T00:00:00Z",
  "cache_age_hours": 2.5,
  "tle_line1": "1 55000U ...",
  "tle_line2": "2 55000 ..."
}
```

### POST /api/v1/tle/refresh

Force refresh TLE data from CelesTrak.

```json
{
  "status": "refreshed",
  "has_tle": true,
  "source": "celestrak"
}
```

---

## History

### GET /api/v1/history/observations?days=7&limit=100

Returns observation history from SQLite:

```json
{
  "observations": [...],
  "total": 150,
  "days": 7
}
```

### GET /api/v1/history/telemetry?days=1&limit=100

Returns telemetry history.

### GET /api/v1/history/events?days=7&limit=100

Returns event history.

### GET /api/v1/history/stats

Returns aggregated statistics:

```json
{
  "total_observations": 150,
  "total_events": 420,
  "total_telemetry_snapshots": 1440,
  "smoke_detections": 12,
  "avg_ai_score": 0.45,
  "uptime_hours": 24.5
}
```

---

## Replay

### GET /api/v1/replay/sessions

Returns list of recorded sessions:

```json
{
  "sessions": [
    {
      "session_id": "sess-001",
      "start_time": "2026-09-18T00:00:00Z",
      "end_time": "2026-09-18T01:00:00Z",
      "total_observations": 120,
      "total_events": 350
    }
  ]
}
```

### GET /api/v1/replay/playback

Returns current playback state.

### POST /api/v1/replay/playback

Control playback:

```json
{
  "action": "start",
  "session_id": "sess-001",
  "speed": 2.0
}
```

---

## Export

### GET /api/v1/export/observations?format=json&date_from=2026-09-01&date_to=2026-09-18

Export observations as JSON or CSV:

```json
{
  "format": "json",
  "count": 150,
  "data": [...]
}
```

### GET /api/v1/export/telemetry?format=csv

Export telemetry data.

### GET /api/v1/export/events

Export mission events.

---

## Events

### GET /api/v1/events

Returns mission event log (most recent first):

```json
[
  {
    "id": "evt-001",
    "timestamp": "2026-09-18T00:00:00Z",
    "event_type": "OBSERVATION",
    "severity": "INFO",
    "message": "Observation captured",
    "data": {}
  }
]
```

---

## Environment

### GET /api/v1/environment/weather?lat=35.0&lon=-120.0

Weather data from Open-Meteo:

```json
{
  "temperature_c": 28.5,
  "wind_speed_kmh": 15.2,
  "wind_direction_deg": 270,
  "humidity_percent": 45,
  "precipitation_mm": 0.0
}
```

### GET /api/v1/environment/air-quality?lat=35.0&lon=-120.0

Air quality data from Open-Meteo.

### GET /api/v1/environment/hotspots?north=90&south=-90&east=180&west=-180&days=1

FIRMS wildfire hotspot data.

---

## Fault Injection

### GET /api/v1/faults

Returns current fault states:

```json
{
  "battery_low": false,
  "camera_failure": false,
  "adcs_failure": false,
  "comms_failure": false,
  "eclipse_stuck": false
}
```

### POST /api/v1/faults/inject

Inject faults:

```json
{ "battery_low": true, "camera_failure": true }
```

### POST /api/v1/faults/clear

Clear all faults:

```json
{
  "battery_low": false,
  "camera_failure": false,
  "adcs_failure": false,
  "comms_failure": false,
  "eclipse_stuck": false
}
```

---

## System

### GET /api/system/resources

Returns system resource statistics:

```json
{
  "memory_mb": 45.2,
  "degradation": "none",
  "caches": {
    "firms": {"size": 150, "evicted": 12},
    "tle": {"size": 1, "evicted": 0}
  },
  "connected_websockets": 2,
  "simulation_running": true
}
```

---

## WebSocket

### WS /ws/telemetry

Streams telemetry packets as JSON:

```json
{
  "type": "telemetry",
  "payload": { ...TelemetryPacket }
}
```

Each telemetry packet includes:

- `packet_sequence` — Incrementing sequence number
- `timestamp` — ISO 8601 timestamp
- `spacecraft_id` — Spacecraft identifier
- `mission_mode` — Current mission mode
- `position` — Lat/lon/alt/velocity
- `attitude` — Roll/pitch/yaw with mode
- `power` — Battery, solar, consumption, eclipse
- `thermal` — Node temperatures with safe ranges
- `health` — Subsystem health status
- `recent_events` — Last 3 mission events
- `resource_stats` — Memory and degradation info

Send `{"type": "ping"}` to receive `{"type": "pong"}` for keepalive.
