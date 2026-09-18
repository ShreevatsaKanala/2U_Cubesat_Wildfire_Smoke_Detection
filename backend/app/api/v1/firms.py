from fastapi import APIRouter, Query, HTTPException

router = APIRouter()

_firms_adapter = None


def _get_firms():
    global _firms_adapter
    if _firms_adapter is None:
        from app.core.config import settings
        from app.adapters.firms import FIRMSAdapter
        _firms_adapter = FIRMSAdapter(api_key=settings.NASA_FIRMS_MAP_KEY)
    return _firms_adapter


@router.get("/api/firms/status")
async def firms_status():
    return _get_firms().get_status()


@router.get("/api/firms/detections")
async def firms_detections(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: float = Query(50.0, description="Search radius in km"),
    days: int = Query(1, ge=1, le=10),
):
    detections = await _get_firms().get_detections_near_point(lat, lon, radius, days)
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": radius,
        "detections": detections,
        "count": len(detections),
    }
