import { create } from "zustand";

export interface SpacecraftTelemetry {
  packet_sequence: number;
  timestamp: string;
  spacecraft_id: string;
  mission_mode: string;
  latitude: number;
  longitude: number;
  altitude_km: number;
  velocity_km_s: number;
  heading_deg: number;
  roll_deg: number;
  pitch_deg: number;
  yaw_deg: number;
  battery_percentage: number;
  battery_voltage: number;
  power_generation_w: number;
  power_consumption_w: number;
  temperatures: Record<string, number>;
  communication_status: string;
  gps_status: string;
  camera_status: string;
  ml_status: string;
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

interface MissionState {
  telemetry: SpacecraftTelemetry | null;
  telemetryHistory: SpacecraftTelemetry[];
  observations: Observation[];
  connected: boolean;
  simulationRunning: boolean;
  setTelemetry: (t: SpacecraftTelemetry) => void;
  addObservation: (o: Observation) => void;
  setConnected: (c: boolean) => void;
  setSimulationRunning: (r: boolean) => void;
  clearHistory: () => void;
}

export const useMissionStore = create<MissionState>((set) => ({
  telemetry: null,
  telemetryHistory: [],
  observations: [],
  connected: false,
  simulationRunning: false,
  setTelemetry: (t) =>
    set((state) => ({
      telemetry: t,
      telemetryHistory: [...state.telemetryHistory.slice(-200), t],
    })),
  addObservation: (o) =>
    set((state) => ({
      observations: [o, ...state.observations].slice(0, 50),
    })),
  setConnected: (c) => set({ connected: c }),
  setSimulationRunning: (r) => set({ simulationRunning: r }),
  clearHistory: () => set({ telemetryHistory: [] }),
}));
