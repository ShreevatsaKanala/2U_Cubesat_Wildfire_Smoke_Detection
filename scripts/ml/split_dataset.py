"""
Split dataset into train/val/test sets with stratification.

Creates reproducible, stratified splits for ML training.
Supports scene-aware splitting when source metadata is available.

Usage:
    python scripts/ml/split_dataset.py --labels data/labels/labels.json --output data/splits
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RANDOM_SEED = 42


def load_labels(labels_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load labels from JSON file."""
    with open(labels_path) as f:
        return json.load(f)


def group_by_source(labels: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """Group image IDs by their source/scene for leakage-free splitting."""
    source_groups: Dict[str, List[str]] = defaultdict(list)

    for image_id, meta in labels.items():
        source = meta.get("source", "unknown")
        # Normalize source to group by dataset/scene
        source_key = str(Path(source).parent) if "/" in source or "\\" in source else source
        source_groups[source_key].append(image_id)

    return dict(source_groups)


def stratified_split(
    labels: Dict[str, Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = RANDOM_SEED,
) -> Dict[str, List[str]]:
    """Create stratified train/val/test splits.

    Args:
        labels: Dict of image_id -> metadata.
        train_ratio: Fraction for training.
        val_ratio: Fraction for validation.
        test_ratio: Fraction for testing.
        seed: Random seed for reproducibility.

    Returns:
        Dict with train, val, test lists of image IDs.
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "Ratios must sum to 1.0"

    rng = random.Random(seed)

    # Group by class for stratification
    class_groups: Dict[str, List[str]] = defaultdict(list)
    for image_id, meta in labels.items():
        class_groups[meta["class"]].append(image_id)

    splits = {"train": [], "val": [], "test": []}

    for class_name, image_ids in class_groups.items():
        rng.shuffle(image_ids)
        n = len(image_ids)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        splits["train"].extend(image_ids[:n_train])
        splits["val"].extend(image_ids[n_train : n_train + n_val])
        splits["test"].extend(image_ids[n_train + n_val :])

        logger.info(
            f"  Class '{class_name}': {n} total -> "
            f"train={n_train}, val={n_val}, test={n - n_train - n_val}"
        )

    # Shuffle within splits
    for split_name in splits:
        rng.shuffle(splits[split_name])

    return splits


def scene_aware_split(
    labels: Dict[str, Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = RANDOM_SEED,
) -> Dict[str, List[str]]:
    """Create splits by source/scene to prevent data leakage.

    Images from the same source/scene stay in the same split.
    """
    rng = random.Random(seed)
    source_groups = group_by_source(labels)

    # Sort for determinism
    source_keys = sorted(source_groups.keys())
    rng.shuffle(source_keys)

    splits = {"train": [], "val": [], "test": []}
    total = sum(len(v) for v in source_groups.values())
    target_train = int(total * train_ratio)
    target_val = int(total * val_ratio)

    current_train, current_val = 0, 0

    for src in source_keys:
        ids = source_groups[src]
        assigned = False

        if current_train <= target_train:
            splits["train"].extend(ids)
            current_train += len(ids)
            assigned = True
        elif current_val <= target_val:
            splits["val"].extend(ids)
            current_val += len(ids)
            assigned = True

        if not assigned:
            splits["test"].extend(ids)

    return splits


def validate_splits(
    splits: Dict[str, List[str]],
    labels: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate splits and compute statistics."""
    stats: Dict[str, Any] = {}

    for split_name, image_ids in splits.items():
        class_counts: Dict[str, int] = defaultdict(int)
        for img_id in image_ids:
            class_counts[labels[img_id]["class"]] += 1

        stats[split_name] = {
            "total": len(image_ids),
            "class_distribution": dict(class_counts),
        }

    # Check no overlap
    all_ids = []
    for ids in splits.values():
        all_ids.extend(ids)

    assert len(all_ids) == len(set(all_ids)), "Overlap detected between splits!"
    assert len(all_ids) == len(labels), "Some images missing from splits!"

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create reproducible train/val/test splits."
    )
    parser.add_argument(
        "--labels",
        default="data/labels/labels.json",
        help="Path to labels JSON file (default: data/labels/labels.json)",
    )
    parser.add_argument(
        "--output",
        default="data/splits",
        help="Output directory for split files (default: data/splits)",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.70,
        help="Training set ratio (default: 0.70)",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.15,
        help="Validation set ratio (default: 0.15)",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.15,
        help="Test set ratio (default: 0.15)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOM_SEED,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--scene-aware",
        action="store_true",
        help="Use scene-aware splitting to prevent data leakage",
    )

    args = parser.parse_args()
    labels_path = Path(args.labels)
    output_dir = Path(args.output)

    if not labels_path.exists():
        logger.error(f"Labels file not found: {labels_path}")
        return

    labels = load_labels(labels_path)
    logger.info(f"Loaded {len(labels)} image labels")

    if len(labels) == 0:
        logger.error("No labels found. Run prepare_dataset.py first.")
        return

    # Check for single-class edge case
    classes = set(meta["class"] for meta in labels.values())
    if len(classes) == 1:
        logger.warning(f"Only one class found: {classes}. Splitting randomly.")

    # Create splits
    logger.info("Creating splits...")
    if args.sceneAware:
        logger.info("Using scene-aware splitting")
        splits = scene_aware_split(
            labels,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            seed=args.seed,
        )
    else:
        splits = stratified_split(
            labels,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            seed=args.seed,
        )

    # Update labels with split information
    for split_name, image_ids in splits.items():
        for img_id in image_ids:
            labels[img_id]["split"] = split_name

    # Validate
    stats = validate_splits(splits, labels)

    # Save splits
    output_dir.mkdir(parents=True, exist_ok=True)
    splits_path = output_dir / "splits.json"
    with open(splits_path, "w") as f:
        json.dump(splits, f, indent=2)
    logger.info(f"Splits saved to {splits_path}")

    # Save updated labels
    labels_output = output_dir / "labels_with_splits.json"
    with open(labels_output, "w") as f:
        json.dump(labels, f, indent=2)

    # Print summary
    print(f"\nDataset splits created (seed={args.seed}):")
    for split_name, split_stats in stats.items():
        print(f"  {split_name}: {split_stats['total']} images")
        for cls, count in split_stats["class_distribution"].items():
            print(f"    {cls}: {count}")


if __name__ == "__main__":
    main()
