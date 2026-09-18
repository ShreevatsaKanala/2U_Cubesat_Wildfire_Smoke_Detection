from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum

class EventType(str, Enum):
    OBSERVATION_STARTED = "OBSERVATION_STARTED"
    OBSERVATION_COMPLETED = "OBSERVATION_COMPLETED"
    ML_RESULT_READY = "ML_RESULT_READY"
    PRIORITY_CHANGED = "PRIORITY_CHANGED"
    FAULT_DETECTED = "FAULT_DETECTED"
    SAFE_MODE_ENTERED = "SAFE_MODE_ENTERED"
    DOWNLINK_STARTED = "DOWNLINK_STARTED"
    DOWNLINK_COMPLETED = "DOWNLINK_COMPLETED"
    MISSION_MODE_CHANGED = "MISSION_MODE_CHANGED"
    SUBSYSTEM_STATUS_CHANGED = "SUBSYSTEM_STATUS_CHANGED"
    AI_INFERENCE_STARTED = "AI_INFERENCE_STARTED"
    AI_INFERENCE_COMPLETED = "AI_INFERENCE_COMPLETED"
    AI_INFERENCE_FAILED = "AI_INFERENCE_FAILED"
    AI_PROVIDER_FAILOVER = "AI_PROVIDER_FAILOVER"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    FAULT_RECOVERY_STARTED = "FAULT_RECOVERY_STARTED"
    FAULT_RECOVERY_COMPLETED = "FAULT_RECOVERY_COMPLETED"
    FAULT_RECOVERY_FAILED = "FAULT_RECOVERY_FAILED"
    RECOVERY_ACTION_TAKEN = "RECOVERY_ACTION_TAKEN"
    LOAD_SHEDDING = "LOAD_SHEDDING"
    POWER_EVENT = "POWER_EVENT"
    THERMAL_EVENT = "THERMAL_EVENT"

class MissionEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: EventType
    description: str = ""
    severity: str = "info"
    subsystem: Optional[str] = None
    data: Optional[dict] = None

class EventLog(BaseModel):
    events: list[MissionEvent] = []
    max_events: int = 1000  # From config: MAX_EVENTS_IN_MEMORY

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Import config limit on first use
        try:
            from app.core.config import settings
            self.max_events = settings.MAX_EVENTS_IN_MEMORY
        except Exception:
            pass

    def add(self, event: MissionEvent):
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def get_recent(self, limit: int = 50) -> list[MissionEvent]:
        return list(reversed(self.events[-limit:]))

    def __len__(self) -> int:
        return len(self.events)
