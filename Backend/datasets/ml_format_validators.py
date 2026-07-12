"""
ML dataset format validators for dataset_upload node (M4.1).

Supported formats (see node-io-contracts.md §1):
  - yolo
  - image_folder
  - image_text_pairs
  - classification_folders
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

ML_FORMAT_TYPES = frozenset({
    'yolo',
    'image_folder',
    'image_text_pairs',
    'classification_folders',
})

IMAGE_EXTENSIONS = frozenset({
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tif', '.tiff',
})


def is_ml_format(format_type: str) -> bool:
    return (format_type or '').lower() in ML_FORMAT_TYPES


def validate_ml_dataset(root_path: str, format_type: str) -> Dict[str, Any]:
    """
    Validate an on-disk ML dataset layout.

    Returns dict with keys:
      valid, error (optional), dataset_path, format, class_names, stats,
      preview_data, dataset_yaml_path (yolo only)
    """
    fmt = (format_type or '').lower()
    if fmt not in ML_FORMAT_TYPES:
        return {'valid': False, 'error': f'Unsupported ML format: {format_type}'}

    path = Path(root_path).resolve()
    if not path.exists():
        return {'valid': False, 'error': f'Path not found: {root_path}'}

    validators = {
        'yolo': _validate_yolo,
        'image_folder': _validate_image_folder,
        'image_text_pairs': _validate_image_text_pairs,
        'classification_folders': _validate_classification_folders,
    }
    return validators[fmt](path)


def _iter_images(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    images: List[Path] = []
    for entry in directory.rglob('*'):
        if entry.is_file() and entry.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(entry)
    return images


def _count_dir_bytes(directory: Path) -> int:
    total = 0
    if directory.is_file():
        return directory.stat().st_size
    for entry in directory.rglob('*'):
        if entry.is_file():
            try:
                total += entry.stat().st_size
            except OSError:
                pass
    return total


def _validate_yolo(root: Path) -> Dict[str, Any]:
    if root.is_file():
        return {'valid': False, 'error': 'YOLO format requires a directory with data.yaml'}

    yaml_path = _find_yaml(root, ('data.yaml', 'data.yml', 'dataset.yaml'))
    if not yaml_path:
        return {
            'valid': False,
            'error': 'YOLO dataset must contain data.yaml (or data.yml / dataset.yaml)',
        }

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f) or {}
    except Exception as exc:
        return {'valid': False, 'error': f'Failed to parse {yaml_path.name}: {exc}'}

    class_names = _extract_yolo_class_names(yaml_data, root)
    images_dir = _resolve_yolo_path(root, yaml_data.get('path') or yaml_data.get('train') or 'images')
    labels_dir = root / 'labels'
    if not labels_dir.is_dir():
        alt = root / 'labels' / 'train'
        labels_dir = alt if alt.is_dir() else labels_dir

    images = _iter_images(images_dir if images_dir.is_dir() else root / 'images')
    label_files = list(labels_dir.rglob('*.txt')) if labels_dir.is_dir() else []

    if not images:
        return {'valid': False, 'error': 'No images found for YOLO dataset'}

    stats = {
        'image_count': len(images),
        'label_count': len(label_files),
        'yaml_path': str(yaml_path),
    }

    preview = [
        {'field': 'classes', 'value': ', '.join(class_names) if class_names else '(from yaml)'},
        {'field': 'images', 'value': str(len(images))},
        {'field': 'labels', 'value': str(len(label_files))},
    ]

    return {
        'valid': True,
        'dataset_path': str(root),
        'format': 'yolo',
        'class_names': class_names,
        'stats': stats,
        'preview_data': preview,
        'dataset_yaml_path': str(yaml_path),
        'row_count': len(images),
    }


def _validate_image_folder(root: Path) -> Dict[str, Any]:
    if root.is_file():
        return {'valid': False, 'error': 'image_folder format requires a directory'}

    images_dir = root / 'images' if (root / 'images').is_dir() else root
    images = _iter_images(images_dir)
    if not images:
        return {'valid': False, 'error': 'image_folder: no images found under images/ or dataset root'}

    metadata_path = root / 'metadata.json'
    metadata: Dict[str, Any] = {}
    if metadata_path.is_file():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as exc:
            return {'valid': False, 'error': f'Invalid metadata.json: {exc}'}

    stats = {
        'image_count': len(images),
        'has_metadata': metadata_path.is_file(),
        'metadata_entries': len(metadata) if isinstance(metadata, (list, dict)) else 0,
    }

    preview = [
        {'field': 'images', 'value': str(len(images))},
        {'field': 'metadata', 'value': 'yes' if metadata_path.is_file() else 'no'},
    ]

    return {
        'valid': True,
        'dataset_path': str(root),
        'format': 'image_folder',
        'class_names': [],
        'stats': stats,
        'preview_data': preview,
        'row_count': len(images),
    }


def _validate_image_text_pairs(root: Path) -> Dict[str, Any]:
    pairs_file: Optional[Path] = None
    base_dir = root

    if root.is_file():
        if root.suffix.lower() not in ('.jsonl', '.json'):
            return {'valid': False, 'error': 'image_text_pairs: expected pairs.jsonl or directory'}
        pairs_file = root
        base_dir = root.parent
    else:
        for name in ('pairs.jsonl', 'pairs.json', 'metadata.jsonl'):
            candidate = root / name
            if candidate.is_file():
                pairs_file = candidate
                break
        if not pairs_file:
            return {'valid': False, 'error': 'image_text_pairs: pairs.jsonl not found in dataset directory'}

    pairs, errors = _read_image_text_pairs(pairs_file)
    if errors:
        return {'valid': False, 'error': errors[0]}
    if not pairs:
        return {'valid': False, 'error': 'image_text_pairs: no valid pairs in file'}

    missing_images = []
    for idx, pair in enumerate(pairs[:50]):
        img_ref = pair.get('image', '')
        if not img_ref:
            continue
        img_path = Path(img_ref)
        if not img_path.is_absolute():
            img_path = base_dir / img_ref
        if not img_path.is_file():
            missing_images.append(f'line {idx + 1}: {img_ref}')

    if missing_images:
        return {
            'valid': False,
            'error': f'image_text_pairs: missing image files (first: {missing_images[0]})',
        }

    stats = {
        'image_count': len(pairs),
        'label_count': len(pairs),
        'pairs_file': str(pairs_file),
    }

    preview = [
        {'image': p.get('image', ''), 'text': (p.get('text', '') or '')[:80]}
        for p in pairs[: min(5, len(pairs))]
    ]

    return {
        'valid': True,
        'dataset_path': str(base_dir),
        'format': 'image_text_pairs',
        'class_names': [],
        'stats': stats,
        'preview_data': preview,
        'row_count': len(pairs),
    }


def _validate_classification_folders(root: Path) -> Dict[str, Any]:
    if root.is_file():
        return {'valid': False, 'error': 'classification_folders format requires a directory'}

    search_roots: List[Path] = []
    for sub in ('train', 'val', 'test'):
        candidate = root / sub
        if candidate.is_dir():
            search_roots.append(candidate)
    if not search_roots:
        search_roots = [root]

    class_names: Set[str] = set()
    image_count = 0
    per_class: Dict[str, int] = {}

    for base in search_roots:
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name.startswith('.'):
                continue
            images = _iter_images(child)
            if not images:
                continue
            class_names.add(child.name)
            per_class[child.name] = per_class.get(child.name, 0) + len(images)
            image_count += len(images)

    if not class_names:
        return {
            'valid': False,
            'error': 'classification_folders: no class subdirectories with images found',
        }

    stats = {
        'image_count': image_count,
        'label_count': image_count,
        'class_count': len(class_names),
        'per_class': per_class,
    }

    preview = [
        {'class': name, 'count': str(per_class.get(name, 0))}
        for name in sorted(class_names)
    ]

    return {
        'valid': True,
        'dataset_path': str(root),
        'format': 'classification_folders',
        'class_names': sorted(class_names),
        'stats': stats,
        'preview_data': preview,
        'row_count': image_count,
    }


def _find_yaml(root: Path, names: Tuple[str, ...]) -> Optional[Path]:
    for name in names:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def _resolve_yolo_path(root: Path, ref: Any) -> Path:
    if not ref:
        return root / 'images'
    ref_path = Path(str(ref))
    if ref_path.is_absolute():
        return ref_path
    return (root / ref_path).resolve()


def _extract_yolo_class_names(yaml_data: Dict[str, Any], root: Path) -> List[str]:
    names = yaml_data.get('names')
    if isinstance(names, dict):
        return [str(names[k]) for k in sorted(names.keys(), key=lambda x: int(x) if str(x).isdigit() else x)]
    if isinstance(names, list):
        return [str(n) for n in names]

    nc = yaml_data.get('nc')
    if isinstance(nc, int) and nc > 0:
        return [f'class_{i}' for i in range(nc)]
    return []


def _read_image_text_pairs(pairs_file: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    pairs: List[Dict[str, Any]] = []
    errors: List[str] = []

    if pairs_file.suffix.lower() == '.json':
        try:
            with open(pairs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'image' in item and 'text' in item:
                        pairs.append({'image': str(item['image']), 'text': str(item['text'])})
            else:
                errors.append('pairs.json must be a JSON array of {image, text} objects')
        except Exception as exc:
            errors.append(f'Failed to parse {pairs_file.name}: {exc}')
        return pairs, errors

    try:
        with open(pairs_file, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    item = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    errors.append(f'{pairs_file.name}:{line_no} invalid JSON: {exc}')
                    return pairs, errors
                if not isinstance(item, dict) or 'image' not in item or 'text' not in item:
                    errors.append(f'{pairs_file.name}:{line_no} must be {{"image":"...","text":"..."}}')
                    return pairs, errors
                pairs.append({'image': str(item['image']), 'text': str(item['text'])})
    except Exception as exc:
        errors.append(f'Failed to read {pairs_file.name}: {exc}')

    return pairs, errors


def compute_path_size_bytes(path: str) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    return _count_dir_bytes(p)
