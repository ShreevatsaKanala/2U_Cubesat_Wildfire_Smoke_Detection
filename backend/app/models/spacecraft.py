from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class MissionMode(str, Enum):
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    CAPTURING = "CAPTURING"
    PROCESSING = "PROCESSING"
    PRIORITIZING = "PRIORITIZING"
    DOWNLINK_PENDING = "DOWNLINK_PENDING"
    DOWNLINKING = "DOWNLINKING"
    SAFE_MODE = "SAFE_MODE"
    FAULT = "FAULT"
    DEBUG = "DEBUG"

class AttitudeMode(str, Enum):
    NADIR = "NADIR"
    SUN_POINTING = "SUN_POINTING"
    TARGET_POINTING = "TARGET_POINTING"
    SAFE = "SAFE"

class SubsystemStatus(str, Enum):
    NOMINAL = "NOMINAL"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    OFFLINE = "OFFLINE"

class AttitudeState(BaseModel):
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    roll_rate_dps: float = 0.0
    pitch_rate_dps: float = 0.0
    yaw_rate_dps: float = 0.0
    attitude_mode: AttitudeMode = AttitudeMode.NADIR
    pointing_target_lat: Optional[float] = None
    pointing_target_lon: Optional[float] = None
    pointing_error_deg: float = 0.0

class PowerState(BaseModel):
    battery_soc: float = Field(default=85.0, ge=0, le=100)
    battery_voltage: float = 7.178
    solar_generation_w: float = 0.0
    power_consumption_w: float = 1.5
    net_power_w: float = 0.0
    charge_state: str = "discharging"
    subsystem_power: dict = Field(default_factory=lambda: {
        "obc": 0.5, "camera": 0.3, "comms": 0.2, "adcs": 0.1, "thermal": 0.1, "ml": 0.3
    })

class ThermalNode(BaseModel):
    name: str
    temperature_c: float = 25.0
    target_temp_c: float = 25.0
    heat_generation_w: float = 0.0
    thermal_state: str = "nominal"
    warning_threshold_c: float = 50.0
    critical_threshold_c: float = 70.0

class ThermalState(BaseModel):
    nodes: dict[str, ThermalNode] = Field(default_factory=lambda: {
        "obc": ThermalNode(name="obc", temperature_c=30.0, heat_generation_w=0.3),
        "battery": ThermalNode(name="battery", temperature_c=22.0, heat_generation_w=0.1),
        "camera": ThermalNode(name="camera", temperature_c=25.0, heat_generation_w=0.2),
        "electronics": ThermalNode(name="electronics", temperature_c=28.0, heat_generation_w=0.4),
        "structure": ThermalNode(name="structure", temperature_c=20.0, heat_generation_w=0.0),
    })

class SubsystemHealth(BaseModel):
    eps: SubsystemStatus = SubsystemStatus.NOMINAL
    obc: SubsystemStatus = SubsystemStatus.NOMINAL
    camera: SubsystemStatus = SubsystemStatus.NOMINAL
    adcs: SubsystemStatus = SubsystemStatus.NOMINAL
    communications: SubsystemStatus = SubsystemStatus.NOMINAL
    navigation: SubsystemStatus = SubsystemStatus.NOMINAL
    thermal: SubsystemStatus = SubsystemStatus.NOMINAL
    ml: SubsystemStatus = SubsystemStatus.NOMINAL

    def overall_health(self) -> SubsystemStatus:
        statuses = [self.eps, self.obc, self.camera, self.adcs, self.communications, self.navigation, self.thermal, self.ml]
        if SubsystemStatus.CRITICAL in statuses:
            return SubsystemStatus.CRITICAL
        if SubsystemStatus.OFFLINE in statuses:
            return SubsystemStatus.OFFLINE
        if SubsystemStatus.WARNING in statuses:
            return SubsystemStatus.WARNING
        if SubsystemStatus.DEGRADED in statuses:
            return SubsystemStatus.DEGRADED
        return SubsystemStatus.NOMINAL

class FaultInjection(BaseModel):
    battery_low: bool = False
    camera_failure: bool = False
    gps_unavailable: bool = False
    comms_lost: bool = False
    ml_unavailable: bool = False
    thermal_warning: bool = False
    thermal_critical: bool = False
    obc_degraded: bool = False

class SpacecraftConfig(BaseModel):
    spacecraft_id: str = "CSAT-001"
    name: str = "2U CubeSat Wildfire Twin"
    mass_kg: float = 2.6
    dimensions: dict = Field(default_factory=lambda: {"length": 0.1, "width": 0.1, "height": 0.3})
    battery_capacity_wh: float = 40.0
    battery_voltage_nominal: float = 7.4
    solar_generation_w: float = 2.0
    power_consumption_w: float = 1.5
    camera_fov_deg_h: float = 62.2
    camera_fov_deg_v: float = 48.8
    camera_resolution: dict = Field(default_factory=lambda: {"width": 1920, "height": 1080})

class SpacecraftState(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    spacecraft_id: str = "CSAT-001"
    mission_mode: MissionMode = MissionMode.IDLE
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_km: float = 500.0
    velocity_km_s: float = 7.6
    heading_deg: float = 90.0
    attitude: AttitudeState = Field(default_factory=AttitudeState)
    power: PowerState = Field(default_factory=PowerState)
    thermal: ThermalState = Field(default_factory=ThermalState)
    health: SubsystemHealth = Field(default_factory=SubsystemHealth)
    faults: FaultInjection = Field(default_factory=FaultInjection)
    communication_status: str = "nominal"
    gps_status: str = "nominal"
    camera_status: str = "standby"
    ml_status: str = "ready"
    current_observation_id: Optional[str] = None
    smoke_probability: Optional[float] = None
    confidence: Optional[float] = None
    priority: Optional[str] = None
    packet_sequence: int = 0
    # Convenience accessors for backward compatibility
    @property
    def roll_deg(self): return self.attitude.roll_deg
    @property
    def pitch_deg(self): return self.attitude.pitch_deg
    @property
    def yaw_deg(self): return self.attitude.yaw_deg
    @property
    def battery_percentage(self): return self.power.battery_soc
    @property
    def battery_voltage(self): return self.power.battery_voltage
    @property
    def power_generation_w(self): return self.power.solar_generation_w
    @property
    def power_consumption_w(self): return self.power.power_consumption_w
    @property
    def temperatures(self):
        return {k: v.temperature_c for k, v in self.thermal.nodes.items()}
