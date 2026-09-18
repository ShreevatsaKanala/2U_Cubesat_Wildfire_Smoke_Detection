from fastapi import APIRouter, Query, HTTPException

router = APIRouter()

_correlation_service = None


def _get_correlation_service():
    global _correlation_service
    if _correlation_service is None:
        from app.services.fire_correlation import FireCorrelationService
        _correlation_service = FireCorrelationService()
    return _correlation_service


@router.get("/api/v1/correlation/status")
async def correlation_status():
    return _get_correlation_service().get_status()


@router.post("/api/v1/correlation/analyze/{observation_id}")
async def analyze_observation(
    observation_id: str,
    radius_km: float = Query(50.0, description="Search radius in km"),
):
    from app.main import engine
    obs = engine.observation_service.get_by_id(observation_id)
    if obs is None:
        raise HTTPException(status_code=404, detail="Observation not found")

    service = _get_correlation_service()
    service.observation_service = engine.observation_service
    result = await service.apply_correlation_to_observation(obs, radius_km)

    return {
        "observation_id": observation_id,
        "correlation": result.fire_correlation_details if hasattr(result, "fire_correlation_details") else result,
        "updated_priority": getattr(result, "priority", None),
    }
