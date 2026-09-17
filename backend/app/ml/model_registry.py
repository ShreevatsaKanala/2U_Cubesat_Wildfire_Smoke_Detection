"""
Model registry for managing ML models in the CubeSat digital twin.

Stores model files, metadata, and version information in a
standardized directory structure under data/models/.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModelRegistry:
    """Registry for managing ML models."""

    def __init__(self, models_dir: str = "data/models") -> None:
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def register(self, name: str, model: Any, config: Dict[str, Any]) -> str:
        """Register a model with config.

        Args:
            name: Model name (e.g. 'smoke-classifier').
            model: The model object (PyTorch, ONNX, etc.).
            config: Model configuration metadata.

        Returns:
            Version string assigned to the registered model.
        """
        version = config.get("version", datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
        model_dir = self.models_dir / name / version
        model_dir.mkdir(parents=True, exist_ok=True)

        # Determine framework and save
        framework = config.get("framework", "unknown")
        export_format = config.get("export_format", "pt")

        if framework == "pytorch":
            model_path = model_dir / f"model.{export_format}"
            try:
                import torch
                torch.save(model.state_dict(), model_path)
            except ImportError:
                raise ImportError("torch is required to save PyTorch models")
        elif framework == "onnx":
            model_path = model_dir / f"model.onnx"
            if hasattr(model, "save"):
                model.save(str(model_path))
        else:
            model_path = model_dir / f"model.{export_format}"

        # Build metadata
        metadata = {
            "name": name,
            "version": version,
            "architecture": config.get("architecture", "unknown"),
            "input_resolution": config.get("input_resolution", [224, 224]),
            "num_classes": config.get("num_classes", 2),
            "class_names": config.get("class_names", ["non_smoke", "smoke"]),
            "training_date": config.get("training_date", datetime.now(timezone.utc).isoformat()),
            "dataset": config.get("dataset", "unknown"),
            "metrics": config.get("metrics", {}),
            "threshold": config.get("threshold", 0.5),
            "model_size_bytes": model_path.stat().st_size if model_path.exists() else 0,
            "parameter_count": config.get("parameter_count", 0),
            "framework": framework,
            "export_format": export_format,
            "model_path": str(model_path),
        }

        self.save_metadata(name, metadata)
        return version

    def load(self, name: str, version: Optional[str] = None) -> Any:
        """Load a registered model.

        Args:
            name: Model name.
            version: Specific version to load. If None, loads latest.

        Returns:
            Loaded model object.

        Raises:
            FileNotFoundError: If model file not found.
        """
        if version is None:
            version = self._get_latest_version(name)

        if version is None:
            raise FileNotFoundError(f"No model versions found for '{name}'")

        metadata = self.load_metadata(name, version)
        model_path = Path(metadata["model_path"])

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        framework = metadata.get("framework", "unknown")

        if framework == "pytorch":
            try:
                import torch
                checkpoint = torch.load(str(model_path), map_location="cpu", weights_only=False)
                return checkpoint
            except ImportError:
                raise ImportError("torch is required to load PyTorch models")

        return model_path

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models with their latest version info."""
        models = []
        for model_dir in sorted(self.models_dir.iterdir()):
            if not model_dir.is_dir():
                continue

            name = model_dir.name
            latest_version = self._get_latest_version(name)
            if latest_version is None:
                continue

            metadata = self.load_metadata(name, latest_version)
            models.append(metadata)

        return models

    def get_model_info(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Get model metadata without loading the model."""
        if version is None:
            version = self._get_latest_version(name)

        if version is None:
            raise FileNotFoundError(f"No model versions found for '{name}'")

        return self.load_metadata(name, version)

    def save_metadata(self, name: str, metadata: Dict[str, Any], version: Optional[str] = None) -> None:
        """Save model metadata to JSON file."""
        if version is None:
            version = metadata.get("version", "latest")

        model_dir = self.models_dir / name / version
        model_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = model_dir / "model_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def load_metadata(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Load model metadata from JSON file."""
        if version is None:
            version = self._get_latest_version(name)

        if version is None:
            raise FileNotFoundError(f"No model versions found for '{name}'")

        metadata_path = self.models_dir / name / version / "model_metadata.json"
        if not metadata_path.exists():
            return {"name": name, "version": version}

        with open(metadata_path) as f:
            return json.load(f)

    def _get_latest_version(self, name: str) -> Optional[str]:
        """Get the latest version string for a model."""
        model_dir = self.models_dir / name
        if not model_dir.exists():
            return None

        versions = sorted(
            [d.name for d in model_dir.iterdir() if d.is_dir()],
            reverse=True,
        )
        return versions[0] if versions else None
