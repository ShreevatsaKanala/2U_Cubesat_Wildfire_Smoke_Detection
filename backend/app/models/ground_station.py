from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class StationStatus(str, Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    MAINTENANCE = "maintenance"


class LinkBudget(BaseModel):
    data_rate_kbps: float = 0.0
    snr_db: float = 0.0
    link_margin_db: float = 0.0
    frequency_ghz: float = 2.2  # S-band default


class GroundStationConfig(BaseModel):
    name: str = "GS-Primary"
    latitude: float = 35.0
    longitude: float = -120.0
    altitude_m: float = 0.0
    min_elevation_deg: float = 10.0
    max_range_km: float = 2500.0


class GroundStationDetail(BaseModel):
    station_id: str
    name: str
    latitude: float
    longitude: float
    altitude_m: float
    min_elevation_deg: float
    status: StationStatus = StationStatus.ACTIVE
    link_budget: LinkBudget = Field(default_factory=LinkBudget)
    description: str = ""


class StationVisibility(BaseModel):
    station_id: str
    station_name: str
    distance_km: float = 0.0
    elevation_deg: float = 0.0
    azimuth_deg: float = 0.0
    is_visible: bool = False
    slant_range_km: float = 0.0
    contact_duration_s: float = 0.0
    max_data_transfer_mb: float = 0.0


class GroundStationNetwork(BaseModel):
    network_id: str = "GSNET-001"
    stations: List[GroundStationDetail] = []
    active_station_id: Optional[str] = None
    last_handoff_time: Optional[datetime] = None


class GroundPass(BaseModel):
    pass_id: str = ""
    station_name: str = ""
    aos_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    los_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_s: float = 0.0
    max_elevation_deg: float = 0.0
    is_visible: bool = False


class HandoffEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    from_station: str = ""
    to_station: str = ""
    reason: str = ""
