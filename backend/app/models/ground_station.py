from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

class GroundStationConfig(BaseModel):
    name: str = "GS-Primary"
    latitude: float = 35.0
    longitude: float = -120.0
    altitude_m: float = 0.0
    min_elevation_deg: float = 10.0
    max_range_km: float = 2500.0

class GroundPass(BaseModel):
    pass_id: str = ""
    station_name: str = ""
    aos_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    los_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_s: float = 0.0
    max_elevation_deg: float = 0.0
    is_visible: bool = False
