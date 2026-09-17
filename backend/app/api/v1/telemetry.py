from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/telemetry/latest")
async def get_latest_telemetry():
    from app.main import engine, telemetry_service
    packet = telemetry_service.get_latest()
    if packet is None:
        packet = engine.get_latest_telemetry()
    return packet.model_dump(mode="json")


@router.get("/api/v1/telemetry/history")
async def get_telemetry_history(limit: int = 100):
    from app.main import telemetry_service
    history = telemetry_service.get_history(limit)
    return [p.model_dump(mode="json") for p in history]
