"""Mock vision provider for offline/testing with deterministic results."""

import hashlib
import random

from app.ai.base import VisionInferenceProvider
from app.ai.schemas import VisionInferenceResult


class MockVisionProvider(VisionInferenceProvider):
    def analyze_image(self, image_base64: str, metadata: dict) -> VisionInferenceResult:
        img_hash = hashlib.md5(image_base64[:256].encode()).hexdigest()
        first_char = img_hash[0]
        hash_value = int(first_char, 16)
        second_char = img_hash[1]
        second_value = int(second_char, 16)

        smoke_base = hash_value / 15.0
        second_frac = second_value / 15.0
        smoke_score = smoke_base * 0.7 + second_frac * 0.3

        if hash_value >= 10:
            smoke_score = max(0.6, smoke_score)

        smoke_score = round(smoke_score, 4)
        smoke_present = smoke_score >= 0.5

        if smoke_score > 0.8:
            confidence = "high"
        elif smoke_score > 0.5:
            confidence = "medium"
        else:
            confidence = "low"

        visual_evidence = []
        if smoke_score > 0.6:
            visual_evidence = ["hazy atmospheric column detected", "reduced surface visibility"]
        elif smoke_score > 0.3:
            visual_evidence = ["possible thin haze"]

        alternatives = []
        if smoke_score > 0.4 and smoke_score < 0.7:
            alternatives = ["cloud cover", "fog", "atmospheric scattering"]

        scene = f"Earth observation scene at ({metadata.get('latitude', 0):.2f}, {metadata.get('longitude', 0):.2f})"

        return VisionInferenceResult(
            smoke_present=smoke_present,
            smoke_score=smoke_score,
            confidence=confidence,
            visual_evidence=visual_evidence,
            alternative_explanations=alternatives,
            scene_description=scene,
            ai_provider="mock",
            ai_model="mock-vision-v1.0",
            ai_latency_ms=round(random.uniform(10.0, 50.0), 2),
            ai_status="success",
        )

    def is_available(self) -> bool:
        return True

    def get_provider_info(self) -> dict:
        return {"provider": "mock", "model": "mock-vision-v1.0", "status": "available"}
