"""YOLO base-weight resolution helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def resolve_yolo_model_source(config: Dict[str, Any]) -> str:
    """Return the explicit YOLO base weight or derive one from version/variant."""
    nested = config.get('config') if isinstance(config.get('config'), dict) else {}
    explicit = (
        config.get('base_weight_uri')
        or config.get('baseWeightUri')
        or config.get('baseModel')
        or nested.get('base_weight_uri')
        or nested.get('baseWeightUri')
        or nested.get('baseModel')
    )
    if explicit:
        return str(explicit)

    yolo_version = str(config.get('yolo_version') or config.get('yoloVersion') or 'v8').strip().lower()
    model_variant = str(config.get('model_variant') or config.get('modelVariant') or 'n').strip().lower().replace('.pt', '')
    if yolo_version.startswith('yolo'):
        model_name = f'{yolo_version}{model_variant}'
    elif yolo_version.startswith('v'):
        version_number = yolo_version[1:]
        family = 'yolo11' if version_number == '11' else f'yolov{version_number}'
        model_name = f'{family}{model_variant}'
    else:
        family = 'yolo11' if yolo_version == '11' else f'yolov{yolo_version}'
        model_name = f'{family}{model_variant}'

    return f'{model_name}.pt'


def yolo_model_label(model_source: str) -> str:
    """Human-readable model label for logs and errors."""
    if not model_source:
        return ''
    return Path(str(model_source)).stem
