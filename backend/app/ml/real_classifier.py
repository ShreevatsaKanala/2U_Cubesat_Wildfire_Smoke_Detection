"""
Real ML classifier for smoke detection on CubeSat.

Implements the InferenceEngine interface using trained models
for RGB smoke vs non-smoke classification targeting Raspberry Pi 5.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import torch
    import numpy as np
    from PIL import Image

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from app.ml.inference import InferenceEngine
from app.ml.preprocessing import Preprocessor
from app.ml.postprocessing import Postprocessor


def _check_torch() -> None:
    if not TORCH_AVAILABLE:
        raise ImportError(
            "torch and Pillow are required for RealSmokeClassifier. "
            "Install with: pip install torch pillow numpy"
        )


class RealSmokeClassifier(InferenceEngine):
    """Real ML classifier for smoke detection."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        smoke_threshold: float = 0.5,
    ) -> None:
        _check_torch()
        self.model_path = model_path
        self.device = device
        self.smoke_threshold = smoke_threshold
        self.model = None
        self.model_name = "smoke-classifier"
        self.model_version = "0.0.0"
        self.input_resolution = (224, 224)

        self.preprocessor = Preprocessor(input_resolution=self.input_resolution)
        self.postprocessor = Postprocessor(
            smoke_threshold=smoke_threshold,
            class_names=["non_smoke", "smoke"],
        )

        if model_path is not None:
            self.load_model(model_path)

    def classify(self, image_path: str) -> Dict[str, Any]:
        """Classify image using the loaded model.

        Returns:
            Dict with smoke_probability, wildfire_probability, confidence,
            model_name, model_version, inference_latency_ms, processing_status, timestamp.
        """
        if not self.is_loaded():
            raise RuntimeError(
                "No model loaded. Provide a valid model_path to __init__ or call load_model()."
            )

        start_time = time.perf_counter()
        tensor = self.preprocessor.preprocess(image_path)

        with torch.no_grad():
            raw_output = self.model(tensor)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        result = self.postprocessor.process(raw_output, elapsed_ms)

        return {
            "smoke_probability": result["smoke_probability"],
            "wildfire_probability": result["wildfire_probability"],
            "confidence": result["confidence"],
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_latency_ms": result["inference_latency_ms"],
            "processing_status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Get loaded model information."""
        if not self.is_loaded():
            return {
                "name": self.model_name,
                "version": self.model_version,
                "status": "not_loaded",
                "framework": "unknown",
                "device": self.device,
            }

        param_count = sum(p.numel() for p in self.model.parameters()) if hasattr(self.model, "parameters") else 0

        return {
            "name": self.model_name,
            "version": self.model_version,
            "input_shape": [self.input_resolution[0], self.input_resolution[1], 3],
            "output_shape": [2],
            "framework": "pytorch",
            "device": self.device,
            "parameter_count": param_count,
            "smoke_threshold": self.smoke_threshold,
            "status": "loaded",
        }

    def warmup(self, num_iterations: int = 5) -> None:
        """Warm up model with dummy predictions."""
        if not self.is_loaded():
            return

        dummy = torch.randn(1, 3, *self.input_resolution).to(self.device)

        with torch.no_grad():
            for _ in range(num_iterations):
                self.model(dummy)

    def load_model(self, model_path: str) -> None:
        """Load model from file.

        Tries torch.load first, then onnxruntime as fallback.
        """
        _check_torch()
        path = Path(model_path)

        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        suffix = path.suffix.lower()

        if suffix in (".pt", ".pth"):
            try:
                self.model = torch.load(
                    str(path), map_location=self.device, weights_only=False
                )
                if hasattr(self.model, "eval"):
                    self.model.eval()
            except Exception:
                self.model = self._try_load_state_dict(path)
        elif suffix == ".onnx":
            self._load_onnx(path)
        else:
            self.model = torch.load(
                str(path), map_location=self.device, weights_only=False
            )
            if hasattr(self.model, "eval"):
                self.model.eval()

        self.model_path = str(path)
        self.model_name = path.parent.parent.name if path.parent.parent.exists() else "smoke-classifier"
        self.model_version = path.parent.name

    def _try_load_state_dict(self, path: Path) -> torch.nn.Module:
        """Try loading as a state dict checkpoint."""
        checkpoint = torch.load(str(path), map_location=self.device, weights_only=False)

        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            model = torch.nn.Linear(224 * 224 * 3, 2)
            model.load_state_dict(checkpoint["model_state_dict"])
            return model.eval()

        if isinstance(checkpoint, torch.nn.Module):
            return checkpoint.eval()

        return checkpoint

    def _load_onnx(self, path: Path) -> None:
        """Load ONNX model via onnxruntime."""
        try:
            import onnxruntime as ort
            self.model = ort.InferenceSession(str(path))
        except ImportError:
            raise ImportError(
                "onnxruntime is required to load .onnx models. "
                "Install with: pip install onnxruntime"
            )

    def is_loaded(self) -> bool:
        """Check if model is loaded and ready."""
        return self.model is not None
