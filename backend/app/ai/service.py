"""AI Vision Service with provider management, retries, and failover."""

import logging
import threading
import time

from app.ai.base import VisionInferenceProvider
from app.ai.mock_provider import MockVisionProvider
from app.ai.preprocessing import ImagePreprocessor
from app.ai.schemas import VisionInferenceResult

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, config):
        self._config = config
        self._ai_mode = getattr(config, "AI_MODE", "mock")
        self._ai_provider_name = getattr(config, "AI_PROVIDER", "openrouter")
        self._timeout = getattr(config, "AI_TIMEOUT_SECONDS", 30)
        self._retry_count = getattr(config, "AI_RETRY_COUNT", 2)
        self._failover_enabled = getattr(config, "AI_FAILOVER_ENABLED", True)
        self._max_rpm = getattr(config, "AI_MAX_REQUESTS_PER_MINUTE", 10)
        self._temperature = getattr(config, "AI_TEMPERATURE", 0)

        self._preprocessor = ImagePreprocessor(
            max_dimension=getattr(config, "AI_IMAGE_MAX_DIMENSION", 1024),
            max_size_mb=getattr(config, "AI_MAX_IMAGE_MB", 10),
        )

        self._providers: dict[str, VisionInferenceProvider] = {}
        self._request_timestamps: list[float] = []
        self._lock = threading.Lock()
        self._metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "failovers": 0,
            "rate_limited": 0,
        }

        self._init_providers()

    def _init_providers(self):
        if self._ai_mode == "mock":
            self._providers["mock"] = MockVisionProvider()
            return

        openrouter_key = getattr(self._config, "OPENROUTER_API_KEY", "")
        groq_key = getattr(self._config, "GROQ_API_KEY", "")
        openrouter_model = getattr(self._config, "OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
        groq_model = getattr(self._config, "GROQ_MODEL", "qwen/qwen3.6-27b")

        if openrouter_key:
            try:
                from app.ai.openrouter_provider import OpenRouterVisionProvider
                self._providers["openrouter"] = OpenRouterVisionProvider(
                    api_key=openrouter_key,
                    model=openrouter_model,
                    timeout=self._timeout,
                    temperature=self._temperature,
                )
            except Exception as e:
                logger.error(f"Failed to init OpenRouter provider: {e}")

        if groq_key:
            try:
                from app.ai.groq_provider import GroqVisionProvider
                self._providers["groq"] = GroqVisionProvider(
                    api_key=groq_key,
                    model=groq_model,
                    timeout=self._timeout,
                    temperature=self._temperature,
                )
            except Exception as e:
                logger.error(f"Failed to init Groq provider: {e}")

        if not self._providers:
            logger.warning("No live AI providers available. AI will report 'unavailable'.")

    def _get_primary_provider(self) -> VisionInferenceProvider | None:
        if not self._providers:
            return None
        if self._ai_provider_name in self._providers:
            return self._providers[self._ai_provider_name]
        return list(self._providers.values())[0]

    def _get_failover_provider(self) -> VisionInferenceProvider | None:
        if not self._failover_enabled:
            return None
        for name, provider in self._providers.items():
            if name != self._ai_provider_name and provider.is_available():
                return provider
        return None

    def analyze_observation(
        self, image_path: str, observation_metadata: dict
    ) -> VisionInferenceResult:
        self._metrics["total_requests"] += 1

        primary = self._get_primary_provider()
        if primary is None:
            self._metrics["failed"] += 1
            return VisionInferenceResult(
                ai_status="unavailable",
                ai_error="No live AI providers configured. Set AI_MODE=mock or configure an API key.",
            )

        if not self._check_rate_limit():
            self._metrics["rate_limited"] += 1
            return VisionInferenceResult(
                ai_status="rate_limited",
                ai_error="Rate limit exceeded",
            )

        self._record_request()

        try:
            processed = self._preprocessor.process(image_path)
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            self._metrics["failed"] += 1
            return VisionInferenceResult(
                ai_status="error",
                ai_error=f"Preprocessing failed: {e}",
            )

        image_base64 = processed["image_base64"]
        metadata = {
            "observation_id": observation_metadata.get("observation_id", ""),
            "latitude": observation_metadata.get("latitude", 0.0),
            "longitude": observation_metadata.get("longitude", 0.0),
            "altitude_km": observation_metadata.get("altitude_km", 500.0),
        }

        result = self._call_provider(primary, image_base64, metadata)

        if result.ai_status in ("success", "timeout", "error"):
            if result.ai_status == "success":
                self._metrics["successful"] += 1
                return result

            if result.ai_status == "timeout":
                failover = self._get_failover_provider()
                if failover:
                    logger.info(
                        f"Primary provider timeout, failing over to {failover.get_provider_info()['provider']}"
                    )
                    self._metrics["failovers"] += 1
                    result = self._call_provider(failover, image_base64, metadata)
                    if result.ai_status == "success":
                        self._metrics["successful"] += 1
                        return result

            self._metrics["failed"] += 1
            return result

        failover = self._get_failover_provider()
        if failover:
            logger.info(f"Primary provider failed, failing over to {failover.get_provider_info()['provider']}")
            self._metrics["failovers"] += 1
            result = self._call_provider(failover, image_base64, metadata)
            if result.ai_status == "success":
                self._metrics["successful"] += 1
                return result

        self._metrics["failed"] += 1
        return result

    def _call_provider(
        self,
        provider: VisionInferenceProvider,
        image_base64: str,
        metadata: dict,
    ) -> VisionInferenceResult:
        last_result = None
        for attempt in range(1 + self._retry_count):
            result = provider.analyze_image(image_base64, metadata)
            if result.ai_status == "success":
                return result
            if result.ai_status in ("rate_limited", "unavailable"):
                return result
            if result.ai_error and "auth" in result.ai_error.lower():
                return result
            last_result = result
            if attempt < self._retry_count:
                self._metrics["retried"] += 1
                time.sleep(1.0 * (attempt + 1))

        return last_result or VisionInferenceResult(
            ai_status="error",
            ai_error="All retries exhausted",
        )

    def _check_rate_limit(self) -> bool:
        with self._lock:
            now = time.time()
            self._request_timestamps = [
                ts for ts in self._request_timestamps if now - ts < 60.0
            ]
            return len(self._request_timestamps) < self._max_rpm

    def _record_request(self):
        with self._lock:
            self._request_timestamps.append(time.time())

    def get_status(self) -> dict:
        provider_status = {}
        for name, provider in self._providers.items():
            info = provider.get_provider_info()
            info["available"] = provider.is_available()
            provider_status[name] = info

        with self._lock:
            now = time.time()
            self._request_timestamps = [
                ts for ts in self._request_timestamps if now - ts < 60.0
            ]
            recent_count = len(self._request_timestamps)

        return {
            "mode": self._ai_mode,
            "primary_provider": self._ai_provider_name,
            "providers": provider_status,
            "failover_enabled": self._failover_enabled,
            "timeout_seconds": self._timeout,
            "retry_count": self._retry_count,
            "max_rpm": self._max_rpm,
            "recent_requests_60s": recent_count,
            "metrics": self._metrics,
        }
