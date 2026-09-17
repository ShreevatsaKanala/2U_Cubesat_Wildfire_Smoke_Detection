# 2U CubeSat Wildfire Smoke Detection — Digital Twin

System-level digital twin for a 2U CubeSat concept using an RGB camera and onboard AI/ML for probable wildfire/smoke indication and intelligent image prioritisation.

## Scope

This repository is an engineering demonstrator and simulation environment. It is not flight-qualified hardware or a definitive autonomous fire-confirmation system.

## Planned mission chain

`Simulated pass → observation → RGB image → onboard inference → probability/confidence → image priority → telemetry/downlink → ground dashboard`

## Phase 1

The first implementation milestone will provide:

- 3D Earth/CubeSat visualisation
- simulated orbit and spacecraft state
- live telemetry via WebSocket
- simulated RGB observation pipeline
- pluggable smoke/wildfire inference interface
- probability/priority mission logic
- NASA FIRMS, NASA GIBS, Open-Meteo and CelesTrak adapters
- ground-station dashboard

## Security

Real credentials must never be committed. Store them in a local `.env` file and keep `.env` ignored by Git.

See `docs/CUBESAT_TWIN_SPEC.md` for the engineering specification and `prompts/OPENCODE_PHASE_1.md` for the OpenCode/MiMo V2.5 implementation prompt.
