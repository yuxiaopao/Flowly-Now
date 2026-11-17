"""Persistent claims and bounded, credential-free evaluation subprocesses."""
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .access import fresh_actor, require_manage, require_resource
from .constants import (EvaluationFailure, DEFAULT_TIMEOUT_SECONDS, DEFAULT_LEASE_SECONDS,
    MAX_ARTIFACT_BYTES, MAX_DATA_BYTES, MAX_OUTPUT_BYTES, POLL_SECONDS,
    CLASSIFICATION_METRICS, DETECTION_METRICS, DEFAULT_METRICS)
from .models import EvaluationJob
from .resources import resolve_resources, copy_resource, artifact_roots, data_roots, dataset_source


def recover_stale(queryset):
    from django.db.models import Q
    now = timezone.now()
    cutoff = now - timedelta(seconds=getattr(settings, 'EVALUATION_LEASE_SECONDS', DEFAULT_LEASE_SECONDS))
    stale = queryset.filter(status='running').filter(Q(lease_expires_at__lte=now) |
        Q(lease_expires_at__isnull=True, started_at__lte=cutoff) |
        Q(lease_expires_at__isnull=True, started_at__isnull=True, created_at__lte=cutoff))
    return stale.update(
        status='failed', error_code='lease_expired', error_message='评测执行进程已失联，请明确重试。',
        completed_at=now, claim_token=None, lease_expires_at=None)


def normalized_parameters(training, values):
    parameters = dict(values or {})
    detection = training.training_kind == 'yolo' and training.model_type not in ('classifier', 'classification')
    allowed = DETECTION_METRICS if detection else CLASSIFICATION_METRICS
    metrics = parameters.get('metrics') or (DETECTION_METRICS if detection else DEFAULT_METRICS)
    if not isinstance(metrics, (list, tuple)) or not metrics or any(value not in allowed for value in metrics):
        raise EvaluationFailure('所选指标不适用于真实模型类型。', 'unsupported_metric', 422)
    parameters['metrics'] = list(dict.fromkeys(metrics))
    parameters['yolo_version'] = training.yolo_version or '11'
    parameters['model_variant'] = training.model_variant or 'n'
    parameters['task'] = {'detection': 'detect', 'classification': 'classify', 'classifier': 'classify', 'segmentation': 'segment',
        'keypoint': 'pose', 'oriented_detection': 'obb'}.get(training.model_type, 'detect')
    return parameters


def create_evaluation(actor, values, source=None, deadline=None):
    from datasets.models import Dataset
    training, dataset, model, data = resolve_resources(actor, values)
    if source and source[0].tenant_id != training.tenant_id:
        raise EvaluationFailure('工作流、模型和测试数据必须属于同一空间。', 'tenant_mismatch', 403)
    parameters = normalized_parameters(training, values.get('parameters'))
    if deadline:
        from datetime import datetime
        parsed = datetime.fromisoformat(deadline)
        if timezone.is_naive(parsed):
            raise EvaluationFailure('工作流总超时必须包含时区。', 'invalid_deadline', 422)
        parameters['_execution_deadline_at'] = parsed.isoformat()
    return EvaluationJob.objects.create(name=values.get('name') or '模型评测', job_id=f'eval_{uuid.uuid4().hex}',
        created_by=fresh_actor(actor), tenant=training.tenant, training_job=training,
        dataset=dataset if isinstance(dataset, Dataset) else None,
        training_dataset=None if isinstance(dataset, Dataset) else dataset,
        workflow=source[0] if source else None, node=source[1] if source else None, execution=source[2] if source else None,
        model_path=str(model), test_dataset_path=str(data), parameters=parameters)


@transaction.atomic
def claim(job_id, actor):
    job = EvaluationJob.objects.select_for_update().select_related('tenant', 'created_by').get(pk=job_id)
    require_manage(actor, job)
    recover_stale(EvaluationJob.objects.filter(pk=job.pk))
    job.refresh_from_db()
    if job.status in ('running', 'completed', 'cancelled'):
        raise EvaluationFailure('评测正在运行、已经完成或已取消，不能重复执行。', 'evaluation_conflict', 409)
    now = timezone.now()
    job.status, job.claim_token, job.started_at = 'running', uuid.uuid4(), now
    job.lease_expires_at = now + timedelta(seconds=getattr(settings, 'EVALUATION_LEASE_SECONDS', DEFAULT_LEASE_SECONDS))
    job.completed_at, job.metrics, job.error_message, job.error_code = None, {}, '', ''
    job.artifact_snapshot = {}
    job.save(update_fields=['status', 'claim_token', 'started_at', 'lease_expires_at', 'completed_at', 'metrics', 'error_message', 'error_code', 'artifact_snapshot'])
    return job


def _child_environment(directory):
    # Deliberate allowlist: no API keys, DATABASE_URL, cloud credentials or host caches.
    environment = {key: os.environ[key] for key in ('SYSTEMROOT', 'WINDIR', 'PATH', 'COMSPEC', 'PATHEXT') if key in os.environ}
    environment.update(TEMP=str(directory), TMP=str(directory), USERPROFILE=str(directory),
        USERNAME='flowly-evaluation', USER='flowly-evaluation', APPDATA=str(directory / 'appdata'),
        LOCALAPPDATA=str(directory / 'localappdata'),
        XDG_CACHE_HOME=str(directory / 'cache'), TORCH_HOME=str(directory / 'torch'),
        MPLCONFIGDIR=str(directory / 'matplotlib'), YOLO_CONFIG_DIR=str(directory / 'ultralytics'),
        CUDA_VISIBLE_DEVICES='', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1', PYTHONIOENCODING='utf-8')
    return environment


def _stop_process(process):
    import psutil
    try:
        descendants = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        descendants = []
    for child in reversed(descendants):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    if process.poll() is None:
        process.terminate()
    _, alive = psutil.wait_procs(descendants, timeout=5)
    for child in alive:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _copy_cached_encoder(training, parameters, directory):
    """Only known pretrained cache entries with their published hash are eligible."""
    if training.training_kind != 'clip_cls' or Path(training.model_path).suffix.lower() == '.torchscript':
        return
    import hashlib
    from urllib.parse import urlparse
    import torch
    candidates = []
    encoder = (training.exported_artifacts or {}).get('encoder_type')
    if encoder in (None, '', 'resnet18_fallback'):
        from torchvision.models import ResNet18_Weights
        filename = Path(urlparse(ResNet18_Weights.DEFAULT.url).path).name
        candidates.append(('resnet18_fallback', Path(torch.hub.get_dir()) / 'checkpoints' / filename, filename.split('-')[-1].split('.')[0]))
    if encoder in (None, '', 'clip'):
        try:
            import clip
            model_name = (training.config or {}).get('base_model') or (training.config or {}).get('baseModel') or 'ViT-B/32'
            url = clip.clip._MODELS.get(model_name)
            if url:
                parts = urlparse(url).path.split('/')
                candidates.append(('clip', Path.home() / '.cache' / 'clip' / parts[-1], parts[-2]))
                parameters['base_encoder_model'] = model_name
        except ImportError:
            pass
    for encoder_type, candidate, expected_hash in candidates:
        if not candidate.is_file():
            continue
        copied = directory / (f'base-{encoder_type}' + candidate.suffix)
        copy_resource(candidate, copied, roots=[candidate.parent.absolute()], maximum=MAX_ARTIFACT_BYTES)
        digest = hashlib.sha256()
        with copied.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        actual = digest.hexdigest()
        if not actual.startswith(expected_hash):
            raise EvaluationFailure('缓存编码器不匹配官方权重摘要，请重新准备真实基础模型。', 'encoder_hash_mismatch', 422)
        parameters.setdefault('base_encoder_files', {})[encoder_type] = str(copied)
        parameters.setdefault('base_encoder_hashes', {})[encoder_type] = actual
def _child_result(job, actor, directory):
    values = {'training_job_id': job.training_job_id, 'dataset_id': job.dataset_id,
        'training_dataset_id': job.training_dataset_id, 'model_path': job.model_path,
        'test_dataset_path': job.test_dataset_path}
    training, dataset, model, data = resolve_resources(actor, values)
    if training.tenant_id != job.tenant_id:
        raise EvaluationFailure('评测关联资源的空间已改变。', 'tenant_mismatch', 403)
    model_copy = directory / ('model' + model.suffix)
    data_copy = directory / 'dataset' if data.is_dir() else directory / ('dataset' + data.suffix)
    artifact_hash = copy_resource(model, model_copy, roots=artifact_roots(),
        maximum=getattr(settings, 'EVALUATION_MAX_ARTIFACT_BYTES', MAX_ARTIFACT_BYTES))
    data_hash = copy_resource(data, data_copy, roots=data_roots(),
        maximum=getattr(settings, 'EVALUATION_MAX_DATA_BYTES', MAX_DATA_BYTES))
    snapshot = {'training_job_id': str(training.pk), 'dataset_id': str(dataset.pk),
        'artifact_sha256': artifact_hash, 'dataset_sha256': data_hash, 'training_kind': training.training_kind,
        'created_by_id': job.created_by_id, 'tenant_id': job.tenant_id,
        'workflow_id': str(job.workflow_id) if job.workflow_id else None,
        'node_id': str(job.node_id) if job.node_id else None, 'execution_id': str(job.execution_id) if job.execution_id else None}
    job.artifact_snapshot = snapshot
    EvaluationJob.objects.filter(pk=job.pk, status='running', claim_token=job.claim_token).update(artifact_snapshot=snapshot)
    parameters = normalized_parameters(training, job.parameters)
    _copy_cached_encoder(training, parameters, directory)
    if parameters.get('base_encoder_hashes'):
        snapshot['base_encoder_hashes'] = parameters['base_encoder_hashes']
    if training.training_kind == 'generic':
        from .evaluators import read_tabular_data
        try:
            read_tabular_data(data_copy, parameters.get('label_column'), parameters.get('features'))
        except (ValueError, TypeError, KeyError) as exc:
            raise EvaluationFailure(str(exc), 'invalid_dataset', 422) from exc
    request = {'model': str(model_copy), 'dataset': str(data_copy), 'parameters': parameters,
        'class_names': training.class_names or [], 'training_kind': training.training_kind,
        'model_configuration': {key: value for key, value in (training.config or {}).items()
            if key in ('input_dim', 'hidden_dims', 'output_dim', 'dropout', 'input_mean', 'input_std', 'feature_names', 'label_column')}}
    if training.training_kind == 'generic' and (training.dataset_id or training.dataset_path):
        try:
            original_dataset, original_path = dataset_source(actor, training, legacy_path=training.dataset_id or training.dataset_path)
        except EvaluationFailure:
            original_path = None
        if original_path and original_path.is_file():
            original_copy = directory / ('training-data' + original_path.suffix)
            snapshot['training_dataset_sha256'] = copy_resource(original_path, original_copy, roots=data_roots(), maximum=MAX_DATA_BYTES)
            request['training_dataset'] = str(original_copy)
    EvaluationJob.objects.filter(pk=job.pk, status='running', claim_token=job.claim_token).update(artifact_snapshot=snapshot)
    request_file, result_file = directory / 'request.json', directory / 'result.json'
    request_file.write_text(json.dumps(request, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    if not EvaluationJob.objects.filter(pk=job.pk, status='running', claim_token=job.claim_token).exists():
        raise EvaluationFailure('本次评测在启动前已停止。', 'execution_replaced', 409)
    require_manage(actor, job)
    require_resource(actor, training)
    require_resource(actor, dataset)
    if job.execution_id:
        from workflows.models import WorkflowExecution
        if not WorkflowExecution.objects.filter(pk=job.execution_id, status='running').exists():
            raise EvaluationFailure('父工作流在评测启动前已停止。', 'parent_stopped', 409)
    process = subprocess.Popen([sys.executable, '-I', str(Path(__file__).with_name('worker.py')), str(request_file), str(result_file)],
        cwd=directory, env=_child_environment(directory), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    timeout = getattr(settings, 'EVALUATION_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS)
    try:
        while process.poll() is None:
            current = EvaluationJob.objects.filter(pk=job.pk).values('status', 'claim_token', 'started_at').first()
            if not current or current['status'] != 'running' or current['claim_token'] != job.claim_token:
                raise EvaluationFailure('本次执行已被取消或新运行取代。', 'execution_replaced', 409)
            require_manage(actor, job)
            require_resource(actor, training)
            require_resource(actor, dataset)
            if job.execution_id:
                from workflows.models import WorkflowExecution
                parent_status = WorkflowExecution.objects.filter(pk=job.execution_id).values_list('status', flat=True).first()
                if parent_status != 'running':
                    raise EvaluationFailure('父工作流已停止，评测不再接收结果。', 'parent_stopped', 409)
            if job.parameters.get('_execution_deadline_at'):
                from datetime import datetime
                if timezone.now() >= datetime.fromisoformat(job.parameters['_execution_deadline_at']):
                    raise EvaluationFailure('工作流总预算已耗尽，未接收迟到评测。', 'evaluation_timeout', 504)
            if (timezone.now() - job.started_at).total_seconds() >= timeout:
                raise EvaluationFailure('模型评测超时，未接收迟到结果。', 'evaluation_timeout', 504)
            try:
                process.wait(timeout=POLL_SECONDS)
            except subprocess.TimeoutExpired:
                continue
        if not result_file.is_file() or result_file.stat().st_size > MAX_OUTPUT_BYTES:
            raise EvaluationFailure('评测子进程没有返回有效结果。', 'worker_failed', 503)
        result = json.loads(result_file.read_text(encoding='utf-8'))
        if not result.get('success'):
            message = result.get('error', '真实模型推理失败。')
            # Pickle errors can include object contents and environment paths.
            if 'Weights only' in message or 'weights_only' in message or 'Unsupported global' in message:
                message = '该模型包含不受支持的 Python 对象。请导出 tensor state_dict、safetensors 或可信 TorchScript/ONNX。'
            raise EvaluationFailure(str(message)[:1000], 'model_evaluation_failed', 422)
        returned = result['metrics']
        if any(metric not in returned for metric in parameters['metrics']):
            raise EvaluationFailure('真实评测未提供所选指标。', 'metric_unavailable', 422)
        return {name: value for name, value in returned.items()
            if name in {'sample_count', 'classes', 'confusion_matrix', 'mode', 'task', 'preprocessing', 'feature_columns'} or name in parameters['metrics']}
    finally:
        if process.poll() is None:
            _stop_process(process)


def run_evaluation(job_id, actor):
    job = claim(job_id, actor)
    status_code = 200
    try:
        with tempfile.TemporaryDirectory(prefix='flowly-evaluation-') as workspace:
            metrics = _child_result(job, actor, Path(workspace))
        require_manage(actor, job)
        training, _, _, _ = resolve_resources(actor, {'training_job_id': job.training_job_id,
            'dataset_id': job.dataset_id, 'training_dataset_id': job.training_dataset_id,
            'model_path': job.model_path, 'test_dataset_path': job.test_dataset_path})
        if training.tenant_id != job.tenant_id:
            raise EvaluationFailure('评测空间在运行期间已改变。', 'tenant_mismatch', 403)
        if job.execution_id:
            from workflows.models import WorkflowExecution
            if not WorkflowExecution.objects.filter(pk=job.execution_id, status='running').exists():
                raise EvaluationFailure('父工作流已停止。', 'parent_stopped', 409)
        if job.parameters.get('_execution_deadline_at'):
            from datetime import datetime
            if timezone.now() >= datetime.fromisoformat(job.parameters['_execution_deadline_at']):
                raise EvaluationFailure('工作流总预算已耗尽。', 'evaluation_timeout', 504)
        job.metrics, job.status = metrics, 'completed'
    except EvaluationFailure as exc:
        job.status, job.error_code, job.error_message = 'failed', exc.code, str(exc)
        status_code = exc.status
    except Exception:
        job.status, job.error_code = 'failed', 'evaluation_unavailable'
        job.error_message, status_code = '模型评测不可用，请检查真实产物、数据和运行环境。', 503
    completed = timezone.now()
    history = list(job.metrics_history or [])
    history.append({'started_at': job.started_at.isoformat(), 'completed_at': completed.isoformat(),
        'status': job.status, 'metrics': job.metrics, 'error_code': job.error_code, 'artifact_snapshot': job.artifact_snapshot})
    changed = EvaluationJob.objects.filter(pk=job.pk, status='running', claim_token=job.claim_token).update(
        status=job.status, metrics=job.metrics, error_code=job.error_code, error_message=job.error_message,
        completed_at=completed, lease_expires_at=None, metrics_history=history)
    job.refresh_from_db()
    if not changed:
        return job, 409
    return job, status_code
