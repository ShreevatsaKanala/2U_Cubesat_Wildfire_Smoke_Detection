"""Abstract base class for vision inference providers."""

from abc import ABC, abstractmethod

from app.ai.schemas import VisionInferenceResult


class VisionInferenceProvider(ABC):
    @abstractmethod
    def analyze_image(self, image_base64: str, metadata: dict) -> VisionInferenceResult:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_provider_info(self) -> dict:
        pass
