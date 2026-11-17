"""Bind cloud training commands to one authenticated desktop and owner."""
import math
import re
from uuid import UUID, uuid4

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from training.models import TrainingJob
from training.execution_control import CANCEL_REQUEST_KEY

DESKTOP_AGENT_CONFIG_KEY = 'desktop_agent_id'
DESKTOP_AGENT_RECORD_CONFIG_KEY = 'desktop_agent_record_id'
TERMINAL_STATUSES = frozenset(('completed', 'failed', 'cancelled', 'timeout'))
TRAINING_EVENTS = frozenset(('training_started', 'training_progress', 'training_complete',
                             'training_error', 'training_cancelled'))
MAX_DESKTOP_JOB_ID_LENGTH = 90  # Keep training_<id> inside the Channels group name limit.
ACTIVE_DESKTOP_STATUSES = frozenset(('queued', 'provisioning', 'preparing', 'running', 'validating', 'packaging'))
MAX_TRAINING_PROGRESS = 100
MAX_DESKTOP_COUNTER = 2_147_483_647
MILLISECONDS_PER_SECOND = 1000


def _progress_number(event, names, *, maximum, minimum=0, integer=False):
    value = next((event[name] for name in names if name in event), None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    # Check bounds before isfinite so arbitrarily large Python integers are safe.
    if not minimum <= value <= maximum or not math.isfinite(value):
        return None
    if integer and value != int(value):
        return None
    return value


def _apply_progress_snapshot(job, event):
    """Keep a validated monotonic snapshot; forward the original event unchanged."""
    total = _progress_number(event, ('totalEpochs', 'total_epochs'),
                             minimum=1, maximum=MAX_DESKTOP_COUNTER, integer=True)
    epoch = _progress_number(event, ('currentEpoch', 'current_epoch'),
                             maximum=MAX_DESKTOP_COUNTER, integer=True)
    if total is not None and total >= job.current_epoch:
        job.total_epochs = int(total)
    if epoch is not None and (not job.total_epochs or epoch <= job.total_epochs):
        job.current_epoch = max(job.current_epoch, int(epoch))
    progress = _progress_number(event, ('progress',), maximum=MAX_TRAINING_PROGRESS)
    if progress is not None:
        job.progress = max(job.progress, int(progress))
    fitness = _progress_number(event, ('bestFitness', 'best_fitness'), maximum=1)
    if fitness is not None:
        job.best_fitness = max(job.best_fitness, fitness)
    elapsed = _progress_number(event, ('elapsedMs', 'elapsed_ms'),
                               maximum=MAX_DESKTOP_COUNTER * MILLISECONDS_PER_SECOND)
    if elapsed is not None:
        job.duration_seconds = max(job.duration_seconds, int(elapsed / MILLISECONDS_PER_SECOND))
    if event.get('running') is True and job.status in ('queued', 'provisioning', 'preparing'):
        job.status = 'running'
        job.started_at = job.started_at or timezone.now()


def desktop_agent_group(record_id):
    return f'agent_{record_id}'


def job_lookup(identifier):
    lookup = Q(job_id=str(identifier))
    try:
        lookup |= Q(pk=UUID(str(identifier)))
    except (ValueError, TypeError, AttributeError):
        pass
    return lookup


def bind_training_job(user, agent, config):
    """Preserve manual job IDs while persisting their assignment before dispatch."""
    if not isinstance(config, dict):
        raise ValidationError({'job_config': '训练配置必须为对象'})
    config = dict(config)
    identifier = str(config.get('jobId') or config.get('job_id') or uuid4())
    if len(identifier) > MAX_DESKTOP_JOB_ID_LENGTH or not re.fullmatch(r'[A-Za-z0-9_-]+', identifier):
        raise ValidationError({'job_config': '训练任务 ID 无效'})
    with transaction.atomic():
        if TrainingJob.objects.filter(
            created_by=user, config__desktop_agent_record_id=str(agent.pk),
            status__in=ACTIVE_DESKTOP_STATUSES,
        ).exists():
            raise ValidationError({'job_config': '设备仍有未结束的训练任务，请等待完成或取消后再下发'})
        jobs = TrainingJob.objects.select_for_update().filter(job_lookup(identifier))
        job = jobs.first()
        if job is not None:
            if job.created_by_id != user.pk:
                raise NotFound('训练任务不存在')
            assigned = (job.config or {}).get(DESKTOP_AGENT_CONFIG_KEY)
            if job.status in TERMINAL_STATUSES or job.status == 'running' or (assigned and assigned != agent.agent_id):
                raise ValidationError({'job_config': '任务已结束、正在运行或已分配给其他设备'})
            job.config = {**(job.config or {}), DESKTOP_AGENT_CONFIG_KEY: agent.agent_id,
                          DESKTOP_AGENT_RECORD_CONFIG_KEY: str(agent.pk)}
            job.save(update_fields=['config', 'updated_at'])
        else:
            job = TrainingJob.objects.create(
                job_id=identifier, created_by=user, training_kind='yolo', framework='ultralytics',
                model_type='detection', name=str(config.get('name', '')),
                config={**config, DESKTOP_AGENT_CONFIG_KEY: agent.agent_id,
                        DESKTOP_AGENT_RECORD_CONFIG_KEY: str(agent.pk)},
            )
    config['jobId'] = identifier
    return job, config


def apply_training_event(user, agent_id, event, *, agent_record_id=None):
    """Only the assigned device can report a job, and terminal states never regress."""
    identifier = event.get('jobId') or event.get('job_id')
    if not identifier:
        return None
    with transaction.atomic():
        job = TrainingJob.objects.select_for_update().filter(job_lookup(identifier), created_by=user).first()
        if job is None or (job.config or {}).get(DESKTOP_AGENT_CONFIG_KEY) != agent_id:
            return None
        if agent_record_id and (job.config or {}).get(DESKTOP_AGENT_RECORD_CONFIG_KEY) != str(agent_record_id):
            return None
        if job.status in TERMINAL_STATUSES:
            return None
        event_type = event['type']
        if (job.config or {}).get(CANCEL_REQUEST_KEY) and event_type != 'training_cancelled':
            return None
        if event_type == 'training_started':
            job.status = 'running'
            job.started_at = job.started_at or timezone.now()
        elif event_type == 'training_progress':
            _apply_progress_snapshot(job, event)
        elif event_type == 'training_complete':
            result = event.get('result') or {}
            if not isinstance(result, dict):
                return None
            success = event.get('success', result.get('success', False))
            job.status = 'completed' if success else 'failed'
            job.progress = 100 if success else job.progress
            job.completed_at = timezone.now()
            job.error_message = '' if success else str(result.get('error') or event.get('error') or '训练失败')
            for field in ('best_weight_path', 'last_weight_path'):
                if isinstance(result.get(field), str):
                    setattr(job, field, result[field])
            if isinstance(result.get('final_metrics'), dict):
                job.metrics = result['final_metrics']
                for source, target in (('mAP50', 'current_metric'), ('fitness', 'best_fitness')):
                    value = job.metrics.get(source)
                    if isinstance(value, (int, float)) and math.isfinite(value):
                        setattr(job, target, value)
            duration = result.get('duration_seconds')
            if isinstance(duration, (int, float)) and math.isfinite(duration) and duration >= 0:
                job.duration_seconds = int(duration)
        elif event_type in ('training_error', 'training_cancelled'):
            job.status = 'cancelled' if event_type == 'training_cancelled' else 'failed'
            job.error_message = str(event.get('error') or '')
            job.completed_at = timezone.now()
        job.save()
        return {str(job.pk), str(identifier), job.job_id} - {''}
