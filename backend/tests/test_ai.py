"""AI Vision Provider tests for Phase 4."""
import pytest
import base64
import hashlib
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from datetime import datetime, timezone
from io import BytesIO

from app.ai.schemas import VisionInferenceResult, VisionRequest
from app.ai.mock_provider import MockVisionProvider
from app.ai.preprocessing import ImagePreprocessor
from app.ai.service import AIService
from app.core.config import Settings


# --- 1. VisionInferenceResult schema ---

def test_vision_result_schema():
    """VisionInferenceResult has all required fields."""
    result = VisionInferenceResult(
        smoke_present=True,
        smoke_score=0.75,
        confidence="high",
        visual_evidence=["haze detected"],
        alternative_explanations=["cloud cover"],
        scene_description="forest scene",
        ai_provider="mock",
        ai_model="mock-v1",
        ai_latency_ms=42.5,
        ai_status="success",
    )
    assert result.smoke_present is True
    assert result.smoke_score == 0.75
    assert result.confidence == "high"
    assert result.visual_evidence == ["haze detected"]
    assert result.alternative_explanations == ["cloud cover"]
    assert result.scene_description == "forest scene"
    assert result.ai_provider == "mock"
    assert result.ai_model == "mock-v1"
    assert result.ai_latency_ms == 42.5
    assert result.ai_status == "success"


def test_vision_result_default_values():
    """VisionInferenceResult defaults are correct."""
    result = VisionInferenceResult()
    assert result.smoke_present is False
    assert result.smoke_score == 0.0
    assert result.confidence == "low"
    assert result.visual_evidence == []
    assert result.alternative_explanations == []
    assert result.scene_description == ""
    assert result.ai_status == "success"


# --- 2. VisionInferenceResult score range ---

def test_vision_result_score_range():
    """smoke_score in [0, 1]."""
    provider = MockVisionProvider()
    for i in range(50):
        result = provider.analyze_image(f"test_image_{i}.jpg", {"latitude": 35.0, "longitude": -120.0})
        assert 0.0 <= result.smoke_score <= 1.0, f"smoke_score out of range: {result.smoke_score}"


# --- 3. VisionInferenceResult confidence values ---

def test_vision_result_confidence_values():
    """confidence is low/medium/high."""
    provider = MockVisionProvider()
    valid_confidences = {"low", "medium", "high"}
    for i in range(50):
        result = provider.analyze_image(f"test_image_{i}.jpg", {"latitude": 35.0, "longitude": -120.0})
        assert result.confidence in valid_confidences, f"Invalid confidence: {result.confidence}"


# --- 4. MockVisionProvider returns valid result ---

def test_mock_provider_returns_valid_result():
    """MockVisionProvider.analyze_image works."""
    provider = MockVisionProvider()
    result = provider.analyze_image("test.jpg", {"latitude": 35.0, "longitude": -120.0})
    assert isinstance(result, VisionInferenceResult)
    assert result.ai_provider == "mock"
    assert result.ai_model == "mock-vision-v1.0"
    assert result.ai_status == "success"


# --- 5. MockVisionProvider is available ---

def test_mock_provider_is_available():
    """MockVisionProvider.is_available() always True."""
    provider = MockVisionProvider()
    assert provider.is_available() is True


# --- 6. MockVisionProvider deterministic ---

def test_mock_provider_deterministic():
    """Same input gives same output."""
    provider = MockVisionProvider()
    metadata = {"latitude": 35.0, "longitude": -120.0}
    for i in range(20):
        r1 = provider.analyze_image(f"image_{i}.png", metadata)
        r2 = provider.analyze_image(f"image_{i}.png", metadata)
        assert r1.smoke_score == r2.smoke_score, f"Not deterministic for image_{i}.png"
        assert r1.confidence == r2.confidence, f"Not deterministic confidence for image_{i}.png"


# --- 7. ImagePreprocessor resize ---

def test_image_preprocessor_resize():
    """Resizes large images."""
    from PIL import Image
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "large.jpg")
        Image.new("RGB", (2048, 1024), color=(128, 128, 128)).save(img_path)

        preprocessor = ImagePreprocessor(max_dimension=1024)
        result = preprocessor.process(img_path)

        assert result["processed_width"] <= 1024
        assert result["processed_height"] <= 1024


# --- 8. ImagePreprocessor maintains aspect ratio ---

def test_image_preprocessor_maintains_aspect():
    """Aspect ratio preserved."""
    from PIL import Image
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "wide.jpg")
        Image.new("RGB", (2000, 1000), color=(128, 128, 128)).save(img_path)

        preprocessor = ImagePreprocessor(max_dimension=1024)
        result = preprocessor.process(img_path)

        original_ratio = 2000 / 1000
        processed_ratio = result["processed_width"] / result["processed_height"]
        assert abs(original_ratio - processed_ratio) < 0.01


# --- 9. ImagePreprocessor returns base64 ---

def test_image_preprocessor_returns_base64():
    """Output is valid base64."""
    from PIL import Image
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "test.jpg")
        Image.new("RGB", (100, 100), color=(128, 128, 128)).save(img_path)

        preprocessor = ImagePreprocessor()
        result = preprocessor.process(img_path)

        decoded = base64.b64decode(result["image_base64"])
        assert len(decoded) > 0


# --- 10. ImagePreprocessor max size ---

def test_image_preprocessor_max_size():
    """Respects max_size_mb."""
    from PIL import Image
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "test.jpg")
        Image.new("RGB", (100, 100), color=(128, 128, 128)).save(img_path)

        preprocessor = ImagePreprocessor(max_size_mb=0.001)
        result = preprocessor.process(img_path)

        assert result["compressed_size_bytes"] <= 0.001 * 1024 * 1024 + 1024


# --- 11. ImagePreprocessor RGB conversion ---

def test_image_preprocessor_rgb_conversion():
    """Handles RGBA/grayscale."""
    from PIL import Image
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        rgba_path = os.path.join(tmpdir, "rgba.png")
        Image.new("RGBA", (100, 100), color=(128, 128, 128, 255)).save(rgba_path)

        preprocessor = ImagePreprocessor()
        result = preprocessor.process(rgba_path)
        decoded = base64.b64decode(result["image_base64"])
        assert len(decoded) > 0

        gray_path = os.path.join(tmpdir, "gray.jpg")
        Image.new("L", (100, 100), color=128).save(gray_path)
        result = preprocessor.process(gray_path)
        decoded = base64.b64decode(result["image_base64"])
        assert len(decoded) > 0


# --- 12. AIService mock mode ---

def test_ai_service_mock_mode():
    """AIService with mock mode uses MockVisionProvider."""
    config = MagicMock()
    config.AI_MODE = "mock"
    config.AI_PROVIDER = "openrouter"
    config.AI_TIMEOUT_SECONDS = 30
    config.AI_RETRY_COUNT = 2
    config.AI_FAILOVER_ENABLED = True
    config.AI_MAX_REQUESTS_PER_MINUTE = 10
    config.AI_TEMPERATURE = 0.0
    config.AI_IMAGE_MAX_DIMENSION = 1024
    config.AI_MAX_IMAGE_MB = 10.0
    config.OPENROUTER_API_KEY = ""
    config.GROQ_API_KEY = ""
    config.OPENROUTER_MODEL = "test-model"
    config.GROQ_MODEL = "test-model"

    service = AIService(config)
    status = service.get_status()
    assert status["mode"] == "mock"
    assert "mock" in status["providers"]


# --- 13. AIService unavailable when no keys ---

def test_ai_service_unavailable_when_no_keys():
    """Returns unavailable when no API keys."""
    config = MagicMock()
    config.AI_MODE = "live"
    config.AI_PROVIDER = "openrouter"
    config.AI_TIMEOUT_SECONDS = 30
    config.AI_RETRY_COUNT = 2
    config.AI_FAILOVER_ENABLED = True
    config.AI_MAX_REQUESTS_PER_MINUTE = 10
    config.AI_TEMPERATURE = 0.0
    config.AI_IMAGE_MAX_DIMENSION = 1024
    config.AI_MAX_IMAGE_MB = 10.0
    config.OPENROUTER_API_KEY = ""
    config.GROQ_API_KEY = ""
    config.OPENROUTER_MODEL = "test-model"
    config.GROQ_MODEL = "test-model"

    service = AIService(config)
    status = service.get_status()
    assert status["providers"] == {}


# --- 14. AIService rate limit ---

def test_ai_service_rate_limit():
    """Rate limiting works."""
    from PIL import Image
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "test.jpg")
        Image.new("RGB", (100, 100), color=(128, 128, 128)).save(img_path)

        config = MagicMock()
        config.AI_MODE = "mock"
        config.AI_PROVIDER = "mock"
        config.AI_TIMEOUT_SECONDS = 30
        config.AI_RETRY_COUNT = 0
        config.AI_FAILOVER_ENABLED = False
        config.AI_MAX_REQUESTS_PER_MINUTE = 2
        config.AI_TEMPERATURE = 0.0
        config.AI_IMAGE_MAX_DIMENSION = 1024
        config.AI_MAX_IMAGE_MB = 10.0
        config.OPENROUTER_API_KEY = ""
        config.GROQ_API_KEY = ""
        config.OPENROUTER_MODEL = "test"
        config.GROQ_MODEL = "test"

        service = AIService(config)
        obs_meta = {"observation_id": "OBS-TEST-001", "latitude": 35.0, "longitude": -120.0, "altitude_km": 500.0}

        result1 = service.analyze_observation(img_path, obs_meta)
        result2 = service.analyze_observation(img_path, obs_meta)
        result3 = service.analyze_observation(img_path, obs_meta)

        assert result3.ai_status == "rate_limited"


# --- 15. AIService retry logic ---

def test_ai_service_retry_logic():
    """Retries on transient failure."""
    config = MagicMock()
    config.AI_MODE = "mock"
    config.AI_PROVIDER = "mock"
    config.AI_TIMEOUT_SECONDS = 30
    config.AI_RETRY_COUNT = 2
    config.AI_FAILOVER_ENABLED = False
    config.AI_MAX_REQUESTS_PER_MINUTE = 100
    config.AI_TEMPERATURE = 0.0
    config.AI_IMAGE_MAX_DIMENSION = 1024
    config.AI_MAX_IMAGE_MB = 10.0
    config.OPENROUTER_API_KEY = ""
    config.GROQ_API_KEY = ""
    config.OPENROUTER_MODEL = "test"
    config.GROQ_MODEL = "test"

    service = AIService(config)
    mock_provider = MagicMock()
    mock_provider.analyze_image.return_value = VisionInferenceResult(
        ai_status="error", ai_error="transient failure"
    )
    mock_provider.get_provider_info.return_value = {"provider": "mock", "model": "test"}
    mock_provider.is_available.return_value = True

    service._providers = {"mock": mock_provider}

    result = service._call_provider(mock_provider, "base64data", {})
    assert mock_provider.analyze_image.call_count == 3


# --- 16. AIService failover ---

def test_ai_service_failover():
    """Failover from OpenRouter to Groq."""
    config = MagicMock()
    config.AI_MODE = "live"
    config.AI_PROVIDER = "openrouter"
    config.AI_TIMEOUT_SECONDS = 30
    config.AI_RETRY_COUNT = 0
    config.AI_FAILOVER_ENABLED = True
    config.AI_MAX_REQUESTS_PER_MINUTE = 100
    config.AI_TEMPERATURE = 0.0
    config.AI_IMAGE_MAX_DIMENSION = 1024
    config.AI_MAX_IMAGE_MB = 10.0
    config.OPENROUTER_API_KEY = "test-key"
    config.GROQ_API_KEY = "test-key"
    config.OPENROUTER_MODEL = "test-model"
    config.GROQ_MODEL = "test-model"

    service = AIService(config)
    openrouter_mock = MagicMock()
    openrouter_mock.analyze_image.return_value = VisionInferenceResult(ai_status="timeout")
    openrouter_mock.get_provider_info.return_value = {"provider": "openrouter"}
    openrouter_mock.is_available.return_value = True

    groq_mock = MagicMock()
    groq_mock.analyze_image.return_value = VisionInferenceResult(
        smoke_score=0.5, confidence="medium", ai_status="success"
    )
    groq_mock.get_provider_info.return_value = {"provider": "groq"}
    groq_mock.is_available.return_value = True

    service._providers = {"openrouter": openrouter_mock, "groq": groq_mock}
    service._ai_provider_name = "openrouter"

    failover = service._get_failover_provider()
    assert failover is groq_mock


# --- 17. AIService no failover when disabled ---

def test_ai_service_no_failover_when_disabled():
    """No failover when AI_FAILOVER_ENABLED=false."""
    config = MagicMock()
    config.AI_MODE = "live"
    config.AI_PROVIDER = "openrouter"
    config.AI_TIMEOUT_SECONDS = 30
    config.AI_RETRY_COUNT = 0
    config.AI_FAILOVER_ENABLED = False
    config.AI_MAX_REQUESTS_PER_MINUTE = 100
    config.AI_TEMPERATURE = 0.0
    config.AI_IMAGE_MAX_DIMENSION = 1024
    config.AI_MAX_IMAGE_MB = 10.0
    config.OPENROUTER_API_KEY = "test-key"
    config.GROQ_API_KEY = "test-key"
    config.OPENROUTER_MODEL = "test-model"
    config.GROQ_MODEL = "test-model"

    service = AIService(config)
    service._failover_enabled = False

    failover = service._get_failover_provider()
    assert failover is None


# --- 18. Observation model AI fields ---

def test_observation_model_ai_fields():
    """Observation has AI fields."""
    from app.models.observation import Observation

    obs = Observation(
        observation_id="OBS-AI-001",
        timestamp=datetime.now(timezone.utc),
        ai_provider="openrouter",
        ai_model="gemini-flash",
        ai_smoke_score=0.85,
        ai_confidence="high",
        ai_visual_evidence=["haze", "smoke column"],
        ai_alternative_explanations=["cloud"],
        ai_scene_description="forest fire scene",
        ai_status="success",
    )
    assert obs.ai_provider == "openrouter"
    assert obs.ai_model == "gemini-flash"
    assert obs.ai_smoke_score == 0.85
    assert obs.ai_confidence == "high"
    assert obs.ai_visual_evidence == ["haze", "smoke column"]
    assert obs.ai_alternative_explanations == ["cloud"]
    assert obs.ai_scene_description == "forest fire scene"
    assert obs.ai_status == "success"


# --- 19. TelemetryPacket AI fields ---

def test_telemetry_model_ai_fields():
    """TelemetryPacket has AI fields."""
    from app.models.telemetry import TelemetryPacket

    pkt = TelemetryPacket(
        packet_sequence=1,
        ai_status="success",
        ai_provider="groq",
        ai_model="qwen-3.6",
        ai_smoke_score=0.72,
        ai_confidence="medium",
        ai_latency_ms=150.0,
    )
    assert pkt.ai_status == "success"
    assert pkt.ai_provider == "groq"
    assert pkt.ai_model == "qwen-3.6"
    assert pkt.ai_smoke_score == 0.72
    assert pkt.ai_confidence == "medium"
    assert pkt.ai_latency_ms == 150.0


# --- 20. Config AI settings ---

def test_config_ai_settings():
    """Settings has all AI config fields."""
    settings = Settings()
    assert hasattr(settings, "AI_MODE")
    assert hasattr(settings, "AI_PROVIDER")
    assert hasattr(settings, "AI_TIMEOUT_SECONDS")
    assert hasattr(settings, "AI_RETRY_COUNT")
    assert hasattr(settings, "AI_FAILOVER_ENABLED")
    assert hasattr(settings, "AI_MAX_REQUESTS_PER_MINUTE")
    assert hasattr(settings, "AI_TEMPERATURE")
    assert hasattr(settings, "AI_IMAGE_MAX_DIMENSION")
    assert hasattr(settings, "AI_MAX_IMAGE_MB")
    assert hasattr(settings, "OPENROUTER_API_KEY")
    assert hasattr(settings, "OPENROUTER_MODEL")
    assert hasattr(settings, "GROQ_API_KEY")
    assert hasattr(settings, "GROQ_MODEL")

    assert settings.AI_MODE in ("mock", "live")
    assert settings.AI_PROVIDER in ("openrouter", "groq")
    assert isinstance(settings.AI_TIMEOUT_SECONDS, int)
    assert isinstance(settings.AI_FAILOVER_ENABLED, bool)


# --- 21. OpenRouter provider parsing ---

def test_openrouter_provider_parsing():
    """Parse valid OpenRouter response."""
    from app.ai.openrouter_provider import OpenRouterVisionProvider

    provider = OpenRouterVisionProvider(api_key="test-key", model="test-model")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "smoke_present": True,
                        "smoke_score": 0.82,
                        "confidence": "high",
                        "visual_evidence": ["smoke column visible"],
                        "alternative_explanations": ["cloud cover"],
                        "scene_description": "satellite view of forest",
                    })
                }
            }
        ]
    }

    safe_prompt = "Analyze image at lat={lat}, lon={lon}, alt={alt}"
    with patch("app.ai.openrouter_provider.httpx.Client") as mock_client, \
         patch("app.ai.openrouter_provider.USER_PROMPT", safe_prompt):
        mock_instance = MagicMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_client.return_value = mock_instance

        result = provider.analyze_image("base64data", {"latitude": 35.0, "longitude": -120.0, "altitude_km": 500.0})

    assert result.ai_status == "success"
    assert result.smoke_present is True
    assert result.smoke_score == 0.82
    assert result.confidence == "high"
    assert result.ai_provider == "openrouter"


# --- 22. Groq provider parsing ---

def test_groq_provider_parsing():
    """Parse valid Groq response."""
    from app.ai.groq_provider import GroqVisionProvider

    provider = GroqVisionProvider(api_key="test-key", model="test-model")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "smoke_present": False,
                        "smoke_score": 0.15,
                        "confidence": "low",
                        "visual_evidence": [],
                        "alternative_explanations": [],
                        "scene_description": "clear scene",
                    })
                }
            }
        ]
    }

    safe_prompt = "Analyze image at lat={lat}, lon={lon}, alt={alt}"
    with patch("app.ai.groq_provider.httpx.Client") as mock_client, \
         patch("app.ai.groq_provider.USER_PROMPT", safe_prompt):
        mock_instance = MagicMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_client.return_value = mock_instance

        result = provider.analyze_image("base64data", {"latitude": 35.0, "longitude": -120.0, "altitude_km": 500.0})

    assert result.ai_status == "success"
    assert result.smoke_present is False
    assert result.smoke_score == 0.15
    assert result.ai_provider == "groq"


# --- 23. Malformed AI response ---

def test_malformed_ai_response():
    """Handles invalid JSON gracefully."""
    from app.ai.openrouter_provider import OpenRouterVisionProvider

    provider = OpenRouterVisionProvider(api_key="test-key", model="test-model")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "not valid json at all"
                }
            }
        ]
    }

    safe_prompt = "Analyze image at lat={lat}, lon={lon}, alt={alt}"
    with patch("app.ai.openrouter_provider.httpx.Client") as mock_client, \
         patch("app.ai.openrouter_provider.USER_PROMPT", safe_prompt):
        mock_instance = MagicMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_client.return_value = mock_instance

        result = provider.analyze_image("base64data", {})

    assert result.ai_status == "error"
    assert "Failed to parse response" in result.ai_error


# --- 24. AI status endpoint ---

def test_ai_status_endpoint():
    """GET /api/ai/status returns correct data."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/ai/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "mode" in data
    assert "provider" in data
    assert "model" in data
    assert "failover_enabled" in data
    assert "timeout_seconds" in data
    assert "max_requests_per_minute" in data
    assert "status" in data
    assert data["mode"] in ("mock", "live")


# --- 25. Priority calculation with AI score ---

def test_priority_calculation_with_ai_score():
    """Priority uses AI smoke_score."""
    from app.services.priority import PriorityCalculator

    calc = PriorityCalculator()
    assert calc.calculate(0.9, 0.9) == "CRITICAL"
    assert calc.calculate(0.7, 0.7) == "HIGH"
    assert calc.calculate(0.5, 0.5) == "MEDIUM"
    assert calc.calculate(0.1, 0.1) == "LOW"
