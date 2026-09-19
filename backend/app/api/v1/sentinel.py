from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()

VALID_PRODUCTS = {"true_color", "ndvi", "false_color"}


@router.get("/api/v1/sentinel/status")
async def sentinel_status():
    from app.sentinel import sentinel_client
    return sentinel_client.get_status().model_dump()


class SentinelObserveRequest(BaseModel):
    observation_id: str
    latitude: float
    longitude: float
    datetime: str = ""


@router.post("/api/v1/sentinel/observe")
async def sentinel_observe(req: SentinelObserveRequest):
    from app.sentinel import sentinel_client
    from app.core.config import settings

    if not settings.COPERNICUS_ENABLED:
        return {
            "observation_id": req.observation_id,
            "available": False,
            "error": "Copernicus integration is disabled (COPERNICUS_ENABLED=false)",
        }

    result = await sentinel_client.observe(
        observation_id=req.observation_id,
        lat=req.latitude,
        lon=req.longitude,
        datetime_str=req.datetime,
        metadata_only=True,
    )
    return result.model_dump()


class SentinelImageRequest(BaseModel):
    latitude: float
    longitude: float
    datetime: str = ""


@router.post("/api/v1/sentinel/observation/{observation_id}/image/{product}")
async def sentinel_observation_image(
    observation_id: str,
    product: str,
    req: SentinelImageRequest,
):
    from app.sentinel import sentinel_client
    from app.core.config import settings

    if not settings.COPERNICUS_ENABLED:
        raise HTTPException(status_code=503, detail="Copernicus integration is disabled")

    if product not in VALID_PRODUCTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid product '{product}'. Must be one of: {', '.join(sorted(VALID_PRODUCTS))}",
        )

    image_b64 = await sentinel_client.get_image(
        observation_id=observation_id,
        product=product,
        lat=req.latitude,
        lon=req.longitude,
        datetime_str=req.datetime,
    )

    if not image_b64:
        raise HTTPException(status_code=404, detail="Image not available")

    import base64
    image_bytes = base64.b64decode(image_b64)
    return Response(content=image_bytes, media_type="image/png")


@router.get("/api/v1/sentinel/observation/{observation_id}")
async def sentinel_observation_detail(observation_id: str):
    from app.sentinel import sentinel_client

    status = sentinel_client.get_status()
    if not status.enabled:
        raise HTTPException(
            status_code=503,
            detail="Copernicus integration is disabled",
        )

    return {
        "observation_id": observation_id,
        "service": "Copernicus Sentinel-2 L2A",
        "available": status.authenticated,
        "current_scene": status.current_scene,
    }
