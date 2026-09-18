"""TLE status and refresh endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/tle", tags=["tle"])


@router.get("/status")
async def get_tle_status():
    """Return current TLE source, epoch, age, and validity."""
    from app.main import engine
    return engine.tle_service.get_status()


@router.post("/refresh")
async def refresh_tle():
    """Force re-fetch TLE from CelesTrak and update orbit service."""
    from app.main import engine
    status = engine.tle_service.refresh()
    if engine.tle_service.is_valid:
        engine.orbit_service.load_tle(
            engine.tle_service.tle_line1,
            engine.tle_service.tle_line2,
        )
    return status
