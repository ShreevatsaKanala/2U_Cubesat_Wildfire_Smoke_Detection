from fastapi import APIRouter
router = APIRouter()

@router.get("/api/v1/spacecraft/state")
async def get_spacecraft_state():
    from app.main import engine
    return engine.get_state().model_dump(mode="json")

@router.get("/api/v1/spacecraft/health")
async def get_health():
    from app.main import engine
    h = engine._state.health
    return {
        "overall": h.overall_health().value,
        "eps": h.eps.value,
        "obc": h.obc.value,
        "camera": h.camera.value,
        "adcs": h.adcs.value,
        "communications": h.communications.value,
        "navigation": h.navigation.value,
        "thermal": h.thermal.value,
        "ml": h.ml.value,
    }

@router.get("/api/v1/spacecraft/power")
async def get_power():
    from app.main import engine
    return engine._state.power.model_dump(mode="json")

@router.get("/api/v1/spacecraft/thermal")
async def get_thermal():
    from app.main import engine
    return engine._state.thermal.model_dump(mode="json")

@router.get("/api/v1/spacecraft/attitude")
async def get_attitude():
    from app.main import engine
    return engine._state.attitude.model_dump(mode="json")
