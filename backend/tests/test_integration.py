"""End-to-end integration tests for CubeSat Digital Twin Phase 5U-V."""
import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone


# ── Full Simulation Tick ────────────────────────────────────────────────

class TestSimulationTick:
    def test_engine_produces_telemetry(self):
        from app.simulation.engine import SimulationEngine
        engine = SimulationEngine()
        engine.start()
        state = engine.update(1.0)
        assert state is not None
        assert state.packet_sequence >= 1
        assert state.altitude_km > 0
        assert state.battery_percentage > 0
        engine.stop()

    def test_engine_update_increments_sequence(self):
        from app.simulation.engine import SimulationEngine
        engine = SimulationEngine()
        engine.start()
        engine.update(1.0)
        seq_after_one = engine.get_state().packet_sequence
        engine.update(1.0)
        seq_after_two = engine.get_state().packet_sequence
        assert seq_after_two >= seq_after_one
        engine.stop()

    def test_camera_capture_flow(self):
        from app.simulation.engine import SimulationEngine
        from app.simulation.camera import CameraSimulator
        from app.models.spacecraft import MissionMode
        engine = SimulationEngine()
        engine.start()
        engine.update(1.0)
        state = engine.get_state()
        state.mission_mode = MissionMode.OBSERVING
        camera = CameraSimulator()
        result = camera.capture(state)
        assert "image_path" in result
        assert result["camera_status"] == "ready"
        engine.stop()

    def test_observation_service_pipeline(self):
        from app.services.observation_service import ObservationService
        from app.models.observation import Observation
        svc = ObservationService()
        obs = Observation(
            observation_id="OBS-E2E-001", timestamp=datetime.now(timezone.utc),
            spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0, altitude_km=500.0,
            image_path="data/obs/e2e.jpg", image_width=1920, image_height=1080,
            capture_mode="auto", camera_status="nominal",
            smoke_probability=0.85, wildfire_probability=0.75, confidence=0.9,
            priority="HIGH",
        )
        svc.store(obs)
        retrieved = svc.get_latest()
        assert retrieved is not None
        assert retrieved.observation_id == "OBS-E2E-001"
        assert retrieved.smoke_probability == 0.85


# ── Observation → AI → Correlation → Persist ────────────────────────────

class TestObservationAICorrelationFlow:
    @pytest.mark.asyncio
    async def test_full_ai_correlation_pipeline(self):
        from app.services.fire_correlation import FireCorrelationService
        from app.adapters.firms import FIRMSAdapter
        from app.adapters.weather import WeatherAdapter
        from app.models.observation import Observation

        firms = MagicMock(spec=FIRMSAdapter)
        firms.get_detections_near_point = AsyncMock(return_value=[
            {"lat": 35.0, "lon": -120.0, "distance_km": 2.0,
             "confidence": 0.9, "frp": 100.0, "confidence_level": 0.9}
        ])
        weather = MagicMock(spec=WeatherAdapter)
        weather.get_weather = AsyncMock(return_value={
            "temperature": 38.0, "humidity": 15.0, "wind_speed": 25.0
        })
        svc = FireCorrelationService(firms_adapter=firms, weather_adapter=weather)
        obs = Observation(
            observation_id="OBS-FLOW-001", timestamp=datetime.now(timezone.utc),
            spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0, altitude_km=500.0,
            image_path="e2e.jpg", image_width=1920, image_height=1080,
            capture_mode="auto", camera_status="nominal",
            smoke_probability=0.9,
        )
        result = await svc.correlate_observation(obs)
        assert result["fused_fire_probability"] > 0.3
        assert result["fire_event"] is True
        assert result["recommended_priority"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        assert result["firms_detections_count"] == 1
        assert result["weather"]["temperature"] == 38.0

    @pytest.mark.asyncio
    async def test_correlation_applies_to_observation(self):
        from app.services.fire_correlation import FireCorrelationService
        from app.adapters.firms import FIRMSAdapter
        from app.adapters.weather import WeatherAdapter
        from app.models.observation import Observation

        firms = MagicMock(spec=FIRMSAdapter)
        firms.get_detections_near_point = AsyncMock(return_value=[])
        weather = MagicMock(spec=WeatherAdapter)
        weather.get_weather = AsyncMock(return_value={"temperature": 10.0, "humidity": 80.0, "wind_speed": 2.0})
        svc = FireCorrelationService(firms_adapter=firms, weather_adapter=weather)
        obs = Observation(
            observation_id="OBS-APPLY-001", timestamp=datetime.now(timezone.utc),
            spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0, altitude_km=500.0,
            image_path="e2e.jpg", image_width=1920, image_height=1080,
            capture_mode="auto", camera_status="nominal",
            smoke_probability=0.1, priority="LOW",
        )
        await svc.apply_correlation_to_observation(obs)
        assert hasattr(obs, "fire_correlation_score")


# ── Ground Station Visibility ───────────────────────────────────────────

class TestGroundStationVisibility:
    def test_ground_station_status(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/api/v1/ground-station/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "is_visible" in data
        assert "distance_km" in data

    def test_downlink_service_e2e(self):
        from app.services.downlink import DownlinkService
        from app.models.downlink import TransferState
        from app.models.observation import Observation
        svc = DownlinkService(rate_bytes_s=1e12, config={"band": "ka_band"})
        for i in range(3):
            obs = Observation(
                observation_id=f"OBS-GS-{i}", timestamp=datetime.now(timezone.utc),
                spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0, altitude_km=500.0,
                image_path=f"gs{i}.jpg", image_width=1920, image_height=1080,
                capture_mode="auto", camera_status="nominal",
            )
            svc.queue_observation(obs)
        item = svc.queue.items[0]
        svc.start_transfer(item, "GS-001", datetime.now(timezone.utc))
        for _ in range(100):
            if item.status == TransferState.TRANSMITTED:
                break
            svc.update_transfer(item, 10.0, datetime.now(timezone.utc))
        assert item.status == TransferState.TRANSMITTED


# ── Fault Recovery + EPS Integration ────────────────────────────────────

class TestFaultEPSIntegration:
    def test_low_battery_triggers_recovery(self):
        from app.services.fault_recovery import FaultRecoveryService
        from app.services.eps_model import EPSModel
        eps = EPSModel()
        svc = FaultRecoveryService()
        eps.state.battery.soc_percent = 5.0
        evt = svc.check_battery(eps.state.battery.soc_percent)
        assert evt is not None
        assert evt.success is True

    def test_thermal_emergency_escalation(self):
        from app.services.fault_recovery import FaultRecoveryService
        from app.services.thermal_model import ThermalModel
        tm = ThermalModel()
        svc = FaultRecoveryService()
        tm.nodes["obc"].temperature_c = 85.0
        max_temp = max(n.temperature_c for n in tm.nodes.values())
        evt = svc.check_thermal(max_temp)
        assert evt is not None and evt.success is True


# ── TLE + Orbit Integration ────────────────────────────────────────────

class TestTLEOrbitIntegration:
    def test_tle_loads_orbit_updates(self):
        from app.services.tle_service import TLEService
        from app.simulation.orbit.sgp4_orbit import SGP4OrbitService
        from unittest.mock import patch as _patch
        l1 = "1 25544U 98067A   24100.50000000  .00016717  00000-0  10270-3 0  9994"
        l2 = "2 25544  51.6400 200.0000 0007000  50.0000 310.0000 15.49000000400000"
        tle = TLEService()
        with _patch("app.services.tle_service.EPOCH_MAX_AGE_DAYS", 1000):
            tle.load_direct(l1, l2, "TEST")
        assert tle.is_valid is True
        orbit = SGP4OrbitService({"tle_line1": l1, "tle_line2": l2})
        result = orbit.update(datetime.now(timezone.utc))
        assert -90 <= result["latitude"] <= 90
        assert -180 <= result["longitude"] <= 180
