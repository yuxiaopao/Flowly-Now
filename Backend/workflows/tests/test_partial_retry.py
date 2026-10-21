"""Tests for partial retry / continue of failed & unfinished nodes."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def test_collect_descendants_bfs():
    from workflows.services.partial_retry import _collect_descendants

    adj = {
        'a': ['b'],
        'b': ['c', 'd'],
        'c': ['e'],
        'd': [],
        'e': [],
        'x': ['y'],
    }
    got = _collect_descendants(['a'], adj)
    assert got == {'a', 'b', 'c', 'd', 'e'}
    assert 'y' not in got


def test_analyze_continue_prefers_failed():
    from workflows.services.partial_retry import analyze_continue

    execution = MagicMock()
    execution.id = 'exec1'
    execution.status = 'completed'
    execution.get_context_snapshot.return_value = {
        'visited': ['ok1', 'fail1'],
        'node_results': {},
    }

    with patch('workflows.services.partial_retry._failed_node_ids', return_value=['fail1']), \
         patch('workflows.services.partial_retry._node_ids_by_status', return_value=[]), \
         patch('workflows.services.partial_retry._never_started_node_ids', return_value=['later']):
        info = analyze_continue(execution)
    assert info['strategy'] == 'retry_failed'
    assert info['can_continue'] is True
    assert 'fail1' in info['failed']


def test_prepare_partial_retry_keeps_successes():
    from workflows.services.partial_retry import prepare_partial_retry

    workflow = SimpleNamespace(id='wf1', nodes=MagicMock(count=MagicMock(return_value=5)))
    execution = MagicMock()
    execution.id = 'exec1'
    execution.status = 'completed'
    execution.workflow = workflow
    execution.input_data = {'chapters': 'demo'}
    execution.output_data = {
        'input_data': {'chapters': 'demo'},
        'variables': {},
        'node_outputs': {
            'ok1': {'video_url': 'http://ok'},
            'fail1': {},
            'down1': {'video_url': 'http://partial'},
        },
    }
    execution.node_status = {'ok1': 'completed', 'fail1': 'failed', 'down1': 'completed'}
    execution.get_context_snapshot.return_value = {
        'visited': ['ok1', 'fail1', 'down1'],
        'node_results': {
            'ok1': {'success': True, 'output': {'video_url': 'http://ok'}},
            'fail1': {'success': True, 'skipped': True, 'skipped_reason': 'boom'},
            'down1': {'success': True, 'output': {'video_url': 'http://partial'}},
        },
        'context_data': execution.output_data,
    }

    failed_ne = SimpleNamespace(node_id='fail1')
    down_ne = SimpleNamespace(
        node_id='down1', status='completed', output_data={'video_url': 'http://partial'},
        error_message='', started_at=None, completed_at=None, duration_ms=0,
        retry_count=0, max_retries_exceeded=False,
        save=MagicMock(),
    )
    fail_row = SimpleNamespace(
        node_id='fail1', status='failed', output_data={},
        error_message='boom', started_at=None, completed_at=None, duration_ms=0,
        retry_count=0, max_retries_exceeded=False,
        save=MagicMock(),
    )

    with patch('workflows.services.partial_retry._build_adjacency', return_value={'fail1': ['down1'], 'ok1': []}), \
         patch('workflows.models.NodeExecution.objects') as neo, \
         patch('django.db.transaction.atomic') as atomic:
        atomic.return_value.__enter__ = lambda s: None
        atomic.return_value.__exit__ = lambda *a: None

        failed_qs = MagicMock()
        failed_qs.only.return_value = [failed_ne]
        failed_qs.__iter__ = lambda self: iter([failed_ne])

        def filter_side(**kwargs):
            if kwargs.get('status') == 'failed':
                return failed_qs
            return [fail_row, down_ne]

        neo.filter.side_effect = filter_side

        result = prepare_partial_retry(execution, include_downstream=True)

    assert result['seeds'] == ['fail1']
    assert set(result['invalidated']) == {'fail1', 'down1'}
    snap = execution.context_snapshot
    assert 'ok1' in snap['visited']
    assert 'fail1' not in snap['visited']
    assert execution.status == 'interrupted'
    fail_row.save.assert_called()
    down_ne.save.assert_called()
