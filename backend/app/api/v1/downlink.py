from fastapi import APIRouter
router = APIRouter()

@router.get("/api/v1/downlink/status")
async def get_downlink_status():
    from app.main import engine
    return engine.downlink_queue.model_dump(mode="json")
