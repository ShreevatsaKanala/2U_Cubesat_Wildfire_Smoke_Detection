import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WeatherAdapter:
    def __init__(self, base_url: str = "https://api.open-meteo.com/v1"):
        self.base_url = base_url

    async def get_weather(self, lat: float, lon: float) -> dict:
        url = f"{self.base_url}/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m",
                "wind_direction_10m",
                "precipitation",
                "surface_pressure",
                "cloud_cover",
                "weather_code",
            ]),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                current = data.get("current", {})
                return {
                    "temperature": current.get("temperature_2m"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "wind_direction": current.get("wind_direction_10m"),
                    "precipitation": current.get("precipitation"),
                    "pressure": current.get("surface_pressure"),
                    "cloud_cover": current.get("cloud_cover"),
                    "weather_code": current.get("weather_code"),
                }
        except httpx.TimeoutException:
            logger.warning("Open-Meteo weather API timeout")
            return self._default_weather()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Open-Meteo weather API HTTP error: {e.response.status_code}")
            return self._default_weather()
        except Exception as e:
            logger.warning(f"Open-Meteo weather API error: {e}")
            return self._default_weather()

    async def get_air_quality(self, lat: float, lon: float) -> dict:
        url = f"{self.base_url}/air-quality"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ",".join([
                "pm10",
                "pm2_5",
                "carbon_monoxide",
                "nitrogen_dioxide",
                "sulphur_dioxide",
                "ozone",
                "european_aqi",
            ]),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                current = data.get("current", {})
                return {
                    "pm10": current.get("pm10"),
                    "pm2_5": current.get("pm2_5"),
                    "carbon_monoxide": current.get("carbon_monoxide"),
                    "nitrogen_dioxide": current.get("nitrogen_dioxide"),
                    "sulphur_dioxide": current.get("sulphur_dioxide"),
                    "ozone": current.get("ozone"),
                    "european_aqi": current.get("european_aqi"),
                }
        except httpx.TimeoutException:
            logger.warning("Open-Meteo air quality API timeout")
            return self._default_air_quality()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Open-Meteo air quality API HTTP error: {e.response.status_code}")
            return self._default_air_quality()
        except Exception as e:
            logger.warning(f"Open-Meteo air quality API error: {e}")
            return self._default_air_quality()

    @staticmethod
    def _default_weather() -> dict:
        return {
            "temperature": None,
            "humidity": None,
            "wind_speed": None,
            "wind_direction": None,
            "precipitation": None,
            "pressure": None,
            "cloud_cover": None,
            "weather_code": None,
        }

    @staticmethod
    def _default_air_quality() -> dict:
        return {
            "pm10": None,
            "pm2_5": None,
            "carbon_monoxide": None,
            "nitrogen_dioxide": None,
            "sulphur_dioxide": None,
            "ozone": None,
            "european_aqi": None,
        }
