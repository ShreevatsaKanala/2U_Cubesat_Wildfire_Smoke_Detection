"""
Simulation Engine for CubeSat Digital Twin.
"""

from datetime import datetime, timezone, timedelta
import math
import random
from typing import Optional

from app.models.spacecraft import SpacecraftState, SpacecraftConfig, MissionMode
from app.models.observation import Observation
from app.models.telemetry import TelemetryPacket
from app.simulation.orbit.sgp4_orbit import SGP4OrbitService
from app.ml.mock_classifier import MockClassifier
from app.simulation.camera import CameraSimulator
from app.services.observation_service import ObservationService
from app.services.priority import PriorityCalculator


class SimulationEngine:

    def __init__(self, config: SpacecraftConfig = None, sim_config: dict = None):
        self.spacecraft_config = config or SpacecraftConfig(
            spacecraft_id="CSAT-001", name="2U CubeSat Wildfire Twin"
        )
        sim_config = sim_config or {}

        self.orbit_service = SGP4OrbitService(sim_config.get("orbit", {}))
        self.classifier = MockClassifier()
        self.camera = CameraSimulator(sim_config.get("camera", {}))
        self.observation_service = ObservationService()
        self.priority_calculator = PriorityCalculator()

        self.running = False
        self.sim_time = datetime.now(timezone.utc)
        self.sim_speed = sim_config.get("sim_speed", 1.0)
        self.telemetry_frequency = sim_config.get("telemetry_frequency", 1.0)
        self.observation_interval = sim_config.get("observation_interval", 30.0)
        self.last_observation_time: Optional[datetime] = None
        self.packet_sequence = 0
        self.current_observation_id: Optional[str] = None

        initial_pos = self.orbit_service.update(self.sim_time)
        self._state = SpacecraftState(
            spacecraft_id=self.spacecraft_config.spacecraft_id,
            mission_mode=MissionMode.IDLE,
            latitude=initial_pos["latitude"],
            longitude=initial_pos["longitude"],
            altitude_km=initial_pos["altitude_km"],
            velocity_km_s=initial_pos["velocity_km_s"],
            heading_deg=90.0,
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=90.0,
            battery_percentage=85.0,
            battery_voltage=self.spacecraft_config.battery_voltage_nominal * 0.97,
            power_generation_w=0.0,
            power_consumption_w=self.spacecraft_config.power_consumption_w,
            temperatures={"battery": 22.0, "cpu": 30.0, "panel": 20.0, "body": 21.0},
            communication_status="nominal",
            gps_status="nominal",
            camera_status="standby",
            ml_status="ready",
            packet_sequence=0,
        )

    def start(self) -> None:
        self.running = True
        self._state.mission_mode = MissionMode.IDLE

    def stop(self) -> None:
        self.running = False

    def reset(self) -> None:
        self.running = False
        self.sim_time = datetime.now(timezone.utc)
        self.packet_sequence = 0
        self.last_observation_time = None
        self.current_observation_id = None
        self.orbit_service = SGP4OrbitService({})
        initial_pos = self.orbit_service.update(self.sim_time)
        self._state = SpacecraftState(
            spacecraft_id=self.spacecraft_config.spacecraft_id,
            mission_mode=MissionMode.IDLE,
            latitude=initial_pos["latitude"],
            longitude=initial_pos["longitude"],
            altitude_km=initial_pos["altitude_km"],
            velocity_km_s=initial_pos["velocity_km_s"],
            heading_deg=90.0,
            battery_percentage=85.0,
            battery_voltage=self.spacecraft_config.battery_voltage_nominal * 0.97,
            temperatures={"battery": 22.0, "cpu": 30.0, "panel": 20.0, "body": 21.0},
            communication_status="nominal",
            gps_status="nominal",
            camera_status="standby",
            ml_status="ready",
            packet_sequence=0,
        )

    def update(self, dt_seconds: float) -> SpacecraftState:
        if not self.running:
            return self._state

        sim_dt = dt_seconds * self.sim_speed
        self.sim_time += timedelta(seconds=sim_dt)
        self.packet_sequence += 1

        orbit_pos = self.orbit_service.update(self.sim_time)
        self._state.latitude = orbit_pos["latitude"]
        self._state.longitude = orbit_pos["longitude"]
        self._state.altitude_km = orbit_pos["altitude_km"]
        self._state.velocity_km_s = orbit_pos["velocity_km_s"]

        self._state.heading_deg = (self._state.longitude * 0.1) % 360

        time_seed = int(self.sim_time.timestamp() * 100) % (2**32)
        rng = random.Random(time_seed)
        self._state.roll_deg = round(rng.gauss(0, 0.5), 2)
        self._state.pitch_deg = round(rng.gauss(0, 0.3), 2)
        self._state.yaw_deg = round(self._state.heading_deg + rng.gauss(0, 1.0), 2)

        orbit_period = 2 * math.pi * math.sqrt(
            (6371 + self._state.altitude_km) ** 3 / 398600.4418
        )
        elapsed_mod = (self.sim_time.timestamp() % orbit_period) / orbit_period
        in_sunlight = not (0.42 < elapsed_mod < 0.58)

        if in_sunlight:
            self._state.power_generation_w = round(
                self.spacecraft_config.solar_generation_w * rng.uniform(0.85, 1.0), 2
            )
        else:
            self._state.power_generation_w = 0.0

        self._state.power_consumption_w = round(
            self.spacecraft_config.power_consumption_w * rng.uniform(0.9, 1.1), 2
        )

        net_w = self._state.power_generation_w - self._state.power_consumption_w
        energy_wh = net_w * (sim_dt / 3600.0)
        delta_pct = (energy_wh / self.spacecraft_config.battery_capacity_wh) * 100.0
        self._state.battery_percentage = round(
            max(0.0, min(100.0, self._state.battery_percentage + delta_pct)), 2
        )
        self._state.battery_voltage = round(
            self.spacecraft_config.battery_voltage_nominal
            * (0.85 + 0.15 * self._state.battery_percentage / 100.0),
            2,
        )

        env_temp = 40.0 if in_sunlight else -15.0
        temps = self._state.temperatures.copy()
        tau = 120.0
        for key in temps:
            heat = 2.0 if key == "cpu" and self._state.power_generation_w > 0 else 0.0
            temps[key] = round(temps[key] + ((env_temp - temps[key]) / tau + heat) * sim_dt, 1)
        self._state.temperatures = temps

        self._state.timestamp = self.sim_time
        self._state.packet_sequence = self.packet_sequence

        self._check_observation()

        if self._state.battery_percentage < 20:
            self._state.mission_mode = MissionMode.SAFE_MODE
        elif self.current_observation_id:
            self._state.mission_mode = MissionMode.PROCESSING
        else:
            self._state.mission_mode = MissionMode.IDLE

        return self._state

    def _check_observation(self):
        if self.last_observation_time is None:
            if self.packet_sequence >= 5:
                self._trigger_observation()
        else:
            if (self.sim_time - self.last_observation_time).total_seconds() >= self.observation_interval:
                self._trigger_observation()

    def _trigger_observation(self) -> Observation:
        ts = self.sim_time.strftime("%Y%m%d-%H%M%S")
        observation_id = f"OBS-{ts}-{self.packet_sequence:04d}"
        self.current_observation_id = observation_id

        self._state.camera_status = "capturing"
        capture = self.camera.capture(self._state)
        self._state.camera_status = "standby"

        self._state.ml_status = "processing"
        cls_result = self.classifier.classify(capture["image_path"])
        self._state.ml_status = "ready"

        priority = self.priority_calculator.calculate(
            cls_result["smoke_probability"], cls_result["confidence"]
        )

        obs = Observation(
            observation_id=observation_id,
            timestamp=self.sim_time,
            spacecraft_id=self._state.spacecraft_id,
            latitude=self._state.latitude,
            longitude=self._state.longitude,
            altitude_km=self._state.altitude_km,
            image_path=capture["image_path"],
            image_width=capture["width"],
            image_height=capture["height"],
            capture_mode=capture.get("capture_mode", "synthetic"),
            camera_status="nominal",
            model_name=cls_result["model_name"],
            model_version=cls_result["model_version"],
            smoke_probability=cls_result["smoke_probability"],
            wildfire_probability=cls_result["wildfire_probability"],
            confidence=cls_result["confidence"],
            priority=priority,
            inference_latency_ms=cls_result["inference_latency_ms"],
            processing_status="completed",
        )

        self.observation_service.store(obs)
        self.last_observation_time = self.sim_time
        self._state.current_observation_id = observation_id
        self._state.smoke_probability = cls_result["smoke_probability"]
        self._state.confidence = cls_result["confidence"]
        self._state.priority = priority

        return obs

    def get_state(self) -> SpacecraftState:
        return self._state

    def get_latest_telemetry(self) -> TelemetryPacket:
        t = self._state
        return TelemetryPacket(
            packet_sequence=t.packet_sequence,
            timestamp=t.timestamp,
            spacecraft_id=t.spacecraft_id,
            mission_mode=t.mission_mode.value,
            latitude=t.latitude,
            longitude=t.longitude,
            altitude_km=t.altitude_km,
            velocity_km_s=t.velocity_km_s,
            heading_deg=t.heading_deg,
            roll_deg=t.roll_deg,
            pitch_deg=t.pitch_deg,
            yaw_deg=t.yaw_deg,
            battery_percentage=t.battery_percentage,
            battery_voltage=t.battery_voltage,
            power_generation_w=t.power_generation_w,
            power_consumption_w=t.power_consumption_w,
            temperatures=t.temperatures,
            communication_status=t.communication_status,
            gps_status=t.gps_status,
            camera_status=t.camera_status,
            ml_status=t.ml_status,
            current_observation_id=t.current_observation_id,
            smoke_probability=t.smoke_probability,
            confidence=t.confidence,
            priority=t.priority,
        )
