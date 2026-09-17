from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TelemetryPacket(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    packet_sequence: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    spacecraft_id: str
    mission_mode: str

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
