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
   
2. Observation Trigger
   → Camera captures image at configurable intervals
   
3. Image Generation
   → Synthetic Earth observation image (gradient + terrain simulation)
   
4. ML Inference
   → Probable smoke/wildfire signature detection
   → Probability, confidence, model metadata
   
5. Priority Decision
   → Weighted scoring of probability × confidence
   → CRITICAL / HIGH / MEDIUM / LOW
   
6. Telemetry Event
   → Observation record created
   → State broadcast via WebSocket
   
7. Ground Dashboard
   → 3D Cesium globe with spacecraft position
   → Live telemetry panels
   → Observation center with ML results
```

## Uncertainty Language

The system uses carefully chosen terminology:

- "Probable smoke signature" (not "fire detected")
- "High-priority observation" (not "confirmed wildfire")
- "Requires ground verification" (not "alert")
- Probability and confidence values are always displayed

## Pluggable Subsystems

Every major component is behind an interface:

| Component | Phase 1 | Future |
|---|---|---|
| Orbit | Analytical circular | SGP4 with real TLE |
| Camera | Synthetic images | Raspberry Pi capture |
| ML | Mock classifier | MobileNet/ONNX/TFLite |
| Persistence | In-memory | SQLite → PostgreSQL |
| Comms | WebSocket only | Actual downlink sim |
| Power | Simple model | Subsystem-level EPS |
| Thermal | Basic model | Multi-node thermal |
| ADCS | Quaternion noise | Full attitude control |

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
```

## Deterministic Mode

The simulation is deterministic when given the same initial conditions:
- Orbit propagates identically
- Observations trigger at same intervals
- Mock classifier produces same results for same inputs
- Attitude variations use time-based seeding

This enables replay and comparison of simulation runs.
