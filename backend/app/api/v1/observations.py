from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("/api/v1/observations")
async def list_observations(limit: int = Query(20)):
    from app.main import engine
    obs_list = engine.observation_service.get_all(limit=limit)
    return [o.model_dump(mode="json") for o in obs_list]


@router.get("/api/v1/observations/{observation_id}")
async def get_observation(observation_id: str):
    from app.main import engine
    obs = engine.observation_service.get_by_id(observation_id)
    if obs is None:
        return {"error": "Observation not found", "observation_id": observation_id}
    return obs.model_dump(mode="json")
