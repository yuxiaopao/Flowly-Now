"""Real InnoDB row-lock regressions; invoked explicitly by the CI MySQL profile."""
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import connection, connections
from django.test import override_settings
from rest_framework.test import APIClient
from applications.models import Application, ApplicationRelease, ApplicationRequest
from users.models import User
from workflows.models import Workflow, Node, Edge, WorkflowExecution

pytestmark = pytest.mark.django_db(transaction=True)


def authenticated(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def nested_application(user):
    assert connection.vendor == 'mysql', 'Run this suite with --ds=config.mysql_test_settings against isolated MySQL.'
    child = Workflow.objects.create(owner=user, name='Concurrent child')
    previous = None
    for kind, config in [('start', {}), ('delay', {'seconds': 0.5}), ('end', {})]:
        node = Node.objects.create(workflow=child, node_type=kind, name=kind, config=config)
        if previous:
            Edge.objects.create(workflow=child, source_node=previous, target_node=node)
        previous = node
    root = Workflow.objects.create(owner=user, name='Concurrent parent')
    previous = None
    for kind, config in [('start', {}), ('subworkflow', {'subworkflowId': str(child.pk)}), ('end', {})]:
        node = Node.objects.create(workflow=root, node_type=kind, name=kind, config=config)
        if previous:
            Edge.objects.create(workflow=root, source_node=previous, target_node=node)
        previous = node
    response = authenticated(user).post('/api/v1/applications/', {'name': 'Concurrent app', 'kind': 'workflow',
        'draft': {'workflow_id': str(root.pk)}}, format='json')
    assert response.status_code == 201, response.content
    return response.json()['data']['id']


def concurrent_posts(user_id, url, *, payload=None, idempotency_key=None):
    barrier = Barrier(2)
    def invoke():
        try:
            user = User.objects.get(pk=user_id)
            client = authenticated(user)
            barrier.wait(timeout=10)
            headers = {'HTTP_IDEMPOTENCY_KEY': idempotency_key} if idempotency_key else {}
            response = client.post(url, payload or {}, format='json', **headers)
            return response.status_code, response.json()['data']
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = [executor.submit(invoke) for _ in range(2)]
        return [future.result(timeout=30) for future in pending]


def test_real_mysql_admission_allows_only_one_nested_request(user, nested_application):
    with override_settings(APPLICATION_MAX_CONCURRENT=1):
        results = concurrent_posts(user.pk, f'/api/v1/applications/{nested_application}/test/', payload={'input_data': {}})
    assert sorted(status for status, _ in results) == [200, 429]
    assert ApplicationRequest.objects.filter(application_id=nested_application, status='completed').count() == 1
    assert ApplicationRequest.objects.filter(application_id=nested_application, error_code='concurrency_limit').count() == 1
    assert WorkflowExecution.objects.count() == 2  # Exactly one root and one real nested execution.


def test_real_mysql_idempotent_parallel_retry_never_starts_a_second_child(user, nested_application):
    results = concurrent_posts(user.pk, f'/api/v1/applications/{nested_application}/test/',
        payload={'input_data': {}}, idempotency_key='real-inno-db-parallel-retry')
    assert sorted(status for status, _ in results) == [200, 202]
    assert len({record['id'] for _, record in results}) == 1
    assert ApplicationRequest.objects.filter(application_id=nested_application).count() == 1
    assert WorkflowExecution.objects.count() == 2


def test_real_mysql_parallel_publication_has_unique_monotonic_versions(user, nested_application):
    url = f'/api/v1/applications/{nested_application}/'
    assert authenticated(user).post(url + 'test/', {'input_data': {}}, format='json').status_code == 200
    results = concurrent_posts(user.pk, url + 'publish/')
    assert [status for status, _ in results] == [201, 201]
    assert sorted(release['version'] for _, release in results) == [1, 2]
    application = Application.objects.get(pk=nested_application)
    assert application.active_release.version == 2
    assert ApplicationRelease.objects.filter(application=application).values('validated_by_request_id').distinct().count() == 1


def test_real_mysql_parent_cancellation_during_child_cannot_finish_completed(user, nested_application):
    url = f'/api/v1/applications/{nested_application}/test/'
    def execute():
        try:
            return authenticated(User.objects.get(pk=user.pk)).post(url, {'input_data': {}}, format='json').status_code
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(execute)
        child = None
        until = time.monotonic() + 10
        while time.monotonic() < until:
            child = WorkflowExecution.objects.filter(trigger_source__parent_execution_id__isnull=False, status='running').first()
            if child and child.node_executions.filter(node__node_type='delay', status='running').exists():
                break
            time.sleep(0.01)
        assert child is not None and child.status == 'running'
        parent_id = child.trigger_source['parent_execution_id']
        WorkflowExecution.objects.filter(pk=parent_id).update(status='cancelled')
        assert pending.result(timeout=15) == 503
    child.refresh_from_db()
    assert child.status == 'cancelled'
    assert WorkflowExecution.objects.get(pk=parent_id).status == 'cancelled'
    assert ApplicationRequest.objects.get(application_id=nested_application).status == 'failed'
