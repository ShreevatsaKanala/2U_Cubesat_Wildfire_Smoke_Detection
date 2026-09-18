"""
Resource Manager for CubeSat Digital Twin — Phase 5W.

Bounded collections, memory monitoring, and graceful degradation.
"""
import collections
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ── Bounded Collections ──────────────────────────────────────────────


class BoundedList:
    """Max-size list that drops the oldest items when full."""

    def __init__(self, max_size: int, name: str = "BoundedList"):
        self._max_size = max_size
        self._name = name
        self._items: collections.deque = collections.deque(maxlen=max_size)
        self._dropped_count = 0

    def append(self, item: Any) -> None:
        if len(self._items) == self._max_size:
            self._dropped_count += 1
            if self._dropped_count % 50 == 1:
                logger.warning(
                    "%s reached max size %d — %d items dropped total",
                    self._name, self._max_size, self._dropped_count,
                )
        self._items.append(item)

    def get_recent(self, limit: int = 10) -> list:
        return list(reversed(list(self._items)[-limit:]))

    def get_all(self) -> list:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    @property
    def dropped_count(self) -> int:
        return self._dropped_count


class BoundedDict:
    """Max-size dict with LRU eviction when full."""

    def __init__(self, max_size: int, name: str = "BoundedDict"):
        self._max_size = max_size
        self._name = name
        self._items: dict[str, tuple[Any, float]] = {}  # key -> (value, last_access)
        self._dropped_count = 0
        self._lock = threading.Lock()

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            now = time.monotonic()
            if key in self._items:
                self._items[key] = (value, now)
                return
            if len(self._items) >= self._max_size:
                self._evict_oldest()
            self._items[key] = (value, now)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return default
            self._items[key] = (entry[0], time.monotonic())
            return entry[0]

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._items

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def _evict_oldest(self) -> None:
        if not self._items:
            return
        oldest_key = min(self._items, key=lambda k: self._items[k][1])
        del self._items[oldest_key]
        self._dropped_count += 1
        if self._dropped_count % 20 == 1:
            logger.warning(
                "%s evicted key '%s' (max %d) — %d evictions total",
                self._name, oldest_key, self._max_size, self._dropped_count,
            )

    def keys(self):
        with self._lock:
            return list(self._items.keys())

    def items_view(self):
        with self._lock:
            return {k: v[0] for k, v in self._items.items()}

    @property
    def dropped_count(self) -> int:
        return self._dropped_count


# ── Memory Monitor ───────────────────────────────────────────────────


class ResourceMonitor:
    """Lightweight memory and queue-size tracking."""

    def __init__(self):
        self._trackers: Dict[str, Callable[[], int]] = {}
        self._counters: Dict[str, int] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._memory_samples: list[tuple[float, float]] = []
        self._last_sample_time = 0.0

    def register_queue(self, name: str, getter: Callable[[], int]) -> None:
        self._trackers[name] = getter

    def increment_counter(self, name: str, amount: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + amount

    def decrement_counter(self, name: str, amount: int = 1) -> None:
        self._counters[name] = max(0, self._counters.get(name, 0) - amount)

    def set_cache_timestamp(self, cache_name: str) -> None:
        self._cache_timestamps[cache_name] = datetime.now(timezone.utc)

    def get_cache_age_minutes(self, cache_name: str) -> Optional[float]:
        ts = self._cache_timestamps.get(cache_name)
        if ts is None:
            return None
        return (datetime.now(timezone.utc) - ts).total_seconds() / 60.0

    def sample_memory(self) -> float:
        now = time.monotonic()
        if now - self._last_sample_time < 2.0:
            return self._memory_samples[-1][1] if self._memory_samples else 0.0
        self._last_sample_time = now
        try:
            import psutil
            process = psutil.Process()
            mem_mb = process.memory_info().rss / (1024 * 1024)
        except (ImportError, Exception):
            try:
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF)
                mem_mb = usage.ru_maxrss / 1024
            except (ImportError, Exception):
                mem_mb = 0.0
        self._memory_samples.append((now, mem_mb))
        if len(self._memory_samples) > 60:
            self._memory_samples = self._memory_samples[-60:]
        return mem_mb

    def get_stats(self) -> dict:
        queues = {}
        for name, getter in self._trackers.items():
            try:
                queues[name] = getter()
            except Exception:
                queues[name] = -1

        return {
            "memory_mb": round(self.sample_memory(), 1),
            "memory_samples": len(self._memory_samples),
            "queue_sizes": queues,
            "counters": dict(self._counters),
            "cache_ages_minutes": {
                k: round(self.get_cache_age_minutes(k), 1) if v is not None else None
                for k, v in self._cache_timestamps.items()
            },
        }


# ── Cache Entry for TTL-based cleanup ────────────────────────────────


class TTLCache:
    """Simple TTL-based cache with periodic cleanup."""

    def __init__(self, max_age_minutes: float, name: str = "TTLCache"):
        self._max_age = timedelta(minutes=max_age_minutes)
        self._name = name
        self._entries: dict[str, tuple[Any, datetime]] = {}
        self._evicted_count = 0

    def put(self, key: str, value: Any) -> None:
        self._entries[key] = (value, datetime.now(timezone.utc))

    def get(self, key: str) -> Optional[Any]:
        entry = self._entries.get(key)
        if entry is None:
            return None
        value, ts = entry
        if datetime.now(timezone.utc) - ts > self._max_age:
            del self._entries[key]
            self._evicted_count += 1
            return None
        return value

    def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired = [k for k, (_, ts) in self._entries.items() if now - ts > self._max_age]
        for k in expired:
            del self._entries[k]
            self._evicted_count += 1
        if expired:
            logger.info(
                "%s cleanup: %d expired entries removed (%d total evictions)",
                self._name, len(expired), self._evicted_count,
            )
        return len(expired)

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, key: str) -> bool:
        if key not in self._entries:
            return False
        _, ts = self._entries[key]
        if datetime.now(timezone.utc) - ts > self._max_age:
            del self._entries[key]
            return False
        return True

    @property
    def evicted_count(self) -> int:
        return self._evicted_count

    def size(self) -> int:
        return len(self._entries)


# ── Graceful Degradation ─────────────────────────────────────────────


class DegradationState:
    """Tracks whether to reduce non-critical work under memory pressure."""

    def __init__(self, memory_warning_mb: float = 500, memory_critical_mb: float = 800):
        self._warning_mb = memory_warning_mb
        self._critical_mb = memory_critical_mb
        self._pressure = "normal"

    def update(self, memory_mb: float) -> str:
        if memory_mb >= self._critical_mb:
            self._pressure = "critical"
        elif memory_mb >= self._warning_mb:
            self._pressure = "warning"
        else:
            self._pressure = "normal"
        return self._pressure

    @property
    def is_normal(self) -> bool:
        return self._pressure == "normal"

    @property
    def is_warning(self) -> bool:
        return self._pressure == "warning"

    @property
    def is_critical(self) -> bool:
        return self._pressure == "critical"

    @property
    def pressure(self) -> str:
        return self._pressure

    def should_reduce_telemetry(self) -> bool:
        return self._pressure != "normal"

    def should_skip_noncritical_persistence(self) -> bool:
        return self._pressure == "critical"


# ── Cleanup Scheduler ────────────────────────────────────────────────


class CleanupScheduler:
    """Runs periodic cleanup of TTL caches in a background thread."""

    def __init__(self, interval_seconds: float = 300):
        self._interval = interval_seconds
        self._caches: list[TTLCache] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register(self, cache: TTLCache) -> None:
        self._caches.append(cache)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="cache-cleanup")
        self._thread.start()
        logger.info("CleanupScheduler started (interval=%ds)", self._interval)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("CleanupScheduler stopped")

    def _run(self) -> None:
        while self._running:
            time.sleep(self._interval)
            for cache in self._caches:
                try:
                    cache.cleanup_expired()
                except Exception as e:
                    logger.error("Cache cleanup failed: %s", e)


# ── Singleton resource monitor ───────────────────────────────────────

resource_monitor = ResourceMonitor()
degradation = DegradationState()
cleanup_scheduler = CleanupScheduler()
