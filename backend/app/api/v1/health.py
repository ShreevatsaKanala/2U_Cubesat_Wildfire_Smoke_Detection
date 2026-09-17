from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/health")
async def health_check():
    from app.main import engine
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "simulation_running": engine.running,
    }
