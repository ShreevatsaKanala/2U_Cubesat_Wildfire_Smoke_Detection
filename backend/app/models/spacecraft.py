from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MissionMode(str, Enum):
    SAFE_MODE = "SAFE_MODE"
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    PROCESSING = "PROCESSING"
    DOWNLINKING = "DOWNLINKING"
    DEBUG = "DEBUG"


class SpacecraftConfig(BaseModel):
    spacecraft_id: str
    name: str
    mass_kg: float = Field(default=2.6)
    dimensions: dict = Field(
        default_factory=lambda: {"length": 0.1, "width": 0.1, "height": 0.3}
    )
    battery_capacity_wh: float = Field(default=40.0)
    battery_voltage_nominal: float = Field(default=7.4)
    solar_generation_w: float = Field(default=2.0)
    power_consumption_w: float = Field(default=1.5)
    camera_fov_deg: float = Field(default=62.2)
    camera_resolution: dict = Field(
        default_factory=lambda: {"width": 1920, "height": 1080}
    )


class SpacecraftState(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    spacecraft_id: str
    mission_mode: MissionMode = MissionMode.SAFE_MODE

    latitude: float = 0.0
    longitude: float = 0.0
    altitude_km: float = 0.0
    velocity_km_s: float = 0.0
    heading_deg: float = 0.0
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0

    battery_percentage: float = Field(default=100.0, ge=0, le=100)
    battery_voltage: float = 0.0
    power_generation_w: float = 0.0
    power_consumption_w: float = 0.0

    temperatures: dict = Field(
        default_factory=lambda: {
            "battery": 25.0,
            "cpu": 30.0,
            "panel": 45.0,
            "body": 22.0,
        }
    )

    communication_status: str = "OK"
    gps_status: str = "OK"
    camera_status: str = "STANDBY"
    ml_status: str = "READY"

    current_observation_id: Optional[str] = None
    smoke_probability: Optional[float] = None
    confidence: Optional[float] = None
    priority: Optional[str] = None

    packet_sequence: int = 0
