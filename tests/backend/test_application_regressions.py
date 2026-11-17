"""Actual HTTP/ORM regression suites, frozen targets and deterministic request evidence."""
import copy
import json
import threading
import uuid
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from applications.models import (Application, ApplicationRequest, ApplicationTestSuite, ApplicationTestCase,
                                 ApplicationEvaluationRun, ApplicationEvaluationResult)
from applications.evaluation_service import execute_run, recover_run
from applications.evaluation_assertions import json_pointer, MISSING, check_assertions, validate_assertions
from tenants.models import Tenant, TenantMembership
from workflows.models import Workflow, Node, Edge, WorkflowExecution

pytestmark = pytest.mark.django_db(transaction=True)
BASE = '/api/v1/applications/'


def body(response, status=200):
    assert response.status_code == status, response.content.decode()
    return response.json()['data']


@pytest.fixture
def app_case(authenticated_client, user):
    workflow = Workflow.objects.create(owner=user, name='Regression source')
    start = Node.objects.create(workflow=workflow, node_type='start', name='Input')
    reply = Node.objects.create(workflow=workflow, node_type='text_template', name='Reply', config={'template': 'Hello {{Customer_ID}}'})
    end = Node.objects.create(workflow=workflow, node_type='end', name='Output')
    Edge.objects.create(workflow=workflow, source_node=start, target_node=reply)
    Edge.objects.create(workflow=workflow, source_node=reply, target_node=end)
    app = body(authenticated_client.post(BASE, {'name': 'Regression app', 'kind': 'workflow', 'draft': {'workflow_id': str(workflow.pk)}}, format='json'), 201)
    return app, workflow, reply


def url(app, action):
    return f'{BASE}{app["id"]}/{action}/'


def suite_and_case(client, app, *, expected='Hello Ada', enabled=True):
    suite = body(client.post(url(app, 'test-suites'), {'name': 'Core questions'}, format='json'), 201)
    row = {'name': 'Preserve case', 'input_data': {'Customer_ID': 'Ada', 'foo_bar': 1, 'fooBar': 2},
           'assertions': [{'type': 'json_equals', 'path': '/variables/text', 'expected': expected}], 'enabled': enabled}
    case = body(client.post(url(app, f'test-suites/{suite["id"]}/cases'), row, format='json'), 201)
    return suite, case


def run(client, app, suite, *, status=201, key=None, **extra):
    headers = {'HTTP_IDEMPOTENCY_KEY': key} if key else {}
    return body(client.post(url(app, 'evaluation-runs'), {'suite_id': suite['id'], 'target': 'draft', **extra}, format='json', **headers), status)


def test_real_cases_run_persisted_requests_and_never_replace_single_test_proof(authenticated_client, app_case):
    app, _, _ = app_case
    suite, case = suite_and_case(authenticated_client, app)
    executed = run(authenticated_client, app, suite)
    assert executed['status'] == 'completed' and executed['passed'] == executed['total'] == 1
    assert executed['runner_mode'] == 'eager' and executed['pass_rate'] == 1
    record = ApplicationRequest.objects.get(pk=executed['results'][0]['request_id'])
    assert record.mode == 'evaluation' and record.input_data == case['input_data']
    assert record.output_data['variables']['text'] == 'Hello Ada'
    assert executed['results'][0]['assertion_results'][0]['passed'] is True
    assert Application.objects.get(pk=app['id']).tested_fingerprint == ''
    assert body(authenticated_client.get(url(app, f'evaluation-runs/{executed["id"]}')))['passed'] == 1


def test_assertion_failure_is_real_and_batch_does_not_become_passed_by_last_case(authenticated_client, app_case):
    app, _, _ = app_case
    suite, _ = suite_and_case(authenticated_client, app, expected='wrong result')
    body(authenticated_client.post(url(app, f'test-suites/{suite["id"]}/cases'), {'name': 'Actually passes',
        'input_data': {'Customer_ID': 'Grace'}, 'assertions': [{'type': 'json_contains', 'path': '/variables/text', 'expected': 'Grace'}]}, format='json'), 201)
    result = run(authenticated_client, app, suite)
    assert result['status'] == 'completed' and result['passed'] == 1 and result['failed'] == 1
    assert result['pass_rate'] == .5 and [row['status'] for row in result['results']] == ['failed', 'passed']
    assert result['results'][0]['assertion_results'][0]['actual'] == '"Hello Ada"'


def test_optional_server_publish_gate_has_complete_current_batch_proof(authenticated_client, app_case):
    app, _, _ = app_case
    suite, case = suite_and_case(authenticated_client, app)
    body(authenticated_client.post(url(app, 'test'), {'input_data': {'Customer_ID': 'Ada'}}, format='json'))
    configured = body(authenticated_client.patch(f'{BASE}{app["id"]}/', {'required_evaluation_suite_id': suite['id']}, format='json'))
    assert configured['evaluation_gate']['ready'] is False
    denied = authenticated_client.post(url(app, 'publish'), {}, format='json')
    assert denied.status_code == 409 and denied.json()['errors']['reason'] == 'evaluation_required'
    executed = run(authenticated_client, app, suite)
    published = body(authenticated_client.post(url(app, 'publish'), {}, format='json'), 201)
    assert published['evaluation_run_id'] == executed['id'] and published['test_request_id']
    body(authenticated_client.patch(url(app, f'test-suites/{suite["id"]}/cases/{case["id"]}'), {'name': 'Changed case'}, format='json'))
    assert body(authenticated_client.get(f'{BASE}{app["id"]}/'))['evaluation_gate']['ready'] is False
    assert authenticated_client.post(url(app, 'publish'), {}, format='json').status_code == 409
    assert authenticated_client.delete(url(app, f'test-suites/{suite["id"]}')).status_code == 409


def test_fixed_draft_and_suite_snapshot_survive_source_and_case_edits(authenticated_client, app_case):
    app, _, reply = app_case
    suite, case = suite_and_case(authenticated_client, app)
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async'):
        queued = run(authenticated_client, app, suite, status=202)
    reply.config = {'template': 'Changed {{Customer_ID}}'}
    reply.save(update_fields=['config'])
    body(authenticated_client.patch(url(app, f'test-suites/{suite["id"]}/cases/{case["id"]}'), {'input_data': {'Customer_ID': 'Changed'}}, format='json'))
    execute_run(queued['id'])
    actual = body(authenticated_client.get(url(app, f'evaluation-runs/{queued["id"]}')))
    assert actual['passed'] == 1 and actual['is_stale'] is True
    evidence = ApplicationEvaluationResult.objects.get(run_id=queued['id'])
    assert evidence.input_data['Customer_ID'] == 'Ada' and evidence.request.output_data['variables']['text'] == 'Hello Ada'


def test_specific_historical_release_is_used_without_changing_active_version(authenticated_client, app_case):
    app, _, reply = app_case
    suite, _ = suite_and_case(authenticated_client, app)
    body(authenticated_client.post(url(app, 'test'), {'input_data': {'Customer_ID': 'Ada'}}, format='json'))
    first = body(authenticated_client.post(url(app, 'publish'), {}, format='json'), 201)
    reply.config = {'template': 'Changed {{Customer_ID}}'}
    reply.save(update_fields=['config'])
    body(authenticated_client.post(url(app, 'test'), {'input_data': {'Customer_ID': 'Ada'}}, format='json'))
    second = body(authenticated_client.post(url(app, 'publish'), {}, format='json'), 201)
    old = run(authenticated_client, app, suite, target='release', release_id=first['id'])
    assert old['passed'] == 1 and old['release_id'] == first['id']
    assert Application.objects.get(pk=app['id']).active_release_id == uuid.UUID(second['id'])


def test_start_is_idempotent_and_does_not_repeat_side_effects(authenticated_client, app_case):
    app, _, reply = app_case
    suite, _ = suite_and_case(authenticated_client, app)
    first = run(authenticated_client, app, suite, key='one-attempt')
    reply.config = {'template': 'Changed {{Customer_ID}}'}
    reply.save(update_fields=['config'])
    again = run(authenticated_client, app, suite, status=200, key='one-attempt')
    assert again['id'] == first['id'] and again['is_stale'] is True
    assert ApplicationRequest.objects.filter(application_id=app['id'], mode='evaluation').count() == 1
    conflict = authenticated_client.post(url(app, 'evaluation-runs'), {'suite_id': suite['id'], 'target': 'release',
        'release_id': str(uuid.uuid4())}, format='json', HTTP_IDEMPOTENCY_KEY='one-attempt')
    assert conflict.status_code == 409


def test_broker_failure_and_expired_queue_never_execute_inline(authenticated_client, app_case):
    app, _, _ = app_case
    suite, _ = suite_and_case(authenticated_client, app)
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async', side_effect=ConnectionError):
        failed = run(authenticated_client, app, suite, status=503)
    assert failed['error_code'] == 'queue_unavailable' and failed['status'] == 'failed'
    assert not ApplicationRequest.objects.filter(application_id=app['id']).exists()
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async'):
        queued = run(authenticated_client, app, suite, status=202)
    ApplicationEvaluationRun.objects.filter(pk=queued['id']).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    expired = body(authenticated_client.get(url(app, f'evaluation-runs/{queued["id"]}')))
    assert expired['status'] == 'failed' and expired['error_code'] == 'queue_expired'
    execute_run(queued['id'])
    assert not ApplicationRequest.objects.filter(application_id=app['id']).exists()


def test_queue_cancel_and_duplicate_delivery_are_durable(authenticated_client, app_case):
    app, _, _ = app_case
    suite, _ = suite_and_case(authenticated_client, app)
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async'):
        queued = run(authenticated_client, app, suite, status=202)
    stopped = body(authenticated_client.post(url(app, f'evaluation-runs/{queued["id"]}/cancel'), {}, format='json'))
    assert stopped['status'] == 'cancelled' and stopped['results'][0]['status'] == 'cancelled'
    execute_run(queued['id'])
    assert not ApplicationRequest.objects.filter(application_id=app['id']).exists()
    completed = run(authenticated_client, app, suite)
    execute_run(completed['id'])
    assert ApplicationRequest.objects.filter(application_id=app['id']).count() == 1


def test_export_import_are_transactional_and_preserve_opaque_payload(authenticated_client, app_case):
    app, _, _ = app_case
    suite, case = suite_and_case(authenticated_client, app)
    exported = authenticated_client.get(url(app, f'test-suites/{suite["id"]}/export'))
    assert exported.status_code == 200 and exported['Cache-Control'] == 'private, no-store'
    portable = exported.json()
    imported = body(authenticated_client.post(url(app, 'test-suites-import'), portable, format='json'), 201)
    rows = body(authenticated_client.get(url(app, f'test-suites/{imported["id"]}/cases')))['results']
    assert rows[0]['input_data'] == case['input_data'] and rows[0]['id'] != case['id']
    bad = copy.deepcopy(portable)
    bad['cases'].append({'name': 'Invalid', 'input_data': {}, 'assertions': [{'type': 'python_eval', 'expected': 'x'}]})
    before = ApplicationTestSuite.objects.count()
    assert authenticated_client.post(url(app, 'test-suites-import'), bad, format='json').status_code == 400
    assert ApplicationTestSuite.objects.count() == before


def test_compare_distinguishes_regression_and_modified_case(authenticated_client, app_case):
    app, _, reply = app_case
    suite, case = suite_and_case(authenticated_client, app)
    first = run(authenticated_client, app, suite)
    reply.config = {'template': 'Changed {{Customer_ID}}'}
    reply.save(update_fields=['config'])
    second = run(authenticated_client, app, suite)
    comparison = body(authenticated_client.get(url(app, f'evaluation-runs/{second["id"]}/compare'), {'baseline_id': first['id']}))
    assert comparison['results'][0]['change'] == 'regressed'
    body(authenticated_client.patch(url(app, f'test-suites/{suite["id"]}/cases/{case["id"]}'), {'name': 'Revised case'}, format='json'))
    third = run(authenticated_client, app, suite)
    comparison = body(authenticated_client.get(url(app, f'evaluation-runs/{third["id"]}/compare'), {'baseline_id': second['id']}))
    assert comparison['results'][0]['change'] == 'modified'


def test_viewer_cannot_write_or_run_and_foreign_ids_are_rejected(authenticated_client, app_case, user):
    app, workflow, _ = app_case
    suite, case = suite_and_case(authenticated_client, app)
    outsider = APIClient()
    tenant = Tenant.objects.create(owner=user, name='Regression team', slug='regression-team', status='active')
    workflow.tenant = tenant
    workflow.save(update_fields=['tenant'])
    Application.objects.filter(pk=app['id']).update(tenant=tenant)
    from users.models import User
    viewer = User.objects.create_user(username='regression-viewer', password='fixture-only-password')
    TenantMembership.objects.create(tenant=tenant, user=viewer, role='viewer', is_active=True)
    outsider.force_authenticate(user=viewer)
    assert outsider.get(url(app, 'test-suites')).status_code == 200
    assert outsider.post(url(app, 'evaluation-runs'), {'suite_id': suite['id'], 'target': 'draft'}, format='json').status_code == 403
    assert outsider.patch(url(app, f'test-suites/{suite["id"]}/cases/{case["id"]}'), {'name': 'No'}, format='json').status_code == 403
    assert authenticated_client.post(url(app, 'evaluation-runs'), {'suite_id': str(uuid.uuid4()), 'target': 'draft'}, format='json').status_code == 404


@pytest.mark.parametrize('assertion', [
    {'type': 'json_equals', 'path': '/a~2b', 'expected': 1},
    {'type': 'sources_min', 'expected': True},
    {'type': 'latency_max', 'expected': -1},
    {'type': 'json_exists', 'expected': 'true'},
    {'type': 'json_type', 'expected': 'function'},
    {'type': 'error_code', 'expected': ''},
    {'type': 'json_equals', 'expected': float('nan')},
])
def test_invalid_assertions_are_rejected(assertion):
    from rest_framework.exceptions import ValidationError
    with pytest.raises(ValidationError):
        validate_assertions([assertion])


def test_json_pointer_and_json_equality_preserve_type_and_escaping():
    assert json_pointer({'a/b': {'~key': [0, {'Customer_ID': 3}]}}, '/a~1b/~0key/1/Customer_ID') == 3
    assert json_pointer({'x': []}, '/x/01') is MISSING
    record = ApplicationRequest(status='completed', output_data={'flag': True, 'empty': None}, latency_ms=0)
    rows = check_assertions(record, validate_assertions([
        {'type': 'json_equals', 'path': '/flag', 'expected': 1},
        {'type': 'json_exists', 'path': '/empty', 'expected': True},
        {'type': 'json_exists', 'path': '/missing', 'expected': False},
        {'type': 'latency_max', 'expected': 0},
    ]))
    assert [row['passed'] for row in rows] == [False, True, True, True]


def test_cancelled_execution_is_not_resurrected_before_engine_start(user):
    from workflows.services.workflow_executor import WorkflowExecutor
    workflow = Workflow.objects.create(owner=user, name='Cancelled before startup')
    Node.objects.create(workflow=workflow, node_type='start', name='Start')
    execution = WorkflowExecution.objects.create(workflow=workflow, status='pending', triggered_by=user, version=1)
    executor = WorkflowExecutor(workflow, execution)
    WorkflowExecution.objects.filter(pk=execution.pk).update(status='cancelled')
    assert executor.execute().status == 'cancelled'
    assert not execution.node_executions.exists()


def test_worker_checks_revoked_actor_before_any_request(authenticated_client, app_case, user):
    app, _, _ = app_case
    suite, _ = suite_and_case(authenticated_client, app)
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async'):
        queued = run(authenticated_client, app, suite, status=202)
    type(user).objects.filter(pk=user.pk).update(is_active=False)
    execute_run(queued['id'])
    actual = ApplicationEvaluationRun.objects.get(pk=queued['id'])
    assert actual.status == 'failed' and actual.error_code == 'permission_revoked'
    assert not ApplicationRequest.objects.filter(application_id=app['id']).exists()


def test_expected_error_code_is_asserted_against_real_failed_request(authenticated_client, app_case):
    app, _, reply = app_case
    reply.node_type = 'unsupported-example'
    reply.save(update_fields=['node_type'])
    suite, case = suite_and_case(authenticated_client, app)
    body(authenticated_client.patch(url(app, f'test-suites/{suite["id"]}/cases/{case["id"]}'),
        {'assertions': [{'type': 'error_code', 'expected': 'workflow_validation'}]}, format='json'))
    result = run(authenticated_client, app, suite)
    assert result['passed'] == 1 and result['results'][0]['status'] == 'passed'
    evidence = ApplicationRequest.objects.get(pk=result['results'][0]['request_id'])
    assert evidence.status == 'failed' and evidence.http_status == 422 and evidence.error_code == 'workflow_validation'


def test_running_cancel_is_acknowledged_after_real_inflight_http_returns(authenticated_client, app_case):
    app, workflow, reply = app_case
    arrived, release = threading.Event(), threading.Event()
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.path)
            if self.path == '/block':
                arrived.set()
                release.wait(10)
            content = b'{"ok":true}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    reply.node_type, reply.config = 'http_request', {'url': f'http://127.0.0.1:{server.server_port}/block', 'method': 'GET'}
    reply.save(update_fields=['node_type', 'config'])
    second = Node.objects.create(workflow=workflow, node_type='http_request', name='Must not run', config={'url': f'http://127.0.0.1:{server.server_port}/after', 'method': 'GET'})
    end = workflow.nodes.get(node_type='end')
    workflow.edges.filter(source_node=reply, target_node=end).delete()
    Edge.objects.create(workflow=workflow, source_node=reply, target_node=second)
    Edge.objects.create(workflow=workflow, source_node=second, target_node=end)
    suite, _ = suite_and_case(authenticated_client, app)
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async'):
        queued = run(authenticated_client, app, suite, status=202)
    errors = []

    def worker():
        close_old_connections()
        try:
            execute_run(queued['id'])
        except Exception as exc:
            errors.append(exc)
        finally:
            close_old_connections()

    task = threading.Thread(target=worker, daemon=True)
    try:
        task.start()
        assert arrived.wait(8), errors
        cancelling = body(authenticated_client.post(url(app, f'evaluation-runs/{queued["id"]}/cancel'), {}, format='json'))
        assert cancelling['status'] == 'cancelling' and cancelling['completed_at'] is None
        release.set()
        task.join(8)
        assert not task.is_alive() and not errors
        final = body(authenticated_client.get(url(app, f'evaluation-runs/{queued["id"]}')))
        assert final['status'] == 'cancelled' and final['results'][0]['status'] == 'cancelled'
        assert calls == ['/block']
        record = ApplicationRequest.objects.get(pk=final['results'][0]['request_id'])
        assert record.status == 'failed' and record.error_code == 'evaluation_cancelled'
    finally:
        release.set()
        task.join(10)
        server.shutdown()
        server.server_close()


def test_different_live_corpus_is_not_attributed_to_version_regression(authenticated_client, user):
    from rag.models import VectorStore, DocumentCollection, Document, Chunk

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            content = json.dumps({'id': 'local-protocol-fixture', 'object': 'chat.completion', 'created': 1, 'model': 'gpt-fixture',
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'Release requires a test. [1]'}, 'finish_reason': 'stop'}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    store = VectorStore.objects.create(owner=user, name='Corpus store', store_type='memory')
    collection = DocumentCollection.objects.create(owner=user, name='Corpus', vector_store=store, retrieval_mode='keyword')
    document = Document.objects.create(collection=collection, title='Release', content='Release requires a test.', status='completed')
    chunk = Chunk.objects.create(document=document, content=document.content, vector_id='release')
    app = body(authenticated_client.post(BASE, {'name': 'Corpus app', 'kind': 'knowledge', 'draft': {'collection_id': str(collection.pk)}}, format='json'), 201)
    suite = body(authenticated_client.post(url(app, 'test-suites'), {'name': 'Corpus questions'}, format='json'), 201)
    body(authenticated_client.post(url(app, f'test-suites/{suite["id"]}/cases'), {'name': 'Evidence', 'input_data': {'query': 'release'},
        'assertions': [{'type': 'grounded', 'expected': True}, {'type': 'sources_min', 'expected': 1}]}, format='json'), 201)
    try:
        with override_settings(RAG_CHAT_MODEL='gpt-fixture', RAG_CHAT_API_KEY='local-fixture', RAG_CHAT_BASE_URL=f'http://127.0.0.1:{server.server_port}/v1'):
            first = run(authenticated_client, app, suite)
            assert first['passed'] == 1
            chunk.content = 'Release requires two tests.'
            chunk.save(update_fields=['content'])
            second = run(authenticated_client, app, suite)
            assert second['passed'] == 1
        compared = body(authenticated_client.get(url(app, f'evaluation-runs/{second["id"]}/compare'), {'baseline_id': first['id']}))
        assert compared['corpus_matches'] is False and compared['results'][0]['change'] == 'inconclusive'
        assert compared['warning']
    finally:
        server.shutdown()
        server.server_close()


def test_dispatch_waits_for_outer_commit_and_never_publishes_rolled_back_batch(authenticated_client, app_case, user):
    from django.db import transaction
    from applications.evaluation_service import start_run
    app, _, _ = app_case
    suite, _ = suite_and_case(authenticated_client, app)
    model = Application.objects.get(pk=app['id'])
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async') as dispatch:
        with transaction.atomic():
            created, _ = start_run(model, user, {'suite_id': suite['id'], 'target': 'draft'}, 'after-commit')
            dispatch.assert_not_called()
        dispatch.assert_called_once_with(args=[str(created.pk)], retry=False)
        from applications.evaluation_service import cancel_run
        cancel_run(created)
        dispatch.reset_mock()
        with pytest.raises(ValueError), transaction.atomic():
            rolled_back, _ = start_run(model, user, {'suite_id': suite['id'], 'target': 'draft'}, 'rollback')
            raise ValueError('rollback fixture')
        dispatch.assert_not_called()
    assert not ApplicationEvaluationRun.objects.filter(pk=rolled_back.pk).exists()


def test_suite_size_limit_rolls_back_case_and_keeps_portable_export(authenticated_client, app_case):
    app, _, _ = app_case
    suite, case = suite_and_case(authenticated_client, app)
    before = ApplicationTestSuite.objects.get(pk=suite['id']).revision
    with patch('applications.evaluation_constants.MAX_IMPORT_BYTES', 100):
        rejected = authenticated_client.patch(url(app, f'test-suites/{suite["id"]}/cases/{case["id"]}'), {'name': 'Must roll back'}, format='json')
    assert rejected.status_code == 400
    assert ApplicationTestCase.objects.get(pk=case['id']).name == 'Preserve case'
    assert ApplicationTestSuite.objects.get(pk=suite['id']).revision == before


def test_total_deadline_reports_attempted_case_as_error_not_unexecuted(authenticated_client, app_case):
    app, _, reply = app_case
    reply.node_type, reply.config = 'delay', {'duration': 200, 'unit': 'ms'}
    reply.save(update_fields=['node_type', 'config'])
    suite, _ = suite_and_case(authenticated_client, app)
    with override_settings(APPLICATION_EVALUATION_MAX_SECONDS=.05):
        result = run(authenticated_client, app, suite)
    assert result['status'] == 'failed' and result['error_code'] == 'evaluation_timeout'
    assert result['results'][0]['status'] == 'error' and result['results'][0]['request_id']


def test_finished_async_request_releases_capacity_without_a_frontend_poll(authenticated_client, app_case, user):
    from applications.evaluation_service import start_run
    app, workflow, _ = app_case
    suite, _ = suite_and_case(authenticated_client, app)
    model = Application.objects.get(pk=app['id'])
    record = ApplicationRequest.objects.create(application=model, caller=user, mode='test', status='running',
        input_data={}, deadline_at=timezone.now()+timedelta(seconds=120), lease_expires_at=timezone.now()+timedelta(seconds=150))
    parent = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user, status='completed',
        trigger_source={'application_request_id': str(record.pk)})
    WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user, status='completed',
        trigger_source={'application_request_id': str(record.pk), 'subworkflow_mode': 'async'})
    record.workflow_execution = parent
    record.save(update_fields=['workflow_execution'])
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False, APPLICATION_MAX_CONCURRENT=1,
                           APPLICATION_EVALUATION_MAX_SECONDS=2), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async'):
        batch, _ = start_run(model, user, {'suite_id': suite['id'], 'target': 'draft'})
        execute_run(batch.pk)
    record.refresh_from_db(); batch.refresh_from_db()
    assert record.status == 'completed'
    assert batch.status == 'completed' and batch.passed == 1
