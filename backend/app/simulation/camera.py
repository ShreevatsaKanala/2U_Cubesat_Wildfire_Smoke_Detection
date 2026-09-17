"""
Camera Simulator for CubeSat Digital Twin.

Generates synthetic test images simulating Earth observation captures.
For Phase 1, creates gradient images with noise patterns. Future phases
will integrate with actual image generation pipelines.
"""

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import math
import random
from typing import Optional

# Default data directory for observations
DEFAULT_DATA_DIR = Path("data/observations")


class CameraSimulator:
    """
    Simulates CubeSat camera for synthetic image generation.

    Creates test images that can be used for ML classifier testing.
    Images include gradient patterns and noise to simulate real
    Earth observation captures.
    """

    def __init__(self, config: dict = None):
        """
        Initialize camera simulator.

        Args:
            config: Optional configuration dictionary with:
                - width: Image width in pixels (default 1920)
                - height: Image height in pixels (default 1080)
                - fov_deg: Camera field of view in degrees (default 62.2)
                - data_dir: Base directory for saving images
        """
        config = config or {}
        self.width = config.get("width", 1920)
        self.height = config.get("height", 1080)
        self.fov_deg = config.get("fov_deg", 62.2)
        self.data_dir = Path(config.get("data_dir", DEFAULT_DATA_DIR))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.status = "ready"
        self.capture_count = 0

    def capture(self, spacecraft_state) -> dict:
        """
        Capture synthetic image from current spacecraft state.

        Args:
            spacecraft_state: Current SpacecraftState with position/orientation

        Returns:
            Dictionary with observation_id, image_path, width, height,
            capture_mode, camera_status, timestamp
        """
        try:
            from PIL import Image, ImageDraw, ImageFilter
        except ImportError:
            return self._capture_fallback(spacecraft_state)

        timestamp = datetime.now(timezone.utc)
        observation_id = f"OBS-{timestamp.strftime('%Y%m%d-%H%M%S')}-{self.capture_count:04d}"

        # Create synthetic image
        img = self._generate_synthetic_image(spacecraft_state, timestamp)

        # Save image
        image_filename = f"{observation_id}.png"
        image_path = self.data_dir / image_filename
        img.save(image_path, "PNG")

        self.capture_count += 1

        return {
            "observation_id": observation_id,
            "image_path": str(image_path).replace("\\", "/"),
            "width": self.width,
            "height": self.height,
            "capture_mode": "synthetic",
            "camera_status": self.status,
            "timestamp": timestamp.isoformat()
        }

    def _generate_synthetic_image(self, spacecraft_state, timestamp: datetime):
        """
        Generate a synthetic Earth observation image.

        Creates gradient patterns simulating terrain, with optional
        smoke/haze patches for interesting observations.
        """
        from PIL import Image, ImageDraw
        import random

        # Use timestamp as seed for deterministic generation
        seed = int(timestamp.timestamp()) % (2**32)
        random.seed(seed)

        # Create base gradient image (simulating Earth surface)
        img = Image.new("RGB", (self.width, self.height))
        pixels = img.load()

        # Generate terrain gradient
        for y in range(self.height):
            for x in range(self.width):
                # Base terrain color (greens/browns)
                r = int(30 + 40 * (y / self.height))
                g = int(80 + 60 * (x / self.width))
                b = int(40 + 30 * ((x + y) / (self.width + self.height)))

                # Add some noise
                noise = random.randint(-10, 10)
                r = max(0, min(255, r + noise))
                g = max(0, min(255, g + noise))
                b = max(0, min(255, b + noise))

                pixels[x, y] = (r, g, b)

        # Add smoke/haze patches for some observations
        smoke_prob = self._calculate_smoke_probability(spacecraft_state)
        if smoke_prob > 0.3:
            draw = ImageDraw.Draw(img)
            num_patches = int(smoke_prob * 5) + 1
            for _ in range(num_patches):
                cx = random.randint(0, self.width)
                cy = random.randint(0, self.height)
                rx = random.randint(50, 200)
                ry = random.randint(30, 150)
                # Semi-transparent smoke (white/gray)
                alpha = int(80 + smoke_prob * 100)
                draw.ellipse(
                    [cx - rx, cy - ry, cx + rx, cy + ry],
                    fill=(200, 200, 200, alpha)
                )

        return img

    def _calculate_smoke_probability(self, spacecraft_state) -> float:
        """
        Calculate probability of smoke/haze based on position.

        Uses latitude to determine if over forested regions.
        """
        lat = getattr(spacecraft_state, 'latitude', 0.0)

        # Simple model: higher probability near equator and mid-latitudes
        # where forest fires are more common
        abs_lat = abs(lat)
        if 10 < abs_lat < 30:  # Tropical/subtropical regions
            return 0.6
        elif 30 < abs_lat < 50:  # Temperate regions
            return 0.4
        else:
            return 0.2

    def _capture_fallback(self, spacecraft_state) -> dict:
        """
        Fallback capture when Pillow is not available.

        Creates a simple text file instead of an image.
        """
        timestamp = datetime.now(timezone.utc)
        observation_id = f"OBS-{timestamp.strftime('%Y%m%d-%H%M%S')}-{self.capture_count:04d}"

        # Create fallback directory
        fallback_dir = self.data_dir / "fallback"
        fallback_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata only
        metadata_path = fallback_dir / f"{observation_id}.txt"
        metadata_path.write_text(
            f"Observation ID: {observation_id}\n"
            f"Timestamp: {timestamp.isoformat()}\n"
            f"Status: Pillow not available, image not generated\n"
            f"Spacecraft Position: {getattr(spacecraft_state, 'latitude', 'N/A')}, "
            f"{getattr(spacecraft_state, 'longitude', 'N/A')}\n"
        )

        self.capture_count += 1

        return {
            "observation_id": observation_id,
            "image_path": str(metadata_path).replace("\\", "/"),
            "width": 0,
            "height": 0,
            "capture_mode": "fallback",
            "camera_status": "pillow_unavailable",
            "timestamp": timestamp.isoformat()
        }

    def get_camera_info(self) -> dict:
        """Return camera specifications."""
        return {
            "width": self.width,
            "height": self.height,
            "fov_deg": self.fov_deg,
            "status": self.status,
            "capture_count": self.capture_count
        }
