import math
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.demo.scenarios import (
    SCENARIO_CONFIGS,
    GROUND_STATIONS,
    ORBIT_PARAMS,
    THERMAL_NODES,
    EVENT_TYPES,
)

_EARTH_RADIUS_KM = 6371.0
_DEG_TO_RAD = math.pi / 180.0
_RAD_TO_DEG = 180.0 / math.pi
_TWO_PI = 2.0 * math.pi


def _hash_deterministic(seed: str) -> float:
    h = 0
    for ch in seed:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return (h & 0xFFFF) / 0xFFFF


class DemoEngine:
    def __init__(self, scenario: str = "NORMAL_MISSION", speed: float = 1.0):
        self._lock = threading.Lock()
        self._scenario = scenario if scenario in SCENARIO_CONFIGS else "NORMAL_MISSION"
        self._speed = speed
        self._running = False
        self._sim_time_s: float = 0.0
        self._start_wall = time.monotonic()

        self._observations: list[dict] = []
        self._events: list[dict] = []
        self._downlink_queue: list[dict] = []

        self._faults: set[str] = set()
        self._next_obs_time: float = 0.0
        self._next_event_id = 1

        self._orbit_phase = 0.0
        self._orbit_ascending_node = 0.0

        self._battery_soc = 92.0
        self._solar_generation_w = 0.0
        self._power_load_w = 0.0

        self._thermal_temps: dict[str, float] = {}
        for node in THERMAL_NODES:
            self._thermal_temps[node] = SCENARIO_CONFIGS[self._scenario]["thermal_base"]

        self._init_thermal()

    def _init_thermal(self):
        base = SCENARIO_CONFIGS[self._scenario]["thermal_base"]
        offsets = {"BATTERY": 5.0, "SOLAR_PANEL": 8.0, "PROCESSOR": 12.0, "ANTENNA": -2.0, "STRUCTURE": 0.0}
        for node in THERMAL_NODES:
            self._thermal_temps[node] = base + offsets.get(node, 0.0)

    def start(self):
        with self._lock:
            self._running = True
            self._start_wall = time.monotonic()

    def stop(self):
        with self._lock:
            self._running = False

    def reset(self):
        with self._lock:
            self._running = False
            self._sim_time_s = 0.0
            self._observations.clear()
            self._events.clear()
            self._downlink_queue.clear()
            self._faults.clear()
            self._next_obs_time = 0.0
            self._next_event_id = 1
            self._orbit_phase = 0.0
            self._battery_soc = 92.0
            self._init_thermal()

    def set_scenario(self, scenario: str):
        if scenario not in SCENARIO_CONFIGS:
            return
        with self._lock:
            self._scenario = scenario
            self._next_obs_time = self._sim_time_s + SCENARIO_CONFIGS[scenario]["observation_interval_s"]
            self._init_thermal()

    def set_speed(self, speed: float):
        with self._lock:
            self._speed = max(0.1, min(speed, 100.0))

    def inject_fault(self, fault_type: str):
        with self._lock:
            self._faults.add(fault_type.upper())

    def clear_fault(self, fault_type: str):
        with self._lock:
            self._faults.discard(fault_type.upper())

    def tick(self, dt_seconds: float) -> dict:
        if not self._running:
            return self.get_state()

        effective_dt = dt_seconds * self._speed
        with self._lock:
            self._sim_time_s += effective_dt
            self._update_orbit(effective_dt)
            self._update_power(effective_dt)
            self._update_thermal(effective_dt)
            self._generate_observations()
            self._update_downlink(effective_dt)
            self._process_faults()

        return self.get_state()

    def _update_orbit(self, dt: float):
        period_s = ORBIT_PARAMS["period_minutes"] * 60.0
        angular_velocity = _TWO_PI / period_s
        self._orbit_phase += angular_velocity * dt
        self._orbit_phase %= _TWO_PI
        self._orbit_ascending_node = (self._orbit_ascending_node + angular_velocity * dt * 0.05) % _TWO_PI

    def _get_position(self) -> dict:
        inc_rad = ORBIT_PARAMS["inclination_deg"] * _DEG_TO_RAD
        alt_km = ORBIT_PARAMS["altitude_km"]

        lat = math.asin(math.sin(inc_rad) * math.sin(self._orbit_phase)) * _RAD_TO_DEG
        lon_offset = math.atan2(
            math.tan(self._orbit_phase) * math.cos(inc_rad),
            1.0
        ) * _RAD_TO_DEG
        lon = (self._orbit_ascending_node * _RAD_TO_DEG + lon_offset) % 360.0
        if lon > 180.0:
            lon -= 360.0

        orbital_speed_km_s = 2.0 * math.pi * (_EARTH_RADIUS_KM + alt_km) / (ORBIT_PARAMS["period_minutes"] * 60.0)

        return {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "altitude_km": alt_km,
            "velocity_km_s": round(orbital_speed_km_s, 4),
        }

    def _get_attitude(self) -> dict:
        seed = f"att_{self._sim_time_s:.1f}"
        jitter_pitch = (_hash_deterministic(seed + "p") - 0.5) * 0.4
        jitter_roll = (_hash_deterministic(seed + "r") - 0.5) * 0.3
        jitter_yaw = (_hash_deterministic(seed + "y") - 0.5) * 0.5
        return {
            "mode": "NADIR",
            "pitch_deg": round(jitter_pitch, 3),
            "roll_deg": round(jitter_roll, 3),
            "yaw_deg": round(jitter_yaw, 3),
            "pointing_accuracy_deg": 0.05,
        }

    def _update_power(self, dt: float):
        cfg = SCENARIO_CONFIGS[self._scenario]
        pos = self._get_position()
        alt_km = pos["altitude_km"]
        orbital_period_s = ORBIT_PARAMS["period_minutes"] * 60.0
        orbit_fraction = (self._orbit_phase / _TWO_PI) % 1.0
        in_eclipse = 0.25 < orbit_fraction < 0.75

        solar_area_m2 = 0.04
        solar_flux_w_m2 = 1361.0 if not in_eclipse else 0.0
        self._solar_generation_w = solar_area_m2 * solar_flux_w_m2 * cfg["solar_efficiency"]

        base_load = 8.0
        if self._scenario == "HIGH_PRIORITY":
            base_load = 12.0
        self._power_load_w = base_load

        if "BATTERY_DRAIN" in self._faults or "POWER_FAULT" in self._faults:
            self._power_load_w += 5.0

        balance = self._solar_generation_w - self._power_load_w
        soc_change = (balance / 30.0) * dt
        self._battery_soc += soc_change
        self._battery_soc = max(0.0, min(100.0, self._battery_soc))

    def _update_thermal(self, dt: float):
        cfg = SCENARIO_CONFIGS[self._scenario]
        base = cfg["thermal_base"]
        pos = self._get_position()
        orbit_fraction = (self._orbit_phase / _TWO_PI) % 1.0
        in_eclipse = 0.25 < orbit_fraction < 0.75
        solar_heat = 5.0 if not in_eclipse else -2.0

        seed_t = f"thermal_{self._sim_time_s:.0f}"
        for i, node in enumerate(THERMAL_NODES):
            noise = (_hash_deterministic(seed_t + node) - 0.5) * 1.5
            target = base + solar_heat * (0.8 if node == "SOLAR_PANEL" else 0.3)
            if node == "PROCESSOR":
                target += 15.0
            elif node == "BATTERY":
                target += 8.0
            elif node == "ANTENNA":
                target -= 5.0

            if "THERMAL_FAULT" in self._faults:
                target += 20.0

            current = self._thermal_temps[node]
            alpha = 0.01
            self._thermal_temps[node] = current + alpha * (target - current) + noise * 0.1

    def _generate_observations(self):
        cfg = SCENARIO_CONFIGS[self._scenario]
        if self._sim_time_s < self._next_obs_time:
            return

        interval = cfg["observation_interval_s"]
        self._next_obs_time = self._sim_time_s + interval

        pos = self._get_position()
        seed_o = f"obs_{self._sim_time_s:.0f}"
        weights = cfg["smoke_score_weights"]
        score = self._weighted_score(seed_o, weights)

        obs = {
            "id": str(uuid.uuid4()),
            "timestamp_s": round(self._sim_time_s, 2),
            "latitude": round(pos["latitude"] + (_hash_deterministic(seed_o + "lat") - 0.5) * 0.5, 4),
            "longitude": round(pos["longitude"] + (_hash_deterministic(seed_o + "lon") - 0.5) * 0.5, 4),
            "altitude_km": pos["altitude_km"],
            "camera_angle_deg": round(_hash_deterministic(seed_o + "cam") * 30.0, 1),
            "ai_smoke_score": round(score, 4),
            "ai_priority": self._score_to_priority(score),
            "visual_evidence": self._visual_evidence(score),
            "alternative_explanations": self._alternatives(score),
            "analysis_complete": True,
        }
        self._observations.append(obs)

        self._add_event("OBSERVATION_CAPTURED", f"Observation {obs['id'][:8]} captured at ({obs['latitude']}, {obs['longitude']})")
        self._add_event("AI_ANALYSIS_COMPLETE", f"AI analysis: smoke score {score:.3f}, priority {obs['ai_priority']}")

        if score >= cfg["priority_threshold"]:
            self._add_event("PRIORITY_ASSIGNMENT", f"Priority assigned: {obs['ai_priority']} (score: {score:.3f})")
            self._queue_downlink(obs)

    def _weighted_score(self, seed: str, weights: list[float]) -> float:
        r = _hash_deterministic(seed)
        cumulative = 0.0
        ranges = [
            (0.0, 0.3),
            (0.3, 0.6),
            (0.6, 0.85),
            (0.85, 0.95),
        ]
        for i, w in enumerate(weights):
            cumulative += w
            if r < cumulative:
                lo, hi = ranges[min(i, len(ranges) - 1)]
                sub_seed = f"{seed}_s{i}"
                return lo + (_hash_deterministic(sub_seed) * (hi - lo))
        return 0.2

    @staticmethod
    def _score_to_priority(score: float) -> str:
        if score >= 0.85:
            return "CRITICAL"
        elif score >= 0.65:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _visual_evidence(score: float) -> str:
        if score >= 0.7:
            return "Dense white-gray plume detected with thermal anomaly. Confirmed smoke signature."
        elif score >= 0.4:
            return "Moderate haze or smoke-like feature observed. Possible agricultural burning."
        elif score >= 0.2:
            return "Light haze or cloud formation. Low confidence smoke detection."
        return "Clear sky or negligible atmospheric feature."

    @staticmethod
    def _alternatives(score: float) -> list[str]:
        if score >= 0.7:
            return ["Cloud formation", "Industrial emissions", "Dust storm"]
        elif score >= 0.4:
            return ["Agricultural burning", "Controlled burn", "Cloud formation"]
        return ["Cloud cover", "Atmospheric scattering", "Sensor noise"]

    def _queue_downlink(self, obs: dict):
        station = self._pick_ground_station()
        item = {
            "id": str(uuid.uuid4()),
            "observation_id": obs["id"],
            "station": station["id"],
            "station_name": station["name"],
            "band": station["band"],
            "data_rate_mbps": station["data_rate_mbps"],
            "data_size_mb": round(12.0 + _hash_deterministic(obs["id"]) * 8.0, 2),
            "progress_pct": 0.0,
            "status": "QUEUED",
            "queued_at_s": round(self._sim_time_s, 2),
        }
        self._downlink_queue.append(item)
        self._add_event("DOWNLINK_QUEUED", f"Data queued for downlink to {station['name']} ({station['band']} band)")

    def _pick_ground_station(self) -> dict:
        pos = self._get_position()
        best = GROUND_STATIONS[0]
        best_dist = float("inf")
        for gs in GROUND_STATIONS:
            dlat = pos["latitude"] - gs["lat"]
            dlon = pos["longitude"] - gs["lon"]
            dist = math.sqrt(dlat ** 2 + dlon ** 2)
            if dist < best_dist:
                best_dist = dist
                best = gs
        return best

    def _update_downlink(self, dt: float):
        for item in self._downlink_queue:
            if item["status"] == "QUEUED":
                item["status"] = "IN_PROGRESS"
                self._add_event("DOWNLINK_STARTED", f"Downlink started to {item['station_name']}")
            if item["status"] == "IN_PROGRESS":
                rate_per_s = item["data_rate_mbps"] / item["data_size_mb"] * 0.1
                item["progress_pct"] = min(100.0, item["progress_pct"] + rate_per_s * dt)
                if item["progress_pct"] >= 100.0:
                    item["status"] = "COMPLETE"
                    self._add_event("DOWNLINK_COMPLETE", f"Downlink to {item['station_name']} complete")

    def _process_faults(self):
        if "COMM_LOSS" in self._faults:
            self._add_event("COMM_LOSS", "Communications link lost")

    def _add_event(self, event_type: str, description: str):
        ev = {
            "id": self._next_event_id,
            "type": event_type,
            "description": description,
            "timestamp_s": round(self._sim_time_s, 2),
            "severity": self._event_severity(event_type),
        }
        self._events.append(ev)
        self._next_event_id += 1
        if len(self._events) > 500:
            self._events = self._events[-500:]

    @staticmethod
    def _event_severity(event_type: str) -> str:
        severity_map = {
            "OBSERVATION_CAPTURED": "INFO",
            "AI_ANALYSIS_COMPLETE": "INFO",
            "PRIORITY_ASSIGNMENT": "WARNING",
            "DOWNLINK_QUEUED": "INFO",
            "GROUND_CONTACT": "INFO",
            "DOWNLINK_STARTED": "INFO",
            "DOWNLINK_COMPLETE": "INFO",
            "COMM_LOSS": "CRITICAL",
        }
        return severity_map.get(event_type, "INFO")

    def _get_ground_station_status(self) -> list[dict]:
        pos = self._get_position()
        alt_km = pos["altitude_km"]
        visibility_radius_deg = math.degrees(math.acos(_EARTH_RADIUS_KM / (_EARTH_RADIUS_KM + alt_km)))

        stations = []
        for gs in GROUND_STATIONS:
            dlat = pos["latitude"] - gs["lat"]
            dlon = pos["longitude"] - gs["lon"]
            dist = math.sqrt(dlat ** 2 + dlon ** 2)
            in_view = dist < visibility_radius_deg
            elevation = max(0.0, 90.0 - dist) if in_view else 0.0
            stations.append({
                "id": gs["id"],
                "name": gs["name"],
                "lat": gs["lat"],
                "lon": gs["lon"],
                "in_view": in_view,
                "elevation_deg": round(elevation, 1),
                "band": gs["band"],
                "data_rate_mbps": gs["data_rate_mbps"],
            })
        return stations

    def get_state(self) -> dict:
        with self._lock:
            pos = self._get_position()
            att = self._get_attitude()
            cfg = SCENARIO_CONFIGS[self._scenario]

            active_downlinks = [d for d in self._downlink_queue if d["status"] == "IN_PROGRESS"]
            queued_downlinks = [d for d in self._downlink_queue if d["status"] == "QUEUED"]
            completed_downlinks = [d for d in self._downlink_queue if d["status"] == "COMPLETE"]

            mode = cfg["mode"]
            if self._battery_soc < 15.0:
                mode = "SAFE"
            elif "COMM_LOSS" in self._faults:
                mode = "SAFE"

            return {
                "running": self._running,
                "scenario": self._scenario,
                "speed": self._speed,
                "sim_time_s": round(self._sim_time_s, 2),
                "mission_elapsed_time": self._format_met(self._sim_time_s),
                "position": pos,
                "attitude": att,
                "power": {
                    "battery_soc_pct": round(self._battery_soc, 2),
                    "solar_generation_w": round(self._solar_generation_w, 2),
                    "power_load_w": round(self._power_load_w, 2),
                    "power_balance_w": round(self._solar_generation_w - self._power_load_w, 2),
                    "in_eclipse": 0.25 < ((self._orbit_phase / _TWO_PI) % 1.0) < 0.75,
                },
                "thermal": {
                    node: round(self._thermal_temps[node], 2) for node in THERMAL_NODES
                },
                "mode": mode,
                "health": {
                    "subsystem_status": {
                        "OBC": "NOMINAL",
                        "ADCS": "NOMINAL",
                        "EPS": "NOMINAL" if "POWER_FAULT" not in self._faults else "DEGRADED",
                        "COMMS": "NOMINAL" if "COMM_LOSS" not in self._faults else "FAULT",
                        "THERMAL": "NOMINAL" if "THERMAL_FAULT" not in self._faults else "WARNING",
                        "PAYLOAD": "NOMINAL",
                    },
                    "faults": list(self._faults),
                },
                "downlink": {
                    "active_count": len(active_downlinks),
                    "queued_count": len(queued_downlinks),
                    "completed_count": len(completed_downlinks),
                    "queue": self._downlink_queue[-20:],
                },
                "observation_count": len(self._observations),
            }

    def get_telemetry(self) -> dict:
        with self._lock:
            pos = self._get_position()
            att = self._get_attitude()
            return {
                "type": "telemetry",
                "timestamp_s": round(self._sim_time_s, 2),
                "mission_elapsed_time": self._format_met(self._sim_time_s),
                "position": pos,
                "attitude": att,
                "power": {
                    "battery_soc_pct": round(self._battery_soc, 2),
                    "solar_generation_w": round(self._solar_generation_w, 2),
                    "power_load_w": round(self._power_load_w, 2),
                },
                "thermal": {
                    node: round(self._thermal_temps[node], 2) for node in THERMAL_NODES
                },
                "mode": SCENARIO_CONFIGS[self._scenario]["mode"],
            }

    def get_observations(self) -> list[dict]:
        with self._lock:
            return list(self._observations[-100:])

    def get_events(self) -> list[dict]:
        with self._lock:
            return list(self._events[-100:])

    def get_downlink_status(self) -> dict:
        with self._lock:
            return {
                "active": [d for d in self._downlink_queue if d["status"] == "IN_PROGRESS"],
                "queued": [d for d in self._downlink_queue if d["status"] == "QUEUED"],
                "completed": [d for d in self._downlink_queue if d["status"] == "COMPLETE"],
            }

    def get_ground_stations(self) -> list[dict]:
        with self._lock:
            return self._get_ground_station_status()

    def get_ai_status(self) -> dict:
        with self._lock:
            scores = [o["ai_smoke_score"] for o in self._observations]
            priorities = [o["ai_priority"] for o in self._observations]
            return {
                "total_analyzed": len(self._observations),
                "avg_smoke_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
                "max_smoke_score": round(max(scores), 4) if scores else 0.0,
                "priority_breakdown": {
                    "CRITICAL": priorities.count("CRITICAL"),
                    "HIGH": priorities.count("HIGH"),
                    "MEDIUM": priorities.count("MEDIUM"),
                    "LOW": priorities.count("LOW"),
                },
                "last_analysis_time_s": round(self._sim_time_s, 2) if self._observations else None,
            }

    @staticmethod
    def _format_met(seconds: float) -> str:
        total = int(seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"T+{h:02d}:{m:02d}:{s:02d}"
