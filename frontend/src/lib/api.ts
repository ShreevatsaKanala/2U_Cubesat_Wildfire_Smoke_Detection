const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/v1/health`);
  return res.json();
}

export async function fetchSpacecraftState() {
  const res = await fetch(`${API_BASE}/api/v1/spacecraft/state`);
  return res.json();
}

export async function fetchTelemetryLatest() {
  const res = await fetch(`${API_BASE}/api/v1/telemetry/latest`);
  return res.json();
}

export async function fetchObservations(limit = 20) {
  const res = await fetch(`${API_BASE}/api/v1/observations?limit=${limit}`);
  return res.json();
}

export async function startSimulation() {
  const res = await fetch(`${API_BASE}/api/v1/simulation/start`, { method: "POST" });
  return res.json();
}

export async function stopSimulation() {
  const res = await fetch(`${API_BASE}/api/v1/simulation/stop`, { method: "POST" });
  return res.json();
}

export async function resetSimulation() {
  const res = await fetch(`${API_BASE}/api/v1/simulation/reset`, { method: "POST" });
  return res.json();
}

export async function fetchConfig() {
  const res = await fetch(`${API_BASE}/api/v1/config`);
  return res.json();
}

export async function fetchWeather(lat: number, lon: number) {
  const res = await fetch(`${API_BASE}/api/v1/environment/weather?lat=${lat}&lon=${lon}`);
  return res.json();
}

export async function fetchAirQuality(lat: number, lon: number) {
  const res = await fetch(`${API_BASE}/api/v1/environment/air-quality?lat=${lat}&lon=${lon}`);
  return res.json();
}

export async function fetchHotspots() {
  const res = await fetch(`${API_BASE}/api/v1/environment/hotspots`);
  return res.json();
}
