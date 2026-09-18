"""Downlink Simulation Service with realistic transfer modeling."""
from datetime import datetime, timezone
import math
import random
import threading
from typing import Optional

from app.models.downlink import DownlinkItem, DownlinkQueue, TransferState
from app.models.observation import Observation


class DownlinkService:
    def __init__(self, rate_bytes_s: float = 1024.0, config: dict = None):
        config = config or {}
        self.queue = DownlinkQueue(
            downlink_rate_bytes_s=rate_bytes_s,
            min_elevation_deg=config.get("min_elevation_deg", 10.0),
            comm_loss_probability=config.get("comm_loss_probability", 0.001),
            power_threshold_soc=config.get("power_threshold_soc", 15.0),
            min_image_size_bytes=config.get("min_image_size_bytes", 500 * 1024),
            max_image_size_bytes=config.get("max_image_size_bytes", 5 * 1024 * 1024),
        )
        self._lock = threading.Lock()
        self._rate_config = {
            "s_band": 10 * 1024,
            "x_band": 100 * 1024,
            "ka_band": 500 * 1024,
        }
        self._current_band = config.get("band", "s_band")

    @property
    def effective_rate_bytes_s(self) -> float:
        return self._rate_config.get(self._current_band, self.queue.downlink_rate_bytes_s)

    def set_band(self, band: str):
        if band in self._rate_config:
            self._current_band = band

    def queue_observation(self, obs: Observation) -> DownlinkItem:
        rng = random.Random(hash(obs.observation_id))
        size = rng.randint(self.queue.min_image_size_bytes, self.queue.max_image_size_bytes)
        item = DownlinkItem(
            observation_id=obs.observation_id,
            priority=obs.priority,
            image_size_bytes=size,
        )
        with self._lock:
            self.queue.enqueue(item)
        return item

    def start_transfer(self, item: DownlinkItem, station_id: str, sim_time: datetime) -> bool:
        with self._lock:
            if item.status != TransferState.QUEUED:
                return False
            item.status = TransferState.TRANSFERRING
            item.assigned_station = station_id
            item.started_at = sim_time
            item._current_rate_bytes_s = self.effective_rate_bytes_s
            return True

    def update_transfer(self, item: DownlinkItem, dt: float, sim_time: datetime,
                        station_visible: bool = True, battery_soc: float = 100.0,
                        comm_loss: bool = False) -> str:
        with self._lock:
            if item.status == TransferState.TRANSFERRING:
                if not station_visible:
                    item.status = TransferState.PAUSED
                    item.paused_at = sim_time
                    item.pause_reason = "station_out_of_view"
                    return TransferState.PAUSED

                if battery_soc < self.queue.power_threshold_soc:
                    item.status = TransferState.PAUSED
                    item.paused_at = sim_time
                    item.pause_reason = "low_power"
                    return TransferState.PAUSED

                if comm_loss or random.random() < self.queue.comm_loss_probability:
                    item.status = TransferState.PAUSED
                    item.paused_at = sim_time
                    item.pause_reason = "comm_link_loss"
                    return TransferState.PAUSED

                rate = self.effective_rate_bytes_s
                transmitted = min(item.bytes_remaining, rate * dt)
                item.bytes_transmitted = min(item.bytes_transmitted + int(transmitted), item.image_size_bytes)

                if item.bytes_transmitted >= item.image_size_bytes:
                    item.status = TransferState.TRANSMITTED
                    item.transmitted_at = sim_time
                    return TransferState.TRANSMITTED

            elif item.status == TransferState.PAUSED:
                if station_visible and battery_soc >= self.queue.power_threshold_soc:
                    item.status = TransferState.TRANSFERRING
                    item.resume_count += 1
                    item._current_rate_bytes_s = self.effective_rate_bytes_s
                    return TransferState.TRANSFERRING

            return item.status

    def prioritize_item(self, observation_id: str, new_priority: str) -> bool:
        with self._lock:
            for item in self.queue.items:
                if item.observation_id == observation_id and item.status in (TransferState.QUEUED, TransferState.PAUSED):
                    item.priority = new_priority
                    self.queue.items.sort(
                        key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(x.priority, 99)
                    )
                    return True
            return False

    def get_transfer_status(self, observation_id: str) -> Optional[dict]:
        with self._lock:
            for item in self.queue.items:
                if item.observation_id == observation_id:
                    return item.model_dump(mode="json")
            return None

    def get_status(self) -> dict:
        with self._lock:
            progress = self.queue.get_overall_progress()
            return {
                "queue_size": self.queue.get_queue_size(),
                "total_transmitted": self.queue.total_transmitted,
                "total_bytes": self.queue.total_bytes,
                "effective_rate_bytes_s": self.effective_rate_bytes_s,
                "current_band": self._current_band,
                "progress": progress,
                "items": [i.model_dump(mode="json") for i in self.queue.items],
            }

    def get_queue_summary(self) -> dict:
        with self._lock:
            active = self.queue.get_transferring_items()
            queued = self.queue.get_pending_items()
            completed = self.queue.get_completed_items()
            return {
                "queued": [{"id": i.observation_id, "priority": i.priority, "size_bytes": i.image_size_bytes} for i in queued],
                "transferring": [
                    {
                        "id": i.observation_id,
                        "priority": i.priority,
                        "size_bytes": i.image_size_bytes,
                        "bytes_transmitted": i.bytes_transmitted,
                        "progress_pct": i.progress_pct,
                        "station": i.assigned_station,
                        "eta_seconds": i.eta_seconds,
                    }
                    for i in active
                ],
                "completed": [
                    {"id": i.observation_id, "priority": i.priority, "size_bytes": i.image_size_bytes}
                    for i in completed
                ],
            }
