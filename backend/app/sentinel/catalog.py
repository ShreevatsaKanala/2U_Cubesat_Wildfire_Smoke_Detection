from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx

from app.sentinel.schemas import SentinelScene

logger = logging.getLogger(__name__)

CATALOG_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/search"


class SentinelCatalog:
    """Search the Sentinel Hub STAC catalogue for scenes."""

    async def search_scenes(
        self,
        bbox: list[float],
        datetime_range: str,
        max_cloud_cover: float = 30.0,
        max_results: int = 5,
    ) -> list[SentinelScene]:
        """
        Parameters
        ----------
        bbox : [west, south, east, north]
        datetime_range : e.g. "2024-01-01T00:00:00Z/2024-01-31T23:59:59Z"
        max_cloud_cover : inclusive upper bound (0-100)
        max_results : cap on returned scenes
        """
        body: dict = {
            "collections": ["SENTINEL-2"],
            "bbox": bbox,
            "datetime": datetime_range,
            "limit": max_results,
            "filter-lang": "cql2-json",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "op": "<=",
                        "args": [
                            {"property": "eo:cloud_cover"},
                            max_cloud_cover,
                        ],
                    },
                    {
                        "op": "=",
                        "args": [
                            {"property": "processing:level"},
                            "S2MSI2A",
                        ],
                    },
                ],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(CATALOG_URL, json=body)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.warning("Sentinel catalogue search timed out")
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning("Sentinel catalogue HTTP error: %s", exc.response.status_code)
            return []
        except Exception as exc:
            logger.warning("Sentinel catalogue error: %s", exc)
            return []

        scenes: list[SentinelScene] = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            scene_bbox = feature.get("bbox", [0.0, 0.0, 0.0, 0.0])
            scene_id = feature.get("id", "")
            product_id = props.get("s2:mgran_id", scene_id)
            dt_str = props.get("datetime", "")
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            scenes.append(
                SentinelScene(
                    scene_id=scene_id,
                    product_id=product_id,
                    datetime=dt,
                    cloud_cover=float(props.get("eo:cloud_cover", 100.0)),
                    bbox=scene_bbox,
                    geometry=geom,
                    data_coverage=float(props.get("s2:datacoverage", 0.0)),
                    platform="sentinel-2",
                )
            )

        scenes.sort(key=lambda s: (s.cloud_cover, s.datetime), reverse=False)
        return scenes[:max_results]
