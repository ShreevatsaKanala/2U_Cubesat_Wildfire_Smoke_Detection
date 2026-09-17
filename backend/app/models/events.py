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
    max_events: int = 500

    def add(self, event: MissionEvent):
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def get_recent(self, limit: int = 50) -> list[MissionEvent]:
        return list(reversed(self.events[-limit:]))
