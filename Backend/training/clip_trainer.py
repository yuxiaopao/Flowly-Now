"""
CLIP classification training helpers (M4.2).

Supports:
  - zero_shot: export encoder manifest + text prompts (uses OpenAI CLIP when installed)
  - finetune: linear probe on classification_folders dataset (CLIP or ResNet fallback)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[Dict[str, Any]], None]]

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tif', '.tiff'}


def run_clip_classification(
    *,
    mode: str,
    class_names: List[str],
    dataset_path: str = '',
    base_model: str = 'ViT-B/32',
    epochs: int = 10,
    batch_size: int = 32,
    learning_rate: float = 1e-4,
    output_dir: str,
    progress_callback: ProgressCallback = None,
) -> Dict[str, Any]:
    """Run CLIP classification and return result dict compatible with node-io-contracts §4."""
    mode = (mode or 'zero_shot').lower()
    if mode not in ('zero_shot', 'finetune'):
        return {'success': False, 'error': f'Unsupported mode: {mode}'}

    if not class_names:
        return {'success': False, 'error': 'classNames is required'}

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    started = time.time()
    try:
        if mode == 'zero_shot':
            result = _run_zero_shot(
                class_names=class_names,
                base_model=base_model,
                output_dir=out,
                progress_callback=progress_callback,
            )
        else:
            if not dataset_path:
                return {'success': False, 'error': 'finetune mode requires dataset_path'}
            result = _run_finetune(
                class_names=class_names,
                dataset_path=dataset_path,
                base_model=base_model,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                output_dir=out,
                progress_callback=progress_callback,
            )
    except Exception as exc:
        logger.exception('CLIP classification failed')
        return {'success': False, 'error': str(exc)}

    result['duration_seconds'] = int(time.time() - started)
    return result


def _emit(cb: ProgressCallback, payload: Dict[str, Any]) -> None:
    if cb:
        try:
            cb(payload)
        except Exception:
            pass


def _try_load_clip(base_model: str):
    try:
        import clip
        import torch

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model, preprocess = clip.load(base_model, device=device)
        return model, preprocess, device, 'clip'
    except Exception as exc:
        logger.info('CLIP package unavailable, using fallback encoder: %s', exc)
        return None


def _run_zero_shot(
    *,
    class_names: List[str],
    base_model: str,
    output_dir: Path,
    progress_callback: ProgressCallback,
) -> Dict[str, Any]:
    _emit(progress_callback, {'type': 'status', 'status': 'preparing', 'progress': 10})

    clip_bundle = _try_load_clip(base_model)
    encoder_type = 'clip' if clip_bundle else 'fallback_manifest'
    model_path = output_dir / 'clip.pt'
    manifest_path = output_dir / 'manifest.json'

    prompts = [f'a photo of a {name}' for name in class_names]
    manifest = {
        'mode': 'zero_shot',
        'base_model': base_model,
        'encoder_type': encoder_type,
        'class_names': class_names,
        'text_prompts': prompts,
    }

    _emit(progress_callback, {'type': 'status', 'status': 'exporting', 'progress': 60})

    try:
        import torch
    except ImportError:
        torch = None

    if clip_bundle and torch is not None:
        model, _, device, _ = clip_bundle
        torch.save(
            {
                'state_dict': model.state_dict(),
                'base_model': base_model,
                'class_names': class_names,
                'text_prompts': prompts,
                'mode': 'zero_shot',
            },
            model_path,
        )
        manifest['model_path'] = str(model_path)
    elif torch is not None:
        torch.save(
            {
                'base_model': base_model,
                'class_names': class_names,
                'text_prompts': prompts,
                'mode': 'zero_shot',
                'encoder_type': 'fallback_manifest',
            },
            model_path,
        )
        manifest['model_path'] = str(model_path)
        manifest['note'] = 'Install `clip` package for full CLIP encoder weights'
    else:
        model_path = output_dir / 'clip_zero_shot.json'
        model_path.write_text(
            json.dumps(
                {
                    'mode': 'zero_shot',
                    'base_model': base_model,
                    'class_names': class_names,
                    'text_prompts': prompts,
                    'encoder_type': 'json_manifest',
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding='utf-8',
        )
        manifest['model_path'] = str(model_path)
        manifest['note'] = 'PyTorch not installed; exported JSON manifest only'

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    _emit(progress_callback, {'type': 'status', 'status': 'completed', 'progress': 100})

    return {
        'success': True,
        'model_path': str(model_path),
        'class_names': class_names,
        'metrics': {'accuracy': None, 'mode': 'zero_shot'},
        'encoder_type': encoder_type,
        'manifest_path': str(manifest_path),
    }


def _collect_classification_samples(dataset_path: str) -> Tuple[List[str], List[int], List[str]]:
    """Return (file_paths, labels, class_names) from classification_folders layout."""
    from datasets.ml_format_validators import validate_ml_dataset

    validation = validate_ml_dataset(dataset_path, 'classification_folders')
    if not validation.get('valid'):
        raise ValueError(validation.get('error', 'Invalid classification dataset'))

    root = Path(validation['dataset_path'])
    class_names = validation.get('class_names') or []
    if not class_names:
        raise ValueError('No classes found in dataset')

    label_map = {name: idx for idx, name in enumerate(class_names)}
    paths: List[str] = []
    labels: List[int] = []

    search_roots: List[Path] = []
    for sub in ('train', 'val', 'test'):
        candidate = root / sub
        if candidate.is_dir():
            search_roots.append(candidate)
    if not search_roots:
        search_roots = [root]

    for base in search_roots:
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name not in label_map:
                continue
            for img in child.rglob('*'):
                if img.is_file() and img.suffix.lower() in IMAGE_EXTENSIONS:
                    paths.append(str(img))
                    labels.append(label_map[child.name])

    if len(paths) < 2:
        raise ValueError('finetune requires at least 2 labeled images')

    return paths, labels, class_names


def _run_finetune(
    *,
    class_names: List[str],
    dataset_path: str,
    base_model: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    output_dir: Path,
    progress_callback: ProgressCallback,
) -> Dict[str, Any]:
    try:
        import torch
    except ImportError:
        return {
            'success': False,
            'error': 'finetune 模式需要 PyTorch，请安装 torch 与 torchvision',
        }

    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset as TorchDataset
    from torchvision import transforms
    from PIL import Image

    file_paths, labels, discovered_classes = _collect_classification_samples(dataset_path)
    if class_names != discovered_classes and set(class_names) <= set(discovered_classes):
        class_names = discovered_classes
    elif set(class_names) != set(discovered_classes):
        logger.warning(
            'Config class_names %s differs from dataset %s; using dataset classes',
            class_names,
            discovered_classes,
        )
        class_names = discovered_classes

    num_classes = len(class_names)
    _emit(progress_callback, {'type': 'status', 'status': 'preparing_data', 'progress': 5})

    clip_bundle = _try_load_clip(base_model)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    if clip_bundle:
        model, preprocess, device, encoder_type = clip_bundle
        model = model.to(device)
        for param in model.parameters():
            param.requires_grad = False
        feature_dim = model.visual.output_dim if hasattr(model.visual, 'output_dim') else 512
        classifier = nn.Linear(feature_dim, num_classes).to(device)
        transform = preprocess
    else:
        from torchvision import models

        encoder_type = 'resnet18_fallback'
        backbone = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        feature_dim = backbone.fc.in_features
        backbone.fc = nn.Identity()
        model = backbone.to(device)
        for param in model.parameters():
            param.requires_grad = False
        classifier = nn.Linear(feature_dim, num_classes).to(device)
        transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    class _ImageListDataset(TorchDataset):
        def __init__(self, paths, y):
            self.paths = paths
            self.y = y

        def __len__(self):
            return len(self.paths)

        def __getitem__(self, idx):
            img = Image.open(self.paths[idx]).convert('RGB')
            return transform(img), self.y[idx]

    split = max(1, int(len(file_paths) * 0.8))
    indices = list(range(len(file_paths)))
    train_idx = indices[:split]
    val_idx = indices[split:] or indices[-1:]

    train_ds = _ImageListDataset([file_paths[i] for i in train_idx], [labels[i] for i in train_idx])
    val_ds = _ImageListDataset([file_paths[i] for i in val_idx], [labels[i] for i in val_idx])

    train_loader = DataLoader(train_ds, batch_size=min(batch_size, len(train_ds)), shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=min(batch_size, len(val_ds)), shuffle=False)

    optimizer = torch.optim.Adam(classifier.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss()

    history: List[Dict[str, Any]] = []
    best_acc = 0.0
    best_state = None

    for epoch in range(max(1, epochs)):
        classifier.train()
        if clip_bundle:
            model.eval()

        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for images, batch_labels in train_loader:
            images = images.to(device)
            batch_labels = batch_labels.to(device)
            with torch.no_grad():
                if clip_bundle:
                    features = model.encode_image(images).float()
                else:
                    features = model(images)
            logits = classifier(features)
            loss = criterion(logits, batch_labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * len(batch_labels)
            preds = logits.argmax(dim=1)
            train_correct += (preds == batch_labels).sum().item()
            train_total += len(batch_labels)

        classifier.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for images, batch_labels in val_loader:
                images = images.to(device)
                batch_labels = batch_labels.to(device)
                if clip_bundle:
                    features = model.encode_image(images).float()
                else:
                    features = model(images)
                logits = classifier(features)
                preds = logits.argmax(dim=1)
                val_correct += (preds == batch_labels).sum().item()
                val_total += len(batch_labels)

        train_acc = train_correct / train_total if train_total else 0.0
        val_acc = val_correct / val_total if val_total else train_acc
        epoch_metrics = {
            'epoch': epoch + 1,
            'train_loss': train_loss / max(train_total, 1),
            'train_acc': round(train_acc, 4),
            'val_acc': round(val_acc, 4),
        }
        history.append(epoch_metrics)

        if val_acc >= best_acc:
            best_acc = val_acc
            best_state = classifier.state_dict()

        progress = int(((epoch + 1) / max(epochs, 1)) * 100)
        _emit(progress_callback, {
            'type': 'epoch',
            'epoch': epoch + 1,
            'total_epochs': epochs,
            'progress': progress,
            'metrics': epoch_metrics,
        })

    if best_state:
        classifier.load_state_dict(best_state)

    model_path = output_dir / 'clip.pt'
    torch.save(
        {
            'mode': 'finetune',
            'base_model': base_model,
            'encoder_type': encoder_type,
            'class_names': class_names,
            'classifier_state_dict': classifier.state_dict(),
            'feature_dim': feature_dim,
            'metrics': {'accuracy': round(best_acc, 4)},
        },
        model_path,
    )

    manifest_path = output_dir / 'manifest.json'
    manifest_path.write_text(
        json.dumps(
            {
                'mode': 'finetune',
                'base_model': base_model,
                'encoder_type': encoder_type,
                'class_names': class_names,
                'model_path': str(model_path),
                'metrics': {'accuracy': round(best_acc, 4)},
                'history': history,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )

    _emit(progress_callback, {'type': 'status', 'status': 'completed', 'progress': 100})

    return {
        'success': True,
        'model_path': str(model_path),
        'class_names': class_names,
        'metrics': {'accuracy': round(best_acc, 4)},
        'encoder_type': encoder_type,
        'manifest_path': str(manifest_path),
        'training_history': history,
    }
