"""
Mock ML Classifier for CubeSat Digital Twin.

Provides deterministic smoke/wildfire classification for testing
the observation pipeline without requiring actual ML models.
Uses image path hashing to generate reproducible predictions.
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, Any

from app.ml.inference import InferenceEngine


class MockClassifier(InferenceEngine):
    """
    Mock classifier for testing observation pipeline.

    Generates deterministic predictions based on image path hash.
    Ensures reproducible results for testing while simulating
    realistic ML inference behavior.
    """

    def __init__(self):
        """Initialize mock classifier."""
        self.model_name = "mock-smoke-classifier-v0.1"
        self.model_version = "0.1.0"
        self.inference_count = 0

    def classify(self, image_path: str) -> Dict[str, Any]:
        """
        Classify image using deterministic hash-based simulation.

        Args:
            image_path: Path to image file (used as seed for determinism)

        Returns:
            Dictionary with classification results
        """
        # Generate deterministic hash from image path
        path_hash = hashlib.md5(image_path.encode()).hexdigest()

        # Convert first hex character to integer (0-15)
        first_char = path_hash[0]
        hash_value = int(first_char, 16)

        # Generate smoke probability (0-1)
        # Map hash to range with some observations having high values
        smoke_base = hash_value / 15.0  # 0 to 1

        # Add secondary variation from second character
        second_char = path_hash[1]
        second_value = int(second_char, 16) / 15.0
        smoke_probability = smoke_base * 0.7 + second_value * 0.3

        # Ensure some observations are "interesting" (high probability)
        if hash_value >= 10:  # ~30% of cases
            smoke_probability = max(0.6, smoke_probability)

        # Wildfire probability correlated but different from smoke
        wildfire_probability = smoke_probability * 0.8 + second_value * 0.2
        wildfire_probability = min(1.0, wildfire_probability)

        # Confidence varies inversely with probability extremes
        confidence_base = 0.7
        if smoke_probability > 0.8 or smoke_probability < 0.2:
            confidence_base = 0.85  # Higher confidence at extremes
        confidence = confidence_base + (second_value * 0.1)

        # Simulated inference latency (50-200ms)
        latency_base = 50
        latency_range = 150
        inference_latency_ms = latency_base + (hash_value / 15.0) * latency_range

        self.inference_count += 1

        return {
            "smoke_probability": round(smoke_probability, 4),
            "wildfire_probability": round(wildfire_probability, 4),
            "confidence": round(confidence, 4),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_latency_ms": round(inference_latency_ms, 2),
            "processing_status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Return mock model information."""
        return {
            "name": self.model_name,
            "version": self.model_version,
            "input_shape": [1080, 1920, 3],
            "output_shape": [3],
            "framework": "mock",
            "device": "cpu",
            "status": "simulated"
        }

    def get_supported_classes(self) -> list:
        """Return supported detection classes."""
        return ["smoke", "wildfire", "clear"]

    def warmup(self, num_iterations: int = 5) -> None:
        """Simulate model warmup."""
        for i in range(num_iterations):
            self.classify(f"warmup_image_{i}.png")
