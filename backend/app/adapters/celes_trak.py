import httpx
import logging

logger = logging.getLogger(__name__)


class CelesTrakAdapter:
    def __init__(self, base_url: str = "https://celestrak.org/NORAD/elements"):
        self.base_url = base_url

    async def get_tle(self, norad_id: str) -> dict:
        url = f"{self.base_url}/gp.php"
        params = {
            "CATNR": norad_id,
            "FORMAT": "TLE",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return self._parse_tle(response.text, norad_id)
        except httpx.TimeoutException:
            logger.warning(f"CelesTrak API timeout for NORAD ID {norad_id}")
            return {"name": "", "line1": "", "line2": ""}
        except httpx.HTTPStatusError as e:
            logger.warning(f"CelesTrak API HTTP error: {e.response.status_code}")
            return {"name": "", "line1": "", "line2": ""}
        except Exception as e:
            logger.warning(f"CelesTrak API error: {e}")
            return {"name": "", "line1": "", "line2": ""}

    @staticmethod
    def _parse_tle(text: str, norad_id: str) -> dict:
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if len(lines) < 3:
            logger.warning(f"Invalid TLE data for NORAD ID {norad_id}")
            return {"name": "", "line1": "", "line2": ""}

        return {
            "name": lines[0],
            "line1": lines[1],
            "line2": lines[2],
        }
