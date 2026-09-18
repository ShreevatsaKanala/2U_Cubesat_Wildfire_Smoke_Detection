"""Deeper EPS (Electrical Power Subsystem) Model for CubeSat Digital Twin.

Provides per-subsystem power consumption, solar panel generation, battery model,
power budget events, and load shedding. Designed to be called BY the simulation engine.
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


class PowerBudgetEvent(str, Enum):
    LOW_POWER_WARNING = "LOW_POWER_WARNING"
    CRITICAL_POWER = "CRITICAL_POWER"
    EMERGENCY_POWER = "EMERGENCY_POWER"
    LOAD_SHEDDING = "LOAD_SHEDDING"


class LoadPriority(int, Enum):
    SCIENCE_ML = 0
    ADCS = 1
    COMMS_TX = 2
    CAMERA = 3
    OBC = 4
    COMMS_RX = 5
    THERMAL = 6


class SubsystemPower(BaseModel):
    name: str
    nominal_w: float = 0.0
    peak_w: float = 0.0
    is_active: bool = True
    duty_cycle: float = 1.0
    is_shed: bool = False

    @property
    def current_w(self) -> float:
        if self.is_shed or not self.is_active:
            return 0.0
        return self.nominal_w * self.duty_cycle


class BatteryState(BaseModel):
    soc_percent: float = Field(default=85.0, ge=0, le=100)
    voltage_v: float = 7.178
    capacity_wh: float = 40.0
    temperature_c: float = 22.0
    charge_cycles: int = 0
    total_ah_throughput: float = 0.0
    depth_of_discharge_max: float = 0.0
    coulomb_count_ah: float = 0.0

    def effective_capacity_wh(self) -> float:
        temp_factor = 1.0
        if self.temperature_c < 0:
            temp_factor = 0.7 + 0.3 * (self.temperature_c + 20) / 20
        elif self.temperature_c > 45:
            temp_factor = 1.0 - 0.02 * (self.temperature_c - 45)
        return self.capacity_wh * max(0.3, min(1.0, temp_factor))


class SolarPanelState(BaseModel):
    generation_w: float = 0.0
    max_generation_w: float = 2.0
    sun_angle_deg: float = 0.0
    in_eclipse: bool = False
    degradation_factor: float = 1.0
    panel_efficiency: float = 0.28


class EPSState(BaseModel):
    subsystems: dict[str, SubsystemPower] = Field(default_factory=dict)
    battery: BatteryState = Field(default_factory=BatteryState)
    solar_panel: SolarPanelState = Field(default_factory=SolarPanelState)
    total_consumption_w: float = 0.0
    net_power_w: float = 0.0
    charge_state: str = "discharging"
    budget_events: list[str] = Field(default_factory=list)
    shed_loads: list[str] = Field(default_factory=list)


class EPSModel:
    """Thread-safe EPS model with realistic power budgeting."""

    ORBIT_RADIUS_KM = 6371.0 + 500.0
    EARTH_RADIUS_KM = 6371.0
    MU_EARTH = 398600.4418
    SOLAR_CONSTANT_W_M2 = 1361.0
    PANEL_AREA_M2 = 0.03
    DEGRADATION_PER_YEAR = 0.005

    def __init__(self, config: dict | None = None):
        self._lock = threading.Lock()
        config = config or {}
        self._start_time = time.time()

        self.state = EPSState(
            subsystems={
                "obc": SubsystemPower(name="obc", nominal_w=2.0, peak_w=5.0),
                "camera": SubsystemPower(name="camera", nominal_w=1.0, peak_w=3.0, is_active=False),
                "comms_tx": SubsystemPower(name="comms_tx", nominal_w=0.5, peak_w=5.0, is_active=False),
                "comms_rx": SubsystemPower(name="comms_rx", nominal_w=0.1, peak_w=1.0),
                "adcs": SubsystemPower(name="adcs", nominal_w=1.5, peak_w=1.5),
                "ml": SubsystemPower(name="ml", nominal_w=0.0, peak_w=2.0, is_active=False),
                "thermal": SubsystemPower(name="thermal", nominal_w=0.0, peak_w=3.0, duty_cycle=0.0),
            },
            battery=BatteryState(
                capacity_wh=config.get("battery_capacity_wh", 40.0),
                soc_percent=config.get("initial_soc", 85.0),
            ),
            solar_panel=SolarPanelState(
                max_generation_w=config.get("solar_max_w", 2.0),
            ),
        )
        self._budget_events: list[dict] = []
        self._max_events = 100

    def _add_budget_event(self, event: PowerBudgetEvent, detail: str) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event.value,
            "detail": detail,
            "soc": self.state.battery.soc_percent,
        }
        self._budget_events.append(entry)
        if len(self._budget_events) > self._max_events:
            self._budget_events = self._budget_events[-self._max_events:]
        return entry

    def update_solar(self, orbital_position: dict, sim_time_s: float) -> float:
        with self._lock:
            pos = orbital_position
            sun_vec = pos.get("sun_vector", [1.0, 0.0, 0.0])
            sat_pos = pos.get("position_km", [0.0, 0.0, self.ORBIT_RADIUS_KM])

            dot = sum(a * b for a, b in zip(sat_pos, sun_vec))
            mag_sat = math.sqrt(sum(x ** 2 for x in sat_pos))
            mag_sun = math.sqrt(sum(x ** 2 for x in sun_vec)) or 1.0
            cos_angle = max(-1.0, min(1.0, dot / (mag_sat * mag_sun)))
            sun_angle_deg = math.degrees(math.acos(cos_angle))

            in_eclipse = self._check_eclipse(sat_pos, sun_vec)

            elapsed_years = (time.time() - self._start_time) / (365.25 * 86400)
            degradation = (1.0 - self.DEGRADATION_PER_YEAR) ** elapsed_years

            if in_eclipse or cos_angle <= 0:
                generation = 0.0
            else:
                irradiance = self.SOLAR_CONSTANT_W_M2 * cos_angle
                generation = (irradiance * self.PANEL_AREA_M2 *
                              self.state.solar_panel.panel_efficiency * degradation)

            self.state.solar_panel.generation_w = round(generation, 3)
            self.state.solar_panel.sun_angle_deg = round(sun_angle_deg, 1)
            self.state.solar_panel.in_eclipse = in_eclipse
            self.state.solar_panel.degradation_factor = round(degradation, 4)

            return generation

    def _check_eclipse(self, sat_pos: list[float], sun_vec: list[float]) -> bool:
        r_sat = math.sqrt(sum(x ** 2 for x in sat_pos))
        if r_sat <= self.EARTH_RADIUS_KM:
            return True

        cos_alpha = sum(a * b for a, b in zip(sat_pos, sun_vec)) / (
            r_sat * math.sqrt(sum(x ** 2 for x in sun_vec)) or 1.0
        )
        if cos_alpha <= 0:
            return False

        shadow_radius = self.EARTH_RADIUS_KM * 0.99
        perp_dist = r_sat * math.sqrt(max(0, 1 - cos_alpha ** 2))
        return perp_dist < shadow_radius

    def update_consumption(self, mission_mode: str = "IDLE",
                           camera_active: bool = False,
                           comms_active: bool = False,
                           ml_active: bool = False,
                           thermal_duty: float = 0.0) -> float:
        with self._lock:
            subs = self.state.subsystems

            subs["obc"].is_active = True
            subs["camera"].is_active = camera_active
            subs["comms_tx"].is_active = comms_active
            subs["comms_rx"].is_active = True
            subs["adcs"].is_active = mission_mode not in ("SAFE_MODE",)
            subs["ml"].is_active = ml_active
            subs["thermal"].duty_cycle = thermal_duty

            if mission_mode == "CAPTURING":
                subs["obc"].nominal_w = 5.0
                subs["camera"].nominal_w = 3.0
            elif mission_mode == "PROCESSING":
                subs["obc"].nominal_w = 2.0
                subs["ml"].nominal_w = 2.0
            elif mission_mode == "DOWNLINKING":
                subs["obc"].nominal_w = 2.0
                subs["comms_tx"].nominal_w = 5.0
            else:
                subs["obc"].nominal_w = 2.0

            total = sum(s.current_w for s in subs.values())
            self.state.total_consumption_w = round(total, 3)
            return total

    def update_battery(self, dt_seconds: float) -> BatteryState:
        with self._lock:
            bat = self.state.battery
            net_w = self.state.solar_panel.generation_w - self.state.total_consumption_w
            self.state.net_power_w = round(net_w, 3)
            self.state.charge_state = "charging" if net_w > 0 else "discharging"

            energy_wh = net_w * (dt_seconds / 3600.0)
            effective_cap = bat.effective_capacity_wh()
            delta_soc = (energy_wh / effective_cap) * 100.0

            if net_w < 0:
                dod = (100.0 - bat.soc_percent) / 100.0
                bat.depth_of_discharge_max = max(bat.depth_of_discharge_max, dod)

            bat.soc_percent = round(max(0.0, min(100.0, bat.soc_percent + delta_soc)), 2)
            bat.voltage_v = round(
                3.0 + 4.4 * (bat.soc_percent / 100.0) * (1.0 - 0.01 * max(0, bat.temperature_c - 25)),
                3,
            )

            bat.total_ah_throughput += abs(net_w * dt_seconds / 3600.0 / bat.voltage_v)
            if net_w < 0 and bat.soc_percent < 100:
                bat.charge_cycles += max(0, int(dt_seconds / 3600))

            self._check_budget_events()
            return bat

    def _check_budget_events(self):
        bat = self.state.battery
        events = self.state.budget_events

        if bat.soc_percent < 10 and "EMERGENCY_POWER" not in events:
            self._add_budget_event(PowerBudgetEvent.EMERGENCY_POWER,
                                   f"SOC={bat.soc_percent:.1f}% — EMERGENCY")
            events.append("EMERGENCY_POWER")
        elif bat.soc_percent < 15 and "CRITICAL_POWER" not in events:
            self._add_budget_event(PowerBudgetEvent.CRITICAL_POWER,
                                   f"SOC={bat.soc_percent:.1f}% — CRITICAL")
            events.append("CRITICAL_POWER")
        elif bat.soc_percent < 30 and "LOW_POWER_WARNING" not in events:
            self._add_budget_event(PowerBudgetEvent.LOW_POWER_WARNING,
                                   f"SOC={bat.soc_percent:.1f}% — LOW POWER WARNING")
            events.append("LOW_POWER_WARNING")

        if bat.soc_percent >= 35:
            events.clear()

    def shed_loads(self, target_consumption_w: float) -> list[str]:
        with self._lock:
            shed_order = [
                LoadPriority.SCIENCE_ML,
                LoadPriority.COMMS_TX,
                LoadPriority.CAMERA,
            ]
            shed_names = []
            current = self.state.total_consumption_w

            for priority in sorted(self.state.subsystems.values(), key=lambda s: s.name):
                pass

            for name in ["ml", "camera", "comms_tx", "adcs"]:
                sub = self.state.subsystems.get(name)
                if sub and sub.is_active and not sub.is_shed and current > target_consumption_w:
                    sub.is_shed = True
                    current -= sub.current_w
                    shed_names.append(name)
                    self._add_budget_event(PowerBudgetEvent.LOAD_SHEDDING,
                                           f"Shed {name} ({sub.nominal_w:.1f}W)")

            self.state.shed_loads = shed_names
            self.state.total_consumption_w = round(
                sum(s.current_w for s in self.state.subsystems.values()), 3
            )
            return shed_names

    def restore_loads(self):
        with self._lock:
            for sub in self.state.subsystems.values():
                sub.is_shed = False
            self.state.shed_loads.clear()
            self.state.total_consumption_w = round(
                sum(s.current_w for s in self.state.subsystems.values()), 3
            )

    def get_status(self) -> dict:
        with self._lock:
            return {
                "subsystems": {k: v.model_dump() for k, v in self.state.subsystems.items()},
                "battery": self.state.battery.model_dump(),
                "solar_panel": self.state.solar_panel.model_dump(),
                "total_consumption_w": self.state.total_consumption_w,
                "net_power_w": self.state.net_power_w,
                "charge_state": self.state.charge_state,
                "budget_events": self._budget_events[-10:],
                "shed_loads": self.state.shed_loads,
            }

    def reset(self):
        with self._lock:
            self.state.battery.soc_percent = 85.0
            self.state.battery.charge_cycles = 0
            self.state.battery.total_ah_throughput = 0.0
            self.state.battery.depth_of_discharge_max = 0.0
            self._budget_events.clear()
            self.state.budget_events.clear()
            self.state.shed_loads.clear()
            for sub in self.state.subsystems.values():
                sub.is_shed = False
            self._start_time = time.time()
