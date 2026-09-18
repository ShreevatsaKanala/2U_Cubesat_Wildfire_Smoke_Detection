# Model Evaluation

## Evaluation Protocol

### Overview

Models are evaluated on a held-out test set that was not used during training or validation. The evaluation produces comprehensive metrics, confusion matrix, threshold analysis, and error analysis.

### Evaluation Steps

1. **Load test split**: Read `splits.json` and `labels.json`
2. **Load model**: Load trained weights from checkpoint
3. **Run inference**: Forward pass on all test images
4. **Calculate metrics**: Compute precision, recall, F1, FPR, FNR, PR-AUC
5. **Generate confusion matrix**: TP, FP, TN, FN counts
6. **Threshold analysis**: Evaluate metrics at different thresholds
7. **Error analysis**: Identify and categorize misclassifications
8. **Save reports**: Output JSON and text reports

### Evaluation Script

```bash
python scripts/ml/evaluate.py \
    --model data/models/best_model.pt \
    --data data/splits \
    --split test \
    --threshold 0.5 \
    --output reports/ml
```

## Metrics

### Primary Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Accuracy** | (TP+TN) / (TP+FP+TN+FN) | Overall correct predictions |
| **Precision** | TP / (TP+FP) | Of predicted smoke, how many are correct |
| **Recall** | TP / (TP+FN) | Of actual smoke, how many are detected |
| **F1** | 2×P×R / (P+R) | Harmonic mean of precision and recall |
| **FPR** | FP / (FP+TN) | False alarm rate (lower is better) |
| **FNR** | FN / (FN+TP) | Miss rate (lower is better) |
| **PR-AUC** | Area under PR curve | Precision-recall trade-off |

### Metric Selection

For smoke detection:
- **Primary**: F1 score (balances precision and recall)
- **Operational**: FPR (false alarms waste resources) and FNR (missed smoke is dangerous)
- **Threshold**: PR-AUC (robust to class imbalance)

### Confusion Matrix

```
                    Predicted
                    non_smoke    smoke
Actual  non_smoke      TN         FP
        smoke          FN         TP
```

Per-class metrics:

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------| 
| non_smoke | TN/(TN+FN) | TN/(TN+FP) | ... | count(non_smoke) |
| smoke | TP/(TP+FP) | TP/(TP+FN) | ... | count(smoke) |

## Threshold Analysis

### Purpose

The default threshold (0.5) may not be optimal for the operational requirements. Threshold analysis evaluates performance across a range of thresholds.

### Procedure

1. Compute predictions at thresholds: 0.05, 0.10, 0.15, ..., 0.95
2. For each threshold, calculate precision, recall, F1, FPR
3. Identify threshold that meets operational constraints

### Output Format

```json
[
  {
    "threshold": 0.05,
    "precision": 0.45,
    "recall": 0.98,
    "f1": 0.62,
    "fpr": 0.32
  },
  ...
]
```

### Threshold Selection Criteria

| Constraint | Recommended Threshold |
|------------|----------------------|
| Minimize false alarms | Higher (0.7-0.9) |
| Maximize detection | Lower (0.3-0.5) |
| Balanced | 0.5 (default) |
| FPR < 5% | Find threshold where FPR ≤ 0.05 |
| Recall > 90% | Find threshold where recall ≥ 0.90 |

## Error Analysis

### Error Types

| Type | Description | Implication |
|------|-------------|-------------|
| **False Positive** | non_smoke → smoke | Wasted downlink, false alarm |
| **False Negative** | smoke → non_smoke | Missed detection, safety risk |
| **Hard Negative** | FP with probability > 0.7 | Highly confusing case |

### Error Categories

For each misclassification, record:
- Image ID
- True label
- Predicted label
- Probability score
- Image metadata (if available)

### Error Analysis Output

```json
{
  "false_positives": [
    {
      "index": 42,
      "image_id": "cloud_image_001.jpg",
      "true_label": 0,
      "predicted_label": 1,
      "probability": 0.85
    }
  ],
  "false_negatives": [...],
  "hard_negatives": [...]
}
```

### Common Error Patterns

| Pattern | Cause | Mitigation |
|---------|-------|------------|
| Clouds → smoke | Visual similarity | Add cloud hard negatives |
| Haze → smoke | Atmospheric effects | Include haze in training |
| Industrial plumes | Plume shape | Add industrial smoke examples |
| Partial smoke | Small smoke area | Augment with partial annotations |

## Model Comparison

### Comparison Template

| Metric | Baseline CNN | MobileNetV3-Small | MobileNetV3-Large |
|--------|-------------|-------------------|-------------------|
| Parameters | ~100K | ~2.5M | ~5.4M |
| Accuracy | TBD | TBD | TBD |
| Precision | TBD | TBD | TBD |
| Recall | TBD | TBD | TBD |
| F1 | TBD | TBD | TBD |
| FPR | TBD | TBD | TBD |
| FNR | TBD | TBD | TBD |
| PR-AUC | TBD | TBD | TBD |
| Inference (ms) | TBD | TBD | TBD |
| Model Size (MB) | TBD | TBD | TBD |

### Selection Criteria

1. **Accuracy**: Which model performs best on test set?
2. **Latency**: Which model meets < 100ms budget on RPi5?
3. **Size**: Which model fits in RPi5 memory constraints?
4. **Trade-off**: Which model best balances accuracy and speed?

## Raspberry Pi 5 Considerations

### Hardware Constraints

- **CPU**: BCM2712, 4× Cortex-A76 @ 2.4GHz
- **RAM**: 4GB or 8GB LPDDR4X
- **GPU**: VideoCore VII (limited ML support)
- **Storage**: microSD (I/O limited)
- **Power**: 5V/3A via USB-C
- **Thermal**: Passive cooling, may throttle under load

### Deployment Considerations

| Factor | Impact | Mitigation |
|--------|--------|------------|
| **CPU inference** | No GPU acceleration | Use optimized models (MobileNetV3) |
| **Memory** | Limited RAM | Quantize model, reduce batch size |
| **I/O latency** | SD card read speed | Cache model in memory |
| **Thermal throttling** | Reduced performance under sustained load | Limit inference frequency |
| **Power consumption** | Battery constraints | Batch inference, sleep between captures |

### Expected Performance (Desktop)

| Model | Preprocess (ms) | Inference (ms) | Total (ms) | Throughput (img/s) |
|-------|-----------------|----------------|------------|-------------------|
| Baseline CNN | TBD | TBD | TBD | TBD |
| MobileNetV3-Small | TBD | TBD | TBD | TBD |
| MobileNetV3-Large | TBD | TBD | TBD | TBD |

**Note**: These are desktop benchmarks. RPi5 performance will be different (likely 2-5x slower).

### Optimization Strategies

1. **Model quantization**: INT8 quantization for faster inference
2. **ONNX Runtime**: Use ONNX format with optimized backend
3. **TorchScript**: Compile model for faster execution
4. **Batch inference**: Process multiple images at once (if memory allows)
5. **Model pruning**: Remove redundant weights
6. **Knowledge distillation**: Train smaller model from larger model

### Deployment Checklist

- [ ] Model accuracy meets threshold (F1 > 0.85)
- [ ] Inference latency < 100ms on RPi5
- [ ] Model size < 50MB
- [ ] Memory usage < 200MB during inference
- [ ] Power consumption acceptable
- [ ] Thermal throttling not triggered
- [ ] Fallback to mock mode works correctly

## Integration with Digital Twin

The evaluation pipeline produces reports that inform model selection for the simulation engine:

1. **Mock mode**: Default — deterministic classifier, no model needed
2. **Real mode**: Trained model loaded from `ML_MODEL_PATH` in `.env`
3. **AI Vision**: External providers (OpenRouter/Groq) provide independent assessment

Model selection should balance accuracy, latency, and resource constraints for the target deployment platform.
