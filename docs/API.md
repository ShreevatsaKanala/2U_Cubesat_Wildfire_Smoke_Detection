# API Reference

Base URL: `http://localhost:8000`

## Health

### GET /api/v1/health

```json
{
  "status": "ok",
  "version": "0.2.0",
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

## Spacecraft

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

## Telemetry

### GET /api/v1/telemetry/latest

Returns latest `TelemetryPacket`.

## Observations

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

## Events

### GET /api/v1/events

Returns mission event log (most recent first):

```json
[
  {
    "id": "evt-001",
    "timestamp": "2026-09-17T00:00:00Z",
    "event_type": "OBSERVATION",
    "severity": "INFO",
    "message": "Observation captured",
    "data": {}
  }
]
```

## Ground Station

### GET /api/v1/ground-station/status

Returns current ground station pass status:

```json
{
  "distance_km": 1234.5,
  "is_visible": false,
  "next_pass_s": 3600,
  "elevation_deg": 0.0,
  "azimuth_deg": 0.0
}
```

### GET /api/v1/ground-station/config

Returns ground station configuration:

```json
{
  "name": "Primary Ground Station",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "altitude_m": 10.0,
  "min_elevation_deg": 10.0
}
```

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
      "created_at": "2026-09-17T00:00:00Z",
      "status": "pending"
    }
  ],
  "total_transmitted": 42,
  "total_failed": 2
}
```

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
