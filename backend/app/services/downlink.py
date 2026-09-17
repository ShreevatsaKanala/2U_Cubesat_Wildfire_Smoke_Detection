"""Downlink Simulation Service."""
from datetime import datetime, timezone
from typing import Optional
from app.models.downlink import DownlinkItem, DownlinkQueue
from app.models.observation import Observation

class DownlinkService:
    def __init__(self, rate_bytes_s: float = 1024.0):
        self.queue = DownlinkQueue(downlink_rate_bytes_s=rate_bytes_s)
    
    def queue_observation(self, obs: Observation):
        item = DownlinkItem(
            observation_id=obs.observation_id,
            priority=obs.priority,
            image_size_bytes=obs.image_width * obs.image_height * 3,
        )
        self.queue.enqueue(item)
    
    def get_status(self) -> dict:
        return {
            "queue_size": self.queue.get_queue_size(),
            "total_transmitted": self.queue.total_transmitted,
            "total_bytes": self.queue.total_bytes,
            "items": [i.model_dump(mode="json") for i in self.queue.items],
        }
