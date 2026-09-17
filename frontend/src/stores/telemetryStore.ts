import { create } from "zustand";

export interface TelemetryPosition {
  latitude: number;
  longitude: number;
  altitude_km: number;
  velocity_km_s: number;
  heading_deg: number;
}

export interface TelemetryAttitude {
  roll_deg: number;
  pitch_deg: number;
  yaw_deg: number;
  attitude_mode: string;
  pointing_error_deg: number;
  roll_rate_dps: number;
  pitch_rate_dps: number;
  yaw_rate_dps: number;
}

export interface TelemetryPower {
  battery_soc: number;
  battery_voltage: number;
  solar_generation_w: number;
  power_consumption_w: number;
  power_balance_w: number;
  eclipse: boolean;
  battery_temperature_c: number;
}

export interface ThermalNode {
  name: string;
  temperature_c: number;
  min_safe_c: number;
  max_safe_c: number;
}

export interface TelemetryThermal {
  nodes: ThermalNode[];
}

export interface SubsystemHealth {
  status: string;
  uptime_s: number;
}

export interface TelemetryHealth {
  overall: string;
  eps: SubsystemHealth;
  obc: SubsystemHealth;
  comms: SubsystemHealth;
  adcs: SubsystemHealth;
  camera: SubsystemHealth;
  gps: SubsystemHealth;
}

export interface SpacecraftTelemetry {
  packet_sequence: number;
  timestamp: string;
  spacecraft_id: string;
  mission_mode: string;
  position: TelemetryPosition;
  attitude: TelemetryAttitude;
  power: TelemetryPower;
  thermal: TelemetryThermal;
  health: TelemetryHealth;
  communication_status: string;
  camera_status: string;
  current_observation_id: string | null;
  smoke_probability: number | null;
  confidence: number | null;
  priority: string | null;
}

export interface Observation {
  observation_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  altitude_km: number;
  image_path: string;
  smoke_probability: number | null;
  wildfire_probability: number | null;
  confidence: number | null;
  priority: string;
  model_name: string | null;
  model_version: string | null;
  inference_latency_ms: number | null;
  processing_status: string;
}

export interface MissionEvent {
  id: string;
  timestamp: string;
  event_type: string;
  severity: string;
  message: string;
  data: Record<string, unknown> | null;
}

export interface GroundStationStatus {
  distance_km: number;
  is_visible: boolean;
  next_pass_s: number;
  elevation_deg: number;
  azimuth_deg: number;
}

export interface DownlinkQueueItem {
  id: string;
  observation_id: string;
  size_bytes: number;
  priority: string;
  created_at: string;
  status: string;
}

export interface DownlinkStatus {
  queue: DownlinkQueueItem[];
  total_transmitted: number;
  total_failed: number;
}

export interface Faults {
  battery_low: boolean;
  camera_failure: boolean;
  adcs_failure: boolean;
  comms_failure: boolean;
  eclipse_stuck: boolean;
}

interface MissionState {
  telemetry: SpacecraftTelemetry | null;
  telemetryHistory: SpacecraftTelemetry[];
  observations: Observation[];
  events: MissionEvent[];
  groundStation: GroundStationStatus | null;
  downlinkQueue: DownlinkStatus | null;
  faults: Faults;
  connected: boolean;
  simulationRunning: boolean;
  orbitMode: "LEO" | "SSO" | "GEO";
  cameraMode: "AUTO" | "MANUAL" | "TRACKING";
  globeView: "follow" | "top-down" | "free";
  replayMode: boolean;
  replayIndex: number;
  simSpeed: number;
  missionStartTime: number;
  stepsPerSec: number;
  setTelemetry: (t: SpacecraftTelemetry) => void;
  setObservations: (o: Observation[]) => void;
  addObservation: (o: Observation) => void;
  setEvents: (e: MissionEvent[]) => void;
  addEvent: (e: MissionEvent) => void;
  setGroundStation: (gs: GroundStationStatus) => void;
  setDownlinkQueue: (dq: DownlinkStatus) => void;
  setFaults: (f: Faults) => void;
  setConnected: (c: boolean) => void;
  setSimulationRunning: (r: boolean) => void;
  setOrbitMode: (m: "LEO" | "SSO" | "GEO") => void;
  setCameraMode: (m: "AUTO" | "MANUAL" | "TRACKING") => void;
  setGlobeView: (v: "follow" | "top-down" | "free") => void;
  setReplayMode: (r: boolean) => void;
  setReplayIndex: (i: number) => void;
  setSimSpeed: (s: number) => void;
  setMissionStartTime: (t: number) => void;
  setStepsPerSec: (s: number) => void;
  clearHistory: () => void;
}

export const useMissionStore = create<MissionState>((set) => ({
  telemetry: null,
  telemetryHistory: [],
  observations: [],
  events: [],
  groundStation: null,
  downlinkQueue: null,
  faults: { battery_low: false, camera_failure: false, adcs_failure: false, comms_failure: false, eclipse_stuck: false },
  connected: false,
  simulationRunning: false,
  orbitMode: "LEO",
  cameraMode: "AUTO",
  globeView: "follow",
  replayMode: false,
  replayIndex: 0,
  simSpeed: 1,
  missionStartTime: Date.now(),
  stepsPerSec: 0,
  setTelemetry: (t) =>
    set((state) => ({
      telemetry: t,
      telemetryHistory: [...state.telemetryHistory.slice(-200), t],
    })),
  setObservations: (o) => set({ observations: o }),
  addObservation: (o) =>
    set((state) => ({
      observations: [o, ...state.observations].slice(0, 50),
    })),
  setEvents: (e) => set({ events: e }),
  addEvent: (e) =>
    set((state) => ({
      events: [e, ...state.events].slice(0, 100),
    })),
  setGroundStation: (gs) => set({ groundStation: gs }),
  setDownlinkQueue: (dq) => set({ downlinkQueue: dq }),
  setFaults: (f) => set({ faults: f }),
  setConnected: (c) => set({ connected: c }),
  setSimulationRunning: (r) => set({ simulationRunning: r }),
  setOrbitMode: (m) => set({ orbitMode: m }),
  setCameraMode: (m) => set({ cameraMode: m }),
  setGlobeView: (v) => set({ globeView: v }),
  setReplayMode: (r) => set({ replayMode: r }),
  setReplayIndex: (i) => set({ replayIndex: i }),
  setSimSpeed: (s) => set({ simSpeed: s }),
  setMissionStartTime: (t) => set({ missionStartTime: t }),
  setStepsPerSec: (s) => set({ stepsPerSec: s }),
  clearHistory: () => set({ telemetryHistory: [] }),
}));
