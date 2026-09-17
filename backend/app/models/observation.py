from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Observation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    observation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    spacecraft_id: str
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_km: float = 0.0

    image_path: str
    image_width: int
    image_height: int

    capture_mode: str
    camera_status: str

    model_name: Optional[str] = None
    model_version: Optional[str] = None
    smoke_probability: Optional[float] = None
    wildfire_probability: Optional[float] = None
    confidence: Optional[float] = None
    priority: str = "LOW"
    inference_latency_ms: Optional[float] = None

    processing_status: str = "pending"
    spacecraft_state_snapshot: Optional[dict] = None
