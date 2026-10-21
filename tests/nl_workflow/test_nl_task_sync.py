# -*- coding: utf-8 -*-
"""Quick unit checks for NL task reconcile helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from nl_to_workflow.task_sync import reconcile_session_with_celery


class TestReconcileSession:
    def test_noop_without_task_id(self):
        session = SimpleNamespace(
            celery_task_id='',
            status='processing',
            workflow_json={},
            messages=[],
        )
        info = reconcile_session_with_celery(session)
        assert info['recovered'] is False

    def test_sync_success_payload(self):
        session = SimpleNamespace(
            id='s1',
            name='demo',
            celery_task_id='task-1',
            status='processing',
            workflow_json={},
            workflow_name='',
            workflow=None,
            messages=[],
            error_message='',
            save=MagicMock(),
            refresh_from_db=MagicMock(),
        )
        fake_result = MagicMock()
        fake_result.state = 'SUCCESS'
        fake_result.result = {
            'status': 'completed',
            'workflow_name': 'QA Bot',
            'workflow_json': {
                'name': 'QA Bot',
                'nodes': [{'id': '1', 'type': 'start'}],
                'edges': [],
            },
        }
        with patch('celery.result.AsyncResult', return_value=fake_result):
            info = reconcile_session_with_celery(session)
        assert info['recovered'] is True
        assert session.status == 'completed'
        assert session.workflow_json['name'] == 'QA Bot'
        session.save.assert_called()
