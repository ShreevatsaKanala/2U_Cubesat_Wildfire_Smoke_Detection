"""
Benchmark model inference performance.

Measures preprocessing, inference, and total pipeline latency,
memory usage, and throughput.

NOTE: This benchmarks on the desktop/host, NOT on Raspberry Pi 5.
Results are indicative of model complexity, not deployment performance.

Usage:
    python scripts/ml/benchmark.py --model data/models/best_model.pt --iterations 100
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    import numpy as np
    import torch
    from PIL import Image

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.error("PyTorch is required. Install with: pip install torch torchvision")

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.info("psutil not installed, memory metrics will be skipped")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def load_model_for_benchmark(model_path: Path) -> torch.nn.Module:
    """Load a trained model for benchmarking."""
    config_path = model_path.parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        model_name = config.get("architecture", "mobilenet_v3_small")
    else:
        model_name = "mobilenet_v3_small"

    try:
        import torchvision.models as tv_models
    except ImportError:
        raise ImportError("torchvision is required")

    if model_name == "baseline":
        sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "ml"))
        from train import BaselineCNN
        model = BaselineCNN(num_classes=2)
    elif model_name == "mobilenet_v3_small":
        model = tv_models.mobilenet_v3_small(pretrained=False)
        in_features = model.classifier[3].in_features
        model.classifier[3] = torch.nn.Linear(in_features, 2)
    elif model_name == "mobilenet_v3_large":
        model = tv_models.mobilenet_v3_large(pretrained=False)
        in_features = model.classifier[3].in_features
        model.classifier[3] = torch.nn.Linear(in_features, 2)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    state_dict = torch.load(str(model_path), map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    return model, model_name


def create_synthetic_image(resolution: int = 224) -> Image.Image:
    """Create a random RGB image for benchmarking."""
    arr = np.random.randint(0, 256, (resolution, resolution, 3), dtype=np.uint8)
    return Image.fromarray(arr)


def preprocess_image(img: Image.Image, resolution: int = 224) -> torch.Tensor:
    """Preprocess image to tensor (mirrors Preprocessor logic)."""
    img = img.resize((resolution, resolution))
    tensor = torch.from_numpy(np.array(img)).permute(2, 0, 1).float() / 255.0
    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
    tensor = (tensor - mean) / std
    return tensor.unsqueeze(0)


def compute_stats(values: List[float]) -> Dict[str, float]:
    """Compute statistics for a list of measurements."""
    if not values:
        return {}
    return {
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "p50": round(statistics.median(values), 4),
        "p95": round(np.percentile(values, 95), 4),
        "p99": round(np.percentile(values, 99), 4),
    }


def benchmark(
    model_path: Path,
    iterations: int = 100,
    warmup: int = 10,
    device_str: str = "cpu",
    resolution: int = 224,
    output_dir: Path = Path("reports/ml"),
) -> Dict[str, Any]:
    """Run inference benchmark.

    Args:
        model_path: Path to trained model weights.
        iterations: Number of benchmark iterations.
        warmup: Number of warmup iterations.
        device_str: Device to benchmark on.
        resolution: Input image resolution.
        output_dir: Where to save results.

    Returns:
        Benchmark results dict.
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for benchmarking.")

    device = torch.device(device_str)
    model, model_name = load_model_for_benchmark(model_path)
    model = model.to(device)

    process = psutil.Process() if PSUTIL_AVAILABLE else None

    logger.info(f"Benchmarking {model_name} on {device}")
    logger.info(f"  Iterations: {iterations}, Warmup: {warmup}, Resolution: {resolution}")

    # Warmup
    logger.info(f"Running {warmup} warmup iterations...")
    for _ in range(warmup):
        img = create_synthetic_image(resolution)
        tensor = preprocess_image(img, resolution).to(device)
        with torch.no_grad():
            model(tensor)

    # Benchmark
    preprocess_times = []
    inference_times = []
    total_times = []
    memory_usage = []

    logger.info(f"Running {iterations} benchmark iterations...")
    for i in range(iterations):
        if PSUTIL_AVAILABLE:
            gc.collect()
            mem_before = process.memory_info().rss / (1024 * 1024)

        # Preprocessing
        t0 = time.perf_counter()
        img = create_synthetic_image(resolution)
        tensor = preprocess_image(img, resolution).to(device)
        t1 = time.perf_counter()

        # Inference
        with torch.no_grad():
            _ = model(tensor)
        t2 = time.perf_counter()

        preprocess_ms = (t1 - t0) * 1000
        inference_ms = (t2 - t1) * 1000
        total_ms = (t2 - t0) * 1000

        preprocess_times.append(preprocess_ms)
        inference_times.append(inference_ms)
        total_times.append(total_ms)

        if PSUTIL_AVAILABLE:
            mem_after = process.memory_info().rss / (1024 * 1024)
            memory_usage.append(mem_after - mem_before)

    # Throughput
    avg_total_ms = statistics.mean(total_times)
    throughput = 1000.0 / avg_total_ms if avg_total_ms > 0 else 0

    results = {
        "model_name": model_name,
        "model_path": str(model_path),
        "device": device_str,
        "resolution": resolution,
        "iterations": iterations,
        "warmup_iterations": warmup,
        "note": "Desktop/host benchmarking only. NOT representative of Raspberry Pi 5 performance.",
        "preprocessing_latency_ms": compute_stats(preprocess_times),
        "inference_latency_ms": compute_stats(inference_times),
        "total_pipeline_latency_ms": compute_stats(total_times),
        "throughput_images_per_second": round(throughput, 2),
        "parameter_count": sum(p.numel() for p in model.parameters()),
    }

    if PSUTIL_AVAILABLE and memory_usage:
        results["memory_usage_mb"] = compute_stats(memory_usage)

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "benchmark_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved to {results_path}")

    # Print formatted table
    print(f"\n{'='*60}")
    print(f"  Benchmark Results: {model_name}")
    print(f"{'='*60}")
    print(f"  Device: {device_str} | Resolution: {resolution}x{resolution}")
    print(f"  Iterations: {iterations} | Warmup: {warmup}")
    print(f"  NOTE: Desktop benchmarking only, not RPi5 performance")
    print(f"{'='*60}")
    print()
    print(f"  {'Metric':<30} {'Mean (ms)':>10} {'Std (ms)':>10} {'Min (ms)':>10} {'P95 (ms)':>10}")
    print(f"  {'-'*70}")

    for key, label in [
        ("preprocessing_latency_ms", "Preprocessing"),
        ("inference_latency_ms", "Inference"),
        ("total_pipeline_latency_ms", "Total Pipeline"),
    ]:
        s = results[key]
        print(f"  {label:<30} {s['mean']:>10.2f} {s['std']:>10.2f} {s['min']:>10.2f} {s['p95']:>10.2f}")

    print()
    print(f"  Throughput: {results['throughput_images_per_second']:.2f} images/sec")
    print(f"  Parameters: {results['parameter_count']:,}")

    if "memory_usage_mb" in results:
        mem = results["memory_usage_mb"]
        print(f"  Memory delta: {mem['mean']:.2f} MB (mean)")

    print(f"{'='*60}\n")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark model inference performance.")
    parser.add_argument("--model", required=True, help="Path to trained model weights (.pt)")
    parser.add_argument("--iterations", type=int, default=100, help="Benchmark iterations (default: 100)")
    parser.add_argument("--warmup", type=int, default=10, help="Warmup iterations (default: 10)")
    parser.add_argument("--device", default="cpu", help="Device (default: cpu)")
    parser.add_argument("--resolution", type=int, default=224, help="Input resolution (default: 224)")
    parser.add_argument("--output", default="reports/ml", help="Output directory (default: reports/ml)")

    args = parser.parse_args()

    benchmark(
        model_path=Path(args.model),
        iterations=args.iterations,
        warmup=args.warmup,
        device_str=args.device,
        resolution=args.resolution,
        output_dir=Path(args.output),
    )


if __name__ == "__main__":
    main()
