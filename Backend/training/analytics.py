"""Read task-specific YOLO metrics without loading a model or changing a run."""
import csv
import json
import math
from pathlib import Path

MAX_REPORT_BYTES = 12 * 1024 * 1024
MAX_HISTORY_ROWS = 20000
TASK_ALIASES = {
    'classification': 'classify', 'detection': 'detect', 'segmentation': 'segment',
    'keypoint': 'pose', 'oriented_detection': 'obb',
}
HISTORY_ALIASES = {
    'train_loss': 'train/loss', 'val_loss': 'val/loss',
    'val_acc': 'metrics/accuracy_top1', 'accuracy': 'metrics/accuracy_top1',
    'top1': 'metrics/accuracy_top1', 'top5': 'metrics/accuracy_top5',
    'precision': 'metrics/precision(B)', 'recall': 'metrics/recall(B)',
    'mAP50': 'metrics/mAP50(B)', 'map50': 'metrics/mAP50(B)',
    'mAP50-95': 'metrics/mAP50-95(B)', 'map50_95': 'metrics/mAP50-95(B)',
    'learning_rate': 'lr/pg0',
}
CSV_ALIASES = {
    'metrics/mAP_0.5': 'metrics/mAP50(B)',
    'metrics/mAP_0.5:0.95': 'metrics/mAP50-95(B)',
    'metrics/precision': 'metrics/precision(B)', 'metrics/recall': 'metrics/recall(B)',
    'metrics/top1_acc': 'metrics/accuracy_top1', 'metrics/top5_acc': 'metrics/accuracy_top5',
    'x/lr0': 'lr/pg0', 'x/lr1': 'lr/pg1', 'x/lr2': 'lr/pg2',
}


def _number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _json(directory, name, warnings):
    if not directory:
        return None
    root = Path(directory).resolve()
    filename = root / name
    if not filename.is_file():
        return None
    if not filename.resolve().is_relative_to(root):
        warnings.append(f'{name} 指向训练目录之外，未读取。')
        return None
    try:
        if filename.stat().st_size > MAX_REPORT_BYTES:
            warnings.append(f'{name} 超过报告大小限制。')
            return None
        with filename.open(encoding='utf-8-sig') as source:
            data = json.load(source, parse_constant=lambda _: None)
        return data if isinstance(data, (dict, list)) else None
    except (OSError, ValueError):
        warnings.append(f'{name} 尚未完整写入，等待下次同步。')
        return None


def _history(run_dir, job, warnings):
    rows = {}
    filename = Path(run_dir) / 'results.csv' if run_dir else None
    if filename and filename.is_file() and filename.resolve().is_relative_to(Path(run_dir).resolve()):
        try:
            zero_based = False
            with filename.open(encoding='utf-8-sig', newline='') as source:
                for index, record in enumerate(csv.DictReader(source)):
                    if index >= MAX_HISTORY_ROWS:
                        warnings.append('训练记录超过展示上限，后续轮次未载入。')
                        break
                    values = {CSV_ALIASES.get(str(key).strip(), str(key).strip()): _number(value)
                              for key, value in record.items() if key}
                    epoch = values.get('epoch')
                    if index == 0 and epoch == 0:
                        zero_based = True
                    if epoch is None or not epoch.is_integer() or epoch < (0 if zero_based else 1):
                        continue
                    # A partially written final line must not replace a complete epoch.
                    if None in record or any(value is None for value in values.values()):
                        continue
                    epoch = int(epoch) + int(zero_based)
                    rows[epoch] = {**values, 'epoch': epoch}
        except OSError:
            warnings.append('训练曲线文件暂时不可读，使用已同步的轮次记录。')
    if rows:
        return list(sorted(rows.values(), key=lambda row: row['epoch'])), 'results.csv'
    for index, entry in enumerate((job.metrics_history or [])[:MAX_HISTORY_ROWS]):
        if not isinstance(entry, dict):
            continue
        epoch = _number(entry.get('epoch', index + 1))
        if epoch is None or not epoch.is_integer() or epoch < 1:
            continue
        row = {'epoch': int(epoch)}
        for key, value in entry.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    numeric = _number(nested_value)
                    if numeric is None:
                        continue
                    name = f'train/{nested_key}_loss' if key == 'loss' else HISTORY_ALIASES.get(nested_key, nested_key)
                    row[name] = numeric
            elif (numeric := _number(value)) is not None:
                row[HISTORY_ALIASES.get(key, key)] = numeric
        rows[int(epoch)] = row
    return list(sorted(rows.values(), key=lambda row: row['epoch'])), 'synced_history'


def build_run_analytics(job, run_dir):
    warnings = []
    history, source = _history(run_dir, job, warnings)
    config = job.config if isinstance(job.config, dict) else {}
    local = config.get('local_monitor') or config.get('localMonitor') or {}
    project = local.get('project_root') or local.get('projectRoot')
    validation = _json(run_dir, 'val-report.json', warnings)
    test = _json(run_dir, 'test-report.json', warnings)
    reports = {
        'validation': validation if isinstance(validation, dict) else None,
        'test': test if isinstance(test, dict) else None,
    }
    labels = _json(project, 'training/labels.json', warnings)
    labels = {item['key']: item.get('label', item['key']) for item in (labels or [])
              if isinstance(item, dict) and item.get('key')} if isinstance(labels, list) else {}
    dataset = _json(project, 'datasets/plantvillage/dataset-report.json', warnings)
    dataset = dataset if isinstance(dataset, dict) else {}
    classes = next((report.get('classes') for report in reports.values()
                    if report and isinstance(report.get('classes'), list)), job.class_names or [])
    keys = {key for row in history for key in row}
    raw_task = config.get('task') or (config.get('training') or {}).get('task') or job.model_type
    task = TASK_ALIASES.get(raw_task, raw_task)
    if any('accuracy_top' in key for key in keys):
        task = 'classify'
    elif any('(M)' in key or 'seg_loss' in key for key in keys):
        task = 'segment'
    elif any('(P)' in key or 'pose_loss' in key for key in keys):
        task = 'pose'
    elif any('angle_loss' in key for key in keys):
        task = 'obb'
    task = task if task in {'classify', 'detect', 'segment', 'pose', 'obb'} else 'detect'
    for split, report in reports.items():
        if not report:
            continue
        matrix = report.get('confusion_matrix')
        matrix_classes = report.get('classes') or classes
        valid = (isinstance(matrix, list) and len(matrix) == len(matrix_classes)
                 and all(isinstance(row, list) and len(row) == len(matrix_classes)
                         and all(isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
                                 for value in row) for row in matrix))
        if matrix is not None and not valid:
            report = {**report, 'confusion_matrix': None}
            reports[split] = report
            warnings.append(f'{split} 混淆矩阵维度或数值无效，未展示。')
    return {
        'id': str(job.pk), 'name': job.name, 'workflow': str(job.workflow_id or ''),
        'node': str(job.node_id or ''), 'status': job.status, 'task': task,
        'model': {'version': job.yolo_version, 'variant': job.model_variant,
                  'label': f'YOLO{str(job.yolo_version or "").removeprefix("v")}{job.model_variant or ""}'},
        'current_epoch': history[-1]['epoch'] if history else job.current_epoch,
        'total_epochs': job.total_epochs, 'best_epoch': job.best_epoch,
        'history': history, 'history_source': source, 'reports': reports,
        'classes': [{'key': key, 'label': labels.get(key, key)} for key in classes],
        'dataset': {'fingerprint': dataset.get('manifest_sha256'),
                    'identity': str(job.dataset_id or job.dataset_path or ''),
                    'counts': dataset.get('counts')},
        'warnings': warnings,
    }
