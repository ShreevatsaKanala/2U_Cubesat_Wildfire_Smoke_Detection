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

## Simulation Capabilities

### Orbit Propagation

- **SGP4** with CelesTrak TLE integration
- Analytical circular orbit fallback
- Configurable altitude, inclination, epoch
- Real-time position and velocity propagation

### Camera Simulation

- Synthetic Earth observation image generation
- Gradient-based terrain simulation
- Deterministic based on timestamp and position
- Interface supports real Raspberry Pi camera replacement

### ML Pipeline

- **Mock mode**: Deterministic hash-based classifier for testing
- **Real mode**: PyTorch model inference (MobileNetV3, ONNX)
- Training scripts for custom model development
- Preprocessing: resize, normalize, tensor conversion
- Priority calculation from smoke probability × confidence

### AI Vision Analysis

- **Live mode**: External vision AI via OpenRouter/Groq
- Structured JSON response with smoke score and reasoning
- Provider failover (OpenRouter → Groq → Mock)
- Rate limiting and timeout management
- Pydantic validation of AI output

### FIRMS + Weather Correlation

- Weighted probability fusion (AI: 0.40, FIRMS: 0.35, Weather: 0.25)
- FIRMS hotspot proximity matching
- Weather condition analysis (wind, humidity, temperature)
- Priority boost based on fused probability
- Configurable correlation threshold

### Ground Network

- 5 pre-configured global ground stations
- Pass detection with visibility windows
- Link budget calculations (data rate, SNR, margin)
- Station handoff events
- Elevation and azimuth calculation

### Downlink Simulation

- Priority-ordered queue management
- Realistic transfer simulation
- TX/fail statistics
- Queue scheduling and prioritization

### Fault Recovery

- Autonomous recovery handlers per subsystem
- Retry logic with configurable max retries
- Cooldown periods between attempts
- Recovery actions: camera reboot, comm failover, GPS propagate, battery shed, thermal emergency, OBC watchdog

### EPS Model

- Per-subsystem power consumption tracking
- Battery SOC (coulomb counting)
- Solar generation vs consumption
- Eclipse detection
- Load shedding with priority-based decisions
- Power budget events (LOW_POWER, CRITICAL, EMERGENCY)

### Thermal Model

- 5-node thermal simulation (OBC, Battery, Camera, Comms, Structure)
- Solar heating, Earth albedo, Earth IR
- Radiative cooling to deep space
- Inter-node conduction
- Safe operating range tracking
- Thermal mode states (NOMINAL, WARMING, COOLING, CRITICAL_HOT, CRITICAL_COLD)

### Persistence

- SQLite database (async via aiosqlite)
- Observations, telemetry, events, sessions
- Bounded memory with TTL caches
- Resource monitoring and degradation tracking

### Replay & Export

- Session recording and playback
- Variable speed replay
- Streaming JSON/CSV export
- Date-filtered data export

## Mission Chain

```
1. TLE Refresh
   → CelesTrak provides updated TLE data
   → Cached with configurable TTL

2. Orbit Propagation
   → SGP4 propagates position and velocity
   → Spacecraft state evolves over time

3. EPS Model
   → Per-subsystem power consumption
   → Battery SOC tracking
   → Solar generation and eclipse detection
   → Load shedding if power critical

4. Thermal Model
   → 5-node thermal simulation
   → Solar heating, Earth albedo, internal dissipation
   → Radiative cooling to deep space

5. ADCS Simulation
   → NADIR, SUN_SYNC, INERTIAL attitude modes
   → Quaternion noise, pointing error

6. Fault Injection
   → Battery, camera, ADCS, comms, eclipse faults
   → Autonomous recovery attempts

7. Camera Capture
   → Synthetic Earth observation image

8. ML Inference
   → Probable smoke/wildfire signature detection
   → Probability, confidence, model metadata

9. AI Vision Analysis
   → External vision AI (OpenRouter/Groq)
   → Structured JSON response

10. Priority Decision
    → Weighted scoring of probability × confidence
    → CRITICAL / HIGH / MEDIUM / LOW

11. FIRMS Correlation
    → Fuse AI detection with FIRMS hotspots
    → Weather condition analysis
    → Fused fire probability

12. Ground Station Network
    → Pass detection across 5 global stations
    → Visibility window calculation

13. Downlink Queue
    → Priority-ordered observation transmission
    → Queue management with TX/fail statistics

14. Persistence
    → Store observation to SQLite database
    → Telemetry snapshots
    → Mission event logging

15. Replay Recording
    → Session metadata for later playback

16. Telemetry Broadcast
    → WebSocket streaming to dashboard
    → Real-time state updates
```

## Uncertainty Language

The system uses carefully chosen terminology:

- "Probable smoke signature" (not "fire detected")
- "High-priority observation" (not "confirmed wildfire")
- "Requires ground verification" (not "alert")
- "AI Smoke Score" (not "probability of fire")
- Probability and confidence values are always displayed

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

# Ground Network (5 stations)
ground_stations = [
    {"name": "Boulder, CO", "lat": 40.0, "lon": -105.3},
    {"name": "Fairbanks, AK", "lat": 64.9, "lon": -147.7},
    {"name": "Svalbard, Norway", "lat": 78.2, "lon": 15.6},
    {"name": "Singapore", "lat": 1.3, "lon": 103.8},
    {"name": "Santiago, Chile", "lat": -33.4, "lon": -70.6},
]

# Correlation weights
WEIGHT_AI = 0.40
WEIGHT_FIRMS = 0.35
WEIGHT_WEATHER = 0.25
```

## Deterministic Mode

The simulation is deterministic when given the same initial conditions:
- Orbit propagates identically
- Observations trigger at same intervals
- Mock classifier produces same results for same inputs
- Attitude variations use time-based seeding

This enables replay and comparison of simulation runs.

## Phase Evolution

| Component | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|-----------|---------|---------|---------|---------|---------|
| Orbit | Analytical | SGP4 | SGP4 + CelesTrak | SGP4 + CelesTrak | SGP4 + CelesTrak |
| Camera | Synthetic | Synthetic | Synthetic | Synthetic | Synthetic |
| ML | Mock | Mock | Mock + Real | Mock + Real | Mock + Real |
| AI | — | — | — | Live (OpenRouter/Groq) | Live + Failover |
| Persistence | In-memory | In-memory | In-memory | In-memory | SQLite |
| Comms | WebSocket | WebSocket + Downlink | Downlink Queue | Downlink Queue | Downlink Queue |
| Power | Simple | Coulomb counting | Coulomb + Eclipse | EPS per-subsystem | EPS + Load shedding |
| Thermal | Basic | Multi-node | 5-node | 5-node | 5-node |
| ADCS | Quaternion | NADIR/SUN_SYNC | NADIR/SUN_SYNC | NADIR/SUN_SYNC | NADIR/SUN_SYNC |
| Fault Mgmt | None | Inject/Clear | Inject/Clear | Inject/Clear | Autonomous Recovery |
| Ground Stn | None | Single station | Single station | Single station | 5-station network |
| Correlation | — | — | — | — | FIRMS + Weather fusion |
| Replay | — | — | — | — | Session recording + playback |
| Export | — | — | — | — | JSON/CSV streaming |
