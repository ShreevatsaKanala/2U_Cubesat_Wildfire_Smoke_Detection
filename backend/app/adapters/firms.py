import httpx
import logging
import os
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "firms")
CACHE_TTL_SECONDS = 1800  # 30 minutes — FIRMS updates every 3 hours
RATE_LIMIT_WINDOW = 60.0  # seconds
RATE_LIMIT_MAX_CALLS = 10  # per window


class FIRMSAdapter:
    def __init__(self, api_key: str = None, base_url: str = "https://firms.modaps.eosdis.nasa.gov/api"):
        self.api_key = api_key
        self.base_url = base_url
        self._call_timestamps: list[float] = []
        self._last_fetch_time: Optional[datetime] = None
        self._last_fetch_status: str = "never"
        self._cache_hits = 0
        self._cache_misses = 0
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _cache_key(self, west: float, south: float, east: float, north: float, days: int) -> str:
        raw = f"{west:.2f},{south:.2f},{east:.2f},{north:.2f},{days}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _cache_path(self, key: str) -> str:
        return os.path.join(CACHE_DIR, f"{key}.json")

    def _read_cache(self, key: str) -> Optional[list[dict]]:
        path = self._cache_path(key)
        if not os.path.exists(path):
            return None
        try:
            mtime = os.path.getmtime(path)
            age = time.time() - mtime
            if age > CACHE_TTL_SECONDS:
                return None
            with open(path, "r") as f:
                data = json.load(f)
            self._cache_hits += 1
            return data
        except Exception:
            return None

    def _write_cache(self, key: str, data: list[dict]) -> None:
        try:
            with open(self._cache_path(key), "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to write FIRMS cache: {e}")

    def _rate_limit_check(self) -> bool:
        now = time.time()
        self._call_timestamps = [t for t in self._call_timestamps if now - t < RATE_LIMIT_WINDOW]
        if len(self._call_timestamps) >= RATE_LIMIT_MAX_CALLS:
            logger.warning("FIRMS API rate limit reached, skipping request")
            return False
        self._call_timestamps.append(now)
        return True

    def _cache_age_seconds(self, key: str) -> Optional[float]:
        path = self._cache_path(key)
        if not os.path.exists(path):
            return None
        return time.time() - os.path.getmtime(path)

    def get_status(self) -> dict:
        return {
            "api_configured": bool(self.api_key),
            "last_fetch_time": self._last_fetch_time.isoformat() if self._last_fetch_time else None,
            "last_fetch_status": self._last_fetch_status,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "rate_limit_window": RATE_LIMIT_WINDOW,
            "rate_limit_max_calls": RATE_LIMIT_MAX_CALLS,
            "rate_limit_remaining": RATE_LIMIT_MAX_CALLS - len(self._call_timestamps),
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
        }

    async def get_hotspots(
        self, north: float, south: float, east: float, west: float, days: int = 1
    ) -> list[dict]:
        if not self.api_key:
            logger.warning("FIRMS API key not configured, returning empty hotspots list")
            self._last_fetch_status = "no_api_key"
            return []

        cache_key = self._cache_key(west, south, east, north, days)
        cached = self._read_cache(cache_key)
        if cached is not None:
            self._last_fetch_status = "cache_hit"
            return cached

        if not self._rate_limit_check():
            self._last_fetch_status = "rate_limited"
            return []

        self._cache_misses += 1
        url = f"{self.base_url}/area/csv/{self.api_key}/VIIRS_SNPP_NRT/{west},{south},{east},{north}/{days}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                hotspots = self._parse_csv(response.text)
                self._last_fetch_time = datetime.now(timezone.utc)
                self._last_fetch_status = "success"
                self._write_cache(cache_key, hotspots)
                return hotspots
        except httpx.TimeoutException:
            logger.warning("FIRMS API timeout for area hotspots")
            self._last_fetch_status = "timeout"
            return []
        except httpx.HTTPStatusError as e:
            logger.warning(f"FIRMS API HTTP error: {e.response.status_code}")
            self._last_fetch_status = f"http_{e.response.status_code}"
            return []
        except Exception as e:
            logger.warning(f"FIRMS API error: {e}")
            self._last_fetch_status = "error"
            return []

    async def get_detections_near_point(
        self, lat: float, lon: float, radius_km: float = 50.0, days: int = 1
    ) -> list[dict]:
        import math
        lat_rad = math.radians(lat)
        deg_per_km_lat = 1.0 / 111.0
        deg_per_km_lon = 1.0 / (111.0 * math.cos(lat_rad)) if abs(lat_rad) < math.pi / 2 else 1.0

        south = lat - radius_km * deg_per_km_lat
        north = lat + radius_km * deg_per_km_lat
        west = lon - radius_km * deg_per_km_lon
        east = lon + radius_km * deg_per_km_lon

        hotspots = await self.get_hotspots(north, south, east, west, days)

        filtered = []
        for h in hotspots:
            if h.get("lat") is None or h.get("lon") is None:
                continue
            dlat_rad = math.radians(h["lat"] - lat)
            dlon_rad = math.radians(h["lon"] - lon)
            a = math.sin(dlat_rad / 2) ** 2 + math.cos(lat_rad) * math.cos(math.radians(h["lat"])) * math.sin(dlon_rad / 2) ** 2
            dist_km = 2 * 6371 * math.asin(math.sqrt(a))
            if dist_km <= radius_km:
                h["distance_km"] = round(dist_km, 2)
                h["confidence_level"] = self._confidence_from_string(h.get("confidence", ""))
                filtered.append(h)

        filtered.sort(key=lambda x: x.get("distance_km", 999))
        return filtered

    async def get_global_hotspots(self, days: int = 1) -> list[dict]:
        if not self.api_key:
            logger.warning("FIRMS API key not configured, returning empty hotspots list")
            self._last_fetch_status = "no_api_key"
            return []

        if not self._rate_limit_check():
            self._last_fetch_status = "rate_limited"
            return []

        url = f"{self.base_url}/csv/{self.api_key}/VIIRS_SNPP_NRT/{days}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                self._last_fetch_time = datetime.now(timezone.utc)
                self._last_fetch_status = "success"
                return self._parse_csv(response.text)
        except httpx.TimeoutException:
            logger.warning("FIRMS API timeout for global hotspots")
            self._last_fetch_status = "timeout"
            return []
        except httpx.HTTPStatusError as e:
            logger.warning(f"FIRMS API HTTP error: {e.response.status_code}")
            self._last_fetch_status = f"http_{e.response.status_code}"
            return []
        except Exception as e:
            logger.warning(f"FIRMS API error: {e}")
            self._last_fetch_status = "error"
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
                "acq_date": row.get("acq_date", ""),
                "acq_time": row.get("acq_time", ""),
                "bright_ti5": self._parse_float(row.get("bright_ti5")),
                "daynight": row.get("daynight", ""),
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

    @staticmethod
    def _confidence_from_string(conf: str) -> float:
        mapping = {"low": 0.3, "nominal": 0.6, "high": 0.8}
        return mapping.get(conf.lower(), 0.5) if conf else 0.5
