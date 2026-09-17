from fastapi import APIRouter
router = APIRouter()

@router.get("/api/v1/ground-station/status")
async def get_ground_station_status():
    from app.main import engine
    return engine.get_ground_pass()

@router.get("/api/v1/ground-station/config")
async def get_ground_station_config():
    from app.main import engine
    return engine.ground_station.model_dump(mode="json")
