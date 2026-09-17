"""
Image preprocessing for ML inference on CubeSat smoke detection.

Handles image loading, resizing, normalization, and tensor conversion.
Targets Raspberry Pi 5 resource constraints with efficient preprocessing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Union

try:
    import torch
    import numpy as np
    from PIL import Image

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def _check_torch() -> None:
    if not TORCH_AVAILABLE:
        raise ImportError(
            "torch and Pillow are required for Preprocessor. "
            "Install with: pip install torch pillow numpy"
        )


class Preprocessor:
    """Image preprocessing for ML inference."""

    def __init__(
        self,
        input_resolution: Tuple[int, int] = (224, 224),
        normalize: bool = True,
    ) -> None:
        _check_torch()
        self.input_resolution = input_resolution
        self.normalize = normalize
        self.mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
        self.std = torch.tensor(IMAGENET_STD).view(3, 1, 1)

    def preprocess(self, image_path: str) -> torch.Tensor:
        """Load RGB image, resize, normalize, return tensor [1, C, H, W]."""
        self.validate_image(image_path)

        img = Image.open(image_path)
        img = img.convert("RGB")
        img = img.resize(self.input_resolution, Image.BILINEAR)

        tensor = torch.from_numpy(np.array(img)).permute(2, 0, 1).float() / 255.0

        if self.normalize:
            tensor = (tensor - self.mean.to(tensor.device)) / self.std.to(tensor.device)

        return tensor.unsqueeze(0)

    def preprocess_batch(self, image_paths: list[str]) -> torch.Tensor:
        """Batch preprocess multiple images into [N, C, H, W] tensor."""
        if not image_paths:
            _check_torch()
            raise ValueError("image_paths must not be empty")

        tensors = [self.preprocess(p) for p in image_paths]
        return torch.cat(tensors, dim=0)

    def validate_image(self, image_path: str) -> bool:
        """Check if image is valid RGB (exists, readable, openable)."""
        _check_torch()
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {image_path}")

        try:
            with Image.open(path) as img:
                img.verify()
        except Exception as e:
            raise ValueError(f"Corrupt or unreadable image: {image_path}: {e}")

        # Re-open to confirm we can actually load it as RGB
        with Image.open(path) as img:
            img.convert("RGB")

        return True
