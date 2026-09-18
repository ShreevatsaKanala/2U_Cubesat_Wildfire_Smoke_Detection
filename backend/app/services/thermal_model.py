"""Thermal Model Service for CubeSat Digital Twin.

5-node thermal model: OBC, Battery, Camera, Comms, Structure.
Accounts for internal dissipation, solar heating, Earth albedo/IR,
radiative cooling, and inter-node conduction.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ThermalMode(str, Enum):
    NOMINAL = "NOMINAL"
    WARMING = "WARMING"
    COOLING = "COOLING"
    CRITICAL_HOT = "CRITICAL_HOT"
    CRITICAL_COLD = "CRITICAL_COLD"


class ThermalNodeConfig(BaseModel):
    name: str
    mass_kg: float = 0.1
    specific_heat_j_kg_k: float = 800.0
    area_m2: float = 0.01
    emissivity: float = 0.85
    min_temp_c: float = -40.0
    max_temp_c: float = 70.0
    optimal_min_c: float = 15.0
    optimal_max_c: float = 35.0


class ThermalNodeState(BaseModel):
    name: str
    temperature_c: float = 25.0
    heat_dissipation_w: float = 0.0
    solar_heating_w: float = 0.0
    earth_albedo_w: float = 0.0
    earth_ir_w: float = 0.0
    radiative_cooling_w: float = 0.0
    conduction_w: float = 0.0
    thermal_mode: ThermalMode = ThermalMode.NOMINAL
    heater_on: bool = False
    heater_power_w: float = 0.0
    temp_rate_per_s: float = 0.0
    prev_temp_c: float = 25.0


class ThermalEvent(BaseModel):
    timestamp: str
    node: str
    mode: ThermalMode
    temperature_c: float
    description: str


class ThermalModelConfig(BaseModel):
    ode45_enabled: bool = False
    timestep_s: float = 1.0
    heater_power_w: float = 3.0
    cooler_power_w: float = 2.0
    earth_albedo: float = 0.3
    earth_ir_flux_w_m2: float = 237.0
    deep_space_temp_k: float = 2.7
    sun_flux_w_m2: float = 1361.0


STEFAN_BOLTZMANN = 5.670374419e-8


class ThermalModel:
    """5-node thermal model with realistic heat transfer physics."""

    DEFAULT_NODES = {
        "obc": ThermalNodeConfig(
            name="obc", mass_kg=0.15, specific_heat_j_kg_k=896,
            area_m2=0.008, emissivity=0.9, min_temp_c=-20, max_temp_c=70,
        ),
        "battery": ThermalNodeConfig(
            name="battery", mass_kg=0.2, specific_heat_j_kg_k=1000,
            area_m2=0.01, emissivity=0.8, min_temp_c=0, max_temp_c=45,
            optimal_min_c=15, optimal_max_c=25,
        ),
        "camera": ThermalNodeConfig(
            name="camera", mass_kg=0.08, specific_heat_j_kg_k=800,
            area_m2=0.006, emissivity=0.85, min_temp_c=-30, max_temp_c=60,
        ),
        "comms": ThermalNodeConfig(
            name="comms", mass_kg=0.05, specific_heat_j_kg_k=500,
            area_m2=0.005, emissivity=0.7, min_temp_c=-40, max_temp_c=85,
        ),
        "structure": ThermalNodeConfig(
            name="structure", mass_kg=1.5, specific_heat_j_kg_k=900,
            area_m2=0.06, emissivity=0.6, min_temp_c=-150, max_temp_c=150,
        ),
    }

    CONDUCTION_MATRIX = {
        ("obc", "structure"): 0.05,
        ("battery", "structure"): 0.04,
        ("camera", "structure"): 0.03,
        ("comms", "structure"): 0.03,
        ("obc", "battery"): 0.01,
        ("camera", "obc"): 0.005,
        ("comms", "obc"): 0.005,
    }

    def __init__(self, config: ThermalModelConfig | None = None,
                 node_configs: dict[str, ThermalNodeConfig] | None = None):
        self._lock = threading.Lock()
        self.config = config or ThermalModelConfig()
        self._node_configs = node_configs or self.DEFAULT_NODES.copy()

        self.nodes: dict[str, ThermalNodeState] = {
            name: ThermalNodeState(name=name)
            for name in self._node_configs
        }
        self._events: list[ThermalEvent] = []
        self._max_events = 100
        self._last_update_time: Optional[float] = None

    def _log_event(self, node_name: str, mode: ThermalMode,
                   temp_c: float, description: str):
        evt = ThermalEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            node=node_name,
            mode=mode,
            temperature_c=round(temp_c, 1),
            description=description,
        )
        self._events.append(evt)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        logger.info(f"[Thermal] {node_name}: {mode.value} at {temp_c:.1f}°C — {description}")

    def update(self, dt_seconds: float, orbital_state: dict | None = None,
               subsystem_power: dict[str, float] | None = None,
               heaters_off: bool = False) -> dict[str, ThermalNodeState]:
        with self._lock:
            now = time.time()
            if self._last_update_time is None:
                self._last_update_time = now
            actual_dt = min(dt_seconds, 10.0)
            self._last_update_time = now

            orbital = orbital_state or {}
            in_sunlight = orbital.get("in_sunlight", True)
            sun_angle = orbital.get("sun_angle_deg", 0.0)
            altitude_km = orbital.get("altitude_km", 500.0)

            power = subsystem_power or {}

            for name, node in self.nodes.items():
                cfg = self._node_configs[name]
                node.prev_temp_c = node.temperature_c

                node.heat_dissipation_w = power.get(name, 0.0) * 0.8

                if in_sunlight:
                    cos_sun = max(0, math.cos(math.radians(sun_angle)))
                    solar_flux = self.config.sun_flux_w_m2 * cos_sun
                    node.solar_heating_w = solar_flux * cfg.area_m2 * 0.15
                else:
                    node.solar_heating_w = 0.0

                if name == "structure":
                    node.earth_albedo_w = (self.config.earth_albedo *
                                           self.config.sun_flux_w_m2 * cfg.area_m2 * 0.05
                                           if in_sunlight else 0.0)
                    node.earth_ir_w = self.config.earth_ir_flux_w_m2 * cfg.area_m2 * 0.03
                else:
                    node.earth_albedo_w = 0.0
                    node.earth_ir_w = 0.0

                temp_k = node.temperature_c + 273.15
                space_k = self.config.deep_space_temp_k
                node.radiative_cooling_w = (
                    STEFAN_BOLTZMANN * cfg.emissivity * cfg.area_m2 *
                    (temp_k ** 4 - space_k ** 4) * 0.01
                )

                node.conduction_w = 0.0
                for (n1, n2), conductance in self.CONDUCTION_MATRIX.items():
                    if name in (n1, n2):
                        other_name = n2 if name == n1 else n1
                        other = self.nodes.get(other_name)
                        if other:
                            node.conduction_w += conductance * (other.temperature_c - node.temperature_c)

                if not heaters_off and node.temperature_c < cfg.min_temp_c + 5:
                    node.heater_on = True
                    node.heater_power_w = self.config.heater_power_w
                elif node.temperature_c > cfg.optimal_max_c:
                    node.heater_on = False
                    node.heater_power_w = 0.0
                elif heaters_off:
                    node.heater_on = False
                    node.heater_power_w = 0.0

                total_heat_w = (
                    node.heat_dissipation_w +
                    node.solar_heating_w +
                    node.earth_albedo_w +
                    node.earth_ir_w +
                    node.heater_power_w -
                    node.radiative_cooling_w +
                    node.conduction_w
                )

                thermal_mass = cfg.mass_kg * cfg.specific_heat_j_kg_k
                if thermal_mass > 0:
                    dT_dt = total_heat_w / thermal_mass
                    node.temperature_c = round(node.temperature_c + dT_dt * actual_dt, 2)
                else:
                    node.temperature_c = node.temperature_c

                node.temp_rate_per_s = round(
                    (node.temperature_c - node.prev_temp_c) / actual_dt, 4
                ) if actual_dt > 0 else 0.0

                prev_mode = node.thermal_mode
                if node.temperature_c > cfg.max_temp_c:
                    node.thermal_mode = ThermalMode.CRITICAL_HOT
                elif node.temperature_c < cfg.min_temp_c:
                    node.thermal_mode = ThermalMode.CRITICAL_COLD
                elif node.temp_rate_per_s > 0.1:
                    node.thermal_mode = ThermalMode.WARMING
                elif node.temp_rate_per_s < -0.1:
                    node.thermal_mode = ThermalMode.COOLING
                else:
                    node.thermal_mode = ThermalMode.NOMINAL

                if node.thermal_mode != prev_mode:
                    self._log_event(
                        name, node.thermal_mode, node.temperature_c,
                        f"Mode change: {prev_mode.value} → {node.thermal_mode.value}",
                    )

            return self.nodes.copy()

    def get_node_temperatures(self) -> dict[str, float]:
        return {name: round(node.temperature_c, 2) for name, node in self.nodes.items()}

    def get_trends(self) -> dict[str, dict]:
        trends = {}
        for name, node in self.nodes.items():
            cfg = self._node_configs[name]
            trends[name] = {
                "temperature_c": round(node.temperature_c, 2),
                "rate_per_s": node.temp_rate_per_s,
                "thermal_mode": node.thermal_mode.value,
                "heater_on": node.heater_on,
                "heat_dissipation_w": round(node.heat_dissipation_w, 3),
                "solar_heating_w": round(node.solar_heating_w, 3),
                "radiative_cooling_w": round(node.radiative_cooling_w, 3),
                "conduction_w": round(node.conduction_w, 3),
                "min_temp_c": cfg.min_temp_c,
                "max_temp_c": cfg.max_temp_c,
                "margin_to_hot_c": round(cfg.max_temp_c - node.temperature_c, 1),
                "margin_to_cold_c": round(node.temperature_c - cfg.min_temp_c, 1),
            }
        return trends

    def get_overall_mode(self) -> ThermalMode:
        modes = [node.thermal_mode for node in self.nodes.values()]
        if ThermalMode.CRITICAL_HOT in modes or ThermalMode.CRITICAL_COLD in modes:
            return ThermalMode.CRITICAL_HOT if ThermalMode.CRITICAL_HOT in modes else ThermalMode.CRITICAL_COLD
        if ThermalMode.WARMING in modes:
            return ThermalMode.WARMING
        if ThermalMode.COOLING in modes:
            return ThermalMode.COOLING
        return ThermalMode.NOMINAL

    def predict_time_to_limit(self, node_name: str) -> Optional[float]:
        node = self.nodes.get(node_name)
        cfg = self._node_configs.get(node_name)
        if not node or not cfg or node.temp_rate_per_s == 0:
            return None

        if node.temp_rate_per_s > 0:
            seconds_to_max = (cfg.max_temp_c - node.temperature_c) / node.temp_rate_per_s
            return max(0, seconds_to_max)
        else:
            seconds_to_min = (node.temperature_c - cfg.min_temp_c) / abs(node.temp_rate_per_s)
            return max(0, seconds_to_min)

    def get_events(self, limit: int = 20) -> list[dict]:
        return [e.model_dump() for e in self._events[-limit:]]

    def get_status(self) -> dict:
        with self._lock:
            return {
                "nodes": {k: v.model_dump() for k, v in self.nodes.items()},
                "trends": self.get_trends(),
                "overall_mode": self.get_overall_mode().value,
                "recent_events": self.get_events(),
            }

    def reset(self):
        with self._lock:
            for name, node in self.nodes.items():
                node.temperature_c = 25.0
                node.prev_temp_c = 25.0
                node.temp_rate_per_s = 0.0
                node.thermal_mode = ThermalMode.NOMINAL
                node.heater_on = False
                node.heater_power_w = 0.0
            self._events.clear()
            self._last_update_time = None
