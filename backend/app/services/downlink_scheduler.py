"""Downlink Scheduler with contact window calculation and transfer optimization."""
from datetime import datetime, timezone, timedelta
import math
import threading
from typing import Optional, List, Dict, Tuple

from app.models.downlink import DownlinkItem, DownlinkQueue, TransferState
from app.models.ground_station import GroundStationConfig, GroundPass
from app.services.downlink import DownlinkService


class DownlinkScheduler:
    def __init__(self, downlink_service: DownlinkService, ground_station: GroundStationConfig = None):
        self.downlink_service = downlink_service
        self.ground_station = ground_station or GroundStationConfig()
        self._lock = threading.Lock()
        self._contact_windows: List[Dict] = []
        self._next_window_index = 0

    def compute_elevation(self, sat_lat: float, sat_lon: float, sat_alt_km: float,
                          gs_lat: float, gs_lon: float, gs_alt_m: float = 0.0) -> float:
        """Compute elevation angle from ground station to satellite."""
        gs_lat_r = math.radians(gs_lat)
        gs_lon_r = math.radians(gs_lon)
        sat_lat_r = math.radians(sat_lat)
        sat_lon_r = math.radians(sat_lon)

        dlat = sat_lat_r - gs_lat_r
        dlon = sat_lon_r - gs_lon_r
        a = math.sin(dlat / 2) ** 2 + math.cos(gs_lat_r) * math.cos(sat_lat_r) * math.sin(dlon / 2) ** 2
        central_angle = 2 * math.asin(math.sqrt(a))

        R_earth = 6371.0
        gs_alt_km = gs_alt_m / 1000.0
        slant_range = math.sqrt(
            R_earth ** 2 + (R_earth + sat_alt_km) ** 2
            - 2 * R_earth * (R_earth + sat_alt_km) * math.cos(central_angle)
        )

        elevation_rad = math.acos(
            ((R_earth + sat_alt_km) ** 2 - R_earth ** 2 - slant_range ** 2)
            / (2 * R_earth * slant_range)
        )
        return math.degrees(elevation_rad)

    def compute_contact_duration(self, orbit_alt_km: float, gs_lat: float, gs_lon: float,
                                  min_elevation_deg: float = 10.0) -> float:
        """Estimate contact window duration in seconds."""
        orbit_period = 2 * math.pi * math.sqrt((6371 + orbit_alt_km) ** 3 / 398600.4418)
        max_range_rad = math.acos(6371 / (6371 + orbit_alt_km) * math.cos(math.radians(min_elevation_deg)))
        contact_fraction = max_range_rad / math.pi
        return orbit_period * contact_fraction

    def estimate_transfer_time(self, file_size_bytes: int, data_rate_bytes_s: float) -> float:
        """Estimate time to transfer a file."""
        if data_rate_bytes_s <= 0:
            return float('inf')
        return file_size_bytes / data_rate_bytes_s

    def compute_transfer_schedule(self, sat_lat: float, sat_lon: float, sat_alt_km: float,
                                  battery_soc: float = 100.0, sim_time: datetime = None) -> Dict:
        """Compute transfer schedule for current conditions."""
        sim_time = sim_time or datetime.now(timezone.utc)
        elevation = self.compute_elevation(
            sat_lat, sat_lon, sat_alt_km,
            self.ground_station.latitude, self.ground_station.longitude,
            self.ground_station.altitude_m
        )
        station_visible = elevation >= self.ground_station.min_elevation_deg
        contact_duration = self.compute_contact_duration(
            sat_alt_km, self.ground_station.latitude, self.ground_station.longitude,
            self.ground_station.min_elevation_deg
        )
        rate = self.downlink_service.effective_rate_bytes_s
        active_items = self.downlink_service.queue.get_transferring_items()
        queued_items = self.downlink_service.queue.get_pending_items()
        total_active_bytes = sum(i.bytes_remaining for i in active_items)
        total_queued_bytes = sum(i.image_size_bytes for i in queued_items)
        can_transfer = station_visible and battery_soc >= self.downlink_service.queue.power_threshold_soc

        return {
            "station_id": self.ground_station.name,
            "satellite_position": {"lat": sat_lat, "lon": sat_lon, "alt_km": sat_alt_km},
            "elevation_deg": round(elevation, 2),
            "station_visible": station_visible,
            "contact_duration_s": round(contact_duration, 1),
            "data_rate_bytes_s": rate,
            "can_transfer": can_transfer,
            "active_transfers": len(active_items),
            "queued_items": len(queued_items),
            "total_bytes_remaining": total_active_bytes + total_queued_bytes,
            "estimated_contact_transfer_mb": round(rate * contact_duration / (1024 * 1024), 2) if can_transfer else 0,
            "time_to_transfer_queue_s": round(
                (total_active_bytes + total_queued_bytes) / rate, 1
            ) if rate > 0 else float('inf'),
        }

    def plan_optimal_transfers(self, queued_items: List[DownlinkItem], available_time_s: float,
                                data_rate_bytes_s: float) -> List[DownlinkItem]:
        """Select which items to transfer during a contact window to maximize data return."""
        if not queued_items or available_time_s <= 0:
            return []

        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_items = sorted(queued_items, key=lambda x: priority_order.get(x.priority, 99))

        selected = []
        time_remaining = available_time_s

        for item in sorted_items:
            transfer_time = self.estimate_transfer_time(item.image_size_bytes, data_rate_bytes_s)
            if transfer_time <= time_remaining:
                selected.append(item)
                time_remaining -= transfer_time
            else:
                break

        return selected

    def update(self, sat_lat: float, sat_lon: float, sat_alt_km: float,
               battery_soc: float, sim_time: datetime) -> Dict:
        """Main scheduler update. Returns status dict with actions taken."""
        schedule = self.compute_transfer_schedule(sat_lat, sat_lon, sat_alt_km, battery_soc, sim_time)
        actions = []

        with self._lock:
            transferring = self.downlink_service.queue.get_transferring_items()
            for item in transferring:
                new_status = self.downlink_service.update_transfer(
                    item, 1.0, sim_time,
                    station_visible=schedule["station_visible"],
                    battery_soc=battery_soc,
                )
                if new_status == TransferState.TRANSMITTED:
                    self.downlink_service.queue.total_transmitted += 1
                    self.downlink_service.queue.total_bytes += item.image_size_bytes
                    actions.append(f"Completed: {item.observation_id}")
                elif new_status == TransferState.PAUSED:
                    actions.append(f"Paused: {item.observation_id} ({item.pause_reason})")

            if schedule["can_transfer"] and len(transferring) < 2:
                queued = self.downlink_service.queue.get_pending_items()
                if queued:
                    bandwidth_per_transfer = schedule["data_rate_bytes_s"] / max(1, len(transferring) + 1)
                    contact_time = schedule["contact_duration_s"]
                    selected = self.plan_optimal_transfers(queued, contact_time, bandwidth_per_transfer)
                    for item in selected[:2]:
                        if self.downlink_service.start_transfer(item, self.ground_station.name, sim_time):
                            actions.append(f"Started: {item.observation_id}")

        return {
            "schedule": schedule,
            "actions": actions,
            "timestamp": sim_time.isoformat(),
        }
