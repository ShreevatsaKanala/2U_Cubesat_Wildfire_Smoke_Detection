"""
Export trained model for deployment.

Converts PyTorch models to ONNX format with verification.
Saves deployment metadata.

Usage:
    python scripts/ml/export.py --model data/models/best_model.pt --format onnx
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    import numpy as np
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.error("PyTorch is required. Install with: pip install torch")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))


def load_model_for_export(model_path: Path) -> Tuple[torch.nn.Module, str]:
    """Load a trained model for export."""
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
        raise ImportError("torchvision is required for MobileNet models")

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
        raise ValueError(f"Unknown model architecture: {model_name}")

    state_dict = torch.load(str(model_path), map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    return model, model_name


def count_parameters(model: torch.nn.Module) -> int:
    """Count total parameters."""
    return sum(p.numel() for p in model.parameters())


def export_to_onnx(
    model: torch.nn.Module,
    output_path: Path,
    input_shape: Tuple[int, int] = (224, 224),
    opset_version: int = 17,
) -> bool:
    """Export model to ONNX format and verify with onnxruntime."""
    dummy_input = torch.randn(1, 3, *input_shape)

    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "output": {0: "batch_size"},
        },
    )

    logger.info(f"ONNX model exported to {output_path}")

    # Verify with onnxruntime
    try:
        import onnxruntime as ort

        session = ort.InferenceSession(str(output_path))
        test_input = dummy_input.numpy()
        outputs = session.run(None, {"input": test_input})
        logger.info(f"ONNX verification passed. Output shape: {outputs[0].shape}")
        return True
    except ImportError:
        logger.warning("onnxruntime not installed, skipping verification")
        return False
    except Exception as e:
        logger.error(f"ONNX verification failed: {e}")
        return False


def get_model_size(path: Path) -> int:
    """Get file size in bytes."""
    return path.stat().st_size if path.exists() else 0


def export_model(
    model_path: Path,
    export_format: str = "onnx",
    output_dir: Path = Path("data/models"),
) -> Dict[str, Any]:
    """Full export pipeline.

    Args:
        model_path: Path to trained model weights.
        export_format: Export format (onnx, torchscript, or both).
        output_dir: Output directory.

    Returns:
        Export metadata dict.
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for export.")

    model, model_name = load_model_for_export(model_path)
    num_params = count_parameters(model)
    input_shape = (224, 224)

    output_dir.mkdir(parents=True, exist_ok=True)
    exported_files = []
    verification_passed = False

    # Export ONNX
    if export_format in ("onnx", "both"):
        onnx_path = output_dir / "deployment_model.onnx"
        verification_passed = export_to_onnx(model, onnx_path, input_shape)
        exported_files.append(str(onnx_path))

    # Export TorchScript
    if export_format in ("torchscript", "both"):
        ts_path = output_dir / "deployment_model.pt"
        dummy_input = torch.randn(1, 3, *input_shape)
        try:
            traced = torch.jit.trace(model, dummy_input)
            traced.save(str(ts_path))
            exported_files.append(str(ts_path))
            logger.info(f"TorchScript model exported to {ts_path}")
        except Exception as e:
            logger.error(f"TorchScript export failed: {e}")

    # Build metadata
    primary_path = Path(exported_files[0]) if exported_files else output_dir / "deployment_model.onnx"

    metadata = {
        "name": model_name,
        "version": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "architecture": model_name,
        "input_shape": [1, 3, *input_shape],
        "output_shape": [1, 2],
        "num_parameters": num_params,
        "model_size_bytes": get_model_size(primary_path),
        "framework": "pytorch",
        "export_format": export_format,
        "quantization": "none",
        "onnx_verification": verification_passed if export_format in ("onnx", "both") else None,
        "export_date": datetime.now(timezone.utc).isoformat(),
        "source_model": str(model_path),
    }

    metadata_path = output_dir / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Metadata saved to {metadata_path}")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Export trained model for deployment.")
    parser.add_argument("--model", required=True, help="Path to trained model weights (.pt)")
    parser.add_argument(
        "--format",
        default="onnx",
        choices=["onnx", "torchscript", "both"],
        help="Export format (default: onnx)",
    )
    parser.add_argument("--output", default="data/models", help="Output directory (default: data/models)")

    args = parser.parse_args()

    metadata = export_model(
        model_path=Path(args.model),
        export_format=args.format,
        output_dir=Path(args.output),
    )

    print(f"\nExport complete:")
    print(f"  Architecture: {metadata['architecture']}")
    print(f"  Parameters: {metadata['num_parameters']:,}")
    print(f"  Format: {metadata['export_format']}")
    print(f"  Model size: {metadata['model_size_bytes']:,} bytes")
    if metadata.get("onnx_verification") is not None:
        print(f"  ONNX verification: {'passed' if metadata['onnx_verification'] else 'failed'}")


if __name__ == "__main__":
    main()
