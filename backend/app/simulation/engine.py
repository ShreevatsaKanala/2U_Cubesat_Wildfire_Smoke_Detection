"""Simulation Engine for CubeSat Digital Twin Phase 3."""
from datetime import datetime, timezone, timedelta
import math
import random
import logging
from typing import Optional

from app.models.spacecraft import (
    SpacecraftState, SpacecraftConfig, MissionMode, AttitudeMode,
    AttitudeState, PowerState, ThermalState, ThermalNode,
    SubsystemStatus, SubsystemHealth, FaultInjection
)
from app.models.observation import Observation
from app.models.telemetry import TelemetryPacket
from app.models.events import MissionEvent, EventType, EventLog
from app.models.ground_station import GroundStationConfig, GroundPass
from app.models.downlink import DownlinkItem, DownlinkQueue
from app.simulation.orbit.sgp4_orbit import SGP4OrbitService
from app.ml.mock_classifier import MockClassifier
from app.simulation.camera import CameraSimulator
from app.services.observation_service import ObservationService
from app.services.priority import PriorityCalculator

logger = logging.getLogger(__name__)


class SimulationEngine:
    def __init__(self, config: SpacecraftConfig = None, sim_config: dict = None):
        self.spacecraft_config = config or SpacecraftConfig()
        sim_config = sim_config or {}
        
        # Store original config for reset
        self._original_config = sim_config.copy()
        
        # Orbit
        self.orbit_service = SGP4OrbitService(sim_config.get("orbit", {}))
        self.orbit_mode = sim_config.get("orbit_mode", "analytical")
        
        # ML / Camera
        self._ml_mode = sim_config.get("ml_mode", "mock")
        self.classifier = self._create_classifier()
        self.camera = CameraSimulator(sim_config.get("camera", {}))
        self.observation_service = ObservationService()
        self.priority_calculator = PriorityCalculator()
        
        # Mission systems
        self.event_log = EventLog()
        self.ground_station = GroundStationConfig(**sim_config.get("ground_station", {}))
        self.downlink_queue = DownlinkQueue()
        
        # Sim state
        self.running = False
        self.sim_time = datetime.now(timezone.utc)
        self.sim_speed = sim_config.get("sim_speed", 1.0)
        self.telemetry_frequency = sim_config.get("telemetry_frequency", 1.0)
        self.observation_interval = sim_config.get("observation_interval", 30.0)
        self.last_observation_time: Optional[datetime] = None
        self.packet_sequence = 0
        self.current_observation_id: Optional[str] = None
        self._state = self._create_initial_state()

    def _create_classifier(self):
        """Create classifier based on ML_MODE setting."""
        if self._ml_mode == "real":
            try:
                from app.ml.real_classifier import RealSmokeClassifier
                from app.core.config import settings
                classifier = RealSmokeClassifier(
                    model_path=settings.ML_MODEL_PATH,
                    device=settings.ML_DEVICE,
                    smoke_threshold=settings.ML_SMOKE_THRESHOLD,
                )
                if classifier.is_loaded():
                    logger.info("Real ML classifier loaded successfully")
                    return classifier
                else:
                    logger.warning("Real ML model not found, falling back to mock. "
                                   "ML UNAVAILABLE — set ML_MODE=mock or train a model.")
                    self._ml_status = "unavailable"
                    return MockClassifier()
            except Exception as e:
                logger.error(f"Failed to load real classifier: {e}. ML UNAVAILABLE.")
                self._ml_status = "unavailable"
                return MockClassifier()
        else:
            return MockClassifier()

    def _create_initial_state(self) -> SpacecraftState:
        initial_pos = self.orbit_service.update(self.sim_time)
        return SpacecraftState(
            spacecraft_id=self.spacecraft_config.spacecraft_id,
            mission_mode=MissionMode.IDLE,
            latitude=initial_pos["latitude"],
            longitude=initial_pos["longitude"],
            altitude_km=initial_pos["altitude_km"],
            velocity_km_s=initial_pos["velocity_km_s"],
            heading_deg=90.0,
            attitude=AttitudeState(
                roll_deg=0.0, pitch_deg=0.0, yaw_deg=90.0,
                attitude_mode=AttitudeMode.NADIR
            ),
            power=PowerState(
                battery_soc=85.0,
                battery_voltage=self.spacecraft_config.battery_voltage_nominal * 0.97,
                charge_state="discharging"
            ),
            thermal=ThermalState(),
            health=SubsystemHealth(),
            faults=FaultInjection(),
            communication_status="nominal",
            gps_status="nominal",
            camera_status="standby",
            ml_status=getattr(self, '_ml_status', 'ready'),
            packet_sequence=0,
        )

    def start(self):
        self.running = True
        self._state.mission_mode = MissionMode.IDLE
        self._add_event(EventType.MISSION_MODE_CHANGED, "Simulation started", "info")

    def stop(self):
        self.running = False
        self._add_event(EventType.MISSION_MODE_CHANGED, "Simulation stopped", "info")

    def reset(self):
        self.running = False
        self.sim_time = datetime.now(timezone.utc)
        self.packet_sequence = 0
        self.last_observation_time = None
        self.current_observation_id = None
        self.orbit_service = SGP4OrbitService(self._original_config.get("orbit", {}))
        self.observation_service = ObservationService()
        self.event_log = EventLog()
        self.downlink_queue = DownlinkQueue()
        self._state = self._create_initial_state()
        self._add_event(EventType.MISSION_MODE_CHANGED, "Simulation reset", "info")

    def update(self, dt_seconds: float) -> SpacecraftState:
        if not self.running:
            return self._state
        sim_dt = dt_seconds * self.sim_speed
        self.sim_time += timedelta(seconds=sim_dt)
        self.packet_sequence += 1
        
        # Update orbit
        orbit_pos = self.orbit_service.update(self.sim_time)
        self._state.latitude = orbit_pos["latitude"]
        self._state.longitude = orbit_pos["longitude"]
        self._state.altitude_km = orbit_pos["altitude_km"]
        self._state.velocity_km_s = orbit_pos["velocity_km_s"]
        self._state.heading_deg = (self._state.longitude * 0.1) % 360
        
        # Check faults
        self._update_faults()
        self._update_health()
        
        # Update attitude
        self._update_attitude(sim_dt)
        
        # Update power
        self._update_power(sim_dt)
        
        # Update thermal
        self._update_thermal(sim_dt)
        
        # Update ground station pass
        self._update_ground_pass()
        
        # Process downlink queue
        self._process_downlink(sim_dt)
        
        # Check observations
        self._check_observation()
        
        # Update mission mode
        self._update_mission_mode()
        
        self._state.timestamp = self.sim_time
        self._state.packet_sequence = self.packet_sequence
        return self._state

    def _update_faults(self):
        f = self._state.faults
        if f.battery_low:
            self._state.power.battery_soc = max(0.0, self._state.power.battery_soc - 0.5)
        if f.thermal_critical:
            for node in self._state.thermal.nodes.values():
                node.temperature_c = max(node.temperature_c, node.critical_threshold_c - 5)
                node.thermal_state = "critical"
        elif f.thermal_warning:
            for node in self._state.thermal.nodes.values():
                node.temperature_c = max(node.temperature_c, node.warning_threshold_c - 5)
                node.thermal_state = "warning"
        if f.gps_unavailable:
            self._state.gps_status = "unavailable"
        else:
            self._state.gps_status = "nominal"
        if f.comms_lost:
            self._state.communication_status = "lost"
        else:
            self._state.communication_status = "nominal"
        if f.camera_failure:
            self._state.camera_status = "failure"
        if f.ml_unavailable:
            self._state.ml_status = "unavailable"

    def _update_health(self):
        h = self._state.health
        f = self._state.faults
        p = self._state.power
        t = self._state.thermal
        
        if f.battery_low and p.battery_soc < 10:
            h.eps = SubsystemStatus.CRITICAL
        elif f.battery_low and p.battery_soc < 20:
            h.eps = SubsystemStatus.WARNING
        else:
            h.eps = SubsystemStatus.NOMINAL
        
        h.camera = SubsystemStatus.OFFLINE if f.camera_failure else SubsystemStatus.NOMINAL
        h.navigation = SubsystemStatus.DEGRADED if f.gps_unavailable else SubsystemStatus.NOMINAL
        h.communications = SubsystemStatus.OFFLINE if f.comms_lost else SubsystemStatus.NOMINAL
        h.ml = SubsystemStatus.OFFLINE if f.ml_unavailable else SubsystemStatus.NOMINAL
        
        max_temp = max(n.temperature_c for n in t.nodes.values())
        if f.thermal_critical or max_temp > 65:
            h.thermal = SubsystemStatus.CRITICAL
        elif f.thermal_warning or max_temp > 50:
            h.thermal = SubsystemStatus.WARNING
        else:
            h.thermal = SubsystemStatus.NOMINAL
        
        h.obc = SubsystemStatus.DEGRADED if f.obc_degraded else SubsystemStatus.NOMINAL

    def _update_attitude(self, dt: float):
        a = self._state.attitude
        if self._state.faults.gps_unavailable:
            a.attitude_mode = AttitudeMode.SAFE
        
        rng = random.Random(int(self.sim_time.timestamp() * 100) % (2**32))
        if a.attitude_mode == AttitudeMode.NADIR:
            a.roll_deg = round(rng.gauss(0, 0.5), 2)
            a.pitch_deg = round(rng.gauss(0, 0.3), 2)
            a.yaw_deg = round(self._state.heading_deg + rng.gauss(0, 1.0), 2)
        elif a.attitude_mode == AttitudeMode.SAFE:
            a.roll_deg = round(a.roll_deg + rng.gauss(0, 0.1) * dt, 2)
            a.pitch_deg = round(a.pitch_deg + rng.gauss(0, 0.1) * dt, 2)
            a.yaw_deg = round(a.yaw_deg + rng.gauss(0, 0.1) * dt, 2)
        a.roll_rate_dps = round(rng.gauss(0, 0.01), 4)
        a.pitch_rate_dps = round(rng.gauss(0, 0.01), 4)
        a.yaw_rate_dps = round(rng.gauss(0, 0.02), 4)
        a.pointing_error_deg = round(math.sqrt(a.roll_deg**2 + a.pitch_deg**2), 2)

    def _update_power(self, dt: float):
        p = self._state.power
        rng = random.Random(int(self.sim_time.timestamp() * 100) % (2**32))
        
        orbit_period = 2 * math.pi * math.sqrt(
            (6371 + self._state.altitude_km) ** 3 / 398600.4418
        )
        elapsed_mod = (self.sim_time.timestamp() % orbit_period) / orbit_period
        in_sunlight = not (0.42 < elapsed_mod < 0.58)
        
        if in_sunlight and not self._state.faults.battery_low:
            p.solar_generation_w = round(
                self.spacecraft_config.solar_generation_w * rng.uniform(0.85, 1.0), 2
            )
        else:
            p.solar_generation_w = 0.0
        
        base = 0.5 + 0.3 + 0.2 + 0.1 + 0.1 + 0.3
        p.power_consumption_w = round(base * rng.uniform(0.9, 1.1), 2)
        
        p.net_power_w = round(p.solar_generation_w - p.power_consumption_w, 2)
        p.charge_state = "charging" if p.net_power_w > 0 else "discharging"
        
        energy_wh = p.net_power_w * (dt / 3600.0)
        delta_pct = (energy_wh / self.spacecraft_config.battery_capacity_wh) * 100.0
        p.battery_soc = round(max(0.0, min(100.0, p.battery_soc + delta_pct)), 2)
        p.battery_voltage = round(
            self.spacecraft_config.battery_voltage_nominal * (0.85 + 0.15 * p.battery_soc / 100.0), 2
        )

    def _update_thermal(self, dt: float):
        orbit_period = 2 * math.pi * math.sqrt(
            (6371 + self._state.altitude_km) ** 3 / 398600.4418
        )
        elapsed_mod = (self.sim_time.timestamp() % orbit_period) / orbit_period
        in_sunlight = not (0.42 < elapsed_mod < 0.58)
        env_temp = 40.0 if in_sunlight else -15.0
        tau = 120.0
        
        for name, node in self._state.thermal.nodes.items():
            heat = node.heat_generation_w
            dT_dt = (env_temp - node.temperature_c) / tau + heat * 0.5
            node.temperature_c = round(node.temperature_c + dT_dt * dt, 1)
            
            if node.temperature_c >= node.critical_threshold_c:
                node.thermal_state = "critical"
            elif node.temperature_c >= node.warning_threshold_c:
                node.thermal_state = "warning"
            else:
                node.thermal_state = "nominal"

    def _update_ground_pass(self):
        gs_lat = math.radians(self.ground_station.latitude)
        gs_lon = math.radians(self.ground_station.longitude)
        sat_lat = math.radians(self._state.latitude)
        sat_lon = math.radians(self._state.longitude)
        
        dlat = sat_lat - gs_lat
        dlon = sat_lon - gs_lon
        a = math.sin(dlat/2)**2 + math.cos(gs_lat)*math.cos(sat_lat)*math.sin(dlon/2)**2
        angle = 2 * math.asin(math.sqrt(a))
        distance_km = angle * 6371
        
        visible = distance_km < self.ground_station.max_range_km
        self._state.health.communications = (
            SubsystemStatus.NOMINAL if visible and not self._state.faults.comms_lost
            else SubsystemStatus.OFFLINE if self._state.faults.comms_lost
            else SubsystemStatus.DEGRADED
        )

    def _process_downlink(self, dt: float):
        q = self.downlink_queue
        pending = q.get_pending_items()
        if not pending:
            return
        
        visible = self._state.health.communications == SubsystemStatus.NOMINAL
        if not visible:
            return
        
        item = pending[0]
        transmitted = min(item.image_size_bytes - item.bytes_transmitted, q.downlink_rate_bytes_s * dt)
        item.bytes_transmitted = min(item.bytes_transmitted + transmitted, item.image_size_bytes)
        if item.bytes_transmitted >= item.image_size_bytes:
            item.status = "transmitted"
            item.transmitted_at = self.sim_time
            q.total_transmitted += 1
            q.total_bytes += item.image_size_bytes
            self._add_event(EventType.DOWNLINK_COMPLETED,
                          f"Observation {item.observation_id} downlinked", "info")

    def _check_observation(self):
        if self._state.faults.camera_failure:
            return
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
        self._add_event(EventType.OBSERVATION_STARTED, f"Observation {observation_id} started", "info")
        
        capture = self.camera.capture(self._state)
        self._state.camera_status = "standby"
        
        self._state.ml_status = "processing"
        try:
            cls_result = self.classifier.classify(capture["image_path"])
        except Exception as e:
            logger.error(f"ML classification failed: {e}")
            cls_result = {
                "smoke_probability": 0.0,
                "wildfire_probability": 0.0,
                "confidence": 0.0,
                "model_name": "unavailable",
                "model_version": "0.0.0",
                "inference_latency_ms": 0.0,
                "processing_status": "error",
            }
            self._state.ml_status = "error"
        else:
            self._state.ml_status = "real" if self._ml_mode == "real" else "mock"
        self._add_event(EventType.ML_RESULT_READY,
                       f"ML result for {observation_id}: smoke={cls_result['smoke_probability']:.3f}", "info")
        
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
            spacecraft_state_snapshot=self._state.model_dump(mode="json"),
        )
        
        self.observation_service.store(obs)
        self.last_observation_time = self.sim_time
        self._state.current_observation_id = observation_id
        self._state.smoke_probability = cls_result["smoke_probability"]
        self._state.confidence = cls_result["confidence"]
        self._state.priority = priority
        self._add_event(EventType.OBSERVATION_COMPLETED,
                       f"Observation {observation_id} completed - Priority: {priority}", "info")
        self._add_event(EventType.PRIORITY_CHANGED,
                       f"Priority set to {priority} for {observation_id}",
                       "warning" if priority in ("HIGH", "CRITICAL") else "info")
        
        # Queue for downlink
        self.downlink_queue.enqueue(DownlinkItem(
            observation_id=observation_id,
            priority=priority,
            image_size_bytes=capture.get("width", 1920) * capture.get("height", 1080) * 3,
        ))
        
        return obs

    def _update_mission_mode(self):
        if self._state.health.overall_health().value in ("CRITICAL", "OFFLINE"):
            if self._state.mission_mode != MissionMode.SAFE_MODE:
                self._add_event(EventType.SAFE_MODE_ENTERED, "Entering safe mode due to critical subsystem", "critical")
            self._state.mission_mode = MissionMode.SAFE_MODE
            self._state.attitude.attitude_mode = AttitudeMode.SAFE
        elif self._state.faults.thermal_critical or self._state.faults.battery_low:
            self._state.mission_mode = MissionMode.SAFE_MODE
            self._state.attitude.attitude_mode = AttitudeMode.SAFE
        elif self.current_observation_id and self._state.camera_status == "capturing":
            self._state.mission_mode = MissionMode.CAPTURING
        elif self.current_observation_id and self._state.ml_status == "processing":
            self._state.mission_mode = MissionMode.PROCESSING
        elif self.downlink_queue.get_queue_size() > 0 and self._state.health.communications == SubsystemStatus.NOMINAL:
            self._state.mission_mode = MissionMode.DOWNLINKING
        else:
            self._state.mission_mode = MissionMode.IDLE

    def _add_event(self, event_type: EventType, description: str, severity: str = "info", subsystem: str = None):
        event = MissionEvent(
            event_id=f"EVT-{self.packet_sequence:06d}",
            timestamp=self.sim_time,
            event_type=event_type,
            description=description,
            severity=severity,
            subsystem=subsystem,
        )
        self.event_log.add(event)

    def get_state(self) -> SpacecraftState:
        return self._state

    def get_latest_telemetry(self) -> TelemetryPacket:
        t = self._state
        recent_events = self.event_log.get_recent(5)
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
            roll_deg=t.attitude.roll_deg,
            pitch_deg=t.attitude.pitch_deg,
            yaw_deg=t.attitude.yaw_deg,
            battery_percentage=t.power.battery_soc,
            battery_voltage=t.power.battery_voltage,
            power_generation_w=t.power.solar_generation_w,
            power_consumption_w=t.power.power_consumption_w,
            temperatures=t.temperatures,
            communication_status=t.communication_status,
            gps_status=t.gps_status,
            camera_status=t.camera_status,
            ml_status=t.ml_status,
            current_observation_id=t.current_observation_id,
            smoke_probability=t.smoke_probability,
            confidence=t.confidence,
            priority=t.priority,
            health_status=t.health.overall_health().value,
            events=[e.model_dump(mode="json") for e in recent_events],
        )

    def get_ground_pass(self) -> dict:
        gs_lat = math.radians(self.ground_station.latitude)
        gs_lon = math.radians(self.ground_station.longitude)
        sat_lat = math.radians(self._state.latitude)
        sat_lon = math.radians(self._state.longitude)
        dlat = sat_lat - gs_lat
        dlon = sat_lon - gs_lon
        a = math.sin(dlat/2)**2 + math.cos(gs_lat)*math.cos(sat_lat)*math.sin(dlon/2)**2
        angle = 2 * math.asin(math.sqrt(a))
        distance_km = angle * 6371
        elevation_deg = max(0, 90 - math.degrees(math.asin(6371/(6371+self._state.altitude_km) * math.cos(math.radians(0)))))
        
        orbit_period = 2 * math.pi * math.sqrt((6371 + self._state.altitude_km)**3 / 398600.4418)
        time_to_next = orbit_period * (1 - angle / math.pi) if angle > 0 else 0
        
        return {
            "station_name": self.ground_station.name,
            "distance_km": round(distance_km, 1),
            "is_visible": distance_km < self.ground_station.max_range_km,
            "estimated_pass_duration_s": round(orbit_period * 0.08, 1),
            "next_pass_in_s": round(max(0, time_to_next), 0),
            "elevation_deg": round(min(90, elevation_deg), 1),
        }
