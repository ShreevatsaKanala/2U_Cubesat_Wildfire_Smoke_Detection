from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter()

@router.get("/api/v1/observations")
async def list_observations(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    priority: Optional[str] = None,
    min_confidence: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    from app.main import engine
    obs_list = engine.observation_service.get_all(limit=limit + offset)
    result = obs_list[offset:offset + limit]
    
    if priority:
        result = [o for o in result if o.priority == priority]
    if min_confidence is not None:
        result = [o for o in result if o.confidence is not None and o.confidence >= min_confidence]
    
    return {
        "observations": [o.model_dump(mode="json") for o in result],
        "total": len(engine.observation_service.observations),
        "limit": limit,
        "offset": offset,
    }

@router.get("/api/v1/observations/{observation_id}")
async def get_observation(observation_id: str):
    from app.main import engine
    obs = engine.observation_service.get_by_id(observation_id)
    if obs is None:
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs.model_dump(mode="json")
