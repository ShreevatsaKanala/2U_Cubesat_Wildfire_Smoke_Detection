from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

class DownlinkItem(BaseModel):
    observation_id: str
    priority: str = "LOW"
    image_size_bytes: int = 0
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    transmitted_at: Optional[datetime] = None
    status: str = "queued"
    bytes_transmitted: int = 0

class DownlinkQueue(BaseModel):
    items: list[DownlinkItem] = []
    total_transmitted: int = 0
    total_bytes: int = 0
    downlink_rate_bytes_s: float = 1024.0

    def enqueue(self, item: DownlinkItem):
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        self.items.append(item)
        self.items.sort(key=lambda x: priority_order.get(x.priority, 99))

    def get_queue_size(self) -> int:
        return len([i for i in self.items if i.status == "queued"])

    def get_pending_items(self) -> list:
        return [i for i in self.items if i.status == "queued"]
