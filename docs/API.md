# API Reference

Base URL: `http://localhost:8000`

## Health

### GET /api/v1/health

```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2026-09-17T00:00:00Z",
  "simulation_running": false
}
```

## Configuration

### GET /api/v1/config

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

## Spacecraft State

### GET /api/v1/spacecraft/state

Returns current `SpacecraftState` with position, attitude, power, thermal, and subsystem status.

## Telemetry

### GET /api/v1/telemetry/latest

Returns latest `TelemetryPacket`.

### GET /api/v1/telemetry/history?limit=100

Returns list of recent telemetry packets.

## Observations

### GET /api/v1/observations?limit=20

Returns list of observations (most recent first).

### GET /api/v1/observations/{observation_id}

Returns specific observation record.

## Simulation Control

### POST /api/v1/simulation/start

```json
{ "status": "started", "running": true }
```

### POST /api/v1/simulation/stop

```json
{ "status": "stopped", "running": false }
```

### POST /api/v1/simulation/reset

```json
{ "status": "reset", "running": false }
```

## Environment

### GET /api/v1/environment/weather?lat=35.0&lon=-120.0

Weather data from Open-Meteo.

### GET /api/v1/environment/air-quality?lat=35.0&lon=-120.0

Air quality data from Open-Meteo.

### GET /api/v1/environment/hotspots?north=90&south=-90&east=180&west=-180&days=1

FIRMS wildfire hotspot data.

## WebSocket

### WS /ws/telemetry

Streams telemetry packets as JSON:

```json
{
  "type": "telemetry",
  "payload": { ...TelemetryPacket }
}
```

Send `{"type": "ping"}` to receive `{"type": "pong"}`.

## Schemas

### TelemetryPacket

| Field | Type | Description |
|---|---|---|
| packet_sequence | int | Packet counter |
| timestamp | datetime | UTC timestamp |
| spacecraft_id | string | Spacecraft identifier |
| mission_mode | string | Current mission mode |
| latitude | float | Degrees |
| longitude | float | Degrees |
| altitude_km | float | Kilometers |
| velocity_km_s | float | km/s |
| heading_deg | float | Degrees |
| roll_deg, pitch_deg, yaw_deg | float | Attitude (degrees) |
| battery_percentage | float | 0-100% |
| battery_voltage | float | Volts |
| power_generation_w | float | Watts |
| power_consumption_w | float | Watts |
| temperatures | dict | Component temperatures (°C) |
| communication_status | string | Subsystem status |
| gps_status | string | Subsystem status |
| camera_status | string | Subsystem status |
| ml_status | string | Subsystem status |
| current_observation_id | string? | Active observation |
| smoke_probability | float? | 0-1 |
| confidence | float? | 0-1 |
| priority | string? | CRITICAL/HIGH/MEDIUM/LOW |

### Observation

| Field | Type | Description |
|---|---|---|
| observation_id | string | Unique ID |
| timestamp | datetime | Capture time |
| spacecraft_id | string | Spacecraft |
| latitude, longitude | float | Position |
| altitude_km | float | Altitude |
| image_path | string | Image file path |
| smoke_probability | float? | 0-1 |
| confidence | float? | 0-1 |
| priority | string | CRITICAL/HIGH/MEDIUM/LOW |
| model_name | string? | ML model used |
| inference_latency_ms | float? | Inference time |
