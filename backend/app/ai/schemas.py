"""Pydantic schemas for AI vision inference."""

from typing import Optional
from pydantic import BaseModel


class VisionRequest(BaseModel):
    image_base64: str
    image_width: int
    image_height: int
    observation_id: str
    latitude: float
    longitude: float
    altitude_km: float
    timestamp: str


class VisionInferenceResult(BaseModel):
    smoke_present: bool = False
    smoke_score: float = 0.0
    confidence: str = "low"
    visual_evidence: list[str] = []
    alternative_explanations: list[str] = []
    scene_description: str = ""
    ai_provider: str = ""
    ai_model: str = ""
    ai_latency_ms: float = 0.0
    ai_status: str = "success"
    ai_error: Optional[str] = None
