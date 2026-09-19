from app.sentinel.auth import SentinelAuth
from app.sentinel.client import SentinelClient
from app.sentinel.catalog import SentinelCatalog
from app.sentinel.process import SentinelProcess
from app.sentinel.cache import SentinelCache
from app.sentinel.schemas import SentinelScene, SentinelObservationResult, SentinelStatus

sentinel_client = SentinelClient()

__all__ = [
    "SentinelAuth", "SentinelClient", "SentinelCatalog", "SentinelProcess",
    "SentinelCache", "SentinelScene", "SentinelObservationResult", "SentinelStatus",
    "sentinel_client",
]
