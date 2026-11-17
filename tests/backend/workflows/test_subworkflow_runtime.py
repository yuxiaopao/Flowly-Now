"""Real nested executions; queue transport failures alone use a boundary mock."""
from unittest.mock import patch
from unittest.mock import MagicMock
from types import SimpleNamespace
from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from users.models import User
from workflows.models import Workflow, Node, Edge, WorkflowExecution
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.subworkflow import configuration, SubworkflowError
from applications.models import ApplicationRelease, ApplicationRequest

pytestmark = pytest.mark.django_db


def graph(owner, name='Child', middle=None):
    workflow = Workflow.objects.create(owner=owner, name=name)
    previous = None
    middle = middle if middle is not None else [('input', {'variable_name': 'input'}), ('output', {'template': 'child:{input}'})]
    for kind, config in [('start', {}), *middle, ('end', {})]:
        node = Node.objects.create(workflow=workflow, name=kind, node_type=kind, config=config)
        if previous:
            Edge.objects.create(workflow=workflow, source_node=previous, target_node=node)
        previous = node
    return workflow


def parent(user, child, **kwargs):
    config = {'subworkflowId': str(child.pk), 'version': 'latest', **kwargs}
    return graph(user, 'Parent', [('subworkflow', config)])


def run(workflow, user, inputs=None, source=None):
    execution = WorkflowExecution.objects.create(workflow=workflow, triggered_by=user, input_data=inputs or {'input': 'hello'},
        version=workflow.version, status='pending', trigger_source=source or {})
    WorkflowExecutor(workflow, execution).execute()
    execution.refresh_from_db()
    return execution


def test_sync_child_input_output_mapping_and_real_trace(user):
    child = graph(user)
    outer = parent(user, child, inputMapping=[{'parentVar': 'customer.Name', 'childParam': 'input'}],
        outputMapping=[{'childOutput': 'result', 'parentVar': 'answer_KeepCase'}])
    execution = run(outer, user, {'customer': {'Name': 'Mapped'}})
    assert execution.status == 'completed', execution.error_message
    assert execution.output_data['variables']['answer_KeepCase'] == 'child:Mapped'
    actual = WorkflowExecution.objects.get(workflow=child)
    assert actual.input_data == {'input': 'Mapped'} and actual.status == 'completed'
    assert actual.trigger_source['parent_execution_id'] == str(execution.pk)
    assert actual.node_executions.count() == 4
    assert actual.output_data['mapped_output'] == {'answer_KeepCase': 'child:Mapped'}


@pytest.mark.parametrize('policy,status', [('stop', 'failed'), ('skip', 'completed'), ('fallback', 'completed')])
def test_child_failure_policy_preserves_failed_child_truth(user, policy, status):
    child = graph(user)
    outer = parent(user, child, onError=policy, fallbackValue='{"answer":"fallback-value"}')
    execution = run(outer, user, {'unrelated': 'missing required input'})
    assert execution.status == status
    actual = WorkflowExecution.objects.get(workflow=child)
    assert actual.status == 'failed'
    if policy == 'fallback':
        assert execution.output_data['variables']['answer'] == 'fallback-value'


def test_foreign_child_and_hidden_snapshot_ids_never_execute(user):
    foreign = User.objects.create_user(username='subworkflow-foreign')
    child = graph(foreign)
    execution = run(parent(user, child), user)
    assert execution.status == 'failed'
    assert not WorkflowExecution.objects.filter(workflow=child).exists()
    Workflow.all_objects.filter(pk=child.pk).update(is_release_snapshot=True)
    execution = run(parent(user, child), user)
    assert execution.status == 'failed' and not WorkflowExecution.objects.filter(workflow=child).exists()


def test_actual_current_version_only_and_no_fabricated_history(user):
    child = graph(user)
    child.version = 4
    child.save()
    assert run(parent(user, child, version=4), user).status == 'completed'
    assert run(parent(user, child, version=3), user).status == 'failed'
    assert WorkflowExecution.objects.filter(workflow=child).count() == 1


def test_recursive_cycle_and_maximum_depth_are_bounded(user):
    child = graph(user)
    outer = parent(user, child)
    child.nodes.filter(node_type='input').update(node_type='subworkflow', config={'subworkflowId': str(outer.pk)})
    execution = run(outer, user)
    assert execution.status == 'failed'
    assert WorkflowExecution.objects.count() <= 2
    with override_settings(WORKFLOW_MAX_SUBWORKFLOW_DEPTH=1):
        assert run(outer, user).status == 'failed'


def test_child_timeout_and_parent_cancel_are_terminal(user):
    child = graph(user, middle=[('delay', {'seconds': 2})])
    execution = run(parent(user, child, timeout=0.1), user)
    assert execution.status == 'failed'
    nested = WorkflowExecution.objects.get(workflow=child)
    assert nested.status == 'timeout'
    outer = WorkflowExecution.objects.create(workflow=child, triggered_by=user, version=1, status='cancelled')
    nested = run(child, user, source={'parent_execution_id': str(outer.pk), 'deadline_at': (timezone.now() + timedelta(seconds=10)).isoformat()})
    assert nested.status == 'cancelled' and not nested.node_executions.filter(status='completed').exists()


def test_async_runs_real_celery_eager_task_and_keeps_mapped_result(user):
    child = graph(user)
    execution = run(parent(user, child, executionMode='async', outputMapping=[{'childOutput': 'result', 'parentVar': 'answer'}]), user)
    assert execution.status == 'completed', execution.error_message
    nested = WorkflowExecution.objects.get(workflow=child)
    assert nested.status == 'completed' and nested.task_id
    assert nested.output_data['mapped_output'] == {'answer': 'child:hello'}
    assert execution.output_data['variables']['child_execution_id'] == str(nested.pk)
    assert 'answer' not in execution.output_data['variables']


def test_async_queue_failure_marks_child_failed_without_orphan(user):
    child = graph(user)
    with patch('workflows.tasks.execute_workflow_task.delay', side_effect=RuntimeError('isolated unavailable queue')):
        execution = run(parent(user, child, executionMode='async'), user)
    assert execution.status == 'failed'
    nested = WorkflowExecution.objects.get(workflow=child)
    assert nested.status == 'failed' and not nested.task_id


@pytest.mark.parametrize('config', [
    {'subworkflowId': 'invalid'}, {'version': 0}, {'executionMode': 'invented'}, {'onError': 'invented'},
    {'timeout': -1}, {'inputMapping': [{'parentVar': 'x', 'childParam': ''}]},
    {'outputMapping': [{'childOutput': 'result', 'parentVar': '_internal'}]}, {'onError': 'fallback', 'fallbackValue': 'not json'},
])
def test_invalid_child_configuration_rejected(user, config):
    child = graph(user)
    with pytest.raises(SubworkflowError):
        configuration({'subworkflowId': str(child.pk), **config})


def test_application_recursively_freezes_child_and_detects_source_changes(user):
    child = graph(user)
    outer = parent(user, child)
    client = APIClient()
    client.force_authenticate(user)
    response = client.post('/api/v1/applications/', {'name': 'Nested app', 'kind': 'workflow', 'draft': {'workflow_id': str(outer.pk)}}, format='json')
    assert response.status_code == 201, response.content
    app_id = response.json()['data']['id']
    base = f'/api/v1/applications/{app_id}/'
    assert client.post(base + 'test/', {'input_data': {'input': 'test'}}, format='json').status_code == 200
    response = client.post(base + 'publish/', {}, format='json')
    assert response.status_code == 201, response.content
    release = ApplicationRelease.objects.get(pk=response.json()['data']['id'])
    assert len(release.workflow_manifest) == 2
    child.nodes.filter(node_type='output').update(config={'template': 'changed:{input}'})
    detail = client.get(base).json()['data']
    assert detail['tested_fingerprint'] != detail['draft_fingerprint']
    assert client.post(base + 'publish/', {}, format='json').status_code == 409
    result = client.post(base + 'invoke/', {'input_data': {'input': 'published'}}, format='json')
    assert result.status_code == 200, result.content
    assert result.json()['data']['output_data']['variables']['result'] == 'child:published'
    request = ApplicationRequest.objects.get(pk=result.json()['data']['id'])
    assert request.workflow_manifest == release.workflow_manifest
    assert request.workflow_execution.workflow_id == release.workflow_snapshot_id


def test_manifest_tampering_and_cycles_fail_closed_before_publication(user):
    child = graph(user)
    outer = parent(user, child)
    client = APIClient()
    client.force_authenticate(user)
    response = client.post('/api/v1/applications/', {'name': 'Nested app', 'kind': 'workflow', 'draft': {'workflow_id': str(outer.pk)}}, format='json')
    app_id = response.json()['data']['id']
    base = f'/api/v1/applications/{app_id}/'
    assert client.post(base + 'test/', {'input_data': {'input': 'x'}}, format='json').status_code == 200
    release_id = client.post(base + 'publish/', {}, format='json').json()['data']['id']
    release = ApplicationRelease.objects.get(pk=release_id)
    child_snapshot_id = release.workflow_manifest[str(release.workflow_snapshot_id)]['children'][0]
    Node.objects.filter(workflow_id=child_snapshot_id, node_type='output').update(config={'template': 'tampered'})
    assert client.post(base + 'invoke/', {'input_data': {'input': 'x'}}, format='json').status_code == 503
    child.nodes.filter(node_type='input').update(node_type='subworkflow', config={'subworkflowId': str(outer.pk)})
    assert client.post(base + 'publish/', {}, format='json').status_code == 409


def test_executor_ignores_non_object_legacy_source_but_rejects_bad_deadline():
    workflow = MagicMock()
    execution = MagicMock()
    executor = WorkflowExecutor(workflow, execution)
    assert executor.deadline_at is None and executor._trigger_source == {}
    execution.trigger_source = {'deadline_at': 42}
    with pytest.raises(ValueError, match='deadline_at'):
        WorkflowExecutor(workflow, execution)


def test_pending_async_application_test_cannot_publish_until_real_child_finishes(user):
    child = graph(user)
    outer = parent(user, child, executionMode='async')
    client = APIClient()
    client.force_authenticate(user)
    response = client.post('/api/v1/applications/', {'name': 'Async app', 'kind': 'workflow', 'draft': {'workflow_id': str(outer.pk)}}, format='json')
    base = '/api/v1/applications/' + response.json()['data']['id'] + '/'
    with patch('workflows.tasks.execute_workflow_task.delay', return_value=SimpleNamespace(id='isolated-pending-task')):
        response = client.post(base + 'test/', {'input_data': {'input': 'async'}}, format='json')
    assert response.status_code == 202, response.content
    request_id = response.json()['data']['id']
    assert response.json()['data']['status'] == 'running'
    assert client.post(base + 'publish/', {}, format='json').status_code == 409
    nested = WorkflowExecution.objects.get(trigger_source__application_request_id=request_id, trigger_source__subworkflow_mode='async')
    from workflows.tasks import execute_workflow_task
    execute_workflow_task.run(str(nested.pk))
    polled = client.get(base + f'requests/{request_id}/').json()['data']
    assert polled['status'] == 'completed'
    assert client.post(base + 'publish/', {}, format='json').status_code == 201


def test_queued_application_child_rechecks_revoked_key_before_real_task(user):
    child = graph(user)
    outer = parent(user, child, executionMode='async')
    client = APIClient()
    client.force_authenticate(user)
    response = client.post('/api/v1/applications/', {'name': 'Async app', 'kind': 'workflow', 'draft': {'workflow_id': str(outer.pk)}}, format='json')
    base = '/api/v1/applications/' + response.json()['data']['id'] + '/'
    assert client.post(base + 'test/', {'input_data': {'input': 'test'}}, format='json').status_code == 200
    assert client.post(base + 'publish/', {}, format='json').status_code == 201
    key = client.post(base + 'api-keys/', {'name': 'revoke test'}, format='json').json()['data']
    caller = APIClient()
    caller.credentials(HTTP_AUTHORIZATION='Bearer ' + key['api_key'])
    with patch('workflows.tasks.execute_workflow_task.delay', return_value=SimpleNamespace(id='isolated-pending-task')):
        response = caller.post(base + 'invoke/', {'input_data': {'input': 'do not run after revocation'}}, format='json')
    assert response.status_code == 200, response.content
    nested = WorkflowExecution.objects.get(trigger_source__application_request_id=response.json()['data']['id'], trigger_source__subworkflow_mode='async')
    assert client.post(base + f'api-keys/{key["id"]}/revoke/', {}, format='json').status_code == 200
    from workflows.tasks import execute_workflow_task
    execute_workflow_task.run(str(nested.pk))
    nested.refresh_from_db()
    assert nested.status == 'cancelled'
    assert not nested.node_executions.filter(status='completed').exists()


def test_finalization_cannot_overwrite_cancel_committed_before_final_update(user):
    from django.db import connection
    workflow = graph(user, middle=[])
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user)
    executor = WorkflowExecutor(workflow, execution)
    injected = False
    table = connection.ops.quote_name(WorkflowExecution._meta.db_table)

    def competing_cancel(execute, sql, params, many, context):
        nonlocal injected
        if not injected and sql.lstrip().upper().startswith('UPDATE ' + table.upper()) and 'completed' in (params or []):
            injected = True
            WorkflowExecution.objects.filter(pk=execution.pk).update(status='cancelled')
        return execute(sql, params, many, context)

    with connection.execute_wrapper(competing_cancel):
        executor.execute()
    execution.refresh_from_db()
    assert injected and execution.status == 'cancelled'
