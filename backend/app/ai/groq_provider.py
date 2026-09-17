"""Groq vision provider."""

import json
import logging
import time

import httpx

from app.ai.base import VisionInferenceProvider
from app.ai.schemas import VisionInferenceResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a satellite imagery analysis AI. Analyze the provided Earth observation "
    "image for signs of smoke or wildfire. Respond ONLY with valid JSON in the exact "
    "format specified. Do not include any text outside the JSON."
)

USER_PROMPT = (
    "Analyze this Earth observation satellite image for smoke or wildfire indicators.\n\n"
    "Respond with ONLY a JSON object in this exact format:\n"
    "{\n"
    '  "smoke_present": true or false,\n'
    '  "smoke_score": 0.0 to 1.0,\n'
    '  "confidence": "low", "medium", or "high",\n'
    '  "visual_evidence": ["list of observed indicators"],\n'
    '  "alternative_explanations": ["other possible causes"],\n'
    '  "scene_description": "brief description of the scene"\n'
    "}\n\n"
    "Coordinates: lat={lat:.4f}, lon={lon:.4f}, alt={alt:.1f} km"
)

JSON_SCHEMA = {
    "name": "vision_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "smoke_present": {"type": "boolean"},
            "smoke_score": {"type": "number"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "visual_evidence": {"type": "array", "items": {"type": "string"}},
            "alternative_explanations": {"type": "array", "items": {"type": "string"}},
            "scene_description": {"type": "string"},
        },
        "required": [
            "smoke_present", "smoke_score", "confidence",
            "visual_evidence", "alternative_explanations", "scene_description",
        ],
        "additionalProperties": False,
    },
}


class GroqVisionProvider(VisionInferenceProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: int = 30,
        temperature: float = 0,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.base_url = "https://api.groq.com/openai/v1"

    def analyze_image(self, image_base64: str, metadata: dict) -> VisionInferenceResult:
        start = time.monotonic()

        user_msg = USER_PROMPT.format(
            lat=metadata.get("latitude", 0.0),
            lon=metadata.get("longitude", 0.0),
            alt=metadata.get("altitude_km", 500.0),
        )

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "response_format": {"type": "json_schema", "json_schema": JSON_SCHEMA},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_msg},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                            },
                        },
                    ],
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                body = resp.json()
        except httpx.TimeoutException:
            return VisionInferenceResult(
                ai_status="timeout",
                ai_provider="groq",
                ai_model=self.model,
                ai_latency_ms=round((time.monotonic() - start) * 1000, 2),
                ai_error="Request timed out",
            )
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                return VisionInferenceResult(
                    ai_status="error",
                    ai_provider="groq",
                    ai_model=self.model,
                    ai_latency_ms=round((time.monotonic() - start) * 1000, 2),
                    ai_error="Authentication failed - invalid API key",
                )
            if status == 429:
                return VisionInferenceResult(
                    ai_status="rate_limited",
                    ai_provider="groq",
                    ai_model=self.model,
                    ai_latency_ms=round((time.monotonic() - start) * 1000, 2),
                    ai_error="Rate limited by provider",
                )
            return VisionInferenceResult(
                ai_status="error",
                ai_provider="groq",
                ai_model=self.model,
                ai_latency_ms=round((time.monotonic() - start) * 1000, 2),
                ai_error=f"HTTP {status}: {e.response.text[:200]}",
            )
        except Exception as e:
            return VisionInferenceResult(
                ai_status="error",
                ai_provider="groq",
                ai_model=self.model,
                ai_latency_ms=round((time.monotonic() - start) * 1000, 2),
                ai_error=str(e)[:200],
            )

        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            latency = round((time.monotonic() - start) * 1000, 2)
            return VisionInferenceResult(
                smoke_present=bool(parsed.get("smoke_present", False)),
                smoke_score=float(parsed.get("smoke_score", 0.0)),
                confidence=str(parsed.get("confidence", "low")),
                visual_evidence=list(parsed.get("visual_evidence", [])),
                alternative_explanations=list(parsed.get("alternative_explanations", [])),
                scene_description=str(parsed.get("scene_description", "")),
                ai_provider="groq",
                ai_model=self.model,
                ai_latency_ms=latency,
                ai_status="success",
            )
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            return VisionInferenceResult(
                ai_status="error",
                ai_provider="groq",
                ai_model=self.model,
                ai_latency_ms=round((time.monotonic() - start) * 1000, 2),
                ai_error=f"Failed to parse response: {e}",
            )

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_provider_info(self) -> dict:
        return {
            "provider": "groq",
            "model": self.model,
            "status": "available" if self.api_key else "no_api_key",
        }
