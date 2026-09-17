"""
Prepare smoke detection dataset for ML training.

Downloads or copies images from a source directory/URL, validates them,
and creates structured labels and manifest files.

Usage:
    python scripts/ml/prepare_dataset.py --source <path_or_url> --output data/raw
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import tempfile
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}


def is_url(source: str) -> bool:
    """Check if source string is a URL."""
    return source.startswith("http://") or source.startswith("https://")


def download_and_extract(url: str, dest_dir: Path) -> Path:
    """Download a zip file and extract it, returning the extraction root."""
    logger.info(f"Downloading dataset from {url}")
    zip_path = dest_dir / "dataset.zip"

    try:
        urllib.request.urlretrieve(url, zip_path)
    except Exception as e:
        raise RuntimeError(f"Failed to download {url}: {e}")

    logger.info("Extracting archive...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)

    zip_path.unlink()

    # Find the root of extracted content
    extracted = list(dest_dir.iterdir())
    # If everything is inside a single subdirectory, return that
    dirs = [d for d in extracted if d.is_dir()]
    if len(dirs) == 1 and all(not f.is_file() for f in extracted if f.is_file()):
        return dirs[0]
    return dest_dir


def validate_image(path: Path) -> bool:
    """Validate that an image exists, is readable, and can be converted to RGB."""
    if not path.exists() or not path.is_file():
        return False

    try:
        from PIL import Image

        with Image.open(path) as img:
            img.verify()

        with Image.open(path) as img:
            img.convert("RGB")

        return True
    except Exception:
        return False


def scan_source_directory(source_dir: Path) -> Dict[str, List[Path]]:
    """Scan a directory for images organized by class subfolders.

    Expects structure: source_dir/<class_name>/<images>

    Returns:
        Dict mapping class_name -> list of image paths.
    """
    classes: Dict[str, List[Path]] = defaultdict(list)

    for item in sorted(source_dir.rglob("*")):
        if not item.is_file():
            continue

        if item.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        # Class name is the immediate parent directory
        class_name = item.parent.name
        if class_name == source_dir.name:
            # Images at root level with no class subfolder
            class_name = "unclassified"

        classes[class_name].append(item)

    return dict(classes)


def generate_image_id(path: Path, source_root: Path) -> str:
    """Generate a deterministic image ID from relative path."""
    rel = path.relative_to(source_root)
    return str(rel).replace("\\", "/")


def create_dataset(
    source: str,
    output_dir: Path,
    manifest_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Main dataset preparation pipeline.

    Args:
        source: Local directory path or URL to dataset.
        output_dir: Output directory for raw images and labels.
        manifest_path: Optional custom path for manifest file.

    Returns:
        Dataset manifest dict.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    labels_dir = output_dir.parent / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)

    source_dir: Path

    if is_url(source):
        tmp_dir = Path(tempfile.mkdtemp(prefix="cubesat_data_"))
        source_dir = download_and_extract(source, tmp_dir)
        logger.info(f"Downloaded and extracted to {source_dir}")
    else:
        source_dir = Path(source)
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

    # Scan for images
    logger.info("Scanning source for images...")
    class_images = scan_source_directory(source_dir)
    total_images = sum(len(v) for v in class_images.values())

    if total_images == 0:
        raise ValueError(f"No valid images found in {source_dir}")

    logger.info(f"Found {total_images} images across {len(class_images)} classes: {list(class_images.keys())}")

    # Copy images and build labels
    labels: Dict[str, Dict[str, Any]] = {}
    class_counts: Dict[str, int] = defaultdict(int)
    resolutions: List[List[int]] = []
    invalid_count = 0

    for class_name, image_paths in class_images.items():
        for img_path in image_paths:
            image_id = generate_image_id(img_path, source_dir)

            if not validate_image(img_path):
                logger.warning(f"Invalid image skipped: {img_path}")
                invalid_count += 1
                continue

            # Copy image to output
            dest = output_dir / class_name / img_path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img_path, dest)

            # Get resolution
            try:
                from PIL import Image

                with Image.open(dest) as img:
                    w, h = img.size
                    resolutions.append([w, h])
            except Exception:
                resolutions.append([0, 0])

            labels[image_id] = {
                "class": class_name,
                "source": str(img_path),
                "split": None,
                "filename": str(dest.relative_to(output_dir)),
            }
            class_counts[class_name] += 1

    # Save labels
    labels_path = labels_dir / "labels.json"
    with open(labels_path, "w") as f:
        json.dump(labels, f, indent=2)
    logger.info(f"Labels saved to {labels_path}")

    # Build manifest
    widths = [r[0] for r in resolutions if r[0] > 0]
    heights = [r[1] for r in resolutions if r[1] > 0]

    manifest: Dict[str, Any] = {
        "dataset_name": Path(source).stem if not is_url(source) else "downloaded_dataset",
        "source": source,
        "license": "unknown",
        "total_images": total_images - invalid_count,
        "invalid_images": invalid_count,
        "num_classes": len(class_counts),
        "class_distribution": dict(class_counts),
        "resolution_stats": {
            "width_mean": round(sum(widths) / len(widths), 1) if widths else 0,
            "height_mean": round(sum(heights) / len(heights), 1) if heights else 0,
            "width_min": min(widths) if widths else 0,
            "width_max": max(widths) if widths else 0,
            "height_min": min(heights) if heights else 0,
            "height_max": max(heights) if heights else 0,
        },
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "known_limitations": [
            "No license information verified",
            "Class balance may be uneven",
        ],
    }

    if manifest_path is None:
        manifest_path = output_dir.parent / "metadata" / "dataset_manifest.json"

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest saved to {manifest_path}")

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare smoke detection dataset for ML training."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to local directory or URL containing dataset",
    )
    parser.add_argument(
        "--output",
        default="data/raw",
        help="Output directory for processed images (default: data/raw)",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Custom path for dataset_manifest.json",
    )

    args = parser.parse_args()

    manifest = create_dataset(
        source=args.source,
        output_dir=Path(args.output),
        manifest_path=Path(args.manifest) if args.manifest else None,
    )

    print(f"\nDataset preparation complete:")
    print(f"  Total images: {manifest['total_images']}")
    print(f"  Classes: {manifest['class_distribution']}")
    print(f"  Resolution: {manifest['resolution_stats']['width_mean']}x{manifest['resolution_stats']['height_mean']}")


if __name__ == "__main__":
    main()
