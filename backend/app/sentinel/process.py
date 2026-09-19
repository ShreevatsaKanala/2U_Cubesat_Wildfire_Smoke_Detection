from __future__ import annotations

import base64
import logging

import httpx

logger = logging.getLogger(__name__)

PROCESS_URL = "https://sh.dataspace.copernicus.eu/process/v1"

TRUE_COLOR_SCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{bands: ["B04", "B03", "B02", "dataMask"], units: "DN"}],
    output: {id: "default", bands: 3, sampleType: "AUTO"}
  };
}
function evaluatePixel(sample) {
  let r = 2.5 * sample.B04;
  let g = 2.5 * sample.B03;
  let b = 2.5 * sample.B02;
  return {default: [clamp(r, 0, 1), clamp(g, 0, 1), clamp(b, 0, 1)]};
}
"""

NDVI_SCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{bands: ["B04", "B08", "dataMask"], units: "DN"}],
    output: {id: "default", bands: 3, sampleType: "AUTO"}
  };
}
function evaluatePixel(sample) {
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
  let v = clamp((ndvi + 0.2) / 1.4, 0, 1);
  if (ndvi < 0) return {default: [0.75, 0.75, 0.75]};
  if (ndvi < 0.2) return {default: [0.85, 0.65, 0.13]};
  if (ndvi < 0.4) return {default: [0.67, 0.85, 0.31]};
  if (ndvi < 0.6) return {default: [0.0, 0.61, 0.45]};
  return {default: [0.0, 0.41, 0.14]};
}
"""

FALSE_COLOR_SCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{bands: ["B08", "B04", "B03", "dataMask"], units: "DN"}],
    output: {id: "default", bands: 3, sampleType: "AUTO"}
  };
}
function evaluatePixel(sample) {
  let r = 2.5 * sample.B08;
  let g = 2.5 * sample.B04;
  let b = 2.5 * sample.B03;
  return {default: [clamp(r, 0, 1), clamp(g, 0, 1), clamp(b, 0, 1)]};
}
"""


class SentinelProcess:
    """Wrapper around Sentinel Hub Process API for image retrieval."""

    def _build_payload(
        self,
        evalscript: str,
        bbox: list[float],
        width: int,
        height: int,
    ) -> dict:
        return {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "maxCloudCoverage": 100,
                        },
                    }
                ],
            },
            "output": {
                "width": width,
                "height": height,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
            },
            "evalscript": evalscript,
        }

    async def _fetch_image(
        self,
        auth_token: str,
        evalscript: str,
        bbox: list[float],
        width: int,
        height: int,
    ) -> bytes:
        payload = self._build_payload(evalscript, bbox, width, height)
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(PROCESS_URL, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.content
        except httpx.TimeoutException:
            logger.warning("Sentinel Process API timed out")
            return b""
        except httpx.HTTPStatusError as exc:
            logger.warning("Sentinel Process API HTTP error: %s", exc.response.status_code)
            return b""
        except Exception as exc:
            logger.warning("Sentinel Process API error: %s", exc)
            return b""

    async def get_true_color(
        self, auth_token: str, bbox: list[float], width: int = 512, height: int = 512
    ) -> bytes:
        return await self._fetch_image(auth_token, TRUE_COLOR_SCRIPT, bbox, width, height)

    async def get_ndvi(
        self, auth_token: str, bbox: list[float], width: int = 512, height: int = 512
    ) -> bytes:
        return await self._fetch_image(auth_token, NDVI_SCRIPT, bbox, width, height)

    async def get_false_color(
        self, auth_token: str, bbox: list[float], width: int = 512, height: int = 512
    ) -> bytes:
        return await self._fetch_image(auth_token, FALSE_COLOR_SCRIPT, bbox, width, height)
