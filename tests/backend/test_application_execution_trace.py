"""Application-scoped traces expose actual snapshot state without opening its APIs."""
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.db import close_old_connections
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework.test import APIClient

from applications.models import ApplicationAPIKey, ApplicationRequest
from tenants.models import Tenant, TenantMembership
from users.models import User
from workflows.models import Workflow, Node, Edge, WorkflowExecution

pytestmark = pytest.mark.django_db(transaction=True)
BASE = '/api/v1/applications/'


def body(response, expected=200):
    assert response.status_code == expected, response.content.decode()
    return response.json()['data']


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def create_app(user, client, *, tenant=None, node_type='text_template', configuration=None):
    graph = Workflow.objects.create(owner=user, tenant=tenant, name='Application trace source')
    first = Node.objects.create(workflow=graph, name='Start', node_type='start')
    middle = Node.objects.create(workflow=graph, name='Actual middle', node_type=node_type,
        config=configuration or {'template': 'Hello {{Customer_ID}}'})
    final = Node.objects.create(workflow=graph, name='End', node_type='end')
    Edge.objects.create(workflow=graph, source_node=first, target_node=middle)
    Edge.objects.create(workflow=graph, source_node=middle, target_node=final)
    values = {'name': 'Trace app', 'kind': 'workflow', 'draft': {'workflow_id': str(graph.pk)}}
    if tenant:
        values['tenant_id'] = tenant.pk
    application = body(client.post(BASE, values, format='json'), 201)
    return application, graph, (first, middle, final)


def trace_url(application, record):
    return f'{BASE}{application["id"]}/requests/{record.pk}/execution/'


@pytest.fixture
def completed(user, authenticated_client):
    app, graph, nodes = create_app(user, authenticated_client)
    result = body(authenticated_client.post(f'{BASE}{app["id"]}/test/',
        {'input_data': {'Customer_ID': 'FORBIDDEN_BUSINESS_INPUT'}}, format='json'))
    record = ApplicationRequest.objects.get(pk=result['id'])
    return app, graph, nodes, record


def assert_summary_fields(summary):
    assert set(summary) == {'id', 'status', 'started_at', 'completed_at', 'nodes'}
    for row in summary['nodes']:
        assert set(row) == {'node_id', 'node_name', 'node_type', 'status', 'started_at', 'completed_at', 'error_message'}


def test_completed_trace_maps_source_nodes_and_keeps_snapshot_apis_hidden(authenticated_client, completed):
    app, graph, nodes, record = completed
    summary = body(authenticated_client.get(trace_url(app, record)))
    assert_summary_fields(summary)
    assert summary['id'] == str(record.workflow_execution_id) and summary['status'] == 'completed'
    assert summary['started_at'] and summary['completed_at']
    assert [row['node_id'] for row in summary['nodes']] == [str(node.pk) for node in nodes]
    assert [row['node_type'] for row in summary['nodes']] == ['start', 'text_template', 'end']
    actual_nodes = list(record.workflow_execution.node_executions.order_by('created_at', 'id'))
    for row, actual in zip(summary['nodes'], actual_nodes):
        assert row['status'] == actual.status == 'completed'
        assert (parse_datetime(row['started_at']) if row['started_at'] else None) == actual.started_at
        assert (parse_datetime(row['completed_at']) if row['completed_at'] else None) == actual.completed_at
    assert 'FORBIDDEN_BUSINESS_INPUT' not in json.dumps(summary)
    execution = record.workflow_execution
    snapshot_nodes = list(execution.node_executions.values_list('node_id', flat=True))
    assert execution.workflow_id != graph.pk
    assert authenticated_client.get(f'/api/v1/workflows/{execution.workflow_id}/').status_code == 404
    assert authenticated_client.get(f'/api/v1/workflows/executions/{execution.pk}/').status_code == 404
    assert authenticated_client.get(f'/api/v1/workflows/nodes/{snapshot_nodes[0]}/').status_code == 404
    node_record = execution.node_executions.first()
    assert authenticated_client.get(f'/api/v1/node-executions/{node_record.pk}/').status_code == 404
    before = WorkflowExecution.objects.count()
    assert authenticated_client.post(trace_url(app, record), {}, format='json').status_code == 405
    assert WorkflowExecution.objects.count() == before


def test_actual_running_trace_changes_to_completed_after_real_http_node_finishes(user, authenticated_client):
    arrived, release = threading.Event(), threading.Event()
    errors, responses = [], []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            arrived.set()
            release.wait(10)
            payload = b'{"private_output":"FORBIDDEN_NODE_OUTPUT"}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    app, _, nodes = create_app(user, authenticated_client, node_type='http_request',
        configuration={'url': f'http://127.0.0.1:{server.server_port}/wait', 'method': 'GET',
            'headers': {'X-Fixture-Only': 'FORBIDDEN_NODE_CONFIG'}})

    def run():
        close_old_connections()
        try:
            responses.append(client_for(User.objects.get(pk=user.pk)).post(f'{BASE}{app["id"]}/test/', {'input_data': {}}, format='json'))
        except Exception as exc:
            errors.append(exc)
        finally:
            close_old_connections()

    task = threading.Thread(target=run, daemon=True)
    try:
        task.start()
        assert arrived.wait(8), errors
        record = ApplicationRequest.objects.get(application_id=app['id'])
        running = body(authenticated_client.get(trace_url(app, record)))
        assert_summary_fields(running)
        assert running['status'] == 'running' and running['completed_at'] is None
        middle = next(row for row in running['nodes'] if row['node_id'] == str(nodes[1].pk))
        actual_middle = record.workflow_execution.node_executions.get(node__name='Actual middle')
        assert middle['status'] == actual_middle.status == 'running' and middle['completed_at'] is None
        assert (parse_datetime(middle['started_at']) if middle['started_at'] else None) == actual_middle.started_at
        release.set()
        task.join(8)
        assert not task.is_alive() and not errors
        assert responses[0].status_code == 200
        final = body(authenticated_client.get(trace_url(app, record)))
        assert final['id'] == running['id'] and final['status'] == 'completed' and final['completed_at']
        assert len(final['nodes']) == 3 and all(row['status'] == 'completed' for row in final['nodes'])
        encoded = json.dumps(final)
        assert 'FORBIDDEN_NODE_OUTPUT' not in encoded and 'FORBIDDEN_NODE_CONFIG' not in encoded
    finally:
        release.set()
        task.join(10)
        server.shutdown()
        server.server_close()


def test_team_viewer_can_read_only_its_visible_application_and_revocation_is_fresh(user, authenticated_client):
    tenant = Tenant.objects.create(owner=user, name='Trace team', slug='trace-team', status='active')
    viewer = User.objects.create_user(username='trace-viewer')
    membership = TenantMembership.objects.create(tenant=tenant, user=viewer, role='viewer', is_active=True)
    app, _, _ = create_app(user, authenticated_client, tenant=tenant)
    result = body(authenticated_client.post(f'{BASE}{app["id"]}/test/', {'input_data': {}}, format='json'))
    record = ApplicationRequest.objects.get(pk=result['id'])
    client = client_for(viewer)
    assert body(client.get(trace_url(app, record)))['status'] == 'completed'
    assert client.post(trace_url(app, record), {}, format='json').status_code == 405
    membership.is_active = False
    membership.save(update_fields=['is_active'])
    assert client.get(trace_url(app, record)).status_code == 404


def test_foreign_app_and_request_ids_cannot_select_another_execution(user, authenticated_client, completed):
    app, _, _, record = completed
    second, _, _ = create_app(user, authenticated_client)
    assert authenticated_client.get(trace_url(second, record)).status_code == 404
    outsider = client_for(User.objects.create_user(username='trace-outsider'))
    assert outsider.get(trace_url(app, record)).status_code == 404
    assert authenticated_client.get(f'{BASE}{app["id"]}/requests/{uuid.uuid4()}/execution/').status_code == 404
    own = body(authenticated_client.get(trace_url(app, record), {'execution_id': str(uuid.uuid4())}))
    assert own['id'] == str(record.workflow_execution_id)


def test_application_keys_cannot_read_management_trace(user, authenticated_client, completed, api_client):
    app, _, _, record = completed
    _, raw = ApplicationAPIKey.issue(application=record.application, created_by=user, name='Trace must be denied')
    api_client.credentials(HTTP_AUTHORIZATION='Bearer '+raw)
    assert api_client.get(trace_url(app, record)).status_code == 401


def test_request_without_admitted_execution_is_explicitly_not_found(user, authenticated_client):
    app, _, _ = create_app(user, authenticated_client, node_type='unknown-unavailable')
    body(authenticated_client.post(f'{BASE}{app["id"]}/test/', {'input_data': {}}, format='json'), 422)
    record = ApplicationRequest.objects.get(application_id=app['id'])
    assert record.workflow_execution_id is None
    assert authenticated_client.get(trace_url(app, record)).status_code == 404


def test_short_node_error_does_not_expand_to_configuration_or_sensitive_url_fields(authenticated_client, completed):
    app, _, _, record = completed
    node = record.workflow_execution.node_executions.first()
    node.error_message = 'Request failed api_key=FORBIDDEN_CREDENTIAL https://example.invalid/?token=FORBIDDEN_URL\n'+('detail '*100)
    node.status, node.completed_at = 'failed', timezone.now()
    node.save(update_fields=['status', 'completed_at', 'error_message'])
    summary = body(authenticated_client.get(trace_url(app, record)))
    error = summary['nodes'][0]['error_message']
    assert error.startswith('Request failed') and len(error) <= 300
    assert 'FORBIDDEN_CREDENTIAL' not in error and 'FORBIDDEN_URL' not in error
    assert '\n' not in error
