"""Resolve registered training artifacts and uploaded data without arbitrary paths."""
import hashlib
import os
import zipfile
from itertools import chain
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.db.models import Q

from .access import fresh_actor, require_resource
from .constants import EvaluationFailure, MAX_ARTIFACT_BYTES, MAX_DATA_BYTES, MAX_SAMPLES


def _uuid(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _roots(name, defaults):
    return [Path(value).absolute() for value in getattr(settings, name, defaults)]


def artifact_roots():
    base = Path(settings.BASE_DIR)
    return _roots('EVALUATION_ARTIFACT_ROOTS', [base / 'data' / 'training_outputs', base / 'outputs'])


def data_roots():
    base = Path(settings.BASE_DIR)
    return _roots('EVALUATION_DATA_ROOTS', [Path(settings.MEDIA_ROOT) / 'datasets', base / 'data' / 'datasets',
                                           base / 'data' / 'training_datasets'])


def checked_path(value, roots, *, directory=False):
    path = Path(value).absolute()
    if not any(path.is_relative_to(root) for root in roots):
        raise EvaluationFailure('资源不在服务端允许的受管目录中。', 'unmanaged_path', 422)
    for current in (path, *path.parents):
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            raise EvaluationFailure('评测资源不能经过符号链接或目录联接。', 'symlink_forbidden', 422)
    if not path.exists() or not (path.is_dir() if directory else path.is_file()):
        raise EvaluationFailure('真实模型或测试数据文件不存在。', 'resource_missing', 422)
    resolved = path.resolve(strict=True)
    if not any(resolved.is_relative_to(root.resolve()) for root in roots):
        raise EvaluationFailure('资源解析到了受管目录之外。', 'unmanaged_path', 422)
    return resolved


def _job_paths(job):
    paths = [job.model_path, job.best_weight_path, job.last_weight_path]
    artifacts = job.exported_artifacts if isinstance(job.exported_artifacts, dict) else {}
    for key in ('torchscript', 'torchscript_path', 'onnx', 'onnx_path', 'model_path', 'best_weight_path'):
        value = artifacts.get(key)
        if isinstance(value, str):
            paths.append(value)
    return [value for value in paths if isinstance(value, str) and value]


def training_source(actor, identifier=None, legacy_path=''):
    from training.models import TrainingJob
    identifier = identifier or _uuid(legacy_path)
    queryset = TrainingJob.objects.select_related('tenant', 'created_by', 'workflow', 'execution', 'node')
    if identifier:
        job = queryset.filter(pk=identifier).first()
    else:
        job = queryset.filter(Q(model_path=legacy_path) | Q(best_weight_path=legacy_path) | Q(last_weight_path=legacy_path)).first()
    if not job:
        raise EvaluationFailure('请选择真实训练任务；旧路径必须匹配已登记的模型产物。', 'model_not_registered', 422)
    require_resource(actor, job)
    if job.status != 'completed':
        raise EvaluationFailure('训练尚未完成，不能将中间状态作为可评测模型。', 'training_not_completed', 409)
    return job


def model_file(job, requested=''):
    paths = _job_paths(job)
    selected = requested if requested and not _uuid(requested) else next(iter(paths), '')
    if selected not in paths:
        raise EvaluationFailure('模型路径不属于该训练任务的已登记产物。', 'artifact_mismatch', 422)
    path = checked_path(selected, artifact_roots())
    source = None
    if job.execution_id or job.node_id:
        from workflows.models import NodeExecution
        if not job.execution_id or not job.node_id or not job.workflow_id:
            raise EvaluationFailure('训练来源关联不完整。', 'untrusted_artifact', 422)
        source = NodeExecution.objects.select_related('execution', 'node', 'node__workflow').filter(
            execution_id=job.execution_id, execution__workflow_id=job.workflow_id,
            node_id=job.node_id, node__workflow_id=job.workflow_id,
            node__node_type__in=('model_training', 'yolo_training', 'clip_classification'), status='completed').first()
        output = source.output_data if source and isinstance(source.output_data, dict) else {}
        actor_id = source.execution.triggered_by_id if source else None
        if source and actor_id is None and source.execution.trigger_type == 'scheduled':
            actor_id = source.node.workflow.owner_id
        if not source or str(output.get('training_run_id', '')) != str(job.pk) or actor_id != job.created_by_id or source.node.workflow.tenant_id != job.tenant_id:
            raise EvaluationFailure('训练产物缺少匹配的真实执行来源。', 'untrusted_artifact', 422)
    canonical = any(path.is_relative_to(root.resolve() / str(job.pk)) for root in artifact_roots())
    if not canonical:
        output = source.output_data if source and isinstance(source.output_data, dict) else {}
        recorded_paths = [output.get(key) for key in ('model_path', 'best_weight_path', 'best_model_path', 'last_weight_path')]
        if str(output.get('training_run_id', '')) != str(job.pk) or selected not in recorded_paths:
            raise EvaluationFailure('自定义模型目录缺少真实完成节点的产物证明。', 'untrusted_artifact', 422)
    if path.stat().st_size > getattr(settings, 'EVALUATION_MAX_ARTIFACT_BYTES', MAX_ARTIFACT_BYTES):
        raise EvaluationFailure('模型文件超过评测大小限制。', 'artifact_limit', 413)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_SAMPLES or sum(entry.file_size for entry in entries) > getattr(settings, 'EVALUATION_MAX_ARTIFACT_BYTES', MAX_ARTIFACT_BYTES):
                raise EvaluationFailure('模型展开后的大小或条目数超过限制。', 'artifact_limit', 413)
            if any(Path(entry.filename).is_absolute() or '..' in Path(entry.filename).parts for entry in entries):
                raise EvaluationFailure('模型归档包含非法路径。', 'invalid_artifact', 422)
    return path


def dataset_source(actor, training, identifier=None, training_identifier=None, legacy_path=''):
    from datasets.models import Dataset
    from training.models import Dataset as TrainingDataset
    candidates = []
    if identifier or _uuid(legacy_path):
        candidates += list(Dataset.objects.select_related('tenant').filter(pk=identifier or _uuid(legacy_path)))
    if training_identifier or _uuid(legacy_path):
        candidates += list(TrainingDataset.objects.select_related('tenant').filter(pk=training_identifier or _uuid(legacy_path)))
    if not identifier and not training_identifier and not _uuid(legacy_path) and legacy_path:
        candidates += list(Dataset.objects.select_related('tenant').filter(Q(file_path=legacy_path) | Q(file=legacy_path)))
        candidates += list(TrainingDataset.objects.select_related('tenant').filter(file_path=legacy_path))
        # Legacy clients send the resolved absolute FileField path.
        media = Path(settings.MEDIA_ROOT).absolute()
        supplied = Path(legacy_path).absolute()
        if supplied.is_relative_to(media):
            candidates += list(Dataset.objects.select_related('tenant').filter(file=str(supplied.relative_to(media)).replace('\\', '/')))
    if not candidates and not identifier and not training_identifier and not legacy_path and training.dataset_id:
        return dataset_source(actor, training, legacy_path=training.dataset_id)
    allowed = []
    for candidate in candidates:
        try:
            require_resource(actor, candidate)
        except EvaluationFailure:
            continue
        if candidate.tenant_id == training.tenant_id:
            allowed.append(candidate)
    if not allowed:
        raise EvaluationFailure('请选择同一可管理空间内已登记的测试数据集。', 'dataset_forbidden', 403)
    dataset = allowed[0]
    if isinstance(dataset, Dataset) and dataset.status != 'ready':
        raise EvaluationFailure('测试数据集尚未就绪。', 'dataset_not_ready', 409)
    value = dataset.get_absolute_file_path() if isinstance(dataset, Dataset) else dataset.file_path
    if isinstance(dataset, Dataset) and dataset.format in ('classification_folders', 'image_folder', 'yolo', 'image_text_pairs') and dataset.file_path:
        value = dataset.file_path
    if value and not Path(value).is_absolute():
        value = str(Path(settings.BASE_DIR) / value)
    if not value:
        raise EvaluationFailure('测试数据集没有已上传的本地数据。', 'dataset_missing', 422)
    is_directory = Path(value).is_dir()
    path = checked_path(value, data_roots(), directory=is_directory)
    # An owned row must not relabel another account's registered upload.
    foreign = chain(Dataset.objects.exclude(created_by_id=dataset.created_by_id).iterator(),
                    TrainingDataset.objects.exclude(created_by_id=dataset.created_by_id).iterator())
    for other in foreign:
        originals = []
        if other.file_path:
            originals.append(str((Path(settings.MEDIA_ROOT) if isinstance(other, Dataset) else Path(settings.BASE_DIR)) / other.file_path))
        if isinstance(other, Dataset) and other.file:
            originals.append(str(Path(settings.MEDIA_ROOT) / str(other.file)))
        for original in originals:
            if not original:
                continue
            registered = Path(os.path.abspath(original))
            folder = getattr(other, 'format', '') in ('classification_folders', 'image_folder', 'yolo', 'image_text_pairs')
            if registered == path or is_directory and registered.is_relative_to(path) or folder and path.is_relative_to(registered):
                raise EvaluationFailure('数据文件或目录包含其他用户已登记的资源。', 'dataset_alias_forbidden', 403)
    return dataset, path


def resolve_resources(actor, values):
    actor = fresh_actor(actor)
    training = training_source(actor, values.get('training_job_id'), values.get('model_path', ''))
    model = model_file(training, values.get('model_path', ''))
    dataset, data = dataset_source(actor, training, values.get('dataset_id'), values.get('training_dataset_id'),
                                   values.get('test_dataset_path', ''))
    return training, dataset, model, data


def copy_resource(source, destination, *, roots, maximum):
    """Copy bounded bytes; recheck path and identity around each opened file."""
    source = checked_path(source, roots, directory=Path(source).is_dir())
    digest = hashlib.sha256()
    total = 0
    def entries():
        if not source.is_dir():
            yield source
            return
        pending = [source]
        entry_count = 0
        while pending:
            directory = pending.pop()
            for entry in directory.iterdir():
                entry_count += 1
                if entry_count > MAX_SAMPLES * 2:
                    raise EvaluationFailure('数据目录条目超过评测限制。', 'dataset_limit', 413)
                checked = checked_path(entry, roots, directory=entry.is_dir())
                if checked.is_dir():
                    pending.append(checked)
                else:
                    yield checked
    files = 0
    for entry in entries():
        checked = checked_path(entry, roots, directory=entry.is_dir())
        if checked.is_dir():
            continue
        files += 1
        if files > MAX_SAMPLES:
            raise EvaluationFailure('数据集文件数超过评测限制。', 'dataset_limit', 413)
        target = destination / checked.relative_to(source) if source.is_dir() else destination
        target.parent.mkdir(parents=True, exist_ok=True)
        digest.update(str(checked.relative_to(source) if source.is_dir() else source.name).encode())
        before = checked.stat()
        with checked.open('rb') as incoming, target.open('wb') as outgoing:
            if os.fstat(incoming.fileno()).st_ino != before.st_ino:
                raise EvaluationFailure('复制期间资源发生变化。', 'resource_changed', 409)
            while block := incoming.read(1024 * 1024):
                total += len(block)
                if total > maximum:
                    raise EvaluationFailure('评测资源超过大小限制。', 'resource_limit', 413)
                digest.update(block)
                outgoing.write(block)
        after = checked.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise EvaluationFailure('复制期间资源发生变化。', 'resource_changed', 409)
    if not files or not total:
        raise EvaluationFailure('测试资源为空。', 'empty_resource', 422)
    return digest.hexdigest()
