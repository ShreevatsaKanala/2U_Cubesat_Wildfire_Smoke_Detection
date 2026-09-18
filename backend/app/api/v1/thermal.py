from fastapi import APIRouter
from app.services.thermal_model import ThermalModel

router = APIRouter()
_thermal_model: ThermalModel | None = None


def get_thermal_model() -> ThermalModel:
    global _thermal_model
    if _thermal_model is None:
        _thermal_model = ThermalModel()
    return _thermal_model


@router.get("/api/thermal/status")
async def get_thermal_status():
    return get_thermal_model().get_status()


@router.post("/api/thermal/reset")
async def reset_thermal():
    get_thermal_model().reset()
    return {"status": "ok"}
