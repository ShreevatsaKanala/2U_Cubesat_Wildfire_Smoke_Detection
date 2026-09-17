"""
Evaluate trained smoke detection model on test set.

Generates comprehensive metrics report, confusion matrix,
threshold analysis, and error analysis.

Usage:
    python scripts/ml/evaluate.py --model data/models/best_model.pt --data data/splits/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    import numpy as np
    import torch
    from torch.utils.data import DataLoader
    from PIL import Image

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.error("PyTorch is required. Install with: pip install torch torchvision")

# Add project root for ML module imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

try:
    from app.ml.metrics import MLMetrics

    MLMETRICS_AVAILABLE = True
except ImportError:
    MLMETRICS_AVAILABLE = False
    logger.warning("MLMetrics not available from app.ml.metrics, using local implementation")


IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class EvalDataset(torch.utils.data.Dataset):
    """Dataset for evaluation."""

    def __init__(self, image_ids: List[str], labels: Dict[str, Any], data_root: Path):
        self.image_ids = image_ids
        self.labels = labels
        self.data_root = data_root
        self.class_to_idx = {"non_smoke": 0, "smoke": 1}

    def __len__(self) -> int:
        return len(self.image_ids)

    def __getitem__(self, idx: int):
        image_id = self.image_ids[idx]
        meta = self.labels[image_id]

        filename = meta.get("filename", image_id)
        img_path = self.data_root / filename
        if not img_path.exists():
            img_path = self.data_root / "raw" / filename

        img = Image.open(img_path).convert("RGB")
        img = img.resize((224, 224))
        tensor = torch.from_numpy(np.array(img)).permute(2, 0, 1).float() / 255.0
        mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
        std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
        tensor = (tensor - mean) / std

        label = self.class_to_idx.get(meta["class"], 0)
        return tensor, label, image_id


def load_model_for_eval(model_path: Path, model_name: str = "mobilenet_v3_small") -> torch.nn.Module:
    """Load a trained model for evaluation."""
    try:
        import torchvision.models as tv_models
    except ImportError:
        raise ImportError("torchvision is required")

    if model_name == "baseline":
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
    return model


def load_config(model_dir: Path) -> Dict[str, Any]:
    """Load model config to determine architecture."""
    config_path = model_dir / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {"architecture": "mobilenet_v3_small"}


def run_inference(
    model: torch.nn.Module,
    dataloader: DataLoader,
    device: torch.device,
) -> Dict[str, Any]:
    """Run inference on all samples and collect results."""
    all_probs = []
    all_labels = []
    all_preds = []
    all_image_ids = []

    model.eval()
    with torch.no_grad():
        for images, labels, image_ids in dataloader:
            images = images.to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)

            smoke_probs = probs[:, 1].cpu().numpy()
            preds = probs.argmax(dim=1).cpu().numpy()

            all_probs.extend(smoke_probs.tolist())
            all_labels.extend(labels.numpy().tolist())
            all_preds.extend(preds.tolist())
            all_image_ids.extend(image_ids)

    return {
        "y_true": np.array(all_labels),
        "y_pred": np.array(all_preds),
        "y_prob": np.array(all_probs),
        "image_ids": all_image_ids,
    }


def threshold_analysis(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    thresholds: List[float] = None,
) -> List[Dict[str, Any]]:
    """Compute metrics at different classification thresholds."""
    if thresholds is None:
        thresholds = [round(t, 2) for t in np.arange(0.1, 1.0, 0.1)]

    results = []
    for thresh in thresholds:
        y_pred = (y_prob >= thresh).astype(int)

        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        tn = int(np.sum((y_true == 0) & (y_pred == 0)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        results.append({
            "threshold": round(float(thresh), 2),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "fpr": round(fpr, 4),
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        })

    return results


def error_analysis(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    image_ids: List[str],
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Identify and categorize misclassifications."""
    false_positives = []
    false_negatives = []

    for i in range(len(y_true)):
        entry = {
            "image_id": image_ids[i],
            "true_label": "smoke" if y_true[i] == 1 else "non_smoke",
            "predicted_label": "smoke" if y_pred[i] == 1 else "non_smoke",
            "probability": round(float(y_prob[i]), 4),
        }

        if y_true[i] == 0 and y_pred[i] == 1:
            false_positives.append(entry)
        elif y_true[i] == 1 and y_pred[i] == 0:
            false_negatives.append(entry)

    return {
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "total_false_positives": len(false_positives),
        "total_false_negatives": len(false_negatives),
    }


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """Compute binary confusion matrix."""
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))

    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def evaluate(
    model_path: Path,
    data_dir: Path,
    split: str = "test",
    threshold: float = 0.5,
    output_dir: Path = Path("reports/ml"),
) -> Dict[str, Any]:
    """Full evaluation pipeline.

    Args:
        model_path: Path to trained model weights.
        data_dir: Directory containing splits.json and images.
        split: Which split to evaluate on.
        threshold: Classification threshold.
        output_dir: Where to save reports.

    Returns:
        Evaluation results dict.
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for evaluation.")

    device = torch.device("cpu")

    # Load splits and labels
    splits_path = data_dir / "splits.json"
    if not splits_path.exists():
        raise FileNotFoundError(f"splits.json not found in {data_dir}")

    with open(splits_path) as f:
        splits = json.load(f)

    labels_path = data_dir / "labels_with_splits.json"
    if not labels_path.exists():
        labels_path = data_dir.parent / "labels" / "labels.json"
    if not labels_path.exists():
        labels_path = data_dir / "labels.json"

    with open(labels_path) as f:
        labels = json.load(f)

    split_ids = splits.get(split, [])
    if not split_ids:
        logger.error(f"No images found for split '{split}'")
        return {}

    logger.info(f"Evaluating on {split} split: {len(split_ids)} images")

    # Load model
    config = load_config(model_path.parent)
    model_name = config.get("architecture", "mobilenet_v3_small")
    model = load_model_for_eval(model_path, model_name)
    model = model.to(device)
    logger.info(f"Loaded model: {model_name}")

    # Create dataloader
    dataset = EvalDataset(split_ids, labels, data_dir.parent)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False, num_workers=0)

    # Run inference
    logger.info("Running inference...")
    results = run_inference(model, dataloader, device)

    y_true = results["y_true"]
    y_pred = results["y_pred"]
    y_prob = results["y_prob"]
    image_ids = results["image_ids"]

    # Calculate metrics
    logger.info("Calculating metrics...")
    accuracy = float(np.mean(y_true == y_pred))

    cm = confusion_matrix(y_true, y_pred)
    tp, fp, tn, fn = cm["tp"], cm["fp"], cm["tn"], cm["fn"]

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    # Additional analyses
    thresh_analysis = threshold_analysis(y_true, y_prob)
    err_analysis = error_analysis(y_true, y_pred, y_prob, image_ids, threshold)

    # Build report
    output_dir.mkdir(parents=True, exist_ok=True)

    # Classification report text
    report_text = (
        f"{'='*60}\n"
        f"  Classification Report ({split} split)\n"
        f"{'='*60}\n\n"
        f"  {'Class':<15} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}\n"
        f"  {'-'*55}\n"
    )

    for cls_name in ["non_smoke", "smoke"]:
        if cls_name == "non_smoke":
            cls_tp, cls_fp, cls_fn = tn, fn, fp
        else:
            cls_tp, cls_fp, cls_fn = tp, fp, fn
        cls_precision = cls_tp / (cls_tp + cls_fp) if (cls_tp + cls_fp) > 0 else 0.0
        cls_recall = cls_tp / (cls_tp + cls_fn) if (cls_tp + cls_fn) > 0 else 0.0
        cls_f1 = 2 * cls_precision * cls_recall / (cls_precision + cls_recall) if (cls_precision + cls_recall) > 0 else 0.0
        cls_support = cls_tp + cls_fn
        report_text += f"  {cls_name:<15} {cls_precision:>10.4f} {cls_recall:>10.4f} {cls_f1:>10.4f} {cls_support:>10}\n"

    report_text += (
        f"\n  {'Accuracy':<15} {accuracy:>10.4f}\n"
        f"  {'Precision':<15} {precision:>10.4f}\n"
        f"  {'Recall':<15} {recall:>10.4f}\n"
        f"  {'F1-Score':<15} {f1:>10.4f}\n"
        f"  {'FPR':<15} {fpr:>10.4f}\n"
        f"  {'FNR':<15} {fnr:>10.4f}\n"
    )

    # Save reports
    with open(output_dir / "classification_report.txt", "w") as f:
        f.write(report_text)

    with open(output_dir / "confusion_matrix.json", "w") as f:
        json.dump(cm, f, indent=2)

    with open(output_dir / "threshold_analysis.json", "w") as f:
        json.dump(thresh_analysis, f, indent=2)

    with open(output_dir / "error_analysis.json", "w") as f:
        json.dump(err_analysis, f, indent=2)

    model_performance = {
        "model_path": str(model_path),
        "model_architecture": model_name,
        "split": split,
        "num_samples": len(split_ids),
        "threshold": threshold,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
        "fnr": round(fnr, 4),
        "confusion_matrix": cm,
    }

    with open(output_dir / "model_performance.json", "w") as f:
        json.dump(model_performance, f, indent=2)

    logger.info(f"Reports saved to {output_dir}")

    # Print summary
    print(report_text)
    print(f"  Confusion Matrix: TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"  Reports saved to: {output_dir}")

    return model_performance


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate trained smoke detection model.")
    parser.add_argument("--model", required=True, help="Path to trained model weights (.pt)")
    parser.add_argument("--data", default="data/splits", help="Data directory (default: data/splits)")
    parser.add_argument("--split", default="test", help="Split to evaluate (default: test)")
    parser.add_argument("--threshold", type=float, default=0.5, help="Classification threshold (default: 0.5)")
    parser.add_argument("--output", default="reports/ml", help="Output directory (default: reports/ml)")

    args = parser.parse_args()

    result = evaluate(
        model_path=Path(args.model),
        data_dir=Path(args.data),
        split=args.split,
        threshold=args.threshold,
        output_dir=Path(args.output),
    )

    if result:
        print(f"\nEvaluation complete:")
        print(f"  Accuracy:  {result['accuracy']:.4f}")
        print(f"  Precision: {result['precision']:.4f}")
        print(f"  Recall:    {result['recall']:.4f}")
        print(f"  F1:        {result['f1']:.4f}")


if __name__ == "__main__":
    main()
