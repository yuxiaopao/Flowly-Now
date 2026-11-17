"""Real HTTP/ORM delivery lifecycle; only external model HTTP is a local fixture."""
import json
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.core.exceptions import ValidationError as ModelValidationError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from applications.models import Application, ApplicationAPIKey, ApplicationRelease, ApplicationRequest
from rag.models import VectorStore, DocumentCollection, Document, Chunk
from tenants.models import Tenant, TenantMembership
from users.models import User
from workflows.models import Workflow, Node, Edge, WorkflowExecution

pytestmark = pytest.mark.django_db
BASE = '/api/v1/applications/'


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def body(response, status=200):
    assert response.status_code == status, response.content.decode()
    return response.json()['data']


@pytest.fixture
def source(user):
    workflow = Workflow.objects.create(name='Application source', owner=user)
    previous = None
    for kind, configuration in [('start', {}), ('input', {'variable_name': 'input'}),
                                ('output', {'template': 'v1:{input}'}), ('end', {})]:
        node = Node.objects.create(workflow=workflow, node_type=kind, name=kind, config=configuration)
        if previous:
            Edge.objects.create(workflow=workflow, source_node=previous, target_node=node)
        previous = node
    return workflow


@pytest.fixture
def application(authenticated_client, source):
    response = authenticated_client.post(BASE, {'name': 'Support app', 'kind': 'workflow',
        'draft': {'workflow_id': str(source.pk)}}, format='json')
    return body(response, 201)


def post(client, application, action, payload=None, status=200):
    return body(client.post(f'{BASE}{application["id"]}/{action}/', payload or {}, format='json'), status)


def publish(client, application):
    result = post(client, application, 'test', {'input_data': {'input': 'hello'}})
    assert result['status'] == 'completed'
    assert result['workflow_execution_id']
    return post(client, application, 'publish', status=201)


def test_real_workflow_test_publish_and_arbitrary_input_keys(authenticated_client, application):
    payload = {'input': 'hello', 'customer_ID': {'do_not_Rename': 7}}
    result = post(authenticated_client, application, 'test', {'input_data': payload})
    assert result['input_data'] == payload
    assert result['output_data']['input_data'] == payload
    assert result['output_data']['variables']['result'] == 'v1:hello'
    assert result['total_tokens'] is None and result['cost'] is None and result['currency'] is None
    execution = WorkflowExecution.objects.get(pk=result['workflow_execution_id'])
    assert execution.status == 'completed' and execution.node_executions.count() == 4
    release = post(authenticated_client, application, 'publish', status=201)
    assert release['version'] == 1 and release['is_active']
    assert body(authenticated_client.get(f'{BASE}{application["id"]}/'))['status'] == 'published'


def test_requires_successful_current_fingerprint(authenticated_client, application, source):
    post(authenticated_client, application, 'publish', status=409)
    publish(authenticated_client, application)
    output = source.nodes.get(node_type='output')
    output.config = {'template': 'v2:{input}'}
    output.save()
    detail = body(authenticated_client.get(f'{BASE}{application["id"]}/'))
    assert detail['draft_fingerprint'] != detail['tested_fingerprint']
    post(authenticated_client, application, 'publish', status=409)
    assert ApplicationRelease.objects.count() == 1


def test_release_runs_frozen_graph_and_rollback_is_pointer_change(authenticated_client, application, source):
    first = publish(authenticated_client, application)
    output = source.nodes.get(node_type='output')
    output.config = {'template': 'v2:{input}'}
    output.save()
    old = post(authenticated_client, application, 'invoke', {'input_data': {'input': 'world'}})
    assert old['output_data']['variables']['result'] == 'v1:world'
    second = publish(authenticated_client, application)
    assert second['version'] == 2
    fresh = post(authenticated_client, application, 'invoke', {'input_data': {'input': 'world'}})
    assert fresh['output_data']['variables']['result'] == 'v2:world'
    post(authenticated_client, application, 'rollback', {'release_id': first['id']})
    again = post(authenticated_client, application, 'invoke', {'input_data': {'input': 'world'}})
    assert again['release_id'] == first['id'] and again['output_data']['variables']['result'] == 'v1:world'
    assert ApplicationRelease.objects.count() == 2


def test_source_deletion_does_not_delete_or_change_release(authenticated_client, application, source):
    release = publish(authenticated_client, application)
    source.delete()
    result = post(authenticated_client, application, 'invoke', {'input_data': {'input': 'kept'}})
    assert result['release_id'] == release['id']
    assert result['output_data']['variables']['result'] == 'v1:kept'


def test_hidden_snapshot_cannot_be_queried_or_modified(authenticated_client, application):
    release = publish(authenticated_client, application)
    snapshot = ApplicationRelease.objects.get(pk=release['id']).workflow_snapshot
    assert snapshot.is_release_snapshot and not Workflow.objects.filter(pk=snapshot.pk).exists()
    assert authenticated_client.get(f'/api/v1/workflows/{snapshot.pk}/').status_code == 404
    listing = body(authenticated_client.get('/api/v1/workflows/'))
    assert str(snapshot.pk) not in {str(row['id']) for row in listing['results']}
    snapshot.name = 'tampered'
    with pytest.raises(ModelValidationError):
        snapshot.save()
    node = snapshot.nodes.first()
    assert authenticated_client.patch(f'/api/v1/workflows/nodes/{node.pk}/', {'name': 'tampered'}, format='json').status_code == 404
    node.name = 'tampered'
    with pytest.raises(ModelValidationError):
        node.save()
    with pytest.raises(ModelValidationError):
        snapshot.edges.first().delete()


def test_failed_test_does_not_allow_publication(authenticated_client, application):
    failure = post(authenticated_client, application, 'test', {'input_data': {}}, status=422)
    assert failure['error_code'] == 'workflow_validation' and failure['status'] == 'failed'
    assert failure['completed_at'] and failure['latency_ms'] is not None
    post(authenticated_client, application, 'publish', status=409)


def test_unpublish_and_soft_delete_revoke_invocations_keep_audit(authenticated_client, application):
    release = publish(authenticated_client, application)
    key = post(authenticated_client, application, 'api-keys', {'name': 'client'}, status=201)
    detail = post(authenticated_client, application, 'unpublish')
    assert detail['status'] == 'unpublished'
    post(authenticated_client, application, 'invoke', {'input_data': {'input': 'x'}}, status=409)
    post(authenticated_client, application, 'rollback', {'release_id': release['id']})
    assert authenticated_client.delete(f'{BASE}{application["id"]}/').status_code == 204
    assert Application.objects.get(pk=application['id']).is_deleted
    assert ApplicationAPIKey.objects.get(pk=key['id']).revoked_at
    assert ApplicationRequest.objects.filter(application_id=application['id']).exists()
    assert ApplicationRelease.objects.filter(pk=release['id']).exists()
    assert authenticated_client.get(f'{BASE}{application["id"]}/').status_code == 404


def test_one_time_hashed_key_only_calls_own_application(authenticated_client, application, source):
    publish(authenticated_client, application)
    key = post(authenticated_client, application, 'api-keys', {'name': 'integration'}, status=201)
    stored = ApplicationAPIKey.objects.get(pk=key['id'])
    assert stored.key_hash != key['api_key'] and key['api_key'] not in str(stored.__dict__)
    listing = body(authenticated_client.get(f'{BASE}{application["id"]}/api-keys/'))
    assert 'api_key' not in listing['results'][0] and 'key_hash' not in listing['results'][0]
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + key['api_key'])
    result = post(client, application, 'invoke', {'input_data': {'input': 'key caller'}})
    assert result['status'] == 'completed'
    for suffix in ('', f'{application["id"]}/', f'{application["id"]}/requests/', 'overview/'):
        assert client.get(BASE + suffix).status_code == 401
    second = body(authenticated_client.post(BASE, {'name': 'Other', 'kind': 'workflow', 'draft': {'workflow_id': str(source.pk)}}, format='json'), 201)
    assert client.post(f'{BASE}{second["id"]}/invoke/', {'input_data': {}}, format='json').status_code == 401
    post(authenticated_client, application, f'api-keys/{key["id"]}/revoke')
    assert client.post(f'{BASE}{application["id"]}/invoke/', {'input_data': {}}, format='json').status_code == 401


@pytest.mark.parametrize('change', ['expired', 'inactive_user'])
def test_key_expiry_and_owner_deactivation_fail_closed(authenticated_client, application, user, change):
    publish(authenticated_client, application)
    key = post(authenticated_client, application, 'api-keys', {'name': 'client'}, status=201)
    if change == 'expired':
        ApplicationAPIKey.objects.filter(pk=key['id']).update(expires_at=timezone.now() - timedelta(seconds=1))
    else:
        User.objects.filter(pk=user.pk).update(is_active=False)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + key['api_key'])
    assert client.post(f'{BASE}{application["id"]}/invoke/', {'input_data': {'input': 'x'}}, format='json').status_code == 401


@pytest.fixture
def team(user, source):
    tenant = Tenant.objects.create(name='Delivery team', slug='delivery-team', owner=user, billing_email='team@example.test')
    source.tenant = tenant
    source.save()
    member = User.objects.create_user(username='delivery-member')
    viewer = User.objects.create_user(username='delivery-viewer')
    TenantMembership.objects.create(tenant=tenant, user=member, role='member')
    TenantMembership.objects.create(tenant=tenant, user=viewer, role='viewer')
    return tenant, member, viewer


def test_team_editor_viewer_and_revocation_boundary(user, team, source):
    tenant, member, viewer = team
    editor = client_for(member)
    application = body(editor.post(BASE, {'name': 'Team app', 'kind': 'workflow', 'tenant_id': tenant.pk,
        'draft': {'workflow_id': str(source.pk)}}, format='json'), 201)
    read_only = client_for(viewer)
    assert read_only.get(f'{BASE}{application["id"]}/').status_code == 200
    assert read_only.patch(f'{BASE}{application["id"]}/', {'name': 'bad'}, format='json').status_code == 403
    assert read_only.post(f'{BASE}{application["id"]}/test/', {'input_data': {}}, format='json').status_code == 403
    publish(editor, application)
    key = post(editor, application, 'api-keys', {'name': 'team-client'}, status=201)
    TenantMembership.objects.filter(tenant=tenant, user=member).update(is_active=False)
    assert editor.get(f'{BASE}{application["id"]}/').status_code == 404
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION='Bearer ' + key['api_key'])
    assert api.post(f'{BASE}{application["id"]}/invoke/', {'input_data': {}}, format='json').status_code == 401
    assert client_for(user).get(f'{BASE}{application["id"]}/').status_code == 200


def test_team_source_scope_and_read_only_resources(authenticated_client, source, team):
    tenant, member, viewer = team
    assert authenticated_client.post(BASE, {'name': 'Personal leak', 'kind': 'workflow',
        'draft': {'workflow_id': str(source.pk)}}, format='json').status_code == 409
    resources = body(client_for(member).get(BASE + f'resources/?kind=workflow&tenant_id={tenant.pk}'))
    assert resources['results'] == [{'id': str(source.pk), 'name': source.name}]
    assert client_for(viewer).get(BASE + f'resources/?kind=workflow&tenant_id={tenant.pk}').status_code == 403


def test_foreign_app_release_and_request_ids_are_scoped(authenticated_client, application):
    publish(authenticated_client, application)
    foreign = User.objects.create_user(username='foreign-app-reader')
    outsider = client_for(foreign)
    assert outsider.get(f'{BASE}{application["id"]}/').status_code == 404
    assert outsider.get(f'{BASE}{application["id"]}/releases/').status_code == 404
    assert outsider.get(f'{BASE}{application["id"]}/requests/').status_code == 404
    record = ApplicationRequest.objects.get(application_id=application['id'], mode='test')
    assert body(authenticated_client.get(f'{BASE}{application["id"]}/requests/{record.pk}/'))['id'] == str(record.pk)
    assert outsider.get(f'{BASE}{application["id"]}/requests/{record.pk}/').status_code == 404


@pytest.mark.parametrize('field,value', [('kind', 'knowledge'), ('tenant_id', 999), ('draft', {'workflow_id': 'bad'}), ('draft', {'workflow_id': '00000000-0000-0000-0000-000000000000', 'invented': True})])
def test_strict_configuration_rejects_mutation_and_invalid_bindings(authenticated_client, application, field, value):
    response = authenticated_client.patch(f'{BASE}{application["id"]}/', {field: value}, format='json')
    assert response.status_code in (400, 404, 409)


@pytest.mark.parametrize('value', [[], 'string', {'huge': 'x' * (101 * 1024)}], ids=['array', 'string', 'oversized'])
def test_bounded_object_input(authenticated_client, application, value):
    response = authenticated_client.post(f'{BASE}{application["id"]}/test/', {'input_data': value}, format='json')
    assert response.status_code == (413 if isinstance(value, dict) else 400)
    assert not ApplicationRequest.objects.exists()


def test_rate_and_concurrency_rejections_are_persisted(authenticated_client, application):
    with override_settings(APPLICATION_RATE_PER_MINUTE=1):
        post(authenticated_client, application, 'test', {'input_data': {'input': 'one'}})
        rejected = post(authenticated_client, application, 'test', {'input_data': {'input': 'two'}}, status=429)
        assert rejected['status'] == 'rejected' and rejected['error_code'] == 'rate_limit'
    ApplicationRequest.objects.create(application_id=application['id'], mode='invoke', status='running')
    with override_settings(APPLICATION_MAX_CONCURRENT=1):
        rejected = post(authenticated_client, application, 'test', {'input_data': {'input': 'three'}}, status=429)
        assert rejected['error_code'] == 'concurrency_limit'


def test_overview_status_filters_and_unknown_usage(authenticated_client, application):
    empty = body(authenticated_client.get(BASE + 'overview/'))
    assert empty['request_count'] == 0 and empty['success_rate'] is None and empty['avg_latency_ms'] is None
    assert empty['total_tokens'] is None and empty['total_cost'] is None
    publish(authenticated_client, application)
    overview = body(authenticated_client.get(BASE + 'overview/'))
    assert overview['application_count'] == 1 and overview['published_count'] == 1
    assert overview['request_count'] == 1 and overview['success_rate'] == 1
    assert overview['total_tokens'] is None and overview['total_cost'] is None
    assert overview['recent_requests'][0]['application_id'] == application['id']
    assert body(authenticated_client.get(BASE + '?status=published'))['count'] == 1
    post(authenticated_client, application, 'unpublish')
    assert body(authenticated_client.get(BASE + '?status=draft'))['count'] == 0
    assert body(authenticated_client.get(BASE + '?status=unpublished'))['count'] == 1


@pytest.fixture
def knowledge(authenticated_client, user):
    store = VectorStore.objects.create(name='Local', store_type='memory', owner=user)
    collection = DocumentCollection.objects.create(name='Policies', vector_store=store, owner=user, retrieval_mode='keyword')
    document = Document.objects.create(collection=collection, title='Refund policy', content='Refunds are allowed within 30 days.', status='completed')
    Chunk.objects.create(document=document, content=document.content, vector_id='policy-chunk')
    application = body(authenticated_client.post(BASE, {'name': 'Knowledge app', 'kind': 'knowledge',
        'draft': {'collection_id': str(collection.pk)}}, format='json'), 201)
    return application, collection


@pytest.fixture
def model_server():
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            value = {'id': 'chatcmpl-fixture', 'object': 'chat.completion', 'created': 1, 'model': 'fixture-model',
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'Refunds are allowed within 30 days [1].'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 31, 'completion_tokens': 12, 'total_tokens': 43}}
            encoded = json.dumps(value).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with override_settings(RAG_CHAT_MODEL='fixture-model', RAG_CHAT_API_KEY='isolated-test-only',
                               RAG_CHAT_BASE_URL=f'http://127.0.0.1:{server.server_port}/v1', RAG_REQUEST_TIMEOUT=2):
            yield calls
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_real_rag_retrieval_and_provider_http_reach_release(authenticated_client, knowledge, model_server):
    application, collection = knowledge
    result = post(authenticated_client, application, 'test', {'input_data': {'query': 'refunds'}})
    assert result['output_data']['grounded'] and result['output_data']['answer_status'] == 'answered'
    assert result['output_data']['sources'][0]['payload']['doc_id'] == str(collection.documents.get().pk)
    assert 'within 30 days' in model_server[0]['messages'][1]['content']
    # Current RAG service returns text, not provider usage; unknown must stay null.
    assert result['total_tokens'] is None and result['cost'] is None
    release = post(authenticated_client, application, 'publish', status=201)
    assert release['knowledge_content_policy'] == 'live'
    collection.documents.get().chunks.update(content='Refunds now require a receipt within 14 days.')
    invocation = post(authenticated_client, application, 'invoke', {'input_data': {'query': 'refunds'}})
    assert '14 days' in invocation['output_data']['sources'][0]['payload']['content']
    assert '14 days' in model_server[-1]['messages'][1]['content']


def test_no_evidence_cannot_publish_or_fabricate_answers(authenticated_client, knowledge, model_server):
    application, _ = knowledge
    result = post(authenticated_client, application, 'test', {'input_data': {'query': 'galaxy-unrelated'}}, status=422)
    assert result['error_code'] == 'no_evidence' and result['output_data']['sources'] == []
    assert model_server == []
    post(authenticated_client, application, 'publish', status=409)


def test_rag_unavailable_and_removed_source_are_truthful(authenticated_client, knowledge):
    application, collection = knowledge
    with override_settings(RAG_CHAT_BASE_URL='http://127.0.0.1:1/v1', RAG_CHAT_API_KEY='isolated-test-only', RAG_CHAT_MODEL='fixture-model', RAG_REQUEST_TIMEOUT=0.1):
        result = post(authenticated_client, application, 'test', {'input_data': {'query': 'refunds'}}, status=503)
    assert result['output_data'] is None and result['error_code'] == 'upstream_unavailable'
    assert result['total_tokens'] is None and result['cost'] is None
    collection.delete()
    result = post(authenticated_client, application, 'test', {'input_data': {'query': 'refunds'}}, status=409)
    assert result['error_code'] == 'source_unavailable'


def test_knowledge_release_pins_retrieval_and_prompt_but_reads_live_content(authenticated_client, knowledge, model_server):
    application, collection = knowledge
    post(authenticated_client, application, 'test', {'input_data': {'query': 'refunds'}})
    post(authenticated_client, application, 'publish', status=201)
    original_prompt = model_server[0]['messages'][0]['content']
    collection.retrieval_mode, collection.embedding_model = 'semantic', 'unavailable-new-model'
    collection.save()
    store = collection.vector_store
    store.store_type, store.host, store.port = 'qdrant', 'unavailable-store.invalid', 1
    store.save()
    body(authenticated_client.patch(f'{BASE}{application["id"]}/', {'draft': {
        'collection_id': str(collection.pk), 'system_prompt': 'Changed draft prompt'}}, format='json'))
    result = post(authenticated_client, application, 'invoke', {'input_data': {'query': 'refunds'}})
    assert result['status'] == 'completed'
    assert model_server[-1]['messages'][0]['content'] == original_prompt


def test_idempotent_replay_returns_same_real_execution(authenticated_client, application):
    url = f'{BASE}{application["id"]}/test/'
    args = {'HTTP_IDEMPOTENCY_KEY': 'test-run-unique-key'}
    first = body(authenticated_client.post(url, {'input_data': {'input': 'once'}}, format='json', **args))
    repeated = body(authenticated_client.post(url, {'input_data': {'input': 'once'}}, format='json', **args))
    assert repeated['id'] == first['id']
    assert ApplicationRequest.objects.count() == 1 and WorkflowExecution.objects.count() == 1
    assert authenticated_client.post(url, {'input_data': {'input': 'different'}}, format='json', **args).status_code == 409


def test_stale_request_is_recovered_by_poll_and_capacity_reopens(authenticated_client, application, source):
    execution = WorkflowExecution.objects.create(workflow=source, version=1, status='running')
    stale = ApplicationRequest.objects.create(application_id=application['id'], mode='test', status='running',
        workflow_execution=execution, deadline_at=timezone.now() - timedelta(seconds=30), lease_expires_at=timezone.now() - timedelta(seconds=1))
    result = body(authenticated_client.get(f'{BASE}{application["id"]}/requests/{stale.pk}/'))
    assert result['status'] == 'failed' and result['error_code'] == 'lease_expired'
    execution.refresh_from_db()
    assert execution.status == 'cancelled'
    with override_settings(APPLICATION_MAX_CONCURRENT=1):
        assert post(authenticated_client, application, 'test', {'input_data': {'input': 'after recovery'}})['status'] == 'completed'


def test_total_deadline_rejects_late_delay_output(authenticated_client, application, source):
    input_node = source.nodes.get(node_type='input')
    input_node.node_type, input_node.config = 'delay', {'seconds': 2}
    input_node.save()
    with override_settings(APPLICATION_MAX_EXECUTION_SECONDS=0.15):
        result = post(authenticated_client, application, 'test', {'input_data': {'input': 'timeout'}}, status=504)
    assert result['status'] == 'failed' and result['error_code'] == 'execution_timeout'
    assert result['output_data'] is None and result['latency_ms'] < 1500
    execution = WorkflowExecution.objects.get(pk=result['workflow_execution_id'])
    assert execution.status == 'timeout'
    assert not execution.node_executions.filter(node__name='output', status='completed').exists()
    post(authenticated_client, application, 'publish', status=409)


def test_late_completion_cannot_overwrite_a_terminal_workflow(authenticated_client, application):
    publish(authenticated_client, application)
    record = ApplicationRequest.objects.get(application_id=application['id'], mode='test')
    execution = record.workflow_execution
    from workflows.services.workflow_executor import WorkflowExecutor
    executor = WorkflowExecutor(execution.workflow, execution)
    WorkflowExecution.objects.filter(pk=execution.pk).update(status='cancelled')
    executor._finalize_execution('completed')
    execution.refresh_from_db()
    assert execution.status == 'cancelled'


def test_snapshot_preserves_literal_node_ids_and_business_keys(authenticated_client, application, source):
    original_id = str(source.nodes.get(node_type='input').pk)
    source.config = {original_id: {'business_ID': original_id}}
    source.save()
    literal = f'unchanged literal: {original_id}'
    output_node = source.nodes.get(node_type='output')
    output_node.config = {'template': literal, original_id: original_id}
    output_node.save()
    result = post(authenticated_client, application, 'test', {'input_data': {'input': 'x'}})
    assert result['output_data']['variables']['result'] == literal
    release = post(authenticated_client, application, 'publish', status=201)
    snapshot = ApplicationRelease.objects.get(pk=release['id']).workflow_snapshot
    assert snapshot.config == source.config
    assert snapshot.nodes.get(node_type='output').config == output_node.config
    invocation = post(authenticated_client, application, 'invoke', {'input_data': {'input': 'x'}})
    assert invocation['output_data']['variables']['result'] == literal


def test_snapshot_node_output_alias_keeps_original_template_reference(authenticated_client, application, source):
    original_id = str(source.nodes.get(node_type='input').pk)
    node = source.nodes.get(node_type='output')
    node.config = {'template': '{{node_outputs.' + original_id + '.input}}'}
    node.save()
    publish(authenticated_client, application)
    result = post(authenticated_client, application, 'invoke', {'input_data': {'input': 'original reference'}})
    assert result['output_data']['variables']['result'] == 'original reference'
    assert result['output_data']['node_outputs'][original_id]['input'] == 'original reference'


def test_release_keeps_its_exact_validation_request_after_later_tests(authenticated_client, application):
    first = post(authenticated_client, application, 'test', {'input_data': {'input': 'release evidence'}})
    release = post(authenticated_client, application, 'publish', status=201)
    assert release['test_request_id'] == first['id'] and release['tested_at'] == first['completed_at']
    proof = ApplicationRelease.objects.get(pk=release['id'])
    assert str(proof.validated_by_request_id) == first['id']
    assert proof.fingerprint == proof.validated_by_request.fingerprint
    later = post(authenticated_client, application, 'test', {'input_data': {'input': 'later draft test'}})
    assert later['id'] != first['id']
    versions = body(authenticated_client.get(f'{BASE}{application["id"]}/releases/'))['results']
    assert versions[0]['test_request_id'] == first['id']


def test_validation_proof_and_request_lookup_cannot_cross_applications(authenticated_client, application, source):
    other = body(authenticated_client.post(BASE, {'name': 'Other proof', 'kind': 'workflow',
        'draft': {'workflow_id': str(source.pk)}}, format='json'), 201)
    foreign_proof = post(authenticated_client, other, 'test', {'input_data': {'input': 'other proof'}})
    assert authenticated_client.get(f'{BASE}{application["id"]}/requests/{foreign_proof["id"]}/').status_code == 404
    assert authenticated_client.post(f'{BASE}{application["id"]}/publish/', {'test_request_id': foreign_proof['id']}, format='json').status_code == 400
    post(authenticated_client, application, 'publish', status=409)
    own_proof = post(authenticated_client, application, 'test', {'input_data': {'input': 'own proof'}})
    release = post(authenticated_client, application, 'publish', status=201)
    assert release['test_request_id'] == own_proof['id']


def test_retrieval_consuming_deadline_never_starts_a_late_model_call(authenticated_client, knowledge, model_server):
    import time
    from unittest.mock import patch
    from rag.services import RAGService
    original = RAGService.retrieve
    retrieved = []

    def slow_real_retrieval(service, *args, **kwargs):
        result = original(service, *args, **kwargs)
        retrieved.append(result)
        time.sleep(0.3)
        return result

    application, _ = knowledge
    with override_settings(APPLICATION_MAX_EXECUTION_SECONDS=0.2), patch.object(RAGService, 'retrieve', slow_real_retrieval), patch.object(RAGService, 'generate_response', wraps=RAGService.generate_response) as generation:
        result = post(authenticated_client, application, 'test', {'input_data': {'query': 'refunds'}}, status=504)
    assert retrieved and retrieved[0]
    assert result['error_code'] == 'execution_timeout'
    generation.assert_not_called()
    assert model_server == []


def test_restored_node_alias_composes_with_published_snapshot_alias(authenticated_client, application, source):
    original_id = '00000000-0000-0000-0000-000000000001'
    current_id = str(source.nodes.get(node_type='input').pk)
    source.config = {'_restored_node_aliases': {original_id: current_id}}
    source.save()
    node = source.nodes.get(node_type='output')
    node.config = {'template': '{{node_outputs.' + original_id + '.input}}'}
    node.save()
    publish(authenticated_client, application)
    result = post(authenticated_client, application, 'invoke', {'input_data': {'input': 'restored then released'}})
    assert result['output_data']['variables']['result'] == 'restored then released'
