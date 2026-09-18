# Dataset

## Target Task

Binary RGB image classification: **smoke** vs **non_smoke** for probable wildfire smoke indication from CubeSat altitude (~500 km).

### Requirements

- Input: RGB images (any resolution, resized to 224×224 for inference)
- Output: Binary class (non_smoke=0, smoke=1) with probability score
- Deployment: Raspberry Pi 5 onboard inference
- Latency budget: < 100ms per image

## Dataset Sources

### Primary Sources

| Dataset | Description | Size | License | URL |
|---------|-------------|------|---------|-----|
| **Smoke Detection Dataset** | Wildfire smoke images from various sources | ~40K images | CC BY 4.0 | https://www.kaggle.com/datasets/datasetsdb/smoke-detection-dataset |
| **Wildfire Smoke Images** | Labeled smoke/non-smoke from wildfire events | ~10K images | Public Domain | https://wildfireed.com/SFMN/ |
| **FIRMS Active Fire Data** | Satellite fire detections (contextual) | N/A | Public Domain | https://firms.modaps.eosdis.nasa.gov/ |

### Supplementary Sources

| Dataset | Purpose | Notes |
|---------|---------|-------|
| **COCO** | Hard negative mining (clouds, haze) | 80K images, CC BY 4.0 |
| **ImageNet** | Pretrained weights, hard negatives | 1.2M images, custom license |
| **OpenImages** | Additional non-smoke examples | 9M images, CC BY 4.0 |

### Data Requirements

- **Minimum**: 1,000 smoke images, 5,000 non-smoke images
- **Recommended**: 10,000 smoke images, 30,000 non-smoke images
- **Balance**: 1:3 to 1:5 smoke:non-smoke ratio (reflects real-world prevalence)

## Hard Negatives

The following classes are known to cause false positives and must be well-represented in training:

| Category | Description | Visual Similarity |
|----------|-------------|-------------------|
| **Cumulus clouds** | White/grey puffy clouds | High (color, texture) |
| **Stratus clouds** | Layered grey clouds | High (uniform appearance) |
| **Haze/Fog** | Atmospheric obscuration | Medium (reduced contrast) |
| **Dust plumes** | Wind-blown dust | Medium (brown/tan color) |
| **Industrial plumes** | Steam/smoke from factories | High (plume shape) |
| **Shadows** | Dark areas from terrain/clouds | Low (but may trigger edge cases) |
| **Sun glint** | Bright reflections | Low (but may saturate sensor) |

### Hard Negative Strategy

- Include at least 2x hard negatives relative to smoke images
- Weight hard negatives higher in loss if needed
- Analyze false positives after each training iteration
- Add new hard negative categories as they are discovered

## Preprocessing

### Raw Data

Images are stored in `data/raw/` organized by class:

```
data/raw/
├── non_smoke/
│   ├── image_001.jpg
│   ├── image_002.jpg
│   └── ...
└── smoke/
    ├── image_001.jpg
    ├── image_002.jpg
    └── ...
```

### Processing Steps

1. **Validation**: Check file exists, is readable, can be converted to RGB
2. **Copy**: Copy valid images to `data/raw/<class>/` structure
3. **Label Generation**: Create `data/labels/labels.json` mapping image IDs to metadata
4. **Manifest**: Generate `data/metadata/dataset_manifest.json` with statistics

### Validation Criteria

- File extension: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`
- Must be openable with PIL
- Must be convertible to RGB mode
- Must not be corrupt or truncated

## Splitting Strategy

### Ratios

| Split | Ratio | Purpose |
|-------|-------|---------|
| Train | 70% | Model training |
| Validation | 15% | Hyperparameter tuning, early stopping |
| Test | 15% | Final performance evaluation |

### Splitting Method

1. **Stratified splitting**: Maintain class distribution across splits
2. **Random seed**: Fixed seed (42) for reproducibility
3. **No data leakage**: Ensure no image appears in multiple splits

### Scene-Aware Splitting (Future)

When scene metadata is available:
- Group images by scene/location
- Ensure all images from one scene are in the same split
- Prevents model from learning scene-specific shortcuts

### Split Files

Splits are stored in `data/splits/splits.json`:

```json
{
  "train": ["image_id_1", "image_id_2", ...],
  "val": ["image_id_3", "image_id_4", ...],
  "test": ["image_id_5", "image_id_6", ...]
}
```

## Class Balance

### Expected Distribution

Real-world smoke detection has significant class imbalance:
- **Non-smoke**: ~95-99% of observations
- **Smoke**: ~1-5% of observations

### Mitigation Strategies

1. **Weighted loss**: Apply class weights in CrossEntropyLoss
2. **Oversampling**: Duplicate smoke images during training
3. **Undersampling**: Reduce non-smoke images to balance
4. **Data augmentation**: Apply stronger augmentation to minority class
5. **Threshold tuning**: Adjust decision threshold to optimize for recall

### Current Approach

- Use stratified splits to maintain distribution
- Apply class weights in loss function
- Monitor F1 score (harmonic mean of precision and recall)
- Tune threshold based on validation set

## Data Directory Structure

```
data/
├── raw/                    # Original images organized by class
│   ├── non_smoke/
│   └── smoke/
├── processed/              # Preprocessed images (optional)
├── labels/                 # Label files
│   ├── classes.json        # Class definitions
│   └── labels.json         # Image ID → metadata mapping
├── splits/                 # Train/val/test splits
│   ├── splits.json         # Split assignments
│   └── labels_with_splits.json  # Labels with split info
├── samples/                # Sample images for testing
├── models/                 # Trained model checkpoints
│   ├── <model_name>/
│   │   ├── <version>/
│   │   │   ├── best_model.pt
│   │   │   ├── config.json
│   │   │   ├── training_log.json
│   │   │   └── model_metadata.json
│   │   └── ...
│   └── ...
└── metadata/               # Dataset metadata
    ├── dataset_manifest.json
    └── ...
```

## Data Pipeline Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `prepare_dataset.py` | Download/copy images, create labels | `python scripts/ml/prepare_dataset.py --source <path>` |
| `split_dataset.py` | Create train/val/test splits | `python scripts/ml/split_dataset.py --data data/raw` |
| `train.py` | Train model | `python scripts/ml/train.py --data data/splits --model mobilenet_v3_small` |
| `evaluate.py` | Evaluate on test set | `python scripts/ml/evaluate.py --model data/models/best_model.pt` |
| `export.py` | Export to ONNX | `python scripts/ml/export.py --model data/models/best_model.pt` |
| `benchmark.py` | Benchmark inference | `python scripts/ml/benchmark.py --model data/models/best_model.pt` |
| `run_pipeline.py` | Run full pipeline | `python scripts/ml/run_pipeline.py --source <path>` |

## Integration with Digital Twin

The ML pipeline integrates with the simulation engine:

1. **Mock mode** (`ML_MODE=mock`): Uses deterministic hash-based classifier — no training required
2. **Real mode** (`ML_MODE=real`): Loads trained model from `ML_MODEL_PATH`

Set `ML_MODE=real` in `.env` after training a model. The simulation falls back to mock if the model fails to load.

For live AI vision analysis (external providers), see the AI Vision Pipeline section in the main README.
