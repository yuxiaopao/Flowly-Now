"""Training artifact contracts shared by training and generated-site flows."""

from __future__ import annotations

from typing import Any, Dict, List


def build_model_artifact_manifest(job) -> Dict[str, Any]:
    """Return the stable artifact manifest consumed by website generation."""
    config = dict(getattr(job, 'config', None) or {})
    labels = _labels_from_job(job)
    training_kind = getattr(job, 'training_kind', '') or 'generic'
    model_type = getattr(job, 'model_type', '') or _task_type_for_kind(training_kind)
    task_type = _task_type_for_kind(training_kind, model_type)
    best_weight_path = getattr(job, 'best_weight_path', '') or getattr(job, 'model_path', '') or ''
    base_model = (
        config.get('base_weight_uri')
        or config.get('baseModel')
        or config.get('base_model')
        or _base_model_from_yolo(job)
    )

    return {
        'schemaVersion': 'flowly.modelArtifactManifest/v1',
        'trainingJobId': str(getattr(job, 'id', '') or ''),
        'taskType': task_type,
        'trainingKind': training_kind,
        'baseModel': base_model,
        'framework': getattr(job, 'framework', '') or _framework_for_kind(training_kind),
        'modelType': model_type,
        'bestWeightPath': best_weight_path,
        'lastWeightPath': getattr(job, 'last_weight_path', '') or '',
        'modelPath': getattr(job, 'model_path', '') or best_weight_path,
        'labels': labels,
        'classNames': labels,
        'metrics': dict(getattr(job, 'metrics', None) or {}),
        'metricHistory': list(getattr(job, 'metrics_history', None) or []),
        'previewSamples': list(getattr(job, 'preview_samples', None) or []),
        'exportedArtifacts': dict(getattr(job, 'exported_artifacts', None) or {}),
        'siteHints': _site_hints(task_type, labels),
    }


def _labels_from_job(job) -> List[str]:
    labels = getattr(job, 'class_names', None) or []
    if isinstance(labels, str):
        return [item.strip() for item in labels.replace('\n', ',').split(',') if item.strip()]
    if isinstance(labels, dict):
        return [str(labels[key]).strip() for key in sorted(labels, key=str) if str(labels[key]).strip()]
    if isinstance(labels, list):
        return [str(item).strip() for item in labels if str(item).strip()]
    return []


def _task_type_for_kind(training_kind: str, model_type: str = '') -> str:
    kind = (training_kind or '').lower()
    current_model_type = (model_type or '').lower()
    if current_model_type in {'detection', 'classification', 'retrieval', 'multimodal'}:
        return current_model_type
    if kind == 'yolo':
        return 'detection'
    if kind == 'clip_ret':
        return 'retrieval'
    if kind in {'clip_cls', 'transformer'}:
        return 'classification'
    return current_model_type or 'classification'


def _framework_for_kind(training_kind: str) -> str:
    if training_kind == 'yolo':
        return 'ultralytics'
    if training_kind == 'transformer':
        return 'transformers'
    return 'pytorch'


def _base_model_from_yolo(job) -> str:
    version = (getattr(job, 'yolo_version', '') or '').lower().replace('v', '')
    variant = (getattr(job, 'model_variant', '') or '').lower()
    if version and variant:
        family = 'yolo11' if version in {'11', 'yolo11'} else f'yolov{version}'
        return f'{family}{variant}.pt'
    return ''


def _site_hints(task_type: str, labels: List[str]) -> Dict[str, Any]:
    default_features = ['imageRecognition', 'videoRecognition', 'factRecognition', 'historyRecords']
    display_mode = 'detection_workbench' if task_type == 'detection' else 'classification_dashboard'
    if task_type == 'retrieval':
        display_mode = 'retrieval_gallery'
    return {
        'requiredFeatures': default_features,
        'recommendedStack': {'backend': 'flask', 'frontend': 'vue', 'database': 'mysql'},
        'displayMode': display_mode,
        'historyFields': ['mode', 'input_summary', 'output_summary', 'latency_ms', 'detections_json'],
        'labelCount': len(labels),
    }
