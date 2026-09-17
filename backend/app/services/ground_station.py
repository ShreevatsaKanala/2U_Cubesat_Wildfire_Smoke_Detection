"""Ground Station Pass Service."""
import math
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.models.ground_station import GroundStationConfig, GroundPass
import uuid

MU_EARTH = 398600.4418

class GroundStationPassService:
    def __init__(self, station: GroundStationConfig):
        self.station = station
    
    def check_visibility(self, sat_lat: float, sat_lon: float, sat_alt_km: float) -> dict:
        gs_lat = math.radians(self.station.latitude)
        gs_lon = math.radians(self.station.longitude)
        sat_lat_r = math.radians(sat_lat)
        sat_lon_r = math.radians(sat_lon)
        
        dlat = sat_lat_r - gs_lat
        dlon = sat_lon_r - gs_lon
        a = math.sin(dlat/2)**2 + math.cos(gs_lat)*math.cos(sat_lat_r)*math.sin(dlon/2)**2
        central_angle = 2 * math.asin(math.sqrt(a))
        distance_km = central_angle * 6371
        
        slant_range = math.sqrt(distance_km**2 + sat_alt_km**2 - 2 * distance_km * sat_alt_km * math.cos(central_angle))
        elevation_rad = math.asin((sat_alt_km * math.sin(math.pi/2 - central_angle)) / slant_range) if slant_range > 0 else 0
        elevation_deg = math.degrees(elevation_rad)
        
        is_visible = (
            distance_km < self.station.max_range_km
            and elevation_deg >= self.station.min_elevation_deg
        )
        
        orbit_period = 2 * math.pi * math.sqrt((6371 + sat_alt_km)**3 / MU_EARTH)
        
        return {
            "distance_km": round(distance_km, 1),
            "elevation_deg": round(elevation_deg, 1),
            "is_visible": is_visible,
            "slant_range_km": round(slant_range, 1),
            "orbit_period_s": round(orbit_period, 1),
        }
    
    def estimate_next_pass(self, sat_lat: float, sat_lon: float, sat_alt_km: float, velocity_km_s: float) -> Optional[dict]:
        orbit_period = 2 * math.pi * math.sqrt((6371 + sat_alt_km)**3 / MU_EARTH)
        
        gs_lat_r = math.radians(self.station.latitude)
        gs_lon_r = math.radians(self.station.longitude)
        sat_lat_r = math.radians(sat_lat)
        sat_lon_r = math.radians(sat_lon)
        
        angular_velocity = (velocity_km_s / (6371 + sat_alt_km)) * (180 / math.pi)
        
        gs_lat_deg = self.station.latitude
        lat_diff = abs(sat_lat - gs_lat_deg)
        
        if lat_diff < 30:
            estimated_wait = orbit_period * (lat_diff / 180.0)
        else:
            estimated_wait = orbit_period * 0.5
        
        return {
            "estimated_wait_s": round(estimated_wait, 0),
            "pass_duration_s": round(orbit_period * 0.08, 1),
            "max_elevation_est_deg": round(max(0, 90 - lat_diff), 1),
        }
