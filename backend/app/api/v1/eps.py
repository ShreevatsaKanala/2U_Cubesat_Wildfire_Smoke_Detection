from fastapi import APIRouter
from app.services.eps_model import EPSModel

router = APIRouter()
_eps_model: EPSModel | None = None


def get_eps_model() -> EPSModel:
    global _eps_model
    if _eps_model is None:
        _eps_model = EPSModel()
    return _eps_model


@router.get("/api/eps/status")
async def get_eps_status():
    return get_eps_model().get_status()


@router.post("/api/eps/reset")
async def reset_eps():
    get_eps_model().reset()
    return {"status": "ok"}
