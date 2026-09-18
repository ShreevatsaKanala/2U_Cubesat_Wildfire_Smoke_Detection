"""Multi-Station Ground Network Service for Phase 5G."""
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from app.models.ground_station import (
    GroundStationDetail, GroundStationNetwork, StationVisibility,
    StationStatus, LinkBudget, HandoffEvent, GroundStationConfig
)

EARTH_RADIUS_KM = 6371.0
MU_EARTH = 398600.4418


def _preconfigured_stations() -> List[GroundStationDetail]:
    return [
        GroundStationDetail(
            station_id="GS-BOULDER",
            name="Boulder, CO",
            latitude=40.0,
            longitude=-105.3,
            altitude_m=1655.0,
            min_elevation_deg=10.0,
            status=StationStatus.ACTIVE,
            link_budget=LinkBudget(data_rate_kbps=256.0, snr_db=18.5, link_margin_db=6.2, frequency_ghz=2.2),
            description="UC Boulder - Primary US ground station",
        ),
        GroundStationDetail(
            station_id="GS-FAIRBANKS",
            name="Fairbanks, AK",
            latitude=64.9,
            longitude=-147.7,
            altitude_m=136.0,
            min_elevation_deg=10.0,
            status=StationStatus.ACTIVE,
            link_budget=LinkBudget(data_rate_kbps=512.0, snr_db=22.1, link_margin_db=8.5, frequency_ghz=8.2),
            description="Poker Flat - High-latitude station for polar orbits",
        ),
        GroundStationDetail(
            station_id="GS-SVALBARD",
            name="Svalbard, Norway",
            latitude=78.2,
            longitude=15.6,
            altitude_m=474.0,
            min_elevation_deg=10.0,
            status=StationStatus.ACTIVE,
            link_budget=LinkBudget(data_rate_kbps=1024.0, snr_db=25.3, link_margin_db=10.1, frequency_ghz=8.2),
            description="Svalbard Satellite Station - Highest latitude station",
        ),
        GroundStationDetail(
            station_id="GS-SINGAPORE",
            name="Singapore",
            latitude=1.3,
            longitude=103.8,
            altitude_m=15.0,
            min_elevation_deg=10.0,
            status=StationStatus.STANDBY,
            link_budget=LinkBudget(data_rate_kbps=128.0, snr_db=14.2, link_margin_db=4.0, frequency_ghz=2.2),
            description="Kranji - Equatorial station for tropical coverage",
        ),
        GroundStationDetail(
            station_id="GS-PUNTA-ARENAS",
            name="Punta Arenas, Chile",
            latitude=-53.2,
            longitude=-71.0,
            altitude_m=34.0,
            min_elevation_deg=10.0,
            status=StationStatus.ACTIVE,
            link_budget=LinkBudget(data_rate_kbps=256.0, snr_db=17.8, link_margin_db=5.8, frequency_ghz=2.2),
            description="Southernmost station - Critical for south polar passes",
        ),
    ]


class GroundNetworkService:
    def __init__(self):
        self.network = GroundStationNetwork(
            network_id="GSNET-CUBESAT-001",
            stations=_preconfigured_stations(),
        )
        self._active_station_id: Optional[str] = "GS-BOULDER"
        self._handoff_history: List[HandoffEvent] = []
        self._station_configs: Dict[str, GroundStationConfig] = {}
        for s in self.network.stations:
            self._station_configs[s.station_id] = GroundStationConfig(
                name=s.name,
                latitude=s.latitude,
                longitude=s.longitude,
                altitude_m=s.altitude_m,
                min_elevation_deg=s.min_elevation_deg,
                max_range_km=2500.0,
            )

    def get_all_stations(self) -> List[GroundStationDetail]:
        return self.network.stations

    def get_station(self, station_id: str) -> Optional[GroundStationDetail]:
        for s in self.network.stations:
            if s.station_id == station_id:
                return s
        return None

    def toggle_station(self, station_id: str) -> Optional[GroundStationDetail]:
        station = self.get_station(station_id)
        if not station:
            return None
        if station.status == StationStatus.ACTIVE:
            station.status = StationStatus.STANDBY
        elif station.status == StationStatus.STANDBY:
            station.status = StationStatus.ACTIVE
        else:
            station.status = StationStatus.ACTIVE
        return station

    def compute_visibility(
        self, sat_lat: float, sat_lon: float, sat_alt_km: float,
        station_id: Optional[str] = None
    ) -> List[StationVisibility]:
        results = []
        stations = (
            [self.get_station(station_id)] if station_id
            else [s for s in self.network.stations if s.status != StationStatus.MAINTENANCE]
        )
        for station in stations:
            if station is None:
                continue
            vis = self._compute_single_visibility(sat_lat, sat_lon, sat_alt_km, station)
            results.append(vis)
        results.sort(key=lambda v: v.elevation_deg, reverse=True)
        return results

    def _compute_single_visibility(
        self, sat_lat: float, sat_lon: float, sat_alt_km: float,
        station: GroundStationDetail
    ) -> StationVisibility:
        gs_lat = math.radians(station.latitude)
        gs_lon = math.radians(station.longitude)
        sat_lat_r = math.radians(sat_lat)
        sat_lon_r = math.radians(sat_lon)

        dlat = sat_lat_r - gs_lat
        dlon = sat_lon_r - gs_lon
        a = math.sin(dlat / 2) ** 2 + math.cos(gs_lat) * math.cos(sat_lat_r) * math.sin(dlon / 2) ** 2
        central_angle = 2 * math.asin(math.sqrt(a))
        surface_distance = central_angle * EARTH_RADIUS_KM

        r_gs = EARTH_RADIUS_KM + (station.altitude_m / 1000.0)
        r_sat = EARTH_RADIUS_KM + sat_alt_km
        slant_range = math.sqrt(
            r_gs ** 2 + r_sat ** 2 - 2 * r_gs * r_sat * math.cos(central_angle)
        )

        if slant_range > 0:
            sin_elev = (r_gs ** 2 + slant_range ** 2 - r_sat ** 2) / (2 * r_gs * slant_range)
            sin_elev = max(-1.0, min(1.0, sin_elev))
            elevation_rad = math.asin(sin_elev)
        else:
            elevation_rad = 0.0
        elevation_deg = math.degrees(elevation_rad)

        dlon_deg = math.degrees(sat_lon_r - gs_lon)
        azimuth_rad = math.atan2(
            math.sin(dlon_deg * math.pi / 180),
            math.cos(gs_lat) * math.tan(sat_lat_r) - math.sin(gs_lat) * math.cos(dlon_deg * math.pi / 180)
        )
        azimuth_deg = (math.degrees(azimuth_rad) + 360) % 360

        is_visible = (
            surface_distance < 2500.0
            and elevation_deg >= station.min_elevation_deg
        )

        orbit_period = 2 * math.pi * math.sqrt((EARTH_RADIUS_KM + sat_alt_km) ** 3 / MU_EARTH)
        contact_duration = orbit_period * 0.08 if is_visible else 0.0

        data_rate_kbps = station.link_budget.data_rate_kbps if is_visible else 0.0
        max_data_mb = (data_rate_kbps * 1000 / 8) * contact_duration / (1024 * 1024)

        return StationVisibility(
            station_id=station.station_id,
            station_name=station.name,
            distance_km=round(surface_distance, 1),
            elevation_deg=round(elevation_deg, 1),
            azimuth_deg=round(azimuth_deg, 1),
            is_visible=is_visible,
            slant_range_km=round(slant_range, 1),
            contact_duration_s=round(contact_duration, 1),
            max_data_transfer_mb=round(max_data_mb, 2),
        )

    def select_best_station(
        self, sat_lat: float, sat_lon: float, sat_alt_km: float
    ) -> Optional[StationVisibility]:
        visibilities = self.compute_visibility(sat_lat, sat_lon, sat_alt_km)
        active_visible = [
            v for v in visibilities
            if v.is_visible and self.get_station(v.station_id) and self.get_station(v.station_id).status == StationStatus.ACTIVE
        ]
        return active_visible[0] if active_visible else None

    def handle_handoff(
        self, sat_lat: float, sat_lon: float, sat_alt_km: float
    ) -> Optional[HandoffEvent]:
        best = self.select_best_station(sat_lat, sat_lon, sat_alt_km)
        if not best:
            return None
        if best.station_id == self._active_station_id:
            return None
        previous = self._active_station_id or "NONE"
        self._active_station_id = best.station_id
        event = HandoffEvent(
            timestamp=datetime.now(timezone.utc),
            from_station=previous,
            to_station=best.station_id,
            reason=f"Best elevation: {best.elevation_deg}° at {best.station_name}",
        )
        self._handoff_history.append(event)
        return event

    def get_active_station_id(self) -> Optional[str]:
        return self._active_station_id

    def get_handoff_history(self, limit: int = 20) -> List[HandoffEvent]:
        return self._handoff_history[-limit:]

    def estimate_pass_quality(self, sat_lat: float, sat_lon: float, sat_alt_km: float) -> dict:
        visibilities = self.compute_visibility(sat_lat, sat_lon, sat_alt_km)
        visible_stations = [v for v in visibilities if v.is_visible]
        if not visible_stations:
            return {
                "in_view": False,
                "visible_count": 0,
                "best_station": None,
                "total_data_budget_mb": 0.0,
                "all_stations": [v.model_dump() for v in visibilities],
            }
        return {
            "in_view": True,
            "visible_count": len(visible_stations),
            "best_station": visible_stations[0].station_id,
            "total_data_budget_mb": round(sum(v.max_data_transfer_mb for v in visible_stations), 2),
            "all_stations": [v.model_dump() for v in visibilities],
        }


ground_network_service = GroundNetworkService()
