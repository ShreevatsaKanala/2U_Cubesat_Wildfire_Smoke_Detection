from __future__ import annotations

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 1800  # 30 minutes


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl

    def is_valid(self) -> bool:
        return time.monotonic() < self.expires_at


class SentinelCache:
    """In-memory TTL cache for Sentinel metadata and images."""

    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._metadata: dict[str, _CacheEntry] = {}
        self._images: dict[str, _CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._ttl = ttl_seconds

    def _evict_expired(self, store: dict[str, _CacheEntry]) -> None:
        expired = [k for k, v in store.items() if not v.is_valid()]
        for k in expired:
            del store[k]

    @staticmethod
    def _make_key(*parts: Any) -> str:
        return "|".join(str(p) for p in parts)

    # -- metadata ----------------------------------------------------------

    def get_metadata(self, key_parts: tuple) -> Optional[dict]:
        key = self._make_key(*key_parts)
        entry = self._metadata.get(key)
        if entry is not None and entry.is_valid():
            self._hits += 1
            return entry.value
        if entry is not None:
            del self._metadata[key]
        self._misses += 1
        return None

    def set_metadata(self, key_parts: tuple, value: dict) -> None:
        self._evict_expired(self._metadata)
        key = self._make_key(*key_parts)
        self._metadata[key] = _CacheEntry(value, self._ttl)

    # -- images ------------------------------------------------------------

    def get_image(self, key_parts: tuple) -> Optional[bytes]:
        key = self._make_key(*key_parts)
        entry = self._images.get(key)
        if entry is not None and entry.is_valid():
            self._hits += 1
            return entry.value
        if entry is not None:
            del self._images[key]
        self._misses += 1
        return None

    def set_image(self, key_parts: tuple, value: bytes) -> None:
        self._evict_expired(self._images)
        key = self._make_key(*key_parts)
        self._images[key] = _CacheEntry(value, self._ttl)

    # -- stats -------------------------------------------------------------

    def get_stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "metadata_entries": len(self._metadata),
            "image_entries": len(self._images),
            "ttl_seconds": self._ttl,
        }
