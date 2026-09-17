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

    Provides CRUD operations for observations with in-memory
    storage for Phase 1 development and testing.
    """

    def __init__(self):
        """Initialize observation service with empty storage."""
        self.observations: List = []
        self._max_observations = 1000  # Memory limit for Phase 1

    def store(self, observation) -> None:
        """
        Store an observation record.

        Args:
            observation: Observation object to store

        Raises:
            ValueError: If observation is None or missing required fields
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
            # Remove oldest observation
            self.observations.pop(0)

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

            ml_results = getattr(obs, 'ml_results', None)
            if ml_results:
                total_smoke += ml_results.get('smoke_probability', 0.0)

        return {
            "total_count": len(self.observations),
            "priorities": priorities,
            "avg_smoke_probability": total_smoke / len(self.observations)
        }
