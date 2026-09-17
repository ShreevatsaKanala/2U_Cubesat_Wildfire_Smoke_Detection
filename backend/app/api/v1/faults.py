from fastapi import APIRouter, Body
router = APIRouter()

@router.post("/api/v1/faults/inject")
async def inject_fault(faults: dict = Body(...)):
    from app.main import engine
    for key, value in faults.items():
        if hasattr(engine._state.faults, key):
            setattr(engine._state.faults, key, value)
    return {"status": "ok", "faults": engine._state.faults.model_dump(mode="json")}

@router.get("/api/v1/faults")
async def get_faults():
    from app.main import engine
    return engine._state.faults.model_dump(mode="json")

@router.post("/api/v1/faults/clear")
async def clear_faults():
    from app.main import engine
    from app.models.spacecraft import FaultInjection
    engine._state.faults = FaultInjection()
    return {"status": "ok", "faults": engine._state.faults.model_dump(mode="json")}
