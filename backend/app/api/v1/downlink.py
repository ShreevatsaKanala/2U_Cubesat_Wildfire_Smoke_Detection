from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
router = APIRouter()


class PrioritizeRequest(BaseModel):
    observation_id: str
    priority: str


@router.get("/api/v1/downlink/status")
async def get_downlink_status():
    from app.main import engine
    service = getattr(engine, '_downlink_service', None)
    if service:
        return service.get_status()
    return engine.downlink_queue.model_dump(mode="json")


@router.get("/api/v1/downlink/queue")
async def get_downlink_queue():
    from app.main import engine
    service = getattr(engine, '_downlink_service', None)
    if service:
        return service.get_queue_summary()
    queue = engine.downlink_queue
    return {
        "queued": [{"id": i.observation_id, "priority": i.priority, "size_bytes": i.image_size_bytes}
                   for i in queue.get_pending_items()],
        "transferring": [],
        "completed": [{"id": i.observation_id, "priority": i.priority, "size_bytes": i.image_size_bytes}
                      for i in queue.items if i.status == "transmitted"],
    }


@router.get("/api/v1/downlink/transfer/{observation_id}")
async def get_transfer_detail(observation_id: str):
    from app.main import engine
    service = getattr(engine, '_downlink_service', None)
    if service:
        detail = service.get_transfer_status(observation_id)
        if detail:
            return detail
    raise HTTPException(status_code=404, detail=f"Transfer {observation_id} not found")


@router.post("/api/v1/downlink/prioritize")
async def prioritize_observation(req: PrioritizeRequest):
    from app.main import engine
    service = getattr(engine, '_downlink_service', None)
    if service:
        success = service.prioritize_item(req.observation_id, req.priority)
        if success:
            return {"status": "ok", "observation_id": req.observation_id, "new_priority": req.priority}
    raise HTTPException(status_code=404, detail=f"Observation {req.observation_id} not found or not reprioritizable")


@router.get("/api/v1/downlink/schedule")
async def get_transfer_schedule():
    from app.main import engine
    scheduler = getattr(engine, '_downlink_scheduler', None)
    if scheduler:
        state = engine.get_state()
        return scheduler.compute_transfer_schedule(
            state.latitude, state.longitude, state.altitude_km,
            state.power.battery_soc, engine.sim_time
        )
    return {"error": "Scheduler not initialized"}
