"""Training strategy metadata and lightweight dataset analysis helpers."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml


YOLO_BASE_WEIGHTS = [
    {'id': 'yolov8n.pt', 'family': 'yolov8', 'variant': 'n', 'label': 'YOLOv8 Nano', 'size': 'nano'},
    {'id': 'yolov8s.pt', 'family': 'yolov8', 'variant': 's', 'label': 'YOLOv8 Small', 'size': 'small'},
    {'id': 'yolov8m.pt', 'family': 'yolov8', 'variant': 'm', 'label': 'YOLOv8 Medium', 'size': 'medium'},
    {'id': 'yolov8l.pt', 'family': 'yolov8', 'variant': 'l', 'label': 'YOLOv8 Large', 'size': 'large'},
    {'id': 'yolov8x.pt', 'family': 'yolov8', 'variant': 'x', 'label': 'YOLOv8 XLarge', 'size': 'xlarge'},
    {'id': 'yolo11n.pt', 'family': 'yolo11', 'variant': 'n', 'label': 'YOLO11 Nano', 'size': 'nano'},
    {'id': 'yolo11s.pt', 'family': 'yolo11', 'variant': 's', 'label': 'YOLO11 Small', 'size': 'small'},
    {'id': 'yolo11m.pt', 'family': 'yolo11', 'variant': 'm', 'label': 'YOLO11 Medium', 'size': 'medium'},
    {'id': 'yolo11l.pt', 'family': 'yolo11', 'variant': 'l', 'label': 'YOLO11 Large', 'size': 'large'},
    {'id': 'yolo11x.pt', 'family': 'yolo11', 'variant': 'x', 'label': 'YOLO11 XLarge', 'size': 'xlarge'},
]

CLIP_BASE_MODELS = [
    {'id': 'ViT-B-32/openai', 'family': 'clip', 'variant': 'ViT-B-32', 'label': 'CLIP ViT-B/32 OpenAI'},
    {'id': 'ViT-B-16/openai', 'family': 'clip', 'variant': 'ViT-B-16', 'label': 'CLIP ViT-B/16 OpenAI'},
    {'id': 'ViT-L-14/openai', 'family': 'clip', 'variant': 'ViT-L-14', 'label': 'CLIP ViT-L/14 OpenAI'},
    {'id': 'laion/CLIP-ViT-B-32-laion2B-s34B-b79K', 'family': 'clip', 'variant': 'ViT-B-32', 'label': 'LAION CLIP ViT-B/32'},
]

TRANSFORMER_BASE_MODELS = [
    {'id': 'bert-base-uncased', 'family': 'text', 'variant': 'base', 'label': 'BERT Base'},
    {'id': 'roberta-base', 'family': 'text', 'variant': 'base', 'label': 'RoBERTa Base'},
    {'id': 'google/vit-base-patch16-224', 'family': 'vision', 'variant': 'base', 'label': 'ViT Base 16/224'},
    {'id': 'facebook/detr-resnet-50', 'family': 'vision', 'variant': 'detection', 'label': 'DETR ResNet-50'},
]


TRAINING_OPTIONS = {
    'strategies': [
        {
            'id': 'yolo',
            'label': 'YOLO 目标检测',
            'training_kind': 'yolo',
            'framework': 'ultralytics',
            'model_type': 'detection',
            'families': ['yolov8', 'yolo11'],
            'variants': ['n', 's', 'm', 'l', 'x'],
            'base_weights': YOLO_BASE_WEIGHTS,
            'outputs': ['best.pt', 'last.pt', 'onnx', 'torchscript'],
        },
        {
            'id': 'clip',
            'label': 'CLIP 分类/检索',
            'training_kinds': ['clip_cls', 'clip_ret'],
            'framework': 'pytorch',
            'model_types': ['classification', 'retrieval'],
            'base_weights': CLIP_BASE_MODELS,
            'outputs': ['clip_classifier.pt', 'clip_index.faiss', 'metadata.json'],
        },
        {
            'id': 'transformer',
            'aliases': ['trusformer', 'transformers'],
            'label': 'Transformer 微调',
            'training_kind': 'transformer',
            'framework': 'transformers',
            'model_types': ['classification', 'detection', 'multimodal'],
            'base_weights': TRANSFORMER_BASE_MODELS,
            'outputs': ['pytorch_model.bin', 'model.safetensors', 'config.json'],
        },
    ]
}


def normalize_training_kind(value: str | None, model_type: str | None = None) -> str:
    """Map UI strategy aliases to persisted training_kind values."""
    normalized = (value or '').strip().lower()
    if normalized in {'yolo', 'clip_cls', 'clip_ret', 'transformer'}:
        return normalized
    if normalized == 'clip':
        return 'clip_ret' if model_type == 'retrieval' else 'clip_cls'
    if normalized in {'transformers', 'trusformer'}:
        return 'transformer'
    return 'generic'


def get_training_options() -> Dict[str, Any]:
    """Return static model strategy metadata used by API and UI."""
    return TRAINING_OPTIONS


def analyze_dataset_payload(payload: Dict[str, Any], dataset_lookup=None) -> Dict[str, Any]:
    """Analyze class names and label distribution from request payload."""
    warnings: List[str] = []
    source = 'manual'
    class_names = _coerce_class_names(payload.get('class_names') or payload.get('classes'))
    dataset_path = payload.get('dataset_path') or ''
    dataset_yaml_path = payload.get('dataset_yaml_path') or ''

    dataset_id = payload.get('dataset_id') or ''
    if dataset_id and dataset_lookup:
        dataset = dataset_lookup(str(dataset_id))
        if dataset:
            dataset_path = dataset_path or getattr(dataset, 'file_path', '') or ''
            class_names = class_names or _coerce_class_names(getattr(dataset, 'columns', []))
            source = 'dataset_record'

    if dataset_yaml_path:
        yaml_classes, yaml_warnings = _read_yolo_yaml(dataset_yaml_path)
        warnings.extend(yaml_warnings)
        if yaml_classes:
            class_names = yaml_classes
            source = 'dataset_yaml'

    label_counts, label_warnings = _scan_yolo_labels(dataset_path, class_names)
    warnings.extend(label_warnings)

    classes = []
    for index, name in enumerate(class_names):
        count = label_counts.get(index, 0)
        classes.append({'id': index, 'name': name, 'sample_count': count})

    recommendations = _build_recommendations(classes, label_counts, payload)
    suggested_task_type = _suggest_task_type(payload, dataset_yaml_path, label_counts)

    return {
        'source': source,
        'dataset_id': dataset_id,
        'dataset_path': dataset_path,
        'dataset_yaml_path': dataset_yaml_path,
        'class_count': len(classes),
        'classes': classes,
        'label_distribution': {str(k): v for k, v in sorted(label_counts.items())},
        'warnings': warnings,
        'recommendations': recommendations,
        'suggested_task_type': suggested_task_type,
        'site_hints': {
            'requires_upload': not bool(dataset_path or dataset_yaml_path or class_names),
            'recommended_site_nodes': ['project_profiler', 'website_generator', 'environment_provision', 'site_preview', 'site_qa', 'project_agent'],
            'display_mode': 'detection_gallery' if suggested_task_type == 'detection' else 'classification_dashboard',
        },
    }


def _coerce_class_names(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.replace('\n', ',').split(',') if item.strip()]
    if isinstance(value, dict):
        return [
            str(value[key]).strip()
            for key in sorted(value, key=lambda item: (0, int(item)) if str(item).isdigit() else (1, str(item)))
        ]
    if isinstance(value, Iterable):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _read_yolo_yaml(path_value: str) -> Tuple[List[str], List[str]]:
    warnings: List[str] = []
    path = Path(path_value).expanduser()
    if not path.exists():
        return [], [f'YOLO数据集配置文件不存在: {path_value}']
    try:
        with open(path, 'r', encoding='utf-8') as stream:
            data = yaml.safe_load(stream) or {}
    except Exception as exc:
        return [], [f'YOLO数据集配置读取失败: {exc}']

    names = data.get('names')
    classes = _coerce_class_names(names)
    if not classes:
        warnings.append('YOLO数据集配置未包含有效 names 字段')
    return classes, warnings


def _scan_yolo_labels(dataset_path: str, class_names: List[str]) -> Tuple[Counter, List[str]]:
    counts: Counter = Counter()
    warnings: List[str] = []
    if not dataset_path:
        return counts, warnings

    root = Path(dataset_path).expanduser()
    if root.is_file():
        root = root.parent
    if not root.exists():
        return counts, [f'数据集路径不存在，无法统计标签分布: {dataset_path}']

    candidate_dirs = [root / 'labels', root / 'train' / 'labels', root / 'valid' / 'labels', root / 'val' / 'labels']
    label_files = []
    for candidate in candidate_dirs:
        if candidate.exists():
            label_files.extend(candidate.rglob('*.txt'))
    if not label_files:
        return counts, warnings

    for label_file in label_files[:2000]:
        try:
            with open(label_file, 'r', encoding='utf-8') as stream:
                for line in stream:
                    first = line.strip().split(' ', 1)[0]
                    if first.isdigit():
                        counts[int(first)] += 1
        except UnicodeDecodeError:
            warnings.append(f'标签文件编码无法读取: {label_file}')
        except OSError as exc:
            warnings.append(f'标签文件读取失败: {label_file}: {exc}')

    if class_names:
        unknown_ids = [idx for idx in counts if idx >= len(class_names)]
        if unknown_ids:
            warnings.append(f'标签中存在超出类别列表范围的ID: {unknown_ids[:10]}')
    return counts, warnings


def _build_recommendations(classes: List[Dict[str, Any]], label_counts: Counter, payload: Dict[str, Any]) -> List[str]:
    recommendations: List[str] = []
    if not classes:
        recommendations.append('请先提供类别名称、YOLO dataset.yaml 或带标签的数据集路径。')
        return recommendations
    if len(classes) <= 3:
        recommendations.append('类别较少，建议优先使用轻量基础权重进行快速验证。')
    elif len(classes) >= 20:
        recommendations.append('类别较多，建议提高训练轮次并使用 m/l/x 级别基础权重对比。')
    if label_counts:
        non_zero = [item['sample_count'] for item in classes if item['sample_count'] > 0]
        if non_zero and max(non_zero) > min(non_zero) * 3:
            recommendations.append('类别样本分布不均衡，建议补充低频类别或开启数据增强。')
    if normalize_training_kind(payload.get('training_kind'), payload.get('model_type')) == 'yolo':
        recommendations.append('训练完成后应优先下载 best.pt，并按需导出 ONNX 用于网站部署。')
    return recommendations


def _suggest_task_type(payload: Dict[str, Any], dataset_yaml_path: str, label_counts: Counter) -> str:
    model_type = (payload.get('model_type') or '').strip().lower()
    if model_type:
        return model_type
    kind = normalize_training_kind(payload.get('training_kind'))
    if kind == 'yolo' or dataset_yaml_path or label_counts:
        return 'detection'
    if kind == 'clip_ret':
        return 'retrieval'
    return 'classification'
