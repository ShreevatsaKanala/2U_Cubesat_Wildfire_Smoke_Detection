from typing import Optional
from app.models.telemetry import TelemetryPacket


class TelemetryService:
    def __init__(self):
        self.latest_telemetry: Optional[TelemetryPacket] = None
        self.telemetry_history: list[TelemetryPacket] = []
        self.max_history: int = 1000

    def update(self, telemetry: TelemetryPacket) -> None:
        self.latest_telemetry = telemetry
        self.telemetry_history.append(telemetry)
        if len(self.telemetry_history) > self.max_history:
            self.telemetry_history = self.telemetry_history[-self.max_history:]

    def get_latest(self) -> Optional[TelemetryPacket]:
        return self.latest_telemetry

    def get_history(self, limit: int = 100) -> list[TelemetryPacket]:
        return self.telemetry_history[-limit:]
