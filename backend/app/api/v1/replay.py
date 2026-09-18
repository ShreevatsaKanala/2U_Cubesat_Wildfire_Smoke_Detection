"""Mission replay API endpoints — session management and playback control."""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.replay_service import replay_service

router = APIRouter()


@router.post("/api/v1/replay/start")
async def replay_start(config: Optional[dict] = None):
    session = await replay_service.start_session(config)
    return {
        "session_id": session.session_id,
        "start_time": session.start_time,
        "config_snapshot": session.config_snapshot,
    }


@router.post("/api/v1/replay/stop")
async def replay_stop():
    session = await replay_service.stop_session()
    if not session:
        return {"message": "No active session"}
    return {
        "session_id": session.session_id,
        "start_time": session.start_time,
        "end_time": session.end_time,
    }


@router.get("/api/v1/replay/sessions")
async def replay_sessions():
    sessions = await replay_service.list_sessions()
    return {"sessions": sessions}


@router.get("/api/v1/replay/sessions/{session_id}")
async def replay_session_detail(session_id: str):
    session = await replay_service.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    return session


@router.get("/api/v1/replay/sessions/{session_id}/telemetry")
async def replay_session_telemetry(session_id: str, limit: int = Query(1000, ge=1, le=5000)):
    data = await replay_service.get_session_telemetry(session_id, limit=limit)
    return {"session_id": session_id, "telemetry": data, "count": len(data)}


@router.get("/api/v1/replay/sessions/{session_id}/observations")
async def replay_session_observations(session_id: str, limit: int = Query(1000, ge=1, le=5000)):
    data = await replay_service.get_session_observations(session_id, limit=limit)
    return {"session_id": session_id, "observations": data, "count": len(data)}


@router.get("/api/v1/replay/sessions/{session_id}/events")
async def replay_session_events(session_id: str, limit: int = Query(1000, ge=1, le=5000)):
    data = await replay_service.get_session_events(session_id, limit=limit)
    return {"session_id": session_id, "events": data, "count": len(data)}


@router.post("/api/v1/replay/playback/{session_id}")
async def replay_playback(session_id: str, speed: float = Query(1.0, ge=0.1, le=10.0)):
    return await replay_service.start_playback(session_id, speed=speed)


@router.post("/api/v1/replay/pause")
async def replay_pause():
    return await replay_service.pause()


@router.post("/api/v1/replay/seek")
async def replay_seek(offset: float = Query(..., ge=0.0)):
    return await replay_service.seek(offset)


@router.get("/api/v1/replay/state")
async def replay_state():
    return replay_service.replay_state
