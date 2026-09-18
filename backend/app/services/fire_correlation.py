"""
Fire Correlation Service for CubeSat Digital Twin — Phase 5H-I.

Correlates AI smoke detections with FIRMS active fire data and weather
conditions to produce a fused fire probability score.
"""

import asyncio
import logging
import math
from datetime import datetime, timezone
from typing import Optional

from app.adapters.firms import FIRMSAdapter
from app.adapters.weather import WeatherAdapter
from app.services.observation_service import ObservationService

logger = logging.getLogger(__name__)

# Weights for probability fusion
WEIGHT_AI = 0.40
WEIGHT_FIRMS = 0.35
WEIGHT_WEATHER = 0.25

DEFAULT_RADIUS_KM = 50.0
CORRELATION_THRESHOLD = 0.55  # fire event generated above this
PRIORITY_BOOST_THRESHOLDS = {
    "CRITICAL": 0.75,
    "HIGH": 0.55,
    "MEDIUM": 0.35,
}


class FireCorrelationService:
    def __init__(
        self,
        firms_adapter: Optional[FIRMSAdapter] = None,
        weather_adapter: Optional[WeatherAdapter] = None,
        observation_service: Optional[ObservationService] = None,
    ):
        self.firms = firms_adapter or FIRMSAdapter()
        self.weather = weather_adapter or WeatherAdapter()
        self.observation_service = observation_service
        self._correlation_count = 0
        self._last_correlation_time: Optional[datetime] = None

    def get_status(self) -> dict:
        return {
            "correlations_performed": self._correlation_count,
            "last_correlation_time": (
                self._last_correlation_time.isoformat() if self._last_correlation_time else None
            ),
            "firms_status": self.firms.get_status(),
            "weights": {
                "ai": WEIGHT_AI,
                "firms": WEIGHT_FIRMS,
                "weather": WEIGHT_WEATHER,
            },
            "correlation_threshold": CORRELATION_THRESHOLD,
            "default_radius_km": DEFAULT_RADIUS_KM,
        }

    async def correlate_observation(self, obs, radius_km: float = DEFAULT_RADIUS_KM) -> dict:
        if obs is None:
            return {"error": "No observation provided"}

        lat = obs.latitude
        lon = obs.longitude

        tasks = [
            self.firms.get_detections_near_point(lat, lon, radius_km),
            self.weather.get_weather(lat, lon),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        firms_detections = results[0] if not isinstance(results[0], Exception) else []
        weather_data = results[1] if not isinstance(results[1], Exception) else self.weather._default_weather()

        firms_score = self._compute_firms_score(firms_detections, radius_km)
        weather_score = self._compute_weather_score(weather_data)
        ai_score = getattr(obs, "smoke_probability", 0.0) or 0.0

        fused = (WEIGHT_AI * ai_score) + (WEIGHT_FIRMS * firms_score) + (WEIGHT_WEATHER * weather_score)
        fused = round(min(1.0, max(0.0, fused)), 4)

        correlation_result = {
            "fused_fire_probability": fused,
            "ai_score": ai_score,
            "firms_score": round(firms_score, 4),
            "weather_score": round(weather_score, 4),
            "firms_detections_count": len(firms_detections),
            "firms_detections": [
                {
                    "lat": d.get("lat"),
                    "lon": d.get("lon"),
                    "distance_km": d.get("distance_km"),
                    "confidence": d.get("confidence"),
                    "frp": d.get("frp"),
                }
                for d in firms_detections[:10]
            ],
            "weather": {
                "temperature": weather_data.get("temperature"),
                "humidity": weather_data.get("humidity"),
                "wind_speed": weather_data.get("wind_speed"),
            },
            "fire_event": fused > CORRELATION_THRESHOLD,
            "correlation_time": datetime.now(timezone.utc).isoformat(),
        }

        self._correlation_count += 1
        self._last_correlation_time = datetime.now(timezone.utc)

        new_priority = self._determine_priority(fused)
        correlation_result["recommended_priority"] = new_priority

        return correlation_result

    def _compute_firms_score(self, detections: list[dict], radius_km: float) -> float:
        if not detections:
            return 0.0

        total_score = 0.0
        for d in detections:
            dist = d.get("distance_km", radius_km)
            proximity_factor = max(0.0, 1.0 - (dist / radius_km))

            conf = d.get("confidence_level", 0.5)
            frp = d.get("frp") or 0.0
            frp_factor = min(1.0, frp / 100.0)

            detection_score = (0.5 * proximity_factor) + (0.3 * conf) + (0.2 * frp_factor)
            total_score += detection_score

        return min(1.0, total_score)

    def _compute_weather_score(self, weather: dict) -> float:
        temp = weather.get("temperature")
        humidity = weather.get("humidity")
        wind = weather.get("wind_speed")

        score = 0.0

        if temp is not None:
            if temp > 35:
                score += 0.4
            elif temp > 25:
                score += 0.2
            elif temp > 15:
                score += 0.1

        if humidity is not None:
            if humidity < 20:
                score += 0.35
            elif humidity < 40:
                score += 0.2
            elif humidity < 60:
                score += 0.1

        if wind is not None:
            if wind > 30:
                score += 0.25
            elif wind > 15:
                score += 0.15
            elif wind > 5:
                score += 0.05

        return min(1.0, score)

    def _determine_priority(self, fused_score: float) -> str:
        if fused_score >= PRIORITY_BOOST_THRESHOLDS["CRITICAL"]:
            return "CRITICAL"
        elif fused_score >= PRIORITY_BOOST_THRESHOLDS["HIGH"]:
            return "HIGH"
        elif fused_score >= PRIORITY_BOOST_THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        return "LOW"

    async def apply_correlation_to_observation(self, obs, radius_km: float = DEFAULT_RADIUS_KM) -> object:
        result = await self.correlate_observation(obs, radius_km)

        if hasattr(obs, "fire_correlation_score"):
            obs.fire_correlation_score = result["fused_fire_probability"]
            obs.fire_correlation_details = result
            obs.firms_detections_nearby = result["firms_detections_count"]
            obs.weather_fire_risk = result["weather_score"]
            obs.correlated_at = datetime.now(timezone.utc)
            obs.correlated_priority = result["recommended_priority"]

            if result["fire_event"] and result["recommended_priority"] != "LOW":
                old_priority = getattr(obs, "priority", "LOW")
                priority_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
                new_order = priority_order.get(result["recommended_priority"], 1)
                old_order = priority_order.get(old_priority, 1)
                if new_order > old_order:
                    obs.priority = result["recommended_priority"]
                    obs.correlated_priority = result["recommended_priority"]

        return obs
