"""Exercise real Celery task entry points without a broker or external nodes."""
from unittest.mock import Mock, patch

import pytest
from celery.exceptions import Retry
from django.test import override_settings

from workflows.models import WorkflowExecution
from workflows.tasks import execute_workflow_task


@pytest.fixture
def execution(workflow):
    return WorkflowExecution.objects.create(workflow=workflow, version=workflow.version, status='pending')


def invoke(task, *args, retries=0):
    task.push_request(id='reliability-task', retries=retries)
    try:
        return task.run(*args)
    finally:
        task.pop_request()


@pytest.mark.django_db
@override_settings(WORKFLOW_MAX_CONCURRENT_PER_WORKFLOW=1)
def test_concurrency_retry_stays_queued_and_is_not_handled_as_failure(execution):
    WorkflowExecution.objects.create(workflow=execution.workflow, version=execution.version, status='running')
    with patch.object(execute_workflow_task, 'retry', side_effect=Retry('capacity')) as retry:
        with pytest.raises(Retry):
            invoke(execute_workflow_task, str(execution.pk))
    execution.refresh_from_db()
    assert execution.status == 'queued'
    assert execution.completed_at is None
    retry.assert_called_once()


@pytest.mark.django_db
def test_transient_start_failure_can_really_run_on_redelivery(execution):
    def finish(*args, **kwargs):
        WorkflowExecution.objects.filter(pk=execution.pk).update(status='completed')

    successful_executor = Mock()
    successful_executor.execute.side_effect = finish
    with patch('workflows.tasks.WorkflowExecutor', side_effect=[ConnectionError('temporary'), successful_executor]), \
            patch.object(execute_workflow_task, 'retry', side_effect=Retry('retry')) as retry:
        with pytest.raises(Retry):
            invoke(execute_workflow_task, str(execution.pk))
        execution.refresh_from_db()
        assert execution.status == 'queued'
        assert execution.completed_at is None
        result = invoke(execute_workflow_task, str(execution.pk), retries=1)
    retry.assert_called_once()
    assert result['status'] == 'completed'
    successful_executor.execute.assert_called_once_with(resume=False)


@pytest.mark.django_db
def test_retry_budget_exhaustion_is_a_terminal_failure(execution):
    with patch('workflows.tasks.WorkflowExecutor', side_effect=ConnectionError('unavailable')), \
            patch.object(execute_workflow_task, 'retry') as retry:
        result = invoke(execute_workflow_task, str(execution.pk), retries=execute_workflow_task.max_retries)
    execution.refresh_from_db()
    assert execution.status == 'failed'
    assert execution.completed_at is not None
    assert 'unavailable' in result['exception']
    retry.assert_not_called()


@pytest.mark.django_db
def test_cancelled_execution_is_not_replayed(execution):
    execution.cancel()
    with patch('workflows.tasks.WorkflowExecutor') as executor:
        result = invoke(execute_workflow_task, str(execution.pk))
    assert result['status'] == 'cancelled'
    executor.assert_not_called()


@pytest.mark.django_db
def test_retry_with_checkpoint_preserves_snapshot(execution):
    snapshot = {'visited': ['node-a'], 'node_results': {'node-a': {'success': True}}}
    execution.context_snapshot = snapshot
    execution.save(update_fields=['context_snapshot'])
    with patch('workflows.tasks.WorkflowExecutor', side_effect=ConnectionError('temporary')), \
            patch.object(execute_workflow_task, 'retry', side_effect=Retry('retry')):
        with pytest.raises(Retry):
            invoke(execute_workflow_task, str(execution.pk))
    execution.refresh_from_db()
    assert execution.status == 'interrupted'
    assert execution.context_snapshot == snapshot
    assert execution.completed_at is None


@pytest.mark.django_db
@override_settings(WORKFLOW_MAX_CONCURRENT_PER_WORKFLOW=1)
def test_waiting_queue_does_not_consume_worker_capacity(execution):
    WorkflowExecution.objects.create(workflow=execution.workflow, version=execution.version, status='queued')
    executor = Mock()
    executor.execute.side_effect = lambda **kw: WorkflowExecution.objects.filter(pk=execution.pk).update(status='completed')
    with patch('workflows.tasks.WorkflowExecutor', return_value=executor), \
            patch.object(execute_workflow_task, 'retry', side_effect=Retry('must not retry')):
        result = invoke(execute_workflow_task, str(execution.pk))
    assert result['status'] == 'completed'


@pytest.mark.django_db
def test_failure_without_checkpoint_does_not_repeat_completed_external_node(execution):
    from workflows.models import Node, NodeExecution

    node = Node.objects.create(workflow=execution.workflow, node_type='email', name='already sent')
    NodeExecution.objects.create(execution=execution, node=node, node_version=node.version, status='completed')
    with patch('workflows.tasks.WorkflowExecutor', side_effect=ConnectionError('after email')), \
            patch.object(execute_workflow_task, 'retry') as retry:
        invoke(execute_workflow_task, str(execution.pk))
    execution.refresh_from_db()
    assert execution.status == 'failed'
    retry.assert_not_called()
