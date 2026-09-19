from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.sentinel.auth import SentinelAuth
from app.sentinel.cache import SentinelCache
from app.sentinel.catalog import SentinelCatalog
from app.sentinel.process import SentinelProcess
from app.sentinel.schemas import SentinelObservationResult, SentinelStatus

logger = logging.getLogger(__name__)

AOI_EXTENT = 0.15  # degrees each side


def _make_bbox(lat: float, lon: float) -> list[float]:
    return [
        round(lon - AOI_EXTENT, 6),
        round(lat - AOI_EXTENT, 6),
        round(lon + AOI_EXTENT, 6),
        round(lat + AOI_EXTENT, 6),
    ]


class SentinelClient:
    def __init__(self) -> None:
        self._auth = SentinelAuth()
        self._catalog = SentinelCatalog()
        self._process = SentinelProcess()
        self._cache = SentinelCache()
        self._last_request: str | None = None
        self._last_success: str | None = None
        self._last_error: str | None = None
        self._current_scene: str | None = None

    @staticmethod
    def _parse_datetime_range(datetime_str: str) -> str:
        if "/" in datetime_str:
            return datetime_str
        try:
            dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            dt = datetime.now(timezone.utc)
        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59)
        return f"{start.isoformat()}/{end.isoformat()}"

    async def observe(
        self,
        observation_id: str,
        lat: float,
        lon: float,
        datetime_str: str,
    ) -> SentinelObservationResult:
        self._last_request = datetime.now(timezone.utc).isoformat()

        bbox = _make_bbox(lat, lon)

        # metadata cache lookup
        meta_key = ("meta", tuple(bbox), datetime_str)
        cached_meta = self._cache.get_metadata(meta_key)
        if cached_meta is not None:
            scene_id = cached_meta.get("scene_id", "")
            cloud_cover = cached_meta.get("cloud_cover")
            acquisition_time = cached_meta.get("acquisition_time")
        else:
            dt_range = self._parse_datetime_range(datetime_str)
            scenes = await self._catalog.search_scenes(
                bbox=bbox,
                datetime_range=dt_range,
                max_cloud_cover=50.0,
                max_results=5,
            )
            if not scenes:
                self._last_error = "No scenes found"
                return SentinelObservationResult(
                    observation_id=observation_id,
                    aoi=bbox,
                    error="No matching Sentinel-2 scenes found for this area/time",
                    available=False,
                )
            best = scenes[0]
            scene_id = best.scene_id
            cloud_cover = best.cloud_cover
            acquisition_time = best.datetime.isoformat()
            self._cache.set_metadata(
                meta_key,
                {
                    "scene_id": scene_id,
                    "cloud_cover": cloud_cover,
                    "acquisition_time": acquisition_time,
                },
            )

        self._current_scene = scene_id

        # auth
        token = await self._auth.get_token()
        if not token:
            self._last_error = "Authentication failed"
            return SentinelObservationResult(
                observation_id=observation_id,
                scene_id=scene_id,
                cloud_cover=cloud_cover,
                aoi=bbox,
                error="Could not authenticate with Copernicus Data Space",
                available=False,
            )

        # images
        true_color = await self._fetch_image(token, "true_color", bbox, scene_id)
        ndvi = await self._fetch_image(token, "ndvi", bbox, scene_id)
        false_color = await self._fetch_image(token, "false_color", bbox, scene_id)

        self._last_success = datetime.now(timezone.utc).isoformat()
        self._last_error = None

        return SentinelObservationResult(
            observation_id=observation_id,
            scene_id=scene_id,
            acquisition_time=acquisition_time,
            cloud_cover=cloud_cover,
            aoi=bbox,
            true_color_url=true_color,
            ndvi_url=ndvi,
            false_color_url=false_color,
            metadata={},
            available=True,
        )

    async def _fetch_image(
        self, token: str, product: str, bbox: list[float], scene_id: str
    ) -> str:
        import base64

        img_key = ("img", product, tuple(bbox), scene_id)
        cached = self._cache.get_image(img_key)
        if cached is not None:
            return base64.b64encode(cached).decode()

        fetchers = {
            "true_color": self._process.get_true_color,
            "ndvi": self._process.get_ndvi,
            "false_color": self._process.get_false_color,
        }
        fetcher = fetchers.get(product)
        if fetcher is None:
            return ""

        raw = await fetcher(token, bbox)
        if not raw:
            return ""

        self._cache.set_image(img_key, raw)
        return base64.b64encode(raw).decode()

    def get_status(self) -> SentinelStatus:
        stats = self._cache.get_stats()
        return SentinelStatus(
            enabled=settings.COPERNICUS_ENABLED,
            authenticated=self._auth.is_authenticated(),
            service="Copernicus Sentinel-2 L2A",
            last_request=self._last_request,
            last_success=self._last_success,
            cache_hits=stats["hits"],
            cache_misses=stats["misses"],
            last_error=self._last_error,
            current_scene=self._current_scene,
        )