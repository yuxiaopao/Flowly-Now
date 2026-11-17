"""Exercise the routed SSE endpoint with the real graph and execution records."""
import json
import asyncio
import threading

from asgiref.sync import async_to_sync, sync_to_async
import pytest

from workflows.models import Edge, Node, NodeExecution, Workflow, WorkflowExecution

pytestmark = pytest.mark.django_db(transaction=True)


def graph(user, **values):
    workflow = Workflow.objects.create(owner=user, name='SSE graph', version=7, **values)
    start = Node.objects.create(workflow=workflow, node_type='start', name='Start')
    input_node = Node.objects.create(workflow=workflow, node_type='input', name='Input',
        config={'variable_name': 'payload', 'required': True})
    end = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=start, target_node=input_node)
    Edge.objects.create(workflow=workflow, source_node=input_node, target_node=end)
    return workflow, input_node


def endpoint(workflow):
    return f'/api/v1/workflows/{workflow.pk}/stream_execute/'


def decode(frame):
    return json.loads(frame.decode('utf-8').removeprefix('data: ').strip())


def consume(response):
    async def collect():
        return [decode(frame) async for frame in response.streaming_content]
    return async_to_sync(collect)()


def test_post_streams_incremental_real_nodes_and_persists_opaque_input_version_and_space(user, authenticated_client):
    from tenants.models import Tenant
    tenant = Tenant.objects.create(owner=user, name='Stream team', slug='stream-team', status='active')
    workflow, input_node = graph(user, tenant=tenant)
    opaque = {'Customer_ID': 'Keep_CASE', 'metadata': {'node_id': 'business-value'}, 'items': [{'camelCase': 4}]}
    response = authenticated_client.post(endpoint(workflow), {'input_data': {'payload': opaque}}, format='json')
    assert response.status_code == 200
    assert response.is_async is True
    assert response['Content-Type'] == 'text/event-stream'
    assert response['X-Accel-Buffering'] == 'no'
    execution = WorkflowExecution.objects.get(workflow=workflow)
    assert execution.version == 7 and execution.tenant_id == tenant.pk
    assert execution.triggered_by_id == user.pk and execution.trigger_type == 'manual'
    assert execution.input_data == {'payload': opaque}
    assert not execution.node_executions.exists()

    async def read_frames():
        frames = response.streaming_content.__aiter__()
        first = decode(await anext(frames))
        assert first['type'] == 'execution_start'
        assert await sync_to_async(NodeExecution.objects.filter(execution=execution).count)() == 0
        second = decode(await anext(frames))
        assert second['type'] == 'node_complete' and second['node_name'] == 'Start'
        assert not await sync_to_async(NodeExecution.objects.filter(execution=execution, node=input_node).exists)()
        return [first, second, *[decode(frame) async for frame in frames]]

    events = async_to_sync(read_frames)()
    assert sum(event['type'] == 'execution_start' for event in events) == 1
    assert sum(event['type'] == 'execution_complete' for event in events) == 1
    input_result = next(event for event in events if event.get('node_id') == str(input_node.pk) and event['type'] == 'node_complete')
    assert input_result['output']['payload'] == opaque
    execution.refresh_from_db()
    assert events[-1]['status'] == execution.status == 'completed'
    assert events[-1]['output_data'] == execution.output_data


@pytest.mark.parametrize('body', [{'input_data': []}, {'input_data': 'text'}, {'input_data': None}, {'input_data': {'payload': 'x' * 102401}}, {'input_data': {}, 'is_async': True}])
def test_invalid_body_is_rejected_before_any_execution(user, authenticated_client, body):
    workflow, _ = graph(user)
    result = authenticated_client.post(endpoint(workflow), body, format='json')
    assert result.status_code == 400
    assert not WorkflowExecution.objects.exists()


def test_preflight_missing_input_and_graph_errors_do_not_create_runs(user, authenticated_client):
    workflow, _ = graph(user)
    result = authenticated_client.post(endpoint(workflow), {'input_data': {}}, format='json')
    assert result.status_code == 400 and result.data['code'] == 'workflow_validation'
    assert result.data['node_issues'][0]['code'] == 'missing_input'
    workflow.nodes.filter(node_type='input').update(node_type='unsupported_custom_node')
    result = authenticated_client.post(endpoint(workflow), {'input_data': {'payload': 'x'}}, format='json')
    assert result.status_code == 400 and any(issue['code'] == 'unsupported_node' for issue in result.data['node_issues'])
    assert not WorkflowExecution.objects.exists()


def test_authentication_and_edit_authority_are_required(user, admin_user, authenticated_client, api_client):
    workflow, _ = graph(user)
    assert api_client.post(endpoint(workflow), {'input_data': {'payload': 1}}, format='json').status_code == 401
    foreign, _ = graph(admin_user)
    assert authenticated_client.post(endpoint(foreign), {'input_data': {'payload': 1}}, format='json').status_code == 404
    foreign.is_public = True
    foreign.save(update_fields=['is_public'])
    assert authenticated_client.post(endpoint(foreign), {'input_data': {'payload': 1}}, format='json').status_code == 403
    assert not WorkflowExecution.objects.exists()


def test_capacity_rejection_preserves_existing_run_and_does_not_reserve_another(user, authenticated_client, settings):
    settings.WORKFLOW_MAX_CONCURRENT_PER_WORKFLOW = 1
    workflow, _ = graph(user)
    existing = WorkflowExecution.objects.create(workflow=workflow, version=7, status='running', triggered_by=user)
    response = authenticated_client.post(endpoint(workflow), {'input_data': {'payload': 'x'}}, format='json')
    assert response.status_code == 429 and response.data['code'] == 'concurrency_limit'
    assert list(WorkflowExecution.objects.values_list('pk', flat=True)) == [existing.pk]


def test_real_runtime_failure_emits_error_and_keeps_failed_database_terminal(user, authenticated_client):
    workflow, input_node = graph(user)
    input_node.config['validation'] = {'rules': [{'type': 'min_length', 'value': 5, 'message': 'too short'}]}
    input_node.save(update_fields=['config'])
    response = authenticated_client.post(endpoint(workflow), {'input_data': {'payload': 'x'}}, format='json')
    assert response.status_code == 200
    events = consume(response)
    execution = WorkflowExecution.objects.get(workflow=workflow)
    assert execution.status == 'failed' and execution.completed_at is not None
    assert 'too short' in execution.error_message
    assert events[-1]['type'] == 'error' and events[-1]['status'] == 'failed'
    assert 'too short' in events[-1]['error']
    assert not any(event['type'] == 'execution_complete' for event in events)


def test_closing_unconsumed_stream_releases_slot_without_claiming_external_cancellation(user, authenticated_client, settings):
    settings.WORKFLOW_MAX_CONCURRENT_PER_WORKFLOW = 1
    workflow, _ = graph(user)
    response = authenticated_client.post(endpoint(workflow), {'input_data': {'payload': 'x'}}, format='json')
    assert response.status_code == 200
    execution = WorkflowExecution.objects.get(workflow=workflow)
    response.close()
    execution.refresh_from_db()
    assert execution.status == 'interrupted'
    assert not execution.node_executions.exists()
    assert '连接' in execution.error_message
    retry = authenticated_client.post(endpoint(workflow), {'input_data': {'payload': 'retry'}}, format='json')
    assert retry.status_code == 200
    assert consume(retry)[-1]['status'] == 'completed'


def test_stream_creation_is_post_only(user, authenticated_client):
    workflow, _ = graph(user)
    assert authenticated_client.get(endpoint(workflow)).status_code == 405
    assert not WorkflowExecution.objects.exists()


@pytest.mark.parametrize('disconnect', [False, True])
def test_actual_asgi_sends_frames_before_a_node_finishes_and_disconnect_preserves_truth(user, monkeypatch, disconnect):
    from asgiref.testing import ApplicationCommunicator
    from django.core.asgi import get_asgi_application
    from users.authentication import generate_tokens
    from workflows.services.langchain_service import LangChainService

    workflow, input_node = graph(user)
    entered, release = threading.Event(), threading.Event()
    original = LangChainService.run_input_node

    def gated_input(service, config, data):
        entered.set()
        assert release.wait(10), 'The transport did not release its real input node'
        return original(service, config, data)

    monkeypatch.setattr(LangChainService, 'run_input_node', gated_input)
    body = json.dumps({'input_data': {'payload': {'Preserve_CASE': True}}}).encode()
    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
        'method': 'POST', 'scheme': 'http', 'path': endpoint(workflow), 'raw_path': endpoint(workflow).encode(),
        'query_string': b'', 'headers': [(b'host', b'testserver'), (b'content-type', b'application/json'),
            (b'content-length', str(len(body)).encode()),
            (b'authorization', f'Bearer {generate_tokens(user)["access"]}'.encode())],
        'server': ('testserver', 80), 'client': ('127.0.0.1', 12345)}

    async def exchange():
        application = ApplicationCommunicator(get_asgi_application(), scope)
        await application.send_input({'type': 'http.request', 'body': body, 'more_body': False})
        frames = []
        try:
            headers = await application.receive_output(timeout=10)
            assert headers['type'] == 'http.response.start' and headers['status'] == 200
            while True:
                message = await application.receive_output(timeout=10)
                assert message['type'] == 'http.response.body'
                frame = decode(message['body'])
                frames.append(frame)
                assert message['more_body'] is True
                if frame['type'] == 'node_start' and frame['node_id'] == str(input_node.pk):
                    break
            assert frames[0]['type'] == 'execution_start'
            assert await asyncio.to_thread(entered.wait, 5)
            assert not release.is_set()
            if disconnect:
                await application.send_input({'type': 'http.disconnect'})
                # Let Django cancel its sending task while the real node is in flight.
                await asyncio.sleep(0)
            release.set()
            if not disconnect:
                while True:
                    message = await application.receive_output(timeout=10)
                    if message.get('body'):
                        frames.append(decode(message['body']))
                    if not message.get('more_body', False):
                        break
            await application.wait(timeout=10)
            return frames
        finally:
            release.set()
            await application.wait(timeout=10)

    events = async_to_sync(exchange)()
    execution = WorkflowExecution.objects.get(workflow=workflow)
    assert NodeExecution.objects.get(execution=execution, node=input_node).status == 'completed'
    if disconnect:
        assert execution.status == 'interrupted'
        assert not execution.node_executions.filter(node__node_type='end').exists()
    else:
        assert execution.status == events[-1]['status'] == 'completed'
        assert events[-1]['type'] == 'execution_complete'
