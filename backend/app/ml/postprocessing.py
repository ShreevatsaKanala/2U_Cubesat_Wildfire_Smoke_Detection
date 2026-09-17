"""
Post-processing for ML model outputs on CubeSat smoke detection.

Converts raw model logits/probabilities into structured classification results
with confidence scoring and thresholding.
"""

from __future__ import annotations

from typing import List, Optional

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def _check_torch() -> None:
    if not TORCH_AVAILABLE:
        raise ImportError(
            "torch is required for Postprocessor. "
            "Install with: pip install torch"
        )


class Postprocessor:
    """Post-processing for model outputs."""

    def __init__(
        self,
        smoke_threshold: float = 0.5,
        class_names: Optional[List[str]] = None,
    ) -> None:
        _check_torch()
        self.smoke_threshold = smoke_threshold
        self.class_names = class_names or ["non_smoke", "smoke"]

    def process(self, raw_output: torch.Tensor, latency_ms: float) -> dict:
        """Convert raw model output to structured result dict.

        Args:
            raw_output: Model output tensor of shape [1, num_classes].
            latency_ms: Inference latency in milliseconds.

        Returns:
            Dict with smoke_probability, wildfire_probability, confidence,
            prediction, class_name, and latency.
        """
        if raw_output.dim() == 1:
            raw_output = raw_output.unsqueeze(0)

        # Apply softmax if values look like logits (not in [0, 1] range)
        if raw_output.min() < 0 or raw_output.max() > 1:
            probs = torch.softmax(raw_output, dim=1)
        else:
            probs = raw_output

        # For binary classification: index 0 = non_smoke, index 1 = smoke
        smoke_prob = probs[0, 1].item() if probs.shape[1] >= 2 else probs[0, 0].item()
        confidence = self.calculate_confidence(probs)
        class_name = self.apply_threshold(smoke_prob)

        return {
            "smoke_probability": round(smoke_prob, 4),
            "wildfire_probability": 0.0,
            "confidence": round(confidence, 4),
            "prediction": class_name,
            "class_name": class_name,
            "inference_latency_ms": round(latency_ms, 2),
        }

    def calculate_confidence(self, probabilities: torch.Tensor) -> float:
        """Calculate prediction confidence from probability distribution.

        For binary: difference between top two probabilities.
        For multi-class: just the max probability.
        """
        if probabilities.numel() <= 2:
            sorted_probs = probabilities.flatten().sort(descending=True).values
            if len(sorted_probs) >= 2:
                return float(sorted_probs[0] - sorted_probs[1])
            return float(sorted_probs[0])

        sorted_probs = probabilities.flatten().sort(descending=True).values
        return float(sorted_probs[0])

    def apply_threshold(self, smoke_probability: float) -> str:
        """Apply threshold to determine smoke vs non_smoke."""
        return "smoke" if smoke_probability >= self.smoke_threshold else "non_smoke"
