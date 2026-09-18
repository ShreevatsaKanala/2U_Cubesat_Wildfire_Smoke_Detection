from fastapi import APIRouter, Body
from app.services.fault_recovery import FaultRecoveryService, RecoveryAction, RecoveryConfig

router = APIRouter()
_recovery_service: FaultRecoveryService | None = None


def get_recovery_service() -> FaultRecoveryService:
    global _recovery_service
    if _recovery_service is None:
        _recovery_service = FaultRecoveryService()
    return _recovery_service


@router.get("/api/v1/recovery/status")
async def get_recovery_status():
    return get_recovery_service().get_status()


@router.post("/api/v1/recovery/trigger")
async def trigger_recovery(payload: dict = Body(...)):
    action_str = payload.get("action", "")
    try:
        action = RecoveryAction(action_str)
    except ValueError:
        return {"error": f"Invalid action: {action_str}. Valid: {[a.value for a in RecoveryAction]}"}
    svc = get_recovery_service()
    evt = svc.manual_trigger(action)
    return {"status": "ok", "event": evt.model_dump()}


@router.post("/api/v1/recovery/reset")
async def reset_recovery():
    get_recovery_service().reset()
    return {"status": "ok"}
