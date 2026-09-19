from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SentinelScene(BaseModel):
    scene_id: str
    product_id: str
    datetime: datetime
    cloud_cover: float = Field(ge=0.0, le=100.0)
    bbox: list[float] = Field(min_length=4, max_length=4)
    geometry: dict
    data_coverage: float = Field(ge=0.0, le=100.0)
    platform: str = "sentinel-2"


class SentinelObservationResult(BaseModel):
    observation_id: str
    scene_id: str = ""
    acquisition_time: Optional[datetime] = None
    cloud_cover: Optional[float] = None
    aoi: list[float] = Field(default_factory=list)
    true_color_url: str = ""
    ndvi_url: str = ""
    false_color_url: str = ""
    metadata: dict = Field(default_factory=dict)
    error: Optional[str] = None
    available: bool = False


class SentinelStatus(BaseModel):
    enabled: bool = False
    authenticated: bool = False
    service: str = "Copernicus Sentinel-2 L2A"
    last_request: Optional[str] = None
    last_success: Optional[str] = None
    cache_hits: int = 0
    cache_misses: int = 0
    last_error: Optional[str] = None
    current_scene: Optional[str] = None
