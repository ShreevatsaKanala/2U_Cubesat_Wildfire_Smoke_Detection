"""API endpoint tests for CubeSat Digital Twin Phase 2."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data
    assert "simulation_running" in data


def test_config_endpoint():
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "spacecraft" in data
    assert "simulation" in data


def test_spacecraft_state_endpoint():
    resp = client.get("/api/v1/spacecraft/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "latitude" in data
    assert "longitude" in data
    assert "altitude_km" in data
    assert "attitude" in data
    assert "power" in data
    assert "thermal" in data
    assert "health" in data


def test_spacecraft_health_endpoint():
    resp = client.get("/api/v1/spacecraft/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall" in data
    assert "eps" in data
    assert "obc" in data


def test_spacecraft_power_endpoint():
    resp = client.get("/api/v1/spacecraft/power")
    assert resp.status_code == 200
    data = resp.json()
    assert "battery_soc" in data
    assert "solar_generation_w" in data


def test_spacecraft_thermal_endpoint():
    resp = client.get("/api/v1/spacecraft/thermal")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data


def test_spacecraft_attitude_endpoint():
    resp = client.get("/api/v1/spacecraft/attitude")
    assert resp.status_code == 200
    data = resp.json()
    assert "roll_deg" in data
    assert "attitude_mode" in data


def test_telemetry_latest_endpoint():
    resp = client.get("/api/v1/telemetry/latest")
    assert resp.status_code == 200


def test_observations_endpoint():
    resp = client.get("/api/v1/observations")
    assert resp.status_code == 200
    data = resp.json()
    assert "observations" in data
    assert "total" in data
    assert isinstance(data["observations"], list)


def test_observations_with_pagination():
    resp = client.get("/api/v1/observations?limit=5&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "observations" in data
    assert "limit" in data
    assert "offset" in data


def test_observations_not_found():
    resp = client.get("/api/v1/observations/NONEXISTENT")
    assert resp.status_code == 404


def test_simulation_start_stop():
    resp = client.post("/api/v1/simulation/start")
    assert resp.status_code == 200
    data = resp.json()
    assert data["running"] is True

    resp = client.post("/api/v1/simulation/stop")
    assert resp.status_code == 200
    data = resp.json()
    assert data["running"] is False


def test_simulation_reset():
    resp = client.post("/api/v1/simulation/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["running"] is False


def test_events_endpoint():
    resp = client.get("/api/v1/events")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_ground_station_status():
    resp = client.get("/api/v1/ground-station/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "distance_km" in data
    assert "is_visible" in data


def test_ground_station_config():
    resp = client.get("/api/v1/ground-station/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "latitude" in data


def test_downlink_status():
    resp = client.get("/api/v1/downlink/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total_transmitted" in data


def test_faults_get():
    resp = client.get("/api/v1/faults")
    assert resp.status_code == 200
    data = resp.json()
    assert "battery_low" in data
    assert "camera_failure" in data


def test_faults_inject():
    resp = client.post("/api/v1/faults/inject", json={"battery_low": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["faults"]["battery_low"] is True
    # Clear it
    client.post("/api/v1/faults/clear")


def test_faults_clear():
    client.post("/api/v1/faults/inject", json={"camera_failure": True})
    resp = client.post("/api/v1/faults/clear")
    assert resp.status_code == 200
    data = resp.json()
    assert data["faults"]["camera_failure"] is False


def test_weather_endpoint():
    resp = client.get("/api/v1/environment/weather?lat=35.0&lon=-120.0")
    assert resp.status_code == 200


def test_hotspots_endpoint():
    resp = client.get("/api/v1/environment/hotspots")
    assert resp.status_code == 200
