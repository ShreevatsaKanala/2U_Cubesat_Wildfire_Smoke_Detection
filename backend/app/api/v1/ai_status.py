"""AI status endpoint."""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
async def get_ai_status():
    model = (
        settings.OPENROUTER_MODEL
        if settings.AI_PROVIDER == "openrouter"
        else settings.GROQ_MODEL
    )
    return {
        "mode": settings.AI_MODE,
        "provider": settings.AI_PROVIDER,
        "model": model,
        "failover_enabled": settings.AI_FAILOVER_ENABLED,
        "timeout_seconds": settings.AI_TIMEOUT_SECONDS,
        "max_requests_per_minute": settings.AI_MAX_REQUESTS_PER_MINUTE,
        "status": "available" if settings.AI_MODE == "live" else "mock",
    }
