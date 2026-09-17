from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models.observation import Observation


class ObservationRepository:
    def __init__(self):
        self._observations: dict[str, Observation] = {}

    async def add(self, observation: Observation) -> Observation:
        self._observations[observation.observation_id] = observation
        return observation

    async def get(self, observation_id: str) -> Optional[Observation]:
        return self._observations.get(observation_id)

    async def list_recent(self, limit: int = 50) -> list[Observation]:
        sorted_obs = sorted(
            self._observations.values(),
            key=lambda o: o.timestamp,
            reverse=True,
        )
        return sorted_obs[:limit]

    async def update(self, observation_id: str, **kwargs) -> Optional[Observation]:
        obs = self._observations.get(observation_id)
        if obs is None:
            return None
        updated_data = obs.model_dump()
        updated_data.update(kwargs)
        updated = Observation(**updated_data)
        self._observations[observation_id] = updated
        return updated
