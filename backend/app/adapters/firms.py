import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FIRMSAdapter:
    def __init__(self, api_key: str = None, base_url: str = "https://firms.modaps.eosdis.nasa.gov/api"):
        self.api_key = api_key
        self.base_url = base_url

    async def get_hotspots(
        self, north: float, south: float, east: float, west: float, days: int = 1
    ) -> list[dict]:
        if not self.api_key:
            logger.warning("FIRMS API key not configured, returning empty hotspots list")
            return []

        url = f"{self.base_url}/area/csv/{self.api_key}/VIIRS_SNPP_NRT/{west},{south},{east},{north}/{days}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return self._parse_csv(response.text)
        except httpx.TimeoutException:
            logger.warning("FIRMS API timeout for area hotspots")
            return []
        except httpx.HTTPStatusError as e:
            logger.warning(f"FIRMS API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.warning(f"FIRMS API error: {e}")
            return []

    async def get_global_hotspots(self, days: int = 1) -> list[dict]:
        if not self.api_key:
            logger.warning("FIRMS API key not configured, returning empty hotspots list")
            return []

        url = f"{self.base_url}/csv/{self.api_key}/VIIRS_SNPP_NRT/{days}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return self._parse_csv(response.text)
        except httpx.TimeoutException:
            logger.warning("FIRMS API timeout for global hotspots")
            return []
        except httpx.HTTPStatusError as e:
            logger.warning(f"FIRMS API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.warning(f"FIRMS API error: {e}")
            return []

    def _parse_csv(self, csv_text: str) -> list[dict]:
        lines = csv_text.strip().split("\n")
        if len(lines) < 2:
            return []

        headers = [h.strip().lower() for h in lines[0].split(",")]
        hotspots = []
        for line in lines[1:]:
            values = line.split(",")
            if len(values) != len(headers):
                continue
            row = dict(zip(headers, values))
            hotspot = {
                "lat": self._parse_float(row.get("latitude")),
                "lon": self._parse_float(row.get("longitude")),
                "confidence": row.get("confidence", ""),
                "frp": self._parse_float(row.get("frp")),
                "brightness": self._parse_float(row.get("bright_ti4")),
                "scan": self._parse_float(row.get("scan")),
                "track": self._parse_float(row.get("track")),
                "satellite": row.get("satellite", ""),
            }
            hotspots.append(hotspot)
        return hotspots

    @staticmethod
    def _parse_float(value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
