from fastapi import APIRouter, Query
router = APIRouter()

@router.get("/api/v1/events")
async def get_events(limit: int = Query(50, ge=1, le=500)):
    from app.main import engine
    events = engine.event_log.get_recent(limit)
    return [e.model_dump(mode="json") for e in events]
