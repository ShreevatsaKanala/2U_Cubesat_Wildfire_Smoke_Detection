from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


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
    )
    return result.model_dump()


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
