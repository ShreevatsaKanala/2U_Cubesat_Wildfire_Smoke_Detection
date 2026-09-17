"""Image preprocessing for AI vision providers."""

import base64
import io
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    def __init__(
        self,
        max_dimension: int = 1024,
        max_size_mb: float = 10.0,
        jpeg_quality: int = 85,
    ):
        self.max_dimension = max_dimension
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.jpeg_quality = jpeg_quality

    def process(self, image_path: str) -> dict:
        """Load image, resize, compress, return base64 + metadata."""
        img = Image.open(image_path)
        original_width, original_height = img.size

        if img.mode != "RGB":
            img = img.convert("RGB")

        width, height = img.size
        if max(width, height) > self.max_dimension:
            if width >= height:
                new_width = self.max_dimension
                new_height = int(height * (self.max_dimension / width))
            else:
                new_height = self.max_dimension
                new_width = int(width * (self.max_dimension / height))
            img = img.resize((new_width, new_height), Image.LANCZOS)
            width, height = new_width, new_height

        quality = self.jpeg_quality
        compressed_bytes = None
        while quality > 10:
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            compressed_bytes = buffer.getvalue()
            if len(compressed_bytes) <= self.max_size_bytes:
                break
            quality -= 5

        if compressed_bytes is None:
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=10, optimize=True)
            compressed_bytes = buffer.getvalue()

        image_base64 = base64.b64encode(compressed_bytes).decode("utf-8")

        return {
            "image_base64": image_base64,
            "original_width": original_width,
            "original_height": original_height,
            "processed_width": width,
            "processed_height": height,
            "compressed_size_bytes": len(compressed_bytes),
        }
