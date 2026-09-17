"""
Run the complete ML training pipeline.

Executes all stages in sequence:
1. Prepare dataset
2. Split dataset
3. Train all models
4. Evaluate best model
5. Export deployment model
6. Benchmark

Usage:
    python scripts/ml/run_pipeline.py --source <data_path>
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "ml"))


def run_step(name: str, func, **kwargs) -> Optional[Dict[str, Any]]:
    """Run a pipeline step with error handling."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  Step: {name}")
    logger.info(f"{'='*60}")

    start = time.time()
    try:
        result = func(**kwargs)
        elapsed = round(time.time() - start, 1)
        logger.info(f"  Completed in {elapsed}s")
        return result
    except Exception as e:
        logger.error(f"  Failed: {e}")
        return None


def pipeline(
    source: str,
    epochs: int = 30,
    device: str = "cpu",
    batch_size: int = 32,
    lr: float = 0.001,
) -> Dict[str, Any]:
    """Run the complete ML pipeline.

    Args:
        source: Dataset source path or URL.
        epochs: Training epochs per model.
        device: Training device.
        batch_size: Training batch size.
        lr: Learning rate.

    Returns:
        Pipeline summary dict.
    """
    from prepare_dataset import create_dataset
    from split_dataset import load_labels, stratified_split, validate_splits
    from train import train, build_model, load_splits as train_load_splits
    from evaluate import evaluate
    from export import export_model
    from benchmark import benchmark

    data_root = Path("data")
    raw_dir = data_root / "raw"
    splits_dir = data_root / "splits"
    models_dir = data_root / "models"
    reports_dir = Path("reports") / "ml"

    summary: Dict[str, Any] = {"steps": {}}
    models_to_train = ["baseline", "mobilenet_v3_small", "mobilenet_v3_large"]
    trained_models: List[Dict[str, Any]] = []

    # Step 1: Prepare dataset
    def step_prepare():
        return create_dataset(source=source, output_dir=raw_dir)

    manifest = run_step("Prepare Dataset", step_prepare)
    if manifest is None:
        logger.error("Dataset preparation failed. Aborting.")
        return summary
    summary["steps"]["prepare"] = {"status": "success", "total_images": manifest["total_images"]}

    # Step 2: Split dataset
    def step_split():
        labels_path = data_root / "labels" / "labels.json"
        if not labels_path.exists():
            raise FileNotFoundError(f"Labels not found: {labels_path}")

        labels = load_labels(labels_path)
        splits = stratified_split(labels)

        # Update labels with split info
        for split_name, image_ids in splits.items():
            for img_id in image_ids:
                labels[img_id]["split"] = split_name

        stats = validate_splits(splits, labels)

        splits_dir.mkdir(parents=True, exist_ok=True)
        with open(splits_dir / "splits.json", "w") as f:
            json.dump(splits, f, indent=2)
        with open(splits_dir / "labels_with_splits.json", "w") as f:
            json.dump(labels, f, indent=2)

        return stats

    split_stats = run_step("Split Dataset", step_split)
    if split_stats is None:
        logger.error("Dataset splitting failed. Aborting.")
        return summary
    summary["steps"]["split"] = {"status": "success", "stats": split_stats}

    # Step 3: Train all models
    train_results = {}
    for model_name in models_to_train:
        def step_train(mn=model_name):
            return train(
                data_dir=splits_dir,
                model_name=mn,
                epochs=epochs,
                batch_size=batch_size,
                lr=lr,
                device_str=device,
                output_dir=models_dir,
            )

        result = run_step(f"Train {model_name}", step_train)
        if result is not None:
            train_results[model_name] = result
            trained_models.append(result)
        else:
            logger.warning(f"Training failed for {model_name}, continuing with others...")

    summary["steps"]["train"] = {
        "status": "success" if train_results else "all_failed",
        "models": {k: {"f1": v["best_val_f1"], "path": v["model_path"]} for k, v in train_results.items()},
    }

    if not train_results:
        logger.error("No models trained successfully. Aborting.")
        return summary

    # Step 4: Evaluate best model
    best_model = max(train_results.values(), key=lambda x: x["best_val_f1"])
    best_model_path = Path(best_model["model_path"])

    def step_evaluate():
        return evaluate(
            model_path=best_model_path,
            data_dir=splits_dir,
            split="test",
            output_dir=reports_dir,
        )

    eval_result = run_step("Evaluate Best Model", step_evaluate)
    summary["steps"]["evaluate"] = {
        "status": "success" if eval_result else "failed",
        "best_model": best_model["model_name"],
        "metrics": eval_result if eval_result else {},
    }

    # Step 5: Export deployment model
    def step_export():
        return export_model(
            model_path=best_model_path,
            export_format="onnx",
            output_dir=models_dir,
        )

    export_result = run_step("Export Deployment Model", step_export)
    summary["steps"]["export"] = {
        "status": "success" if export_result else "failed",
        "metadata": export_result if export_result else {},
    }

    # Step 6: Benchmark
    def step_benchmark():
        return benchmark(
            model_path=best_model_path,
            iterations=100,
            output_dir=reports_dir,
        )

    bench_result = run_step("Benchmark Model", step_benchmark)
    summary["steps"]["benchmark"] = {
        "status": "success" if bench_result else "failed",
        "throughput": bench_result.get("throughput_images_per_second") if bench_result else None,
    }

    # Final summary
    summary["best_model"] = best_model["model_name"]
    summary["best_f1"] = best_model["best_val_f1"]

    logger.info(f"\n{'='*60}")
    logger.info(f"  Pipeline Complete")
    logger.info(f"{'='*60}")
    logger.info(f"  Best model: {best_model['model_name']}")
    logger.info(f"  Best F1: {best_model['best_val_f1']:.4f}")
    logger.info(f"  Models trained: {list(train_results.keys())}")

    if eval_result:
        logger.info(f"  Test accuracy: {eval_result.get('accuracy', 'N/A')}")
        logger.info(f"  Test F1: {eval_result.get('f1', 'N/A')}")

    if bench_result:
        logger.info(f"  Throughput: {bench_result.get('throughput_images_per_second', 'N/A')} img/s")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete ML pipeline.")
    parser.add_argument("--source", required=True, help="Dataset source (path or URL)")
    parser.add_argument("--epochs", type=int, default=30, help="Training epochs (default: 30)")
    parser.add_argument("--device", default="cpu", help="Device (default: cpu)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate (default: 0.001)")

    args = parser.parse_args()

    summary = pipeline(
        source=args.source,
        epochs=args.epochs,
        device=args.device,
        batch_size=args.batch_size,
        lr=args.lr,
    )

    # Save summary
    summary_path = Path("reports") / "ml" / "pipeline_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nPipeline summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
