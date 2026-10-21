"""
Cross-cutting execution control helpers.

Covers gaps that pause/resume alone do not solve:
- JSON-safe checkpoints (Decimal / datetime / UUID / bytes)
- Claim lock so two workers never resume the same execution
- Per-workflow concurrency caps
- Heartbeat + stale "running" recovery when a worker dies
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def make_json_safe(value: Any) -> Any:
    """Recursively coerce values so Django JSONField / Redis can store them."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except Exception:
            return value.hex()
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(v) for v in value]
    if hasattr(value, 'isoformat'):
        try:
            return value.isoformat()
        except Exception:
            pass
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError, OverflowError):
        return str(value)


def max_concurrent_per_workflow() -> int:
    return max(1, int(getattr(settings, 'WORKFLOW_MAX_CONCURRENT_PER_WORKFLOW', 3)))


def stale_running_minutes() -> int:
    return max(5, int(getattr(settings, 'WORKFLOW_STALE_RUNNING_MINUTES', 45)))


def heartbeat_interval_seconds() -> float:
    return float(getattr(settings, 'WORKFLOW_HEARTBEAT_INTERVAL_SEC', 15))


def count_active_runs(workflow_id, exclude_execution_id=None) -> int:
    """Count executions that occupy a worker slot (queued/pending/running)."""
    from workflows.models import WorkflowExecution

    qs = WorkflowExecution.objects.filter(
        workflow_id=workflow_id,
        status__in=('queued', 'pending', 'running'),
    )
    if exclude_execution_id:
        qs = qs.exclude(id=exclude_execution_id)
    return qs.count()


def check_concurrency_allowed(workflow_id, exclude_execution_id=None) -> Tuple[bool, str]:
    """Return (ok, message). Paused/interrupted do not consume concurrency slots."""
    limit = max_concurrent_per_workflow()
    current = count_active_runs(workflow_id, exclude_execution_id=exclude_execution_id)
    if current >= limit:
        return False, (
            f'该工作流已有 {current} 个进行中的执行（上限 {limit}）。'
            f'请等待完成、暂停后恢复，或取消多余任务。'
        )
    return True, ''


def write_heartbeat(execution, extra: Optional[Dict[str, Any]] = None) -> None:
    """Persist last heartbeat into context_data (no schema migration)."""
    base = dict(execution.context_data or {})
    base['heartbeat_at'] = timezone.now().isoformat()
    if extra:
        base.update(make_json_safe(extra))
    execution.context_data = base
    try:
        execution.save(update_fields=['context_data'])
    except Exception as e:
        logger.debug('Heartbeat save failed for %s: %s', execution.id, e)


def get_heartbeat_at(execution) -> Optional[datetime]:
    raw = (execution.context_data or {}).get('heartbeat_at')
    if not raw:
        return None
    try:
        if isinstance(raw, datetime):
            return raw
        return datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
    except Exception:
        return None


@transaction.atomic
def claim_execution_for_run(
    execution_id,
    *,
    allowed_statuses: Tuple[str, ...],
    task_id: Optional[str] = None,
    require_snapshot: bool = False,
) -> Tuple[bool, Any, str]:
    """
    Atomically claim an execution for a worker.

    Prevents double-resume / double-start races across concurrent Celery workers.
    Returns (ok, execution, message).
    """
    from workflows.models import WorkflowExecution

    try:
        execution = (
            WorkflowExecution.objects.select_for_update()
            .select_related('workflow')
            .get(id=execution_id)
        )
    except WorkflowExecution.DoesNotExist:
        return False, None, 'Execution not found'

    if execution.status not in allowed_statuses:
        return False, execution, f'Execution status is {execution.status}, cannot claim'

    if require_snapshot:
        snap = execution.context_snapshot or {}
        if not snap.get('visited') and not snap.get('node_results'):
            return False, execution, 'No resume snapshot available'

    execution.status = 'running'
    execution.paused_at = None
    update_fields = ['status', 'paused_at']
    if task_id:
        execution.task_id = task_id
        update_fields.append('task_id')
    if not execution.started_at:
        execution.started_at = timezone.now()
        update_fields.append('started_at')
    execution.save(update_fields=update_fields)
    write_heartbeat(execution, extra={'claimed_at': timezone.now().isoformat()})
    return True, execution, 'claimed'


def recover_stale_running_executions(minutes: Optional[int] = None) -> Dict[str, Any]:
    """
    Mark long-silent 'running' executions as interrupted so they can be resumed.

    Uses heartbeat_at when present; falls back to started_at / queued_at.
    """
    from workflows.models import WorkflowExecution

    cutoff_minutes = minutes if minutes is not None else stale_running_minutes()
    cutoff = timezone.now() - timedelta(minutes=cutoff_minutes)
    recovered = []
    scanned = 0

    qs = WorkflowExecution.objects.filter(status='running').order_by('started_at')[:200]
    for execution in qs:
        scanned += 1
        hb = get_heartbeat_at(execution)
        ref = hb or execution.started_at or execution.queued_at
        if not ref:
            continue
        # Make naive/aware comparable
        if timezone.is_naive(ref):
            ref = timezone.make_aware(ref, timezone.get_current_timezone())
        if ref > cutoff:
            continue

        snap = execution.context_snapshot or {}
        msg = (
            f'Stale running recovered after {cutoff_minutes}m without heartbeat '
            f'(last activity ≈ {ref.isoformat()})'
        )
        try:
            execution.mark_interrupted(error_message=msg, context_snapshot=snap)
            recovered.append(str(execution.id))
            logger.warning('Recovered stale execution %s: %s', execution.id, msg)
        except Exception as e:
            logger.error('Failed recovering stale execution %s: %s', execution.id, e)

    return {
        'scanned': scanned,
        'recovered': recovered,
        'recovered_count': len(recovered),
        'cutoff_minutes': cutoff_minutes,
    }


def has_resumable_snapshot(execution) -> bool:
    snap = execution.context_snapshot or {}
    if snap.get('visited') is not None or snap.get('node_results'):
        return True
    cd = execution.context_data or {}
    return bool(cd.get('last_checkpoint'))
