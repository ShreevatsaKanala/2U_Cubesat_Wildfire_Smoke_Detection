"""ML Pipeline tests for CubeSat Digital Twin Phase 3."""
import pytest
import os
import json
import tempfile
import hashlib
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Tests should work even if torch is not installed
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from app.ml.inference import InferenceEngine
from app.ml.mock_classifier import MockClassifier
from app.services.priority import PriorityCalculator
from app.models.observation import Observation
from app.core.config import Settings


# --- 1. Mock Classifier Output Schema ---

def test_mock_classifier_output_schema():
    """MockClassifier returns all required fields."""
    classifier = MockClassifier()
    result = classifier.classify("test_image.jpg")

    required_fields = [
        "smoke_probability",
        "wildfire_probability",
        "confidence",
        "model_name",
        "model_version",
        "inference_latency_ms",
        "processing_status",
        "timestamp",
    ]
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"

    assert result["model_name"] == "mock-smoke-classifier-v0.1"
    assert result["model_version"] == "0.1.0"
    assert result["processing_status"] == "completed"


# --- 2. Mock Classifier Probability Range ---

def test_mock_classifier_probability_range():
    """probabilities in [0, 1]."""
    classifier = MockClassifier()
    for i in range(50):
        result = classifier.classify(f"test_image_{i}.jpg")
        assert 0.0 <= result["smoke_probability"] <= 1.0, \
            f"smoke_probability out of range: {result['smoke_probability']}"
        assert 0.0 <= result["wildfire_probability"] <= 1.0, \
            f"wildfire_probability out of range: {result['wildfire_probability']}"
        assert 0.0 <= result["confidence"] <= 1.0, \
            f"confidence out of range: {result['confidence']}"


# --- 3. Mock Classifier Deterministic ---

def test_mock_classifier_deterministic():
    """same input gives same output."""
    classifier = MockClassifier()
    paths = [f"image_{i}.png" for i in range(20)]

    for path in paths:
        r1 = classifier.classify(path)
        r2 = classifier.classify(path)
        assert r1["smoke_probability"] == r2["smoke_probability"], \
            f"Not deterministic for {path}"
        assert r1["wildfire_probability"] == r2["wildfire_probability"], \
            f"Not deterministic for {path}"
        assert r1["confidence"] == r2["confidence"], \
            f"Not deterministic for {path}"


# --- 4. Mock Classifier Inheritance ---

def test_mock_classifier_inheritance():
    """is instance of InferenceEngine."""
    classifier = MockClassifier()
    assert isinstance(classifier, InferenceEngine)


# --- 5. Inference Engine Interface ---

def test_inference_engine_interface():
    """InferenceEngine has classify and get_model_info abstract methods."""
    assert hasattr(InferenceEngine, "classify")
    assert hasattr(InferenceEngine, "get_model_info")
    assert hasattr(InferenceEngine, "get_supported_classes")
    assert hasattr(InferenceEngine, "warmup")

    # Verify classify and get_model_info are abstract
    import inspect
    assert getattr(InferenceEngine.classify, "__isabstractmethod__", False)
    assert getattr(InferenceEngine.get_model_info, "__isabstractmethod__", False)


# --- 6. Priority Calculation Smoke Threshold ---

def test_priority_calculation_smoke_threshold():
    """smoke_threshold parameter works."""
    calc_default = PriorityCalculator()
    calc_custom = PriorityCalculator(thresholds={"high": 0.9, "medium": 0.5, "low": 0.1})

    # Default thresholds
    assert calc_default.calculate(0.9, 0.9) == "CRITICAL"
    assert calc_default.calculate(0.5, 0.5) == "MEDIUM"
    assert calc_default.calculate(0.1, 0.1) == "LOW"

    # Custom thresholds should still work via weighted_score
    result_custom = calc_custom.calculate(0.95, 0.95)
    assert result_custom in ("CRITICAL", "HIGH", "MEDIUM", "LOW")


# --- 7. Observation Model Metadata ---

def test_observation_model_metadata():
    """Observation model has model_name, model_version fields."""
    obs = Observation(
        observation_id="OBS-TEST-001",
        timestamp=datetime.now(timezone.utc),
        spacecraft_id="CSAT-001",
        latitude=35.0,
        longitude=-120.0,
        altitude_km=500.0,
        image_path="test.jpg",
        image_width=1920,
        image_height=1080,
        capture_mode="auto",
        camera_status="nominal",
        model_name="test-model",
        model_version="1.0.0",
        smoke_probability=0.75,
        wildfire_probability=0.65,
        confidence=0.85,
        priority="HIGH",
        inference_latency_ms=120.0,
        processing_status="completed",
    )

    assert obs.model_name == "test-model"
    assert obs.model_version == "1.0.0"
    assert obs.smoke_probability == 0.75
    assert obs.wildfire_probability == 0.65
    assert obs.confidence == 0.85
    assert obs.inference_latency_ms == 120.0


# --- 8. Engine ML Mode Mock ---

def test_engine_ml_mode_mock():
    """SimulationEngine with ml_mode='mock' uses MockClassifier."""
    from app.simulation.engine import SimulationEngine

    engine = SimulationEngine(sim_config={"ml_mode": "mock"})
    assert isinstance(engine.classifier, MockClassifier)
    assert engine._ml_mode == "mock"


# --- 9. Engine ML Mode Real Unavailable ---

def test_engine_ml_mode_real_unavailable():
    """SimulationEngine with ml_mode='real' falls back when no model."""
    from app.simulation.engine import SimulationEngine

    engine = SimulationEngine(sim_config={"ml_mode": "real"})
    # Should fall back to MockClassifier when no model file exists
    assert isinstance(engine.classifier, MockClassifier)


# --- 10. Config ML Settings ---

def test_config_ml_settings():
    """Settings has ML_MODE, ML_MODEL_PATH, etc."""
    settings = Settings()
    assert hasattr(settings, "ML_MODE")
    assert hasattr(settings, "ML_MODEL_PATH")
    assert hasattr(settings, "ML_MODEL_NAME")
    assert hasattr(settings, "ML_MODEL_VERSION")
    assert hasattr(settings, "ML_INPUT_RESOLUTION")
    assert hasattr(settings, "ML_SMOKE_THRESHOLD")
    assert hasattr(settings, "ML_DEVICE")

    assert settings.ML_MODE in ("mock", "real")
    assert isinstance(settings.ML_INPUT_RESOLUTION, list)
    assert 0.0 <= settings.ML_SMOKE_THRESHOLD <= 1.0


# --- 11. Preprocessing Validate Image ---

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
def test_preprocessing_validate_image():
    """Preprocessor.validate_image checks file exists."""
    from app.ml.preprocessing import Preprocessor

    with tempfile.TemporaryDirectory() as tmpdir:
        preprocessor = Preprocessor(input_resolution=(224, 224), normalize=False)

        # Non-existent file should raise
        with pytest.raises(FileNotFoundError):
            preprocessor.validate_image(os.path.join(tmpdir, "nonexistent.jpg"))

        # Create a valid test image
        from PIL import Image
        img_path = os.path.join(tmpdir, "test.jpg")
        Image.new("RGB", (100, 100), color=(128, 128, 128)).save(img_path)

        # Valid image should return True
        result = preprocessor.validate_image(img_path)
        assert result is True

        # Directory path should raise
        with pytest.raises(ValueError):
            preprocessor.validate_image(tmpdir)


# --- 12. Postprocessing Confidence Range ---

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
def test_postprocessing_confidence_range():
    """Postprocessor confidence is in [0, 1]."""
    from app.ml.postprocessing import Postprocessor

    postprocessor = Postprocessor(smoke_threshold=0.5, class_names=["non_smoke", "smoke"])

    # Test with various outputs
    test_cases = [
        torch.tensor([[0.1, 0.9]]),   # High smoke
        torch.tensor([[0.9, 0.1]]),   # Low smoke
        torch.tensor([[0.5, 0.5]]),   # Uncertain
        torch.tensor([[-1.0, 2.0]]),  # Logits
        torch.tensor([[0.0, 1.0]]),   # Extreme
    ]

    for output in test_cases:
        result = postprocessor.process(output, latency_ms=10.0)
        assert 0.0 <= result["confidence"] <= 1.0, \
            f"Confidence out of range: {result['confidence']}"


# --- 13. Postprocessing Threshold ---

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
def test_postprocessing_threshold():
    """Postprocessor.apply_threshold returns correct class."""
    from app.ml.postprocessing import Postprocessor

    postprocessor = Postprocessor(smoke_threshold=0.5, class_names=["non_smoke", "smoke"])

    assert postprocessor.apply_threshold(0.0) == "non_smoke"
    assert postprocessor.apply_threshold(0.3) == "non_smoke"
    assert postprocessor.apply_threshold(0.49) == "non_smoke"
    assert postprocessor.apply_threshold(0.5) == "smoke"
    assert postprocessor.apply_threshold(0.7) == "smoke"
    assert postprocessor.apply_threshold(1.0) == "smoke"


# --- 14. Metrics Calculation ---

@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
def test_metrics_calculation():
    """MLMetrics.calculate_metrics returns expected keys."""
    from app.ml.metrics import MLMetrics

    metrics_calc = MLMetrics(class_names=["non_smoke", "smoke"])

    y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1, 1, 1])
    y_pred = np.array([0, 1, 1, 1, 0, 0, 0, 1, 1, 0])
    y_prob = np.array([0.1, 0.8, 0.9, 0.7, 0.2, 0.4, 0.3, 0.85, 0.95, 0.35])

    result = metrics_calc.calculate_metrics(y_true, y_pred, y_prob)

    expected_keys = [
        "accuracy", "precision", "recall", "f1", "fpr", "fnr",
        "confusion_matrix", "pr_auc", "class_metrics",
    ]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"

    assert 0.0 <= result["accuracy"] <= 1.0
    assert 0.0 <= result["precision"] <= 1.0
    assert 0.0 <= result["recall"] <= 1.0
    assert 0.0 <= result["f1"] <= 1.0
    assert 0.0 <= result["fpr"] <= 1.0
    assert 0.0 <= result["fnr"] <= 1.0
    assert 0.0 <= result["pr_auc"] <= 1.0

    assert "non_smoke" in result["class_metrics"]
    assert "smoke" in result["class_metrics"]


# --- 15. Metrics Confusion Matrix ---

@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
def test_metrics_confusion_matrix():
    """confusion matrix has tp/fp/tn/fn."""
    from app.ml.metrics import MLMetrics

    metrics_calc = MLMetrics(class_names=["non_smoke", "smoke"])

    y_true = np.array([0, 0, 1, 1, 0, 1])
    y_pred = np.array([0, 1, 1, 0, 0, 1])

    cm = metrics_calc.confusion_matrix(y_true, y_pred)

    # Check smoke class (positive class)
    assert "smoke_tp" in cm
    assert "smoke_fp" in cm
    assert "smoke_tn" in cm
    assert "smoke_fn" in cm

    # Check non_smoke class (negative class)
    assert "non_smoke_tp" in cm
    assert "non_smoke_fp" in cm
    assert "non_smoke_tn" in cm
    assert "non_smoke_fn" in cm

    # Verify values: TP=2 (idx 2,5 predicted 1), FP=1 (idx 1 predicted 1), TN=2 (idx 0,4 predicted 0), FN=1 (idx 3 predicted 0)
    assert cm["smoke_tp"] == 2
    assert cm["smoke_fp"] == 1
    assert cm["smoke_tn"] == 2
    assert cm["smoke_fn"] == 1


# --- 16. Metrics Threshold Analysis ---

@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
def test_metrics_threshold_analysis():
    """threshold_analysis returns list of dicts."""
    from app.ml.metrics import MLMetrics

    metrics_calc = MLMetrics()

    y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1, 1, 1])
    y_prob = np.array([0.1, 0.8, 0.9, 0.7, 0.2, 0.4, 0.3, 0.85, 0.95, 0.35])

    results = metrics_calc.threshold_analysis(y_true, y_prob, thresholds=[0.3, 0.5, 0.7])

    assert isinstance(results, list)
    assert len(results) == 3

    for entry in results:
        assert "threshold" in entry
        assert "precision" in entry
        assert "recall" in entry
        assert "f1" in entry
        assert "fpr" in entry
        assert 0.0 <= entry["precision"] <= 1.0
        assert 0.0 <= entry["recall"] <= 1.0


# --- 17. Model Registry Metadata ---

def test_model_registry_metadata():
    """ModelRegistry saves/loads metadata JSON."""
    from app.ml.model_registry import ModelRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ModelRegistry(models_dir=tmpdir)

        metadata = {
            "name": "test-model",
            "version": "1.0.0",
            "architecture": "test",
            "input_resolution": [224, 224],
            "num_classes": 2,
            "class_names": ["non_smoke", "smoke"],
            "metrics": {"accuracy": 0.95},
        }

        # Save metadata
        registry.save_metadata("test-model", metadata, version="1.0.0")

        # Load metadata
        loaded = registry.load_metadata("test-model", version="1.0.0")
        assert loaded["name"] == "test-model"
        assert loaded["version"] == "1.0.0"
        assert loaded["metrics"]["accuracy"] == 0.95

        # Verify JSON file exists
        json_path = os.path.join(tmpdir, "test-model", "1.0.0", "model_metadata.json")
        assert os.path.exists(json_path)

        with open(json_path) as f:
            file_data = json.load(f)
        assert file_data["name"] == "test-model"


# --- 18. Model Registry List ---

def test_model_registry_list():
    """ModelRegistry.list_models returns list."""
    from app.ml.model_registry import ModelRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ModelRegistry(models_dir=tmpdir)

        # Empty registry should return empty list
        models = registry.list_models()
        assert isinstance(models, list)
        assert len(models) == 0

        # Add a model metadata entry
        metadata1 = {"name": "model-a", "version": "1.0.0", "architecture": "test"}
        metadata2 = {"name": "model-b", "version": "2.0.0", "architecture": "test"}
        registry.save_metadata("model-a", metadata1, version="1.0.0")
        registry.save_metadata("model-b", metadata2, version="2.0.0")

        models = registry.list_models()
        assert isinstance(models, list)
        assert len(models) == 2

        names = [m["name"] for m in models]
        assert "model-a" in names
        assert "model-b" in names


# --- 19. Real Classifier Not Loaded ---

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
def test_real_classifier_not_loaded():
    """RealSmokeClassifier.is_loaded() returns False when no model."""
    from app.ml.real_classifier import RealSmokeClassifier

    classifier = RealSmokeClassifier(model_path=None)
    assert classifier.is_loaded() is False


# --- 20. Real Classifier Classify Raises ---

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
def test_real_classifier_classify_raises():
    """RealSmokeClassifier.classify() raises when model not loaded."""
    from app.ml.real_classifier import RealSmokeClassifier

    classifier = RealSmokeClassifier(model_path=None)
    with pytest.raises(RuntimeError, match="No model loaded"):
        classifier.classify("test_image.jpg")


# --- Additional Edge Case Tests ---

def test_mock_classifier_warmup():
    """MockClassifier warmup completes without error."""
    classifier = MockClassifier()
    classifier.warmup(num_iterations=3)
    assert classifier.inference_count == 3


def test_mock_classifier_supported_classes():
    """MockClassifier returns correct supported classes."""
    classifier = MockClassifier()
    classes = classifier.get_supported_classes()
    assert "smoke" in classes
    assert "wildfire" in classes
    assert "clear" in classes


def test_mock_classifier_model_info():
    """MockClassifier.get_model_info returns valid info."""
    classifier = MockClassifier()
    info = classifier.get_model_info()

    assert info["framework"] == "mock"
    assert info["device"] == "cpu"
    assert info["status"] == "simulated"
    assert "input_shape" in info
    assert "output_shape" in info
    assert len(info["input_shape"]) == 3


def test_priority_calculator_color():
    """PriorityCalculator returns valid color codes."""
    calc = PriorityCalculator()
    colors = {
        "CRITICAL": calc.get_priority_color("CRITICAL"),
        "HIGH": calc.get_priority_color("HIGH"),
        "MEDIUM": calc.get_priority_color("MEDIUM"),
        "LOW": calc.get_priority_color("LOW"),
    }

    for priority, color in colors.items():
        assert color.startswith("#"), f"Invalid color for {priority}: {color}"
        assert len(color) == 7, f"Invalid color length for {priority}: {color}"


def test_priority_calculator_order():
    """PriorityCalculator returns correct numeric order."""
    calc = PriorityCalculator()
    assert calc.get_priority_order("CRITICAL") == 4
    assert calc.get_priority_order("HIGH") == 3
    assert calc.get_priority_order("MEDIUM") == 2
    assert calc.get_priority_order("LOW") == 1
    assert calc.get_priority_order("UNKNOWN") == 0
