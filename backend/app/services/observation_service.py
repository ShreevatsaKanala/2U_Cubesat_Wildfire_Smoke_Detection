"""
Observation Service for CubeSat Digital Twin.

Manages storage and retrieval of observation records.
Phase 1 uses in-memory storage; future phases will integrate
with database backends.
"""

from datetime import datetime, timezone
from typing import Optional, List


class ObservationService:
    """
    Service for managing observation records.

    Provides CRUD operations for observations with bounded in-memory
    storage that drops the oldest observations when the limit is reached.
    """

    def __init__(self):
        """Initialize observation service with bounded storage."""
        from app.core.config import settings
        self.observations: List = []
        self._max_observations = settings.MAX_OBSERVATIONS_IN_MEMORY
        self._dropped_count = 0

    def __len__(self) -> int:
        return len(self.observations)

    def store(self, observation) -> None:
        """
        Store an observation record.

        Drops the oldest observation when the memory limit is reached.
        """
        if observation is None:
            raise ValueError("Cannot store None observation")

        obs_id = getattr(observation, 'observation_id', None)
        if obs_id:
            existing = self.get_by_id(obs_id)
            if existing:
                return

        # Enforce memory limit
        if len(self.observations) >= self._max_observations:
            self.observations.pop(0)
            self._dropped_count += 1
            if self._dropped_count % 20 == 1:
                import logging
                logging.getLogger(__name__).warning(
                    "Observation storage full (%d) — dropped %d total",
                    self._max_observations, self._dropped_count,
                )

        self.observations.append(observation)

    def get_latest(self) -> Optional[object]:
        """
        Get the most recent observation.

        Returns:
            Latest Observation object, or None if no observations
        """
        if not self.observations:
            return None
        return self.observations[-1]

    def get_all(self, limit: int = 50) -> List:
        """
        Get observations with pagination.

        Args:
            limit: Maximum number of observations to return

        Returns:
            List of Observation objects (most recent first)
        """
        # Return most recent observations, limited by count
        return list(reversed(self.observations[-limit:]))

    def get_by_id(self, observation_id: str) -> Optional[object]:
        """
        Get observation by its unique ID.

        Args:
            observation_id: Unique observation identifier

        Returns:
            Observation object if found, None otherwise
        """
        for obs in self.observations:
            if getattr(obs, 'observation_id', None) == observation_id:
                return obs
        return None

    def get_count(self) -> int:
        """Get total number of stored observations."""
        return len(self.observations)

    def clear(self) -> int:
        """
        Clear all stored observations.

        Returns:
            Number of observations cleared
        """
        count = len(self.observations)
        self.observations.clear()
        return count

    def get_statistics(self) -> dict:
        """
        Get statistics about stored observations.

        Returns:
            Dictionary with observation statistics
        """
        if not self.observations:
            return {
                "total_count": 0,
                "priorities": {},
                "avg_smoke_probability": 0.0
            }

        priorities = {}
        total_smoke = 0.0

        for obs in self.observations:
            priority = getattr(obs, 'priority', 'UNKNOWN')
            priorities[priority] = priorities.get(priority, 0) + 1

            sp = getattr(obs, 'smoke_probability', None)
            if sp is not None:
                total_smoke += sp

        return {
            "total_count": len(self.observations),
            "priorities": priorities,
            "avg_smoke_probability": total_smoke / len(self.observations)
        }
