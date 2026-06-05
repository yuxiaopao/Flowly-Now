# Augmentation App

This app provides data augmentation capabilities for the Flowly workflow platform.

## Features

- **Image Augmentation**: Using albumentations library (with PIL fallback)
- **Text Augmentation**: Synonym replacement, random insertion, random swap
- **Tabular Augmentation**: SMOTE (if available), noise injection, row duplication

## Usage

### API Endpoints

- `POST /api/v1/augmentations/run/` - Run augmentation job
- `GET /api/v1/augmentations/{id}/` - Get job status
- `GET /api/v1/augmentations/` - List jobs
- `GET /api/v1/augmentations/{id}/status/` - Get job status detail
- `POST /api/v1/augmentations/{id}/cancel/` - Cancel job
- `POST /api/v1/augmentations/{id}/retry/` - Retry failed job
- `GET /api/v1/augmentations/presets/` - Get preset configurations
- `GET /api/v1/augmentations/statistics/` - Get statistics

## Models

### AugmentationJob

Tracks augmentation operations with:
- Input/output datasets
- Strategy (geometric, color, noise, mixup, all)
- Ratio (augmentation multiplier)
- Progress tracking
- Status (pending, running, completed, failed)

## Augmentors

### ImageAugmentor

Real image augmentation supporting:
- Geometric: Rotate, Flip, Scale, Crop, Translate
- Color: Brightness, Contrast, Saturation, Grayscale
- Noise: Gaussian Noise, Random Erasing

### TextAugmentor

Text augmentation supporting:
- Synonym Replacement
- Random Insertion
- Random Swap
- Back-translation (stub)

### TabularAugmentor

Tabular data augmentation supporting:
- SMOTE (with imbalanced-learn)
- Gaussian Noise injection
- Row shuffling and duplication

## Configuration

Add to `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    ...
    'augmentation',
]
```

Add to URLs in `config/urls.py`:

```python
path('api/v1/augmentations/', include('augmentation.urls')),
```

## Dependencies

- albumentations (optional, PIL fallback)
- numpy
- pandas
- imbalanced-learn (optional for SMOTE)
