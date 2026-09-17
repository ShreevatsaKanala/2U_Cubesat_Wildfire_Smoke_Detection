"""Backend tests for CubeSat Digital Twin Phase 1."""
import pytest
from datetime import datetime, timezone
from app.models.spacecraft import SpacecraftConfig, SpacecraftState, MissionMode
from app.models.telemetry import TelemetryPacket
from app.models.observation import Observation
from app.simulation.engine import SimulationEngine
from app.simulation.orbit.sgp4_orbit import SGP4OrbitService
from app.simulation.camera import CameraSimulator
from app.ml.mock_classifier import MockClassifier
from app.ml.inference import InferenceEngine
from app.services.priority import PriorityCalculator
from app.services.observation_service import ObservationService


# --- Model Tests ---

def test_spacecraft_config_creation():
    config = SpacecraftConfig(spacecraft_id="CSAT-001", name="Test Sat")
    assert config.spacecraft_id == "CSAT-001"
    assert config.mass_kg == 2.6
    assert config.battery_capacity_wh == 40.0
    assert config.camera_resolution["width"] == 1920


def test_spacecraft_state_creation():
    state = SpacecraftState(
        spacecraft_id="CSAT-001",
        mission_mode=MissionMode.IDLE,
        latitude=0.0,
        longitude=0.0,
        altitude_km=500.0,
        velocity_km_s=7.6,
        heading_deg=90.0,
        roll_deg=0.0,
        pitch_deg=0.0,
        yaw_deg=90.0,
        battery_percentage=85.0,
        battery_voltage=7.2,
        power_generation_w=1.5,
        power_consumption_w=1.2,
        temperatures={"battery": 20.0, "cpu": 35.0, "panel": 10.0, "body": 18.0},
    )
    assert state.spacecraft_id == "CSAT-001"
    assert state.battery_percentage == 85.0
    assert state.mission_mode == MissionMode.IDLE


def test_telemetry_packet():
    now = datetime.now(timezone.utc)
    packet = TelemetryPacket(
        packet_sequence=1,
        timestamp=now,
        spacecraft_id="CSAT-001",
        mission_mode="IDLE",
        latitude=10.0,
        longitude=20.0,
        altitude_km=500.0,
        velocity_km_s=7.6,
        heading_deg=90.0,
        roll_deg=0.0,
        pitch_deg=0.0,
        yaw_deg=90.0,
        battery_percentage=85.0,
        battery_voltage=7.2,
        power_generation_w=1.5,
        power_consumption_w=1.2,
        temperatures={"battery": 20.0, "cpu": 35.0, "panel": 10.0, "body": 18.0},
    )
    assert packet.packet_sequence == 1
    assert packet.latitude == 10.0
    d = packet.model_dump(mode="json")
    assert "packet_sequence" in d
    assert d["latitude"] == 10.0


def test_observation_model():
    obs = Observation(
        observation_id="OBS-TEST-001",
        timestamp=datetime.now(timezone.utc),
        spacecraft_id="CSAT-001",
        latitude=35.0,
        longitude=-120.0,
        altitude_km=500.0,
        image_path="data/observations/test.jpg",
        image_width=1920,
        image_height=1080,
        capture_mode="auto",
        camera_status="nominal",
        smoke_probability=0.75,
        wildfire_probability=0.65,
        confidence=0.85,
        priority="HIGH",
        inference_latency_ms=120.0,
        processing_status="completed",
    )
    assert obs.priority == "HIGH"
    assert obs.smoke_probability == 0.75


# --- Orbit Tests ---

def test_orbit_service_default():
    orbit = SGP4OrbitService({})
    assert orbit._altitude_km == 500.0


def test_orbit_update():
    orbit = SGP4OrbitService({})
    now = datetime.now(timezone.utc)
    result = orbit.update(now)
    assert "latitude" in result
    assert "longitude" in result
    assert "altitude_km" in result
    assert "velocity_km_s" in result
    assert -90 <= result["latitude"] <= 90
    assert -180 <= result["longitude"] <= 180


# --- ML Tests ---

def test_mock_classifier_returns_valid_output():
    classifier = MockClassifier()
    result = classifier.classify("test_image_path.jpg")
    assert 0.0 <= result["smoke_probability"] <= 1.0
    assert 0.0 <= result["wildfire_probability"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["model_name"] == "mock-smoke-classifier-v0.1"
    assert result["processing_status"] == "completed"
    assert result["inference_latency_ms"] > 0


def test_mock_classifier_deterministic():
    classifier = MockClassifier()
    r1 = classifier.classify("same_path.jpg")
    r2 = classifier.classify("same_path.jpg")
    assert r1["smoke_probability"] == r2["smoke_probability"]
    assert r1["confidence"] == r2["confidence"]


def test_inference_engine_interface():
    classifier = MockClassifier()
    assert isinstance(classifier, InferenceEngine)


# --- Priority Tests ---

def test_priority_calculation_critical():
    calc = PriorityCalculator()
    assert calc.calculate(0.9, 0.9) == "CRITICAL"


def test_priority_calculation_high():
    calc = PriorityCalculator()
    assert calc.calculate(0.8, 0.6) == "HIGH"


def test_priority_calculation_medium():
    calc = PriorityCalculator()
    assert calc.calculate(0.5, 0.5) == "MEDIUM"


def test_priority_calculation_low():
    calc = PriorityCalculator()
    assert calc.calculate(0.1, 0.1) == "LOW"


def test_priority_description():
    calc = PriorityCalculator()
    desc = calc.get_priority_description("CRITICAL")
    assert isinstance(desc, str)
    assert len(desc) > 0


# --- Observation Service Tests ---

def test_observation_service_store_and_retrieve():
    svc = ObservationService()
    assert svc.get_latest() is None
    assert len(svc.get_all()) == 0

    obs = Observation(
        observation_id="OBS-TEST-001",
        timestamp=datetime.now(timezone.utc),
        spacecraft_id="CSAT-001",
        latitude=0.0, longitude=0.0, altitude_km=500.0,
        image_path="test.jpg", image_width=1920, image_height=1080,
        capture_mode="auto", camera_status="nominal",
    )
    svc.store(obs)
    assert svc.get_latest() is not None
    assert svc.get_latest().observation_id == "OBS-TEST-001"
    assert len(svc.get_all()) == 1
    assert svc.get_by_id("OBS-TEST-001") is not None
    assert svc.get_by_id("NONEXISTENT") is None


# --- Simulation Engine Tests ---

def test_simulation_engine_init():
    engine = SimulationEngine()
    state = engine.get_state()
    assert state.spacecraft_id == "CSAT-001"
    assert state.battery_percentage == 85.0


def test_simulation_engine_update():
    engine = SimulationEngine()
    engine.start()
    state = engine.update(1.0)
    assert state is not None
    assert state.altitude_km > 0
    assert state.packet_sequence >= 1


def test_simulation_engine_start_stop():
    engine = SimulationEngine()
    assert engine.running is False
    engine.start()
    assert engine.running is True
    engine.stop()
    assert engine.running is False


def test_simulation_engine_reset():
    engine = SimulationEngine()
    engine.start()
    engine.update(10.0)
    engine.reset()
    state = engine.get_state()
    assert state.battery_percentage == 85.0
    assert state.packet_sequence == 0


# --- Camera Tests ---

def test_camera_capture():
    camera = CameraSimulator()
    state = SpacecraftState(
        timestamp=datetime.now(timezone.utc),
        spacecraft_id="CSAT-001",
        mission_mode=MissionMode.OBSERVING,
        latitude=35.0, longitude=-120.0, altitude_km=500.0,
        velocity_km_s=7.6, heading_deg=90.0,
        roll_deg=0.0, pitch_deg=0.0, yaw_deg=90.0,
        battery_percentage=85.0, battery_voltage=7.2,
        power_generation_w=1.5, power_consumption_w=1.2,
        temperatures={"battery": 20.0, "cpu": 35.0, "panel": 10.0, "body": 18.0},
    )
    result = camera.capture(state)
    assert "image_path" in result
    assert result["width"] == 1920
    assert result["height"] == 1080
    assert result["camera_status"] == "ready"
