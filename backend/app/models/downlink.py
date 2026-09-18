from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
class TransferState:
    QUEUED = "queued"
    TRANSFERRING = "transferring"
    PAUSED = "paused"
    TRANSMITTED = "transmitted"
    FAILED = "failed"
    # Alias for backward compat
    COMPLETE = "transmitted"


class DownlinkItem(BaseModel):
    observation_id: str
    priority: str = "LOW"
    image_size_bytes: int = 0
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    transmitted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    status: str = TransferState.QUEUED
    bytes_transmitted: int = 0
    assigned_station: Optional[str] = None
    pause_reason: Optional[str] = None
    fail_reason: Optional[str] = None
    resume_count: int = 0

    @property
    def progress_pct(self) -> float:
        if self.image_size_bytes <= 0:
            return 0.0
        return round(self.bytes_transmitted / self.image_size_bytes * 100, 2)

    @property
    def bytes_remaining(self) -> int:
        return max(0, self.image_size_bytes - self.bytes_transmitted)

    @property
    def eta_seconds(self) -> float:
        if self.status != TransferState.TRANSFERRING:
            return 0.0
        rate = getattr(self, '_current_rate_bytes_s', 0.0)
        if rate <= 0:
            return 0.0
        return round(self.bytes_remaining / rate, 1)

    def model_dump(self, **kwargs):
        d = super().model_dump(**kwargs)
        d["progress_pct"] = self.progress_pct
        d["bytes_remaining"] = self.bytes_remaining
        d["eta_seconds"] = self.eta_seconds
        return d


class DownlinkQueue(BaseModel):
    items: list[DownlinkItem] = []
    total_transmitted: int = 0
    total_bytes: int = 0
    downlink_rate_bytes_s: float = 1024.0
    min_elevation_deg: float = 10.0
    comm_loss_probability: float = 0.001
    power_threshold_soc: float = 15.0
    min_image_size_bytes: int = 500 * 1024
    max_image_size_bytes: int = 5 * 1024 * 1024

    def enqueue(self, item: DownlinkItem):
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        self.items.append(item)
        self.items.sort(key=lambda x: priority_order.get(x.priority, 99))

    def get_queue_size(self) -> int:
        return len([i for i in self.items if i.status == TransferState.QUEUED])

    def get_pending_items(self) -> list:
        return [i for i in self.items if i.status == TransferState.QUEUED]

    def get_transferring_items(self) -> list:
        return [i for i in self.items if i.status == TransferState.TRANSFERRING]

    def get_active_items(self) -> list:
        return [i for i in self.items if i.status in (TransferState.TRANSFERRING, TransferState.PAUSED)]

    def get_completed_items(self) -> list:
        return [i for i in self.items if i.status == TransferState.TRANSMITTED]

    def get_overall_progress(self) -> dict:
        active = self.get_active_items()
        queued = self.get_pending_items()
        completed = self.get_completed_items()
        total_active_bytes = sum(i.image_size_bytes for i in active)
        total_active_transferred = sum(i.bytes_transmitted for i in active)
        total_queued_bytes = sum(i.image_size_bytes for i in queued)
        total_completed_bytes = sum(i.image_size_bytes for i in completed)
        return {
            "queued_count": len(queued),
            "active_count": len(active),
            "completed_count": len(completed),
            "total_queued_bytes": total_queued_bytes,
            "total_active_bytes": total_active_bytes,
            "total_active_transferred": total_active_transferred,
            "total_completed_bytes": total_completed_bytes,
            "overall_progress_pct": round(
                (total_active_transferred + total_completed_bytes) /
                max(1, total_active_bytes + total_queued_bytes + total_completed_bytes) * 100, 2
            ),
        }
