"""真实 Channels 应用的身份、资源隔离和控制消息契约。"""
from uuid import uuid4
from unittest.mock import patch
from types import SimpleNamespace

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser

from training.consumers import TrainingConsumer
from training.models import TrainingJob
from users.models import User
from workflows.consumers import ExecutionConsumer, MonitoringConsumer, WorkflowConsumer
from workflows.models import Workflow, WorkflowExecution

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def resources(user):
    workflow = Workflow.objects.create(name='实时中文测试', owner=user)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=workflow.version, triggered_by=user, status='running', context_snapshot={'visited': []})
    training = TrainingJob.objects.create(name='实时训练', job_id=str(uuid4()), created_by=user)
    return {
        'workflow': (WorkflowConsumer, 'workflow_id', str(workflow.id)),
        'execution': (ExecutionConsumer, 'execution_id', str(execution.id)),
        'training': (TrainingConsumer, 'job_id', str(training.id)),
    }


def communicator(resource, user):
    consumer, key, identifier = resource
    client = WebsocketCommunicator(consumer.as_asgi(), '/')
    client.scope.update(user=user, url_route={'kwargs': {key: identifier}})
    return client


@pytest.mark.parametrize('kind', ['workflow', 'execution', 'training'])
@pytest.mark.parametrize('identity', ['anonymous', 'foreign', 'owner'])
def test_resource_connection_permissions(resources, user, kind, identity):
    viewer = user if identity == 'owner' else AnonymousUser() if identity == 'anonymous' else User.objects.create_user(username='foreign')
    async def scenario():
        client = communicator(resources[kind], viewer)
        connected, code = await client.connect()
        try:
            assert connected is (identity == 'owner')
            if connected:
                assert (await client.receive_json_from())['type'] == 'connected'
                await client.send_json_to({'type': 'ping'})
                assert (await client.receive_json_from())['type'] == 'pong'
            else:
                assert code == (4401 if identity == 'anonymous' else 4403)
        finally:
            await client.disconnect()
    async_to_sync(scenario)()


@pytest.mark.parametrize('kind', ['workflow', 'execution', 'training'])
def test_missing_resource_is_rejected(resources, user, kind):
    consumer, key, _ = resources[kind]
    async def scenario():
        client = communicator((consumer, key, str(uuid4())), user)
        assert await client.connect() == (False, 4403)
        await client.disconnect()
    async_to_sync(scenario)()


@pytest.mark.parametrize('kind', ['workflow', 'execution'])
def test_status_serializes_uuid_and_chinese_names(resources, user, kind):
    async def scenario():
        client = communicator(resources[kind], user)
        assert (await client.connect())[0]
        await client.receive_json_from()
        await client.send_json_to({'type': 'get_status'})
        message = await client.receive_json_from()
        assert message['type'] == f'{kind}_status'
        assert message['data']['id'] == resources[kind][2]
        assert 'error' not in message['data']
        await client.disconnect()
    async_to_sync(scenario)()


def test_execution_controls_persist_without_async_orm_errors(resources, user):
    async def scenario():
        client = communicator(resources['execution'], user)
        assert (await client.connect())[0]
        await client.receive_json_from()
        for action, event in [('pause', 'execution_paused'), ('resume', 'execution_resumed'), ('cancel', 'execution_cancelled')]:
            await client.send_json_to({'type': action})
            response = await client.receive_json_from()
            assert response['type'] == event, response
        await client.disconnect()
    with patch('workflows.tasks.resume_workflow_task.delay', return_value=SimpleNamespace(id='resume-test')) as dispatch:
        async_to_sync(scenario)()
        dispatch.assert_called_once_with(resources['execution'][2])
    execution = WorkflowExecution.objects.get(pk=resources['execution'][2])
    assert execution.status == 'cancelled'
    assert execution.completed_at is not None


def test_monitoring_is_private_to_each_user(user):
    other = User.objects.create_user(username='monitor-other')
    async def scenario():
        first = WebsocketCommunicator(MonitoringConsumer.as_asgi(), '/')
        second = WebsocketCommunicator(MonitoringConsumer.as_asgi(), '/')
        first.scope['user'], second.scope['user'] = user, other
        assert (await first.connect())[0] and (await second.connect())[0]
        await first.receive_json_from()
        await second.receive_json_from()
        await get_channel_layer().group_send(f'monitoring_{user.id}', {'type': 'metric_update', 'data': {'name': '私有告警'}})
        assert (await first.receive_json_from())['data']['name'] == '私有告警'
        assert await second.receive_nothing(timeout=0.1)
        await first.disconnect()
        await second.disconnect()
    async_to_sync(scenario)()


def test_anonymous_monitoring_is_rejected():
    async def scenario():
        client = WebsocketCommunicator(MonitoringConsumer.as_asgi(), '/')
        client.scope['user'] = AnonymousUser()
        assert await client.connect() == (False, 4401)
        await client.disconnect()
    async_to_sync(scenario)()


def test_billing_monitoring_remains_private_even_with_a_tenant(user):
    from billing.models import Invoice
    from django.utils import timezone
    from monitoring.broadcasts import monitoring_groups
    now = timezone.now()
    invoice = Invoice.objects.create(user=user, invoice_number='audit-private', subtotal=10, total=10, period_start=now, period_end=now, due_date=now)
    assert monitoring_groups({'event': 'invoice_created', 'invoice_id': invoice.id, 'tenant_id': str(uuid4())}) == {f'monitoring_{user.id}'}


def test_global_branding_and_private_session_events_keep_their_scopes(user):
    from monitoring.broadcasts import monitoring_groups
    assert monitoring_groups({'event': 'branding_cache_invalidated', 'tenant_id': None}) == {'monitoring_public'}
    tenant_id = str(uuid4())
    assert monitoring_groups({'event': 'branding_cache_invalidated', 'tenant_id': tenant_id}) == {f'monitoring_tenant_{tenant_id}'}
    assert monitoring_groups({'event': 'nl_session_created', 'user_id': user.id}) == {f'monitoring_{user.id}'}
