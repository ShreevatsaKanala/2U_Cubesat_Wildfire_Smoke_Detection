from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/spacecraft/state")
async def get_spacecraft_state():
    from app.main import engine
    state = engine.get_state()
    return state.model_dump(mode="json")
