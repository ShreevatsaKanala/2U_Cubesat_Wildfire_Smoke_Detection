"""
TLE Service for CubeSat Digital Twin.

Fetches, caches, and validates Two-Line Element sets from CelesTrak.
Provides thread-safe access and automatic cache refresh.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import httpx
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default CubeSat NORAD IDs for fallback
DEFAULT_NORAD_ID = "55000"  # Generic placeholder
FALLBACK_TLE_LINE1 = "1 25544U 98067A   24100.50000000  .00016717  00000-0  10270-3 0  9994"
FALLBACK_TLE_LINE2 = "2 25544  51.6400 200.0000 0007000  50.0000 310.0000 15.49000000400000"

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "tle"
CACHE_MAX_AGE_HOURS = 24
EPOCH_MAX_AGE_DAYS = 60  # TLE older than this is considered stale


class TLEService:
    """
    Manages TLE data lifecycle: fetch, cache, validate, serve.

    Thread-safe via internal lock. Falls back to hardcoded TLE on network failure.
    """

    def __init__(self, norad_id: str = DEFAULT_NORAD_ID):
        self._lock = threading.Lock()
        self._norad_id = norad_id
        self._tle_line1: Optional[str] = None
        self._tle_line2: Optional[str] = None
        self._tle_name: Optional[str] = None
        self._epoch: Optional[datetime] = None
        self._fetched_at: Optional[datetime] = None
        self._source: str = "unknown"
        self._valid: bool = False

        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def is_valid(self) -> bool:
        return self._valid

    @property
    def tle_line1(self) -> Optional[str]:
        return self._tle_line1

    @property
    def tle_line2(self) -> Optional[str]:
        return self._tle_line2

    def get_status(self) -> dict:
        """Return current TLE status for the API endpoint."""
        with self._lock:
            return {
                "norad_id": self._norad_id,
                "name": self._tle_name,
                "source": self._source,
                "epoch": self._epoch.isoformat() if self._epoch else None,
                "fetched_at": self._fetched_at.isoformat() if self._fetched_at else None,
                "valid": self._valid,
                "age_hours": round(
                    (datetime.now(timezone.utc) - self._epoch).total_seconds() / 3600, 2
                ) if self._epoch else None,
                "cache_age_hours": round(
                    (datetime.now(timezone.utc) - self._fetched_at).total_seconds() / 3600, 2
                ) if self._fetched_at else None,
                "cache_dir": str(CACHE_DIR),
            }

    def initialize(self) -> tuple[Optional[str], Optional[str]]:
        """
        Initialize TLE by checking cache, then fetching if needed.
        Returns (tle_line1, tle_line2) or (None, None) on failure.
        """
        with self._lock:
            # Try cache first
            if self._try_load_cache():
                logger.info("TLE loaded from cache (NORAD %s)", self._norad_id)
                return self._tle_line1, self._tle_line2

        # Fetch from CelesTrak (outside lock)
        tle = self._fetch_from_celestrak(self._norad_id)
        if tle:
            with self._lock:
                self._apply_tle(tle["name"], tle["line1"], tle["line2"], "celestrak")
                self._save_cache()
            logger.info("TLE fetched from CelesTrak (NORAD %s)", self._norad_id)
            return self._tle_line1, self._tle_line2

        # Fallback
        with self._lock:
            self._apply_tle("ISS (ZARYA)", FALLBACK_TLE_LINE1, FALLBACK_TLE_LINE2, "fallback")
        logger.warning("Using fallback hardcoded TLE (NORAD %s)", self._norad_id)
        return self._tle_line1, self._tle_line2

    def refresh(self) -> dict:
        """
        Force re-fetch TLE from CelesTrak, ignoring cache.
        Returns status dict.
        """
        tle = self._fetch_from_celestrak(self._norad_id)
        if tle:
            with self._lock:
                self._apply_tle(tle["name"], tle["line1"], tle["line2"], "celestrak-refresh")
                self._save_cache()
            logger.info("TLE refreshed from CelesTrak (NORAD %s)", self._norad_id)
        else:
            logger.warning("TLE refresh failed, keeping existing TLE")
        return self.get_status()

    def load_direct(self, tle_line1: str, tle_line2: str, name: str = "direct-load") -> None:
        """Load TLE directly (e.g., from API input)."""
        with self._lock:
            self._apply_tle(name, tle_line1, tle_line2, "direct")
            self._save_cache()
        logger.info("TLE loaded directly: %s", name)

    def _apply_tle(self, name: str, line1: str, line2: str, source: str) -> None:
        """Set TLE fields and validate. Must be called under lock."""
        self._tle_name = name
        self._tle_line1 = line1
        self._tle_line2 = line2
        self._source = source
        self._fetched_at = datetime.now(timezone.utc)
        self._epoch = self._parse_epoch(line1)
        self._valid = self._validate_tle(line1, line2, self._epoch)

    def _parse_epoch(self, tle_line1: str) -> Optional[datetime]:
        """Extract epoch from TLE line 1 (columns 18-32, Julian year + day)."""
        try:
            epoch_str = tle_line1[18:32].strip()
            year = int(epoch_str[:2])
            year = year + 2000 if year < 57 else year + 1900
            day_of_year = float(epoch_str[2:])
            epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)
            return epoch
        except (ValueError, IndexError):
            return None

    def _validate_tle(self, line1: str, line2: str, epoch: Optional[datetime]) -> bool:
        """Check TLE basic validity: format and epoch freshness."""
        if not line1 or not line2:
            return False
        if not line1.startswith("1 ") or not line2.startswith("2 "):
            return False
        if len(line1) < 69 or len(line2) < 69:
            return False
        if epoch is None:
            return False
        age_days = (datetime.now(timezone.utc) - epoch).total_seconds() / 86400
        if age_days > EPOCH_MAX_AGE_DAYS:
            logger.warning("TLE epoch is %.1f days old (max %d days)", age_days, EPOCH_MAX_AGE_DAYS)
            return False
        return True

    def _try_load_cache(self) -> bool:
        """Try to load TLE from cache if fresh enough. Must be called under lock."""
        cache_file = CACHE_DIR / f"tle_{self._norad_id}.json"
        if not cache_file.exists():
            return False
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            fetched_at = datetime.fromisoformat(data["fetched_at"])
            age_hours = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
            if age_hours > CACHE_MAX_AGE_HOURS:
                logger.info("TLE cache expired (%.1f hours old)", age_hours)
                return False
            self._apply_tle(data["name"], data["line1"], data["line2"], "cache")
            return True
        except Exception as e:
            logger.warning("Failed to read TLE cache: %s", e)
            return False

    def _save_cache(self) -> None:
        """Save current TLE to disk cache. Must be called under lock."""
        cache_file = CACHE_DIR / f"tle_{self._norad_id}.json"
        data = {
            "norad_id": self._norad_id,
            "name": self._tle_name,
            "line1": self._tle_line1,
            "line2": self._tle_line2,
            "fetched_at": self._fetched_at.isoformat() if self._fetched_at else None,
        }
        try:
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to write TLE cache: %s", e)

    @staticmethod
    def _fetch_from_celestrak(norad_id: str) -> Optional[dict]:
        """Fetch TLE from CelesTrak API. Returns parsed TLE dict or None."""
        url = settings.CELESTRAK_BASE_URL
        params = {"CATNR": norad_id, "FORMAT": "TLE"}
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return TLEService._parse_tle_text(response.text, norad_id)
        except httpx.TimeoutException:
            logger.warning("CelesTrak timeout for NORAD %s", norad_id)
        except httpx.HTTPStatusError as e:
            logger.warning("CelesTrak HTTP %d for NORAD %s", e.response.status_code, norad_id)
        except Exception as e:
            logger.warning("CelesTrak fetch error for NORAD %s: %s", norad_id, e)
        return None

    @staticmethod
    def _parse_tle_text(text: str, norad_id: str) -> Optional[dict]:
        """Parse raw TLE text response into structured dict."""
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if len(lines) < 3:
            logger.warning("Invalid TLE response for NORAD %s (got %d lines)", norad_id, len(lines))
            return None
        return {"name": lines[0], "line1": lines[1], "line2": lines[2]}
