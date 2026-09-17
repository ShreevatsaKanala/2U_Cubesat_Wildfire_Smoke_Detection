const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export async function fetchHealth() {
  return get<{ status: string }>("/api/v1/health");
}

export async function fetchSpacecraftHealth() {
  return get<{
    overall: string;
    eps: { status: string; uptime_s: number };
    obc: { status: string; uptime_s: number };
    comms: { status: string; uptime_s: number };
    adcs: { status: string; uptime_s: number };
    camera: { status: string; uptime_s: number };
    gps: { status: string; uptime_s: number };
  }>("/api/v1/spacecraft/health");
}

export async function fetchSpacecraftPower() {
  return get<{
    battery_soc: number;
    battery_voltage: number;
    solar_generation_w: number;
    power_consumption_w: number;
    power_balance_w: number;
    eclipse: boolean;
    battery_temperature_c: number;
  }>("/api/v1/spacecraft/power");
}

export async function fetchSpacecraftThermal() {
  return get<{
    nodes: { name: string; temperature_c: number; min_safe_c: number; max_safe_c: number }[];
  }>("/api/v1/spacecraft/thermal");
}

export async function fetchSpacecraftAttitude() {
  return get<{
    roll_deg: number;
    pitch_deg: number;
    yaw_deg: number;
    attitude_mode: string;
    pointing_error_deg: number;
    roll_rate_dps: number;
    pitch_rate_dps: number;
    yaw_rate_dps: number;
  }>("/api/v1/spacecraft/attitude");
}

export async function fetchEvents(limit = 50) {
  return get<{ id: string; timestamp: string; event_type: string; severity: string; message: string; data: unknown }[]>(
    `/api/v1/events?limit=${limit}`
  );
}

export async function fetchGroundStationStatus() {
  return get<{
    distance_km: number;
    is_visible: boolean;
    next_pass_s: number;
    elevation_deg: number;
    azimuth_deg: number;
  }>("/api/v1/ground-station/status");
}

export async function fetchGroundStationConfig() {
  return get<{
    name: string;
    latitude: number;
    longitude: number;
    altitude_m: number;
    min_elevation_deg: number;
  }>("/api/v1/ground-station/config");
}

export async function fetchDownlinkStatus() {
  return get<{
    queue: { id: string; observation_id: string; size_bytes: number; priority: string; created_at: string; status: string }[];
    total_transmitted: number;
    total_failed: number;
  }>("/api/v1/downlink/status");
}

export async function fetchFaults() {
  return get<{
    battery_low: boolean;
    camera_failure: boolean;
    adcs_failure: boolean;
    comms_failure: boolean;
    eclipse_stuck: boolean;
  }>("/api/v1/faults");
}

export async function injectFaults(faults: {
  battery_low?: boolean;
  camera_failure?: boolean;
  adcs_failure?: boolean;
  comms_failure?: boolean;
  eclipse_stuck?: boolean;
}) {
  return post<{
    battery_low: boolean;
    camera_failure: boolean;
    adcs_failure: boolean;
    comms_failure: boolean;
    eclipse_stuck: boolean;
  }>("/api/v1/faults/inject", faults);
}

export async function clearFaults() {
  return post<{
    battery_low: boolean;
    camera_failure: boolean;
    adcs_failure: boolean;
    comms_failure: boolean;
    eclipse_stuck: boolean;
  }>("/api/v1/faults/clear");
}

export async function fetchObservations(limit = 20, offset = 0) {
  return get<{
    observations: {
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
      ai_provider: string | null;
      ai_model: string | null;
      ai_smoke_score: number | null;
      ai_confidence: string | null;
      ai_visual_evidence: string[] | null;
      ai_alternative_explanations: string[] | null;
      ai_scene_description: string | null;
      ai_status: string | null;
    }[];
    total: number;
    limit: number;
    offset: number;
  }>(`/api/v1/observations?limit=${limit}&offset=${offset}`);
}

export async function startSimulation() {
  return post<{ status: string }>("/api/v1/simulation/start");
}

export async function stopSimulation() {
  return post<{ status: string }>("/api/v1/simulation/stop");
}

export async function resetSimulation() {
  return post<{ status: string }>("/api/v1/simulation/reset");
}

export async function fetchWeather(lat: number, lon: number) {
  return get<{ temperature?: number; humidity?: number; description?: string }>(
    `/api/v1/environment/weather?lat=${lat}&lon=${lon}`
  );
}

export async function fetchAirQuality(lat: number, lon: number) {
  return get<{ aqi?: number; label?: string }>(`/api/v1/environment/air-quality?lat=${lat}&lon=${lon}`);
}

export async function fetchHotspots() {
  return get<{ lat: number; lon: number; frp: number; confidence: string }[]>("/api/v1/environment/hotspots");
}

export async function fetchAIStatus() {
  return get<{
    mode: string;
    provider: string;
    model: string;
    failover_enabled: boolean;
    timeout_seconds: number;
    max_requests_per_minute: number;
    status: string;
  }>("/api/ai/status");
}

export async function fetchMLStatus() {
  return get<{
    mode: string;
    model_name: string;
    model_version: string;
    model_loaded: boolean;
    threshold: number;
  }>("/api/v1/ml/status");
}

export async function fetchMLModels() {
  return get<{
    models: {
      name: string;
      params_m: number;
      size_mb: number;
      precision: number;
      recall: number;
      f1: number;
      latency_ms: number;
    }[];
  }>("/api/v1/ml/models");
}

export async function fetchMLMetrics() {
  return get<{
    accuracy: number;
    precision: number;
    recall: number;
    f1: number;
    confusion_matrix: number[][];
    auc_roc: number;
  }>("/api/v1/ml/metrics");
}

export async function fetchDatasetManifest() {
  return get<{
    name: string;
    version: string;
    source: string;
    license: string;
    total_images: number;
    classes: string[];
    splits: { train: number; val: number; test: number };
    dimensions: { width: number; height: number; channels: number };
  }>("/api/v1/dataset/manifest");
}

export async function fetchDatasetStats() {
  return get<{
    class_counts: Record<string, number>;
    total_images: number;
    splits: { train: number; val: number; test: number };
    dimensions: { width: number; height: number; channels: number };
  }>("/api/v1/dataset/stats");
}
