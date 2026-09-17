"""
Priority Calculator for CubeSat observations.

Determines observation priority based on smoke probability and
classification confidence. Used to triage observations for
downlink and analysis.
"""

from typing import Dict


class PriorityCalculator:
    """
    Calculates observation priority for downlink scheduling.

    Uses weighted scoring of smoke probability and confidence
    to assign priority levels (CRITICAL, HIGH, MEDIUM, LOW).
    """

    def __init__(self, thresholds: dict = None):
        """
        Initialize priority calculator.

        Args:
            thresholds: Optional custom thresholds dict with keys:
                - high: Threshold for HIGH priority (default 0.7)
                - medium: Threshold for MEDIUM priority (default 0.4)
                - low: Threshold for LOW priority (default 0.1)
        """
        self.thresholds = thresholds or {
            "high": 0.7,
            "medium": 0.4,
            "low": 0.1
        }

    def calculate(self, smoke_probability: float, confidence: float) -> str:
        """
        Calculate observation priority.

        Args:
            smoke_probability: Probability of smoke detection (0-1)
            confidence: Model confidence in prediction (0-1)

        Returns:
            Priority string: "CRITICAL", "HIGH", "MEDIUM", or "LOW"
        """
        # Weighted score combines probability and confidence
        weighted_score = smoke_probability * confidence

        if weighted_score >= 0.6:
            return "CRITICAL"
        elif weighted_score >= 0.4:
            return "HIGH"
        elif weighted_score >= 0.2:
            return "MEDIUM"
        else:
            return "LOW"

    def get_priority_description(self, priority: str) -> str:
        """
        Get human-readable description of priority level.

        Args:
            priority: Priority string

        Returns:
            Description of what the priority means
        """
        descriptions = {
            "CRITICAL": "Immediate attention required. High probability of active wildfire "
                       "with strong model confidence. Recommend immediate downlink and "
                       "alert to ground stations.",
            "HIGH": "Elevated priority. Significant smoke detected with good confidence. "
                   "Schedule for priority downlink within next pass.",
            "MEDIUM": "Moderate priority. Some smoke indicators detected. "
                     "Include in regular downlink queue.",
            "LOW": "Standard priority. Clear conditions or low confidence detection. "
                  "Process in standard queue."
        }
        return descriptions.get(priority, "Unknown priority level")

    def get_priority_color(self, priority: str) -> str:
        """
        Get color code for priority visualization.

        Args:
            priority: Priority string

        Returns:
            Hex color code
        """
        colors = {
            "CRITICAL": "#FF0000",
            "HIGH": "#FF6600",
            "MEDIUM": "#FFCC00",
            "LOW": "#00CC00"
        }
        return colors.get(priority, "#808080")

    def get_priority_order(self, priority: str) -> int:
        """
        Get numeric order for priority sorting (higher = more urgent).

        Args:
            priority: Priority string

        Returns:
            Numeric priority (4=Critical, 3=High, 2=Medium, 1=Low)
        """
        order = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1
        }
        return order.get(priority, 0)
