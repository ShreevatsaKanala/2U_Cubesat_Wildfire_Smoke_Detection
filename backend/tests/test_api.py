"""API endpoint tests for CubeSat Digital Twin Phase 1."""
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
    assert "battery_percentage" in data


def test_telemetry_latest_endpoint():
    resp = client.get("/api/v1/telemetry/latest")
    assert resp.status_code == 200


def test_observations_endpoint():
    resp = client.get("/api/v1/observations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


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


def test_weather_endpoint():
    resp = client.get("/api/v1/environment/weather?lat=35.0&lon=-120.0")
    assert resp.status_code == 200


def test_hotspots_endpoint():
    resp = client.get("/api/v1/environment/hotspots")
    assert resp.status_code == 200
