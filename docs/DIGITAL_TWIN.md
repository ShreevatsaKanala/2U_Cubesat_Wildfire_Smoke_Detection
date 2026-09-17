# Digital Twin

## What is a Digital Twin?

A digital twin is a virtual representation of a physical system that mirrors its real-world counterpart's state, behaviour, and environment. This project creates a system-level digital twin of a 2U CubeSat for wildfire smoke detection.

## Simulation vs Reality

**This is a simulation environment.** All spacecraft parameters are configurable simulation values:

- Orbital parameters (altitude, inclination, period)
- Spacecraft mass, dimensions, power budget
- Camera field of view, resolution
- Battery capacity, voltage, thermal limits
- ML model performance characteristics
- Telemetry rates, downlink budgets

None of these represent actual flight hardware specifications.

## Mission Chain

```
1. Orbit Propagation
   → Spacecraft position and attitude evolve over time

2. Power Model
   → Battery SOC, solar generation, eclipse detection
   → Coulomb counting with configurable efficiency

3. Thermal Model
   → Multi-node thermal simulation
   → Solar heating, Earth albedo, internal dissipation
   → Radiative cooling to deep space

4. ADCS Simulation
   → NADIR, SUN_SYNC, INERTIAL attitude modes
   → Quaternion noise, pointing error

5. Fault Injection (Phase 2)
   → Battery, camera, ADCS, comms, eclipse faults
   → Real-time fault state changes

6. Observation Trigger
   → Camera captures image at configurable intervals

7. Image Generation
   → Synthetic Earth observation image (gradient + terrain simulation)

8. ML Inference
   → Probable smoke/wildfire signature detection
   → Probability, confidence, model metadata

9. Priority Decision
   → Weighted scoring of probability × confidence
   → CRITICAL / HIGH / MEDIUM / LOW

10. Ground Station Pass Check
    → Visibility window detection
    → Elevation and azimuth calculation

11. Downlink Queue
    → Priority-ordered observation transmission
    → Queue management with TX/fail statistics

12. Telemetry Event
    → Observation record created
    → State broadcast via WebSocket
    → Mission events logged

13. Ground Dashboard
    → 3D Cesium globe with spacecraft position
    → Ground track, camera footprint, FIRMS markers
    → Live telemetry, power, thermal, health panels
    → Fault injection, event log, downlink queue
```

## Uncertainty Language

The system uses carefully chosen terminology:

- "Probable smoke signature" (not "fire detected")
- "High-priority observation" (not "confirmed wildfire")
- "Requires ground verification" (not "alert")
- Probability and confidence values are always displayed

## Pluggable Subsystems

| Component | Phase 1 | Phase 2 | Future |
|---|---|---|---|
| Orbit | Analytical circular | SGP4 with analytical fallback | Full SGP4 with real TLE |
| Camera | Synthetic images | Synthetic images | Raspberry Pi capture |
| ML | Mock classifier | Mock classifier (pipeline ready) | MobileNet/ONNX/TFLite |
| Persistence | In-memory | In-memory | SQLite → PostgreSQL |
| Comms | WebSocket only | WebSocket + downlink queue | Actual downlink sim |
| Power | Simple model | Coulomb counting, eclipse | Subsystem-level EPS |
| Thermal | Basic model | Multi-node thermal | Detailed thermal |
| ADCS | Quaternion noise | NADIR/SUN_SYNC/INERTIAL modes | Full attitude control |
| Fault Mgmt | None | Inject/clear 5 fault types | Autonomous recovery |
| Ground Stn | None | Pass detection, visibility | Multi-station network |

## Configuration

All simulation parameters live in configuration, not hard-coded:

```python
# Orbital parameters
altitude_km = 500.0
inclination_deg = 97.4  # Sun-synchronous

# Spacecraft
mass_kg = 2.6
battery_capacity_wh = 40.0
solar_generation_w = 2.0

# Simulation
sim_speed = 1.0
telemetry_frequency_hz = 1.0
observation_interval_s = 30.0

# Ground Station
ground_station_lat = 37.7749
ground_station_lon = -122.4194
min_elevation_deg = 10.0
```

## Deterministic Mode

The simulation is deterministic when given the same initial conditions:
- Orbit propagates identically
- Observations trigger at same intervals
- Mock classifier produces same results for same inputs
- Attitude variations use time-based seeding

This enables replay and comparison of simulation runs.
