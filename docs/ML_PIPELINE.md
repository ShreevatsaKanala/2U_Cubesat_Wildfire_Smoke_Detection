# ML Pipeline

## Overview

The CubeSat Digital Twin includes an ML pipeline for smoke detection from RGB imagery captured by the onboard camera. The pipeline classifies images as containing smoke or not, assigns a confidence score, and uses these to prioritize observations for downlink to ground stations.

The pipeline is designed to run in two modes:
- **Mock mode** (`ML_MODE=mock`): Uses a deterministic hash-based classifier for testing the observation pipeline without ML dependencies.
- **Real mode** (`ML_MODE=real`): Uses a trained PyTorch model for actual inference (requires model files and torch).

## Architecture

```
Camera Capture → Preprocessing → Model Inference → Postprocessing → Priority → Observation
     ↓               ↓               ↓                ↓              ↓           ↓
  RGB Image    Resize 224x224    Forward Pass     Threshold &    Weighted     Store &
  (1920x1080)  Normalize         Raw Logits      Confidence     Score        Downlink
               IMAGENET stats    Softmax         Apply          smoke ×       Queue
```

### Data Flow

1. **Camera** captures RGB image (synthetic in simulation, real in deployment)
2. **Preprocessor** resizes to 224×224, normalizes with ImageNet statistics, converts to tensor
3. **Classifier** runs forward pass, returns raw logits or probabilities
4. **Postprocessor** applies softmax, calculates confidence, applies threshold
5. **PriorityCalculator** assigns CRITICAL/HIGH/MEDIUM/LOW based on weighted score
6. **Observation** is stored with full metadata and queued for downlink

## Models

### Baseline CNN

- **Architecture**: 4-layer CNN with batch normalization
- **Layers**: Conv2d(3→16) → Conv2d(16→32) → Conv2d(32→64) → Conv2d(64→128) → AdaptiveAvgPool → FC(128→64→2)
- **Parameters**: ~100K
- **Use case**: Quick validation, baseline comparison, resource-constrained testing

### MobileNetV3 Small

- **Architecture**: MobileNetV3-Small with pretrained ImageNet weights, final classifier replaced
- **Parameters**: ~2.5M
- **Use case**: Primary model for deployment on Raspberry Pi 5
- **Why chosen**: Best trade-off between accuracy and inference speed for edge deployment

### MobileNetV3 Large

- **Architecture**: MobileNetV3-Large with pretrained ImageNet weights, final classifier replaced
- **Parameters**: ~5.4M
- **Use case**: Higher accuracy when compute budget allows, desktop evaluation

## Preprocessing

All models use consistent preprocessing:

1. **Resize**: Bilinear interpolation to 224×224
2. **Normalize**: Divide by 255, then apply ImageNet normalization:
   - Mean: [0.485, 0.456, 0.406]
   - Std: [0.229, 0.224, 0.225]
3. **Tensor format**: `[1, 3, 224, 224]` (batch, channels, height, width)

No data augmentation is applied during inference. Training augmentation (if used) is handled separately in the training pipeline.

## Training

### Setup

- **Optimizer**: Adam (lr=0.001)
- **Scheduler**: ReduceLROnPlateau (patience=3, factor=0.5, monitor=val_f1)
- **Loss**: CrossEntropyLoss
- **Early stopping**: patience=7 epochs (no improvement on val_f1)
- **Batch size**: 32
- **Epochs**: Up to 30 (with early stopping)

### Reproducibility

- `torch.manual_seed(42)`
- `np.random.seed(42)`
- `torch.cuda.manual_seed_all(42)` (when CUDA available)
- Deterministic worker initialization (num_workers=0)

### Data Loading

- Train/val/test splits stored in `splits.json`
- Labels stored in `labels.json` or `labels_with_splits.json`
- Image IDs map to filenames and class labels
- No on-the-fly augmentation during training (simple pipeline)

## Evaluation

### Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| Accuracy | (TP+TN) / Total | > 0.90 |
| Precision | TP / (TP+FP) | > 0.85 |
| Recall | TP / (TP+FN) | > 0.80 |
| F1 | 2×P×R / (P+R) | > 0.85 |
| FPR | FP / (FP+TN) | < 0.10 |
| FNR | FN / (FN+TP) | < 0.20 |
| PR-AUC | Area under PR curve | > 0.90 |

### Confusion Matrix

Binary classification with classes: `non_smoke` (negative), `smoke` (positive).

|  | Predicted non_smoke | Predicted smoke |
|--|---------------------|-----------------|
| Actual non_smoke | TN | FP |
| Actual smoke | FN | TP |

### Error Analysis

The evaluation pipeline identifies:
- **False Positives**: non_smoke images classified as smoke (may be clouds, haze, dust)
- **False Negatives**: smoke images classified as non_smoke (missed detections)
- **Hard Negatives**: FP with probability > 0.7 (confusing cases)

## Threshold Selection

The default threshold is 0.5, but the optimal threshold depends on the operational cost of false positives vs false negatives:

- **Lower threshold** (e.g., 0.3): More sensitive, catches more smoke, but more false alarms
- **Higher threshold** (e.g., 0.7): Fewer false alarms, but may miss some smoke events

Threshold analysis evaluates precision, recall, F1, and FPR at thresholds from 0.05 to 0.95 in 0.05 increments. The recommended threshold is selected from the analysis to balance operational requirements.

## Export

### ONNX Export

Models can be exported to ONNX format for cross-platform deployment:

```python
torch.onnx.export(model, dummy_input, "model.onnx", opset_version=17)
```

### Deployment Format

For Raspberry Pi 5 deployment:
- **Format**: PyTorch `.pt` or ONNX `.onnx`
- **Input**: `[1, 3, 224, 224]` float32 tensor
- **Output**: `[1, 2]` logits (non_smoke, smoke)

## Benchmarking

### Desktop Benchmarking

Benchmarking is performed on the host machine using `scripts/ml/benchmark.py`:

1. Warmup iterations (default: 10)
2. Timed iterations (default: 100)
3. Measures: preprocessing, inference, total pipeline latency
4. Reports: mean, std, min, p95, p99 latency
5. Throughput: images per second

**Note**: Desktop benchmarks are NOT representative of Raspberry Pi 5 performance. They indicate model complexity relative to other models.

### Raspberry Pi 5 Projection

Actual RPi5 performance depends on:
- CPU/GPU utilization
- Memory bandwidth
- Thermal throttling
- I/O latency

Expected ranges (to be validated):
- Baseline CNN: 10-30ms per image
- MobileNetV3 Small: 20-50ms per image
- MobileNetV3 Large: 40-100ms per image

## Integration

### Configuration

Environment variables in `.env`:

```
ML_MODE=mock              # "mock" or "real"
ML_MODEL_PATH=data/models/best_model.pt
ML_SMOKE_THRESHOLD=0.5
ML_DEVICE=cpu             # "cpu" or "cuda"
```

### SimulationEngine Integration

The engine creates the appropriate classifier based on `ml_mode`:

```python
if ml_mode == "real":
    classifier = RealSmokeClassifier(model_path, device, threshold)
    if not classifier.is_loaded():
        # Fallback to mock
        classifier = MockClassifier()
else:
    classifier = MockClassifier()
```

### Fallback Behavior

If the real model fails to load (missing file, missing torch, corrupt model):
1. Warning is logged
2. `_ml_status` is set to "unavailable"
3. MockClassifier is used instead
4. Simulation continues with mock predictions

## Limitations

### Current Limitations

1. **No trained model yet**: The pipeline is ready but no model has been trained on real data
2. **Synthetic training data**: Initial training will use publicly available smoke datasets, which may not represent CubeSat imagery
3. **Binary classification only**: Currently smoke vs non_smoke; does not distinguish fire types, smoke density, or other phenomena
4. **Single frame analysis**: No temporal analysis across video sequences
5. **Fixed input resolution**: 224×224 may lose detail in large smoke plumes
6. **No calibration**: Model probabilities may not be well-calibrated
7. **Desktop benchmarking only**: RPi5 performance not yet measured

### What the Model Can Do

- Detect visible smoke in RGB imagery
- Provide probability scores for prioritization
- Run inference within acceptable latency for CubeSat operations
- Fall back gracefully when unavailable

### What the Model Cannot Do

- Detect invisible gases or thermal anomalies
- Determine smoke source or composition
- Analyze temporal patterns (single frame only)
- Guarantee accuracy on unseen domains
- Replace human verification

### Known Failure Modes

- **Clouds**: May be misclassified as smoke (hard negatives)
- **Haze/Fog**: Similar visual appearance to distant smoke
- **Industrial plumes**: May trigger false positives
- **Low light**: Reduced accuracy in dawn/dusk conditions
- **Partial smoke**: May miss smoke covering < 10% of frame
