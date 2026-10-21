"""Partial retry / continue: re-run failed or unfinished nodes while keeping successes.

Supports:
- retry_failed: soft-fail media left holes → re-run failed (+ downstream)
- continue_incomplete: interrupted / never-finished → resume unfinished nodes
- continue (auto): pick the right strategy so the final film can complete
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

RETRYABLE_STATUSES = frozenset({
    'completed', 'failed', 'cancelled', 'interrupted', 'timeout', 'paused',
})

CONTINUE_STATUSES = frozenset({
    'completed', 'failed', 'cancelled', 'interrupted', 'timeout', 'paused',
})


def _sid(value: Any) -> str:
    return str(value)


def _build_adjacency(workflow) -> Dict[str, List[str]]:
    from workflows.models import Edge

    adj: Dict[str, List[str]] = {}
    for edge in Edge.objects.filter(workflow=workflow).only('source_node_id', 'target_node_id'):
        src, tgt = _sid(edge.source_node_id), _sid(edge.target_node_id)
        adj.setdefault(src, []).append(tgt)
    return adj


def _collect_descendants(seeds: Iterable[str], adj: Dict[str, List[str]]) -> Set[str]:
    out: Set[str] = set()
    stack = list(seeds)
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        for nxt in adj.get(cur) or []:
            if nxt not in out:
                stack.append(nxt)
    return out


def _failed_node_ids(execution) -> List[str]:
    from workflows.models import NodeExecution

    qs = NodeExecution.objects.filter(execution=execution, status='failed')
    try:
        qs = qs.only('node_id')
    except Exception:
        pass
    return [_sid(ne.node_id) for ne in qs]


def _node_ids_by_status(execution, statuses: Iterable[str]) -> List[str]:
    from workflows.models import NodeExecution

    qs = NodeExecution.objects.filter(execution=execution, status__in=list(statuses))
    try:
        qs = qs.only('node_id')
    except Exception:
        pass
    return [_sid(ne.node_id) for ne in qs]


def _all_workflow_node_ids(execution) -> Set[str]:
    return {_sid(n.id) for n in execution.workflow.nodes.all().only('id')}


def _never_started_node_ids(execution) -> List[str]:
    from workflows.models import NodeExecution

    all_ids = _all_workflow_node_ids(execution)
    started = {
        _sid(ne.node_id)
        for ne in NodeExecution.objects.filter(execution=execution).only('node_id')
    }
    return sorted(all_ids - started)


def analyze_continue(execution) -> Dict[str, Any]:
    """Inspect what is left to do for a complete final result."""
    from .media_execution import MEDIA_EXECUTION_KIND
    if (execution.trigger_source or {}).get('kind') == MEDIA_EXECUTION_KIND:
        return {
            'execution_id': _sid(execution.id), 'status': execution.status,
            'strategy': 'none', 'can_continue': False, 'has_snapshot': False,
            **{key: [] for key in ('failed', 'pending', 'running', 'skipped',
                                  'never_started', 'incomplete', 'queue_node_ids')},
            'hint': '这是独立成片任务或历史成片归档，不代表画布节点执行，不能作为节点断点续跑',
        }
    failed = _failed_node_ids(execution)
    pending = _node_ids_by_status(execution, ('pending',))
    running = _node_ids_by_status(execution, ('running', 'retrying'))
    skipped = _node_ids_by_status(execution, ('skipped',))
    never_started = _never_started_node_ids(execution)
    incomplete = list(dict.fromkeys(pending + running + never_started))

    snap = execution.get_context_snapshot() or {}
    has_snapshot = bool(snap.get('visited') is not None or snap.get('node_results'))
    queue = list(snap.get('queue_node_ids') or [])

    strategy = 'none'
    if execution.status == 'running':
        strategy = 'running'
    elif failed:
        strategy = 'retry_failed'
    elif execution.status in ('paused', 'interrupted') and (incomplete or queue or has_snapshot):
        strategy = 'resume'
    elif incomplete:
        strategy = 'continue_incomplete'
    elif execution.status in ('failed', 'timeout', 'cancelled') and has_snapshot:
        strategy = 'resume'
    elif execution.status == 'completed' and not failed and not incomplete:
        strategy = 'done'

    return {
        'execution_id': _sid(execution.id),
        'status': execution.status,
        'strategy': strategy,
        'can_continue': strategy in ('retry_failed', 'resume', 'continue_incomplete'),
        'failed': failed,
        'pending': pending,
        'running': running,
        'skipped': skipped,
        'never_started': never_started,
        'incomplete': incomplete,
        'has_snapshot': has_snapshot,
        'queue_node_ids': queue,
        'hint': {
            'retry_failed': '存在失败节点：从失败点局部补跑（保留成功产物）',
            'resume': '未执行完：从断点继续剩余节点',
            'continue_incomplete': '存在未完成节点：继续跑完以保证成片完整',
            'running': '仍在运行中，请等待或先暂停',
            'done': '已全部完成，无需继续',
            'none': '没有可继续的任务',
        }.get(strategy, ''),
    }


def _rebuild_snapshot_from_node_executions(execution) -> Dict[str, Any]:
    """Fallback when context_snapshot is thin after soft-complete."""
    from workflows.models import NodeExecution

    visited: List[str] = []
    node_results: Dict[str, Any] = {}
    node_outputs: Dict[str, Any] = {}

    for ne in NodeExecution.objects.filter(execution=execution).select_related('node'):
        nid = _sid(ne.node_id)
        if ne.status in ('completed', 'skipped', 'failed'):
            visited.append(nid)
        od = ne.output_data if isinstance(ne.output_data, dict) else {}
        if ne.status == 'completed':
            node_results[nid] = {'success': True, 'output': od}
            node_outputs[nid] = od
        elif ne.status == 'skipped':
            node_results[nid] = {
                'success': True,
                'skipped': True,
                'skipped_reason': ne.error_message or 'skipped',
                'output': od,
            }
        elif ne.status == 'failed':
            node_results[nid] = {
                'success': True,
                'skipped': True,
                'skipped_reason': ne.error_message or 'failed',
                'output': od,
            }

    context_data = {}
    if isinstance(execution.output_data, dict) and execution.output_data:
        context_data = dict(execution.output_data)
    elif isinstance(execution.context_snapshot, dict):
        context_data = dict((execution.context_snapshot or {}).get('context_data') or {})

    if 'input_data' not in context_data:
        context_data['input_data'] = (
            execution.input_data if isinstance(execution.input_data, dict) else {}
        )
    if 'variables' not in context_data:
        context_data['variables'] = {}
    existing_outs = (
        context_data.get('node_outputs')
        if isinstance(context_data.get('node_outputs'), dict)
        else {}
    )
    context_data['node_outputs'] = {**existing_outs, **node_outputs}

    return {
        'visited': visited,
        'node_results': node_results,
        'context_data': context_data,
        'queue_node_ids': [],
        'reason': 'rebuilt_from_node_executions',
        'execution_id': _sid(execution.id),
        'saved_at': timezone.now().isoformat(),
    }


def _apply_invalidate_and_snapshot(
    execution,
    *,
    seeds: List[str],
    invalidate: Set[str],
    reason: str,
) -> Dict[str, Any]:
    snap = execution.get_context_snapshot() or {}
    if not snap.get('visited') and not snap.get('node_results'):
        snap = _rebuild_snapshot_from_node_executions(execution)
    elif not snap.get('node_results'):
        rebuilt = _rebuild_snapshot_from_node_executions(execution)
        snap = {**rebuilt, **{k: v for k, v in snap.items() if v}}

    visited = [v for v in (snap.get('visited') or []) if _sid(v) not in invalidate]
    node_results = {
        _sid(k): v
        for k, v in (snap.get('node_results') or {}).items()
        if _sid(k) not in invalidate
    }

    context_data = dict(snap.get('context_data') or {})
    if not context_data and isinstance(execution.output_data, dict):
        context_data = dict(execution.output_data)
    if 'input_data' not in context_data:
        context_data['input_data'] = (
            execution.input_data if isinstance(execution.input_data, dict) else {}
        )
    outs = context_data.get('node_outputs')
    if isinstance(outs, dict):
        context_data['node_outputs'] = {
            _sid(k): v for k, v in outs.items() if _sid(k) not in invalidate
        }
    else:
        context_data['node_outputs'] = {}

    queue_node_ids = list(dict.fromkeys(seeds))

    new_snap = {
        'visited': visited,
        'node_results': node_results,
        'context_data': context_data,
        'execution_order': [
            x for x in (snap.get('execution_order') or []) if _sid(x) not in invalidate
        ],
        'queue_node_ids': queue_node_ids,
        'queued_ids': queue_node_ids,
        'reason': reason,
        'partial_retry': True,
        'partial_retry_seeds': list(seeds),
        'partial_retry_invalidated': sorted(invalidate),
        'saved_at': timezone.now().isoformat(),
        'execution_id': _sid(execution.id),
    }

    from workflows.models import NodeExecution

    with transaction.atomic():
        for ne in NodeExecution.objects.filter(execution=execution):
            if _sid(ne.node_id) not in invalidate:
                continue
            ne.status = 'pending'
            ne.output_data = {}
            ne.error_message = ''
            ne.started_at = None
            ne.completed_at = None
            ne.duration_ms = None
            ne.retry_count = 0
            ne.max_retries_exceeded = False
            ne.save(update_fields=[
                'status', 'output_data', 'error_message',
                'started_at', 'completed_at', 'duration_ms',
                'retry_count', 'max_retries_exceeded',
            ])

        ns = dict(execution.node_status or {})
        for nid in invalidate:
            ns[nid] = 'pending'
        execution.node_status = ns
        execution.context_snapshot = new_snap
        execution.status = 'interrupted'
        execution.error_message = None
        execution.error_stack = None
        execution.completed_at = None
        execution.duration_ms = None
        total = max(execution.workflow.nodes.count() or 1, 1)
        execution.executed_nodes = len(visited)
        execution.progress = min(99, int(100 * len(visited) / total))
        execution.save(update_fields=[
            'node_status', 'context_snapshot', 'status', 'error_message', 'error_stack',
            'completed_at', 'duration_ms', 'executed_nodes', 'progress',
        ])

    return {
        'execution_id': _sid(execution.id),
        'seeds': seeds,
        'invalidated': sorted(invalidate),
        'kept_visited': len(visited),
        'status': execution.status,
        'reason': reason,
    }


def prepare_partial_retry(
    execution,
    *,
    node_ids: Optional[List[str]] = None,
    include_downstream: bool = True,
) -> Dict[str, Any]:
    """Re-run failed (or selected) nodes + optional downstream; keep successes."""
    if execution.status not in RETRYABLE_STATUSES:
        raise ValueError(
            f'当前状态 {execution.status} 不可局部重试；需为已完成/失败/中断等终态或可恢复态'
        )
    if execution.status == 'running':
        raise ValueError('执行仍在运行中，请等待结束或先暂停后再局部重试')

    seeds = [_sid(x) for x in (node_ids or []) if x]
    if not seeds:
        seeds = _failed_node_ids(execution)
    if not seeds:
        raise ValueError('没有失败节点可局部重试')

    adj = _build_adjacency(execution.workflow)
    invalidate: Set[str] = set(seeds)
    if include_downstream:
        invalidate = _collect_descendants(seeds, adj)

    result = _apply_invalidate_and_snapshot(
        execution,
        seeds=seeds,
        invalidate=invalidate,
        reason='partial_retry',
    )
    result['include_downstream'] = include_downstream
    logger.info(
        'Prepared partial retry for execution %s: seeds=%s invalidated=%s',
        execution.id, seeds, len(invalidate),
    )
    return result


def prepare_continue_incomplete(
    execution,
    *,
    include_failed_downstream: bool = True,
) -> Dict[str, Any]:
    """Continue unfinished nodes (pending / never-started / stuck running / failed)."""
    if execution.status not in CONTINUE_STATUSES:
        raise ValueError(
            f'当前状态 {execution.status} 不可继续；需为中断/暂停/失败/已完成(有缺口)等'
        )
    if execution.status == 'running':
        raise ValueError('执行仍在运行中，请等待结束或先暂停后再继续')

    analysis = analyze_continue(execution)
    failed = analysis['failed']
    incomplete = analysis['incomplete']
    seeds = list(dict.fromkeys(failed + incomplete))
    if not seeds:
        queue = analysis.get('queue_node_ids') or []
        if queue:
            seeds = [_sid(x) for x in queue]
        else:
            raise ValueError('没有未完成或失败的节点可继续')

    adj = _build_adjacency(execution.workflow)
    invalidate: Set[str] = set(seeds)
    if include_failed_downstream and failed:
        invalidate |= _collect_descendants(failed, adj)
    invalidate |= set(incomplete)

    result = _apply_invalidate_and_snapshot(
        execution,
        seeds=seeds,
        invalidate=invalidate,
        reason='continue_incomplete',
    )
    result['strategy'] = 'continue_incomplete'
    result['analysis'] = analysis
    logger.info(
        'Prepared continue-incomplete for execution %s: seeds=%s invalidated=%s',
        execution.id, seeds, len(invalidate),
    )
    return result


def prepare_continue(
    execution,
    *,
    mode: str = 'auto',
    node_ids: Optional[List[str]] = None,
    include_downstream: bool = True,
    force: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """
    Unified continue entry.

    Returns (strategy, payload). strategy is one of:
      resume | retry_failed | continue_incomplete
    """
    mode = (mode or 'auto').strip().lower()
    analysis = analyze_continue(execution)

    if execution.status == 'running' and not force:
        raise ValueError('执行仍在运行中。请等待结束，或先暂停后再点「继续执行」。')

    if force and execution.status == 'running':
        execution.status = 'interrupted'
        execution.save(update_fields=['status'])
        analysis = analyze_continue(execution)

    if node_ids:
        prepared = prepare_partial_retry(
            execution, node_ids=node_ids, include_downstream=include_downstream
        )
        prepared['strategy'] = 'retry_failed'
        prepared['analysis'] = analysis
        return 'retry_failed', prepared

    if mode in ('failed', 'failed_only', 'retry_failed'):
        prepared = prepare_partial_retry(
            execution, include_downstream=include_downstream
        )
        prepared['strategy'] = 'retry_failed'
        prepared['analysis'] = analysis
        return 'retry_failed', prepared

    if mode in ('resume', 'checkpoint'):
        if not analysis.get('has_snapshot') and not analysis.get('incomplete'):
            raise ValueError('没有可用断点，无法从断点继续')
        if not analysis.get('has_snapshot'):
            prepared = prepare_continue_incomplete(
                execution, include_failed_downstream=include_downstream
            )
            return 'continue_incomplete', prepared
        if execution.status not in ('paused', 'interrupted'):
            execution.status = 'interrupted'
            execution.save(update_fields=['status'])
        return 'resume', {
            'execution_id': _sid(execution.id),
            'strategy': 'resume',
            'status': execution.status,
            'analysis': analysis,
            'message': '将从断点继续未完成节点',
        }

    if mode in ('incomplete', 'continue_incomplete', 'unfinished'):
        prepared = prepare_continue_incomplete(
            execution, include_failed_downstream=include_downstream
        )
        return 'continue_incomplete', prepared

    strategy = analysis['strategy']
    if strategy == 'done':
        raise ValueError('执行已完整完成，无需继续')
    if strategy == 'none':
        raise ValueError('没有可继续的任务')
    if strategy == 'retry_failed':
        prepared = prepare_partial_retry(
            execution, include_downstream=include_downstream
        )
        prepared['strategy'] = 'retry_failed'
        prepared['analysis'] = analysis
        return 'retry_failed', prepared
    if strategy == 'continue_incomplete':
        prepared = prepare_continue_incomplete(
            execution, include_failed_downstream=include_downstream
        )
        return 'continue_incomplete', prepared
    if strategy == 'resume':
        if analysis['failed']:
            prepared = prepare_partial_retry(
                execution, include_downstream=include_downstream
            )
            prepared['strategy'] = 'retry_failed'
            prepared['analysis'] = analysis
            return 'retry_failed', prepared
        if analysis['incomplete']:
            prepared = prepare_continue_incomplete(
                execution, include_failed_downstream=include_downstream
            )
            return 'continue_incomplete', prepared
        if execution.status not in ('paused', 'interrupted'):
            execution.status = 'interrupted'
            execution.save(update_fields=['status'])
        return 'resume', {
            'execution_id': _sid(execution.id),
            'strategy': 'resume',
            'status': execution.status,
            'analysis': analysis,
            'message': '将从断点继续未完成节点',
        }

    raise ValueError(f'无法继续：strategy={strategy}')
