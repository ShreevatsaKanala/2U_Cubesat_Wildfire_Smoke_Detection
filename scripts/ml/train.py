"""
Train smoke detection classifier models.

Supports baseline CNN, MobileNetV3 Small, and MobileNetV3 Large architectures.
Saves best model, training config, and metrics.

Usage:
    python scripts/ml/train.py --data data/splits/ --model mobilenet_v3_small --epochs 30
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
    from PIL import Image

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.error("PyTorch is required. Install with: pip install torch torchvision")

# Add project root to path for ML module imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class SmokeDataset(Dataset):
    """Dataset for loading smoke/non-smoke images."""

    def __init__(
        self,
        image_ids: List[str],
        labels: Dict[str, Dict[str, Any]],
        data_root: Path,
        transform=None,
    ):
        self.image_ids = image_ids
        self.labels = labels
        self.data_root = data_root
        self.transform = transform
        self.class_to_idx = {"non_smoke": 0, "smoke": 1}

    def __len__(self) -> int:
        return len(self.image_ids)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        image_id = self.image_ids[idx]
        meta = self.labels[image_id]

        # Resolve image path
        filename = meta.get("filename", image_id)
        img_path = self.data_root / filename
        if not img_path.exists():
            img_path = self.data_root / "raw" / filename

        img = Image.open(img_path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        else:
            img = img.resize((224, 224))
            img = torch.from_numpy(np.array(img)).permute(2, 0, 1).float() / 255.0
            mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
            std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
            img = (img - mean) / std

        label = self.class_to_idx.get(meta["class"], 0)
        return img, label


class BaselineCNN(nn.Module):
    """Simple CNN baseline (~100K params)."""

    def __init__(self, num_classes: int = 2):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x


def build_model(model_name: str, num_classes: int = 2) -> nn.Module:
    """Build and return the requested model architecture."""
    if model_name == "baseline":
        return BaselineCNN(num_classes)

    try:
        import torchvision.models as tv_models
    except ImportError:
        raise ImportError("torchvision is required for MobileNet models. Install with: pip install torchvision")

    if model_name == "mobilenet_v3_small":
        model = tv_models.mobilenet_v3_small(pretrained=True)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, num_classes)
        return model

    if model_name == "mobilenet_v3_large":
        model = tv_models.mobilenet_v3_large(pretrained=True)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, num_classes)
        return model

    raise ValueError(f"Unknown model: {model_name}. Choose from: baseline, mobilenet_v3_small, mobilenet_v3_large")


def count_parameters(model: nn.Module) -> int:
    """Count total trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def load_splits(data_dir: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load splits.json and labels from the data directory."""
    splits_path = data_dir / "splits.json"
    if not splits_path.exists():
        raise FileNotFoundError(f"splits.json not found in {data_dir}. Run split_dataset.py first.")

    with open(splits_path) as f:
        splits = json.load(f)

    # Try to find labels
    labels_path = data_dir / "labels_with_splits.json"
    if not labels_path.exists():
        labels_path = data_dir.parent / "labels" / "labels.json"
    if not labels_path.exists():
        labels_path = data_dir / "labels.json"

    if not labels_path.exists():
        raise FileNotFoundError(f"Labels file not found. Searched: {labels_path}")

    with open(labels_path) as f:
        labels = json.load(f)

    return splits, labels


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
) -> Dict[str, float]:
    """Train for one epoch, return loss and accuracy."""
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for images, targets in loader:
        images, targets = images.to(device), targets.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * images.size(0)
        _, predicted = outputs.max(1)
        correct += predicted.eq(targets).sum().item()
        total += targets.size(0)

    return {
        "loss": round(total_loss / total, 4) if total > 0 else 0,
        "accuracy": round(correct / total, 4) if total > 0 else 0,
    }


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Dict[str, float]:
    """Evaluate model, return loss, accuracy, F1."""
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, targets in loader:
            images, targets = images.to(device), targets.to(device)
            outputs = model(images)
            loss = criterion(outputs, targets)

            total_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(targets.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    total = len(all_labels)

    accuracy = float(np.mean(all_preds == all_labels))

    # Calculate F1 for binary classification
    tp = int(np.sum((all_labels == 1) & (all_preds == 1)))
    fp = int(np.sum((all_labels == 0) & (all_preds == 1)))
    fn = int(np.sum((all_labels == 1) & (all_preds == 0)))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "loss": round(total_loss / total, 4) if total > 0 else 0,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def train(
    data_dir: Path,
    model_name: str,
    epochs: int = 30,
    batch_size: int = 32,
    lr: float = 0.001,
    device_str: str = "cpu",
    output_dir: Path = Path("data/models"),
) -> Dict[str, Any]:
    """Full training pipeline.

    Args:
        data_dir: Directory containing splits.json and images.
        model_name: Model architecture name.
        epochs: Number of training epochs.
        batch_size: Batch size.
        lr: Learning rate.
        device_str: Device string (cpu/cuda).
        output_dir: Where to save trained models.

    Returns:
        Training results dict with metrics and paths.
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for training.")

    device = torch.device(device_str)
    logger.info(f"Using device: {device}")

    # Set seeds for reproducibility
    torch.manual_seed(42)
    np.random.seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)

    # Load data
    splits, labels = load_splits(data_dir)

    train_dataset = SmokeDataset(splits["train"], labels, data_dir.parent)
    val_dataset = SmokeDataset(splits["val"], labels, data_dir.parent)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    logger.info(f"Training: {len(train_dataset)} images, Validation: {len(val_dataset)} images")

    # Build model
    model = build_model(model_name, num_classes=2)
    model = model.to(device)
    param_count = count_parameters(model)
    logger.info(f"Model '{model_name}' has {param_count:,} parameters")

    # Training setup
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=3)

    # Training loop
    best_f1 = 0.0
    patience_counter = 0
    early_stop_patience = 7
    training_log: List[Dict[str, Any]] = []

    model_output_dir = output_dir / model_name
    model_output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting training for {epochs} epochs...")

    for epoch in range(1, epochs + 1):
        start_time = time.time()

        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_metrics = evaluate(model, val_loader, criterion, device)

        scheduler.step(val_metrics["f1"])

        elapsed = round(time.time() - start_time, 1)

        epoch_log = {
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "train_accuracy": train_metrics["accuracy"],
            "val_loss": val_metrics["loss"],
            "val_accuracy": val_metrics["accuracy"],
            "val_f1": val_metrics["f1"],
            "val_precision": val_metrics["precision"],
            "val_recall": val_metrics["recall"],
            "learning_rate": optimizer.param_groups[0]["lr"],
            "elapsed_seconds": elapsed,
        }
        training_log.append(epoch_log)

        logger.info(
            f"Epoch {epoch:3d}/{epochs} | "
            f"train_loss={train_metrics['loss']:.4f} | "
            f"val_f1={val_metrics['f1']:.4f} | "
            f"val_acc={val_metrics['accuracy']:.4f} | "
            f"lr={optimizer.param_groups[0]['lr']:.6f} | "
            f"{elapsed}s"
        )

        # Save best model
        if val_metrics["f1"] > best_f1:
            best_f1 = val_metrics["f1"]
            patience_counter = 0

            torch.save(model.state_dict(), model_output_dir / "best_model.pt")
            logger.info(f"  -> New best F1: {best_f1:.4f}, model saved")
        else:
            patience_counter += 1

        # Early stopping
        if patience_counter >= early_stop_patience:
            logger.info(f"Early stopping at epoch {epoch} (no improvement for {early_stop_patience} epochs)")
            break

    # Save training artifacts
    config = {
        "architecture": model_name,
        "num_classes": 2,
        "class_names": ["non_smoke", "smoke"],
        "input_resolution": [224, 224],
        "epochs_trained": len(training_log),
        "batch_size": batch_size,
        "learning_rate": lr,
        "optimizer": "adam",
        "scheduler": "ReduceLROnPlateau",
        "early_stopping_patience": early_stop_patience,
        "device": device_str,
        "parameter_count": param_count,
        "best_val_f1": best_f1,
        "training_date": datetime.now(timezone.utc).isoformat(),
    }

    with open(model_output_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    with open(model_output_dir / "training_log.json", "w") as f:
        json.dump(training_log, f, indent=2)

    class_mapping = {"non_smoke": 0, "smoke": 1}
    with open(model_output_dir / "class_mapping.json", "w") as f:
        json.dump(class_mapping, f, indent=2)

    logger.info(f"\nTraining complete. Best validation F1: {best_f1:.4f}")
    logger.info(f"Model saved to: {model_output_dir / 'best_model.pt'}")

    return {
        "model_name": model_name,
        "model_path": str(model_output_dir / "best_model.pt"),
        "config_path": str(model_output_dir / "config.json"),
        "best_val_f1": best_f1,
        "epochs_trained": len(training_log),
        "parameter_count": param_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train smoke detection classifier.")
    parser.add_argument("--data", default="data/splits", help="Data directory with splits.json")
    parser.add_argument(
        "--model",
        default="mobilenet_v3_small",
        choices=["baseline", "mobilenet_v3_small", "mobilenet_v3_large"],
        help="Model architecture (default: mobilenet_v3_small)",
    )
    parser.add_argument("--epochs", type=int, default=30, help="Training epochs (default: 30)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate (default: 0.001)")
    parser.add_argument("--device", default="cpu", help="Device: cpu or cuda (default: cpu)")
    parser.add_argument("--output", default="data/models", help="Output directory (default: data/models)")

    args = parser.parse_args()

    result = train(
        data_dir=Path(args.data),
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        device_str=args.device,
        output_dir=Path(args.output),
    )

    print(f"\nTraining complete:")
    print(f"  Model: {result['model_name']}")
    print(f"  Best F1: {result['best_val_f1']:.4f}")
    print(f"  Parameters: {result['parameter_count']:,}")
    print(f"  Saved to: {result['model_path']}")


if __name__ == "__main__":
    main()
