from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class MissionEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str
    description: str
    severity: str = "info"
    subsystem: Optional[str] = None

class TelemetryPacket(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    packet_sequence: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    spacecraft_id: str = "CSAT-001"
    mission_mode: str = "IDLE"
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_km: float = 500.0
    velocity_km_s: float = 7.6
    heading_deg: float = 90.0
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    battery_percentage: float = 85.0
    battery_voltage: float = 7.178
    power_generation_w: float = 0.0
    power_consumption_w: float = 1.5
    temperatures: dict = Field(default_factory=dict)
    communication_status: str = "nominal"
    gps_status: str = "nominal"
    camera_status: str = "standby"
    ml_status: str = "ready"
    current_observation_id: Optional[str] = None
    smoke_probability: Optional[float] = None
    confidence: Optional[float] = None
    priority: Optional[str] = None
    ai_status: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_smoke_score: Optional[float] = None
    ai_confidence: Optional[str] = None
    ai_latency_ms: Optional[float] = None
    health_status: str = "NOMINAL"
    events: list = Field(default_factory=list)
