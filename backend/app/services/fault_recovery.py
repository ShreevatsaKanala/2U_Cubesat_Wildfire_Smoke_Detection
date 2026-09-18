"""Autonomous Fault Recovery Service for CubeSat Digital Twin.

Designed to be called BY the simulation engine. Each recovery handler monitors
a specific subsystem and performs automated recovery actions with retries and cooldown.
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


class RecoveryAction(str, Enum):
    CAMERA_REBOOT = "camera_reboot"
    COMM_FAILOVER = "comm_failover"
    GPS_PROPAGATE = "gps_propagate"
    BATTERY_SHED = "battery_shed"
    THERMAL_EMERGENCY = "thermal_emergency"
    OBC_WATCHDOG = "obc_watchdog"


class RecoveryState(str, Enum):
    IDLE = "idle"
    ATTEMPTING = "attempting"
    COOLDOWN = "cooldown"
    FAILED = "failed"
    RECOVERED = "recovered"


class RecoveryRecord(BaseModel):
    action: RecoveryAction
    state: RecoveryState = RecoveryState.IDLE
    attempts: int = 0
    max_retries: int = 3
    cooldown_seconds: float = 60.0
    last_attempt_time: Optional[float] = None
    last_recovery_time: Optional[float] = None
    last_error: Optional[str] = None


class RecoveryEvent(BaseModel):
    timestamp: str
    action: RecoveryAction
    description: str
    severity: str = "info"
    success: bool = False


class RecoveryConfig(BaseModel):
    camera_reboot_delay_s: float = 30.0
    camera_recover_timeout_s: float = 120.0
    camera_max_retries: int = 3
    camera_cooldown_s: float = 60.0

    comm_retry_delay_s: float = 10.0
    comm_max_retries: int = 5
    comm_cooldown_s: float = 30.0

    gps_propagate_timeout_s: float = 60.0
    gps_max_retries: int = 3
    gps_cooldown_s: float = 45.0

    battery_soc_shed_threshold: float = 10.0
    battery_soc_warning_threshold: float = 30.0
    battery_soc_critical_threshold: float = 15.0

    thermal_emergency_threshold_c: float = 80.0
    thermal_max_retries: int = 2
    thermal_cooldown_s: float = 120.0

    obc_heartbeat_timeout_s: float = 30.0
    obc_max_retries: int = 3
    obc_cooldown_s: float = 60.0


class FaultRecoveryService:
    """Thread-safe fault recovery service that monitors subsystems and performs recovery."""

    def __init__(self, config: RecoveryConfig | None = None):
        self.config = config or RecoveryConfig()
        self._lock = threading.Lock()

        self._records: dict[RecoveryAction, RecoveryRecord] = {
            action: RecoveryRecord(action=action, max_retries=self._get_max_retries(action),
                                   cooldown_seconds=self._get_cooldown(action))
            for action in RecoveryAction
        }
        self._event_history: list[RecoveryEvent] = []
        self._max_history = 200

        self._last_heartbeat_time: float = time.time()
        self._comm_backup_active: bool = False
        self._gps_last_known_position: Optional[dict] = None
        self._heaters_off: bool = False

    def _get_max_retries(self, action: RecoveryAction) -> int:
        mapping = {
            RecoveryAction.CAMERA_REBOOT: self.config.camera_max_retries,
            RecoveryAction.COMM_FAILOVER: self.config.comm_max_retries,
            RecoveryAction.GPS_PROPAGATE: self.config.gps_max_retries,
            RecoveryAction.THERMAL_EMERGENCY: self.config.thermal_max_retries,
            RecoveryAction.OBC_WATCHDOG: self.config.obc_max_retries,
            RecoveryAction.BATTERY_SHED: 1,
        }
        return mapping.get(action, 3)

    def _get_cooldown(self, action: RecoveryAction) -> float:
        mapping = {
            RecoveryAction.CAMERA_REBOOT: self.config.camera_cooldown_s,
            RecoveryAction.COMM_FAILOVER: self.config.comm_cooldown_s,
            RecoveryAction.GPS_PROPAGATE: self.config.gps_cooldown_s,
            RecoveryAction.THERMAL_EMERGENCY: self.config.thermal_cooldown_s,
            RecoveryAction.OBC_WATCHDOG: self.config.obc_cooldown_s,
            RecoveryAction.BATTERY_SHED: 0,
        }
        return mapping.get(action, 60.0)

    def _log_event(self, action: RecoveryAction, description: str,
                   severity: str = "info", success: bool = False) -> RecoveryEvent:
        evt = RecoveryEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            description=description,
            severity=severity,
            success=success,
        )
        self._event_history.append(evt)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        logger.info(f"[Recovery] {action.value}: {description}")
        return evt

    def _can_attempt(self, action: RecoveryAction) -> bool:
        rec = self._records[action]
        now = time.time()

        if rec.state == RecoveryState.RECOVERED:
            return False
        if rec.state == RecoveryState.COOLDOWN:
            if rec.last_attempt_time and (now - rec.last_attempt_time) >= rec.cooldown_seconds:
                rec.state = RecoveryState.IDLE
            else:
                return False
        if rec.attempts >= rec.max_retries:
            rec.state = RecoveryState.FAILED
            return False
        return True

    def _start_attempt(self, action: RecoveryAction) -> RecoveryEvent:
        rec = self._records[action]
        rec.state = RecoveryState.ATTEMPTING
        rec.attempts += 1
        rec.last_attempt_time = time.time()
        return self._log_event(action, f"Recovery attempt #{rec.attempts}", severity="warning")

    def _finish_attempt(self, action: RecoveryAction, success: bool,
                        detail: str = "") -> RecoveryEvent:
        rec = self._records[action]
        if success:
            rec.state = RecoveryState.RECOVERED
            rec.last_recovery_time = time.time()
            return self._log_event(action, f"Recovered: {detail}", severity="info", success=True)
        else:
            rec.state = RecoveryState.COOLDOWN
            rec.last_error = detail
            return self._log_event(action, f"Failed: {detail}", severity="warning", success=False)

    # ─── Camera Recovery ──────────────────────────────────────────────
    def check_camera(self, camera_status: str, sim_time_s: float) -> Optional[RecoveryEvent]:
        with self._lock:
            if camera_status != "error":
                return None
            action = RecoveryAction.CAMERA_REBOOT
            if not self._can_attempt(action):
                return None
            evt = self._start_attempt(action)
            elapsed = sim_time_s
            if elapsed >= self.config.camera_recover_timeout_s:
                return self._finish_attempt(action, True,
                                            "Camera auto-recovered after timeout")
            return self._finish_attempt(action, False,
                                        f"Camera reboot pending, {elapsed:.0f}s elapsed")

    # ─── Communication Recovery ───────────────────────────────────────
    def check_comm(self, communication_status: str, sim_time_s: float) -> Optional[RecoveryEvent]:
        with self._lock:
            if communication_status not in ("degraded", "lost"):
                self._comm_backup_active = False
                return None
            action = RecoveryAction.COMM_FAILOVER
            if not self._can_attempt(action):
                return None
            evt = self._start_attempt(action)
            self._comm_backup_active = True
            return self._finish_attempt(action, True,
                                        "Switched to backup antenna")

    @property
    def comm_backup_active(self) -> bool:
        return self._comm_backup_active

    # ─── GPS Recovery ─────────────────────────────────────────────────
    def check_gps(self, gps_status: str, position: dict,
                  sim_time_s: float) -> Optional[RecoveryEvent]:
        with self._lock:
            if gps_status != "lost":
                return None
            self._gps_last_known_position = position.copy()
            action = RecoveryAction.GPS_PROPAGATE
            if not self._can_attempt(action):
                return None
            evt = self._start_attempt(action)
            if sim_time_s <= self.config.gps_propagate_timeout_s:
                return self._finish_attempt(action, True,
                                            f"Using propagated position, "
                                            f"{sim_time_s:.0f}s/{self.config.gps_propagate_timeout_s:.0f}s")
            return self._finish_attempt(action, False,
                                        "GPS acquisition timeout exceeded")

    def get_gps_propagated_position(self) -> Optional[dict]:
        return self._gps_last_known_position

    # ─── Battery Recovery ─────────────────────────────────────────────
    def check_battery(self, battery_soc: float) -> Optional[RecoveryEvent]:
        with self._lock:
            if battery_soc >= self.config.battery_soc_shed_threshold:
                return None
            action = RecoveryAction.BATTERY_SHED
            if not self._can_attempt(action):
                return None
            evt = self._start_attempt(action)
            return self._finish_attempt(action, True,
                                        f"SOC={battery_soc:.1f}%, shed non-critical loads, entered safe mode")

    # ─── Thermal Recovery ─────────────────────────────────────────────
    def check_thermal(self, max_temperature_c: float) -> Optional[RecoveryEvent]:
        with self._lock:
            if max_temperature_c < self.config.thermal_emergency_threshold_c:
                self._heaters_off = False
                return None
            action = RecoveryAction.THERMAL_EMERGENCY
            if not self._can_attempt(action):
                return None
            evt = self._start_attempt(action)
            self._heaters_off = True
            return self._finish_attempt(action, True,
                                        f"Max temp={max_temperature_c:.1f}°C, "
                                        f"emergency cooling active, safe mode entered")

    @property
    def heaters_off(self) -> bool:
        return self._heaters_off

    # ─── OBC Recovery ─────────────────────────────────────────────────
    def update_heartbeat(self):
        with self._lock:
            self._last_heartbeat_time = time.time()

    def check_obc(self) -> Optional[RecoveryEvent]:
        with self._lock:
            elapsed = time.time() - self._last_heartbeat_time
            if elapsed < self.config.obc_heartbeat_timeout_s:
                return None
            action = RecoveryAction.OBC_WATCHDOG
            if not self._can_attempt(action):
                return None
            evt = self._start_attempt(action)
            self._last_heartbeat_time = time.time()
            return self._finish_attempt(action, True,
                                        f"Heartbeat missed for {elapsed:.0f}s, watchdog reset triggered")

    # ─── Full Recovery Check ──────────────────────────────────────────
    def run_checks(self, state, sim_time_s: float = 0.0) -> list[RecoveryEvent]:
        events: list[RecoveryEvent] = []

        cam_evt = self.check_camera(state.camera_status, sim_time_s)
        if cam_evt:
            events.append(cam_evt)

        comm_evt = self.check_comm(state.communication_status, sim_time_s)
        if comm_evt:
            events.append(comm_evt)

        gps_evt = self.check_gps(
            state.gps_status,
            {"lat": state.latitude, "lon": state.longitude, "alt": state.altitude_km},
            sim_time_s,
        )
        if gps_evt:
            events.append(gps_evt)

        bat_evt = self.check_battery(state.power.battery_soc)
        if bat_evt:
            events.append(bat_evt)

        max_temp = max((n.temperature_c for n in state.thermal.nodes.values()), default=0)
        therm_evt = self.check_thermal(max_temp)
        if therm_evt:
            events.append(therm_evt)

        obc_evt = self.check_obc()
        if obc_evt:
            events.append(obc_evt)

        return events

    # ─── Manual Trigger ───────────────────────────────────────────────
    def manual_trigger(self, action: RecoveryAction) -> RecoveryEvent:
        with self._lock:
            rec = self._records[action]
            rec.attempts = 0
            rec.state = RecoveryState.IDLE
            return self._start_attempt(action)

    # ─── Status & History ─────────────────────────────────────────────
    def get_status(self) -> dict:
        with self._lock:
            return {
                "records": {k.value: v.model_dump() for k, v in self._records.items()},
                "recent_events": [e.model_dump() for e in self._event_history[-20:]],
                "comm_backup_active": self._comm_backup_active,
                "heaters_off": self._heaters_off,
                "gps_last_known": self._gps_last_known_position,
            }

    def reset(self):
        with self._lock:
            for rec in self._records.values():
                rec.state = RecoveryState.IDLE
                rec.attempts = 0
                rec.last_attempt_time = None
                rec.last_recovery_time = None
                rec.last_error = None
            self._event_history.clear()
            self._comm_backup_active = False
            self._heaters_off = False
            self._gps_last_known_position = None
            self._last_heartbeat_time = time.time()
