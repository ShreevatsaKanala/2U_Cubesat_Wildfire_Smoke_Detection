from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class Observation(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    observation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    spacecraft_id: str = "CSAT-001"
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_km: float = 500.0
    image_path: str = ""
    image_width: int = 1920
    image_height: int = 1080
    capture_mode: str = "synthetic"
    camera_status: str = "nominal"
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    smoke_probability: Optional[float] = None
    wildfire_probability: Optional[float] = None
    confidence: Optional[float] = None
    priority: str = "LOW"
    inference_latency_ms: Optional[float] = None
    processing_status: str = "completed"
    verification_status: str = "unverified"
    downlink_status: str = "pending"
    spacecraft_state_snapshot: Optional[dict] = None
