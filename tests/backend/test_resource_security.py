"""HTTP and Channels regressions for template and desktop ownership."""
from unittest.mock import patch, AsyncMock

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient

from agents.consumers import DesktopAgentConsumer
from agents.models_desktop import DesktopAgent
from marketplace.models import WorkflowTemplate
from training.models import TrainingJob
from users.models import User
from users.authentication import generate_tokens
from users.websocket_auth import JWTAuthMiddlewareStack
from training.consumers import TrainingConsumer
from agents.desktop_jobs import DESKTOP_AGENT_CONFIG_KEY
from agents.desktop_jobs import DESKTOP_AGENT_RECORD_CONFIG_KEY, desktop_agent_group
from training.execution_control import CANCEL_REQUEST_KEY
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async

pytestmark = pytest.mark.django_db(transaction=True)
DESKTOP_URL = '/api/v1/agents/desktop/'
MARKET_URL = '/api/v1/marketplace/templates/'


@pytest.fixture
def foreign_user():
    return User.objects.create_user(username='resource-foreign')


@pytest.fixture
def desktop(user):
    return DesktopAgent.objects.create(agent_id='owned-desktop', owner=user,
                                       gpu_available=True, supports_yolo_training=True,
                                       status='online')


@pytest.fixture
def template(user):
    return WorkflowTemplate.objects.create(name='Public template', slug='resource-public',
                                           created_by=user, is_published=True)


def authenticated(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.parametrize('method', ['patch', 'delete'])
@pytest.mark.parametrize('identity', ['anonymous', 'foreign'])
def test_public_template_does_not_allow_unowned_writes(template, foreign_user, method, identity):
    client = APIClient() if identity == 'anonymous' else authenticated(foreign_user)
    response = getattr(client, method)(f'{MARKET_URL}{template.pk}/', {'name': 'Changed'}, format='json')
    assert response.status_code in (401, 403)
    assert WorkflowTemplate.objects.get(pk=template.pk).name == 'Public template'


def test_template_owner_can_edit_but_not_assign_owner_or_verification(template, user, foreign_user):
    response = authenticated(user).patch(f'{MARKET_URL}{template.pk}/', {
        'name': 'Owner edit', 'created_by': foreign_user.pk, 'is_verified': True,
        'install_count': 100,
    }, format='json')
    assert response.status_code == 200
    template.refresh_from_db()
    assert template.name == 'Owner edit'
    assert template.created_by_id == user.pk
    assert not template.is_verified
    assert template.install_count == 0


def test_public_template_remains_readable(template):
    assert APIClient().get(f'{MARKET_URL}{template.pk}/').status_code == 200


@pytest.mark.parametrize('action,payload', [
    ('register', {'agent_id': 'anonymous-agent'}),
    ('heartbeat', {'agent_id': 'owned-desktop', 'status': 'offline'}),
])
def test_desktop_mutations_require_login(desktop, action, payload):
    response = APIClient().post(f'{DESKTOP_URL}{action}/', payload, format='json')
    assert response.status_code == 401
    desktop.refresh_from_db()
    assert desktop.status == 'online'


def test_registration_preserves_owner_on_conflict(desktop, foreign_user):
    response = authenticated(foreign_user).post(f'{DESKTOP_URL}register/', {
        'agent_id': desktop.agent_id, 'display_name': 'Hijacked',
    }, format='json')
    assert response.status_code in (403, 409)
    assert response.json()['errors']['code'] == 'agent_identity_conflict'
    desktop.refresh_from_db()
    assert desktop.owner_id != foreign_user.pk
    assert desktop.display_name != 'Hijacked'


def test_owner_can_register_and_reregister(user):
    client = authenticated(user)
    payload = {'agent_id': 'new-desktop', 'display_name': 'Mine'}
    assert client.post(f'{DESKTOP_URL}register/', payload, format='json').status_code == 201
    assert client.post(f'{DESKTOP_URL}register/', payload, format='json').status_code == 200
    assert DesktopAgent.objects.get(agent_id='new-desktop').owner_id == user.pk


def test_available_devices_are_private(desktop, foreign_user):
    response = authenticated(foreign_user).get(f'{DESKTOP_URL}available/')
    assert response.status_code == 200
    assert desktop.agent_id not in str(response.data)


def test_foreign_heartbeat_cannot_change_device(desktop, foreign_user):
    response = authenticated(foreign_user).post(f'{DESKTOP_URL}heartbeat/', {
        'agent_id': desktop.agent_id, 'status': 'offline',
    }, format='json')
    assert response.status_code == 404
    desktop.refresh_from_db()
    assert desktop.status == 'online'


def test_foreign_dispatch_does_not_send_command(desktop, foreign_user):
    with patch('channels.layers.get_channel_layer') as channel:
        response = authenticated(foreign_user).post(f'{DESKTOP_URL}dispatch_training/', {
            'agent_id': desktop.agent_id, 'job_config': {},
        }, format='json')
    assert response.status_code == 404
    channel.assert_not_called()


def test_device_patch_cannot_reassign_identity(desktop, user, foreign_user):
    response = authenticated(user).patch(f'{DESKTOP_URL}{desktop.pk}/', {
        'owner': foreign_user.pk, 'agent_id': 'stolen-identity', 'display_name': 'Renamed',
    }, format='json')
    assert response.status_code == 200
    desktop.refresh_from_db()
    assert desktop.owner_id == user.pk
    assert desktop.agent_id == 'owned-desktop'
    assert desktop.display_name == 'Renamed'


@pytest.mark.parametrize('identity', ['anonymous', 'foreign', 'owner'])
def test_desktop_websocket_checks_ownership(desktop, user, foreign_user, identity):
    viewer = user if identity == 'owner' else foreign_user if identity == 'foreign' else AnonymousUser()

    async def scenario():
        client = WebsocketCommunicator(DesktopAgentConsumer.as_asgi(), '/')
        client.scope.update(user=viewer, url_route={'kwargs': {'agent_id': desktop.agent_id}})
        connected, code = await client.connect()
        try:
            assert connected is (identity == 'owner')
            if not connected:
                assert code == (4401 if identity == 'anonymous' else 4403)
        finally:
            await client.disconnect()

    async_to_sync(scenario)()


def test_agent_result_cannot_update_foreign_training(desktop, user, foreign_user):
    job = TrainingJob.objects.create(created_by=foreign_user, status='running')

    async def scenario():
        client = WebsocketCommunicator(DesktopAgentConsumer.as_asgi(), '/')
        client.scope.update(user=user, url_route={'kwargs': {'agent_id': desktop.agent_id}})
        assert (await client.connect())[0]
        await client.receive_json_from()
        await client.send_json_to({'type': 'training_complete', 'jobId': str(job.pk),
                                   'result': {'success': True}})
        await client.send_json_to({'type': 'status_report'})
        await client.receive_nothing(timeout=0.05)
        await client.disconnect()

    async_to_sync(scenario)()
    job.refresh_from_db()
    assert job.status == 'running'


@pytest.mark.parametrize('config', [[], 'invalid', {'jobId': 'bad/group'}, {'jobId': 'x' * 100}])
def test_dispatch_rejects_invalid_configuration_without_changing_device(desktop, user, config):
    response = authenticated(user).post(f'{DESKTOP_URL}dispatch_training/', {
        'agent_id': desktop.agent_id, 'job_config': config,
    }, format='json')
    assert response.status_code == 400
    desktop.refresh_from_db()
    assert desktop.status == 'online'


def test_dispatch_does_not_bind_another_users_job(desktop, user, foreign_user):
    job = TrainingJob.objects.create(created_by=foreign_user)
    response = authenticated(user).post(f'{DESKTOP_URL}dispatch_training/', {
        'agent_id': desktop.agent_id, 'job_config': {'jobId': str(job.pk)},
    }, format='json')
    assert response.status_code == 404
    job.refresh_from_db()
    assert DESKTOP_AGENT_CONFIG_KEY not in job.config


def test_rest_creation_always_uses_logged_in_owner(user, foreign_user):
    response = authenticated(user).post(DESKTOP_URL, {
        'agent_id': 'created-via-crud', 'owner': foreign_user.pk,
    }, format='json')
    assert response.status_code == 201
    assert DesktopAgent.objects.get(agent_id='created-via-crud').owner_id == user.pk


def test_heartbeat_rejects_unknown_status(desktop, user):
    response = authenticated(user).post(f'{DESKTOP_URL}heartbeat/', {
        'agent_id': desktop.agent_id, 'status': 'invented',
    }, format='json')
    assert response.status_code == 400


def test_electron_authorization_header_authenticates_real_websocket(desktop, user):
    token = generate_tokens(user)['access']

    async def scenario():
        client = WebsocketCommunicator(JWTAuthMiddlewareStack(DesktopAgentConsumer.as_asgi()), '/',
                                       headers=[(b'authorization', f'Bearer {token}'.encode())])
        client.scope['url_route'] = {'kwargs': {'agent_id': desktop.agent_id}}
        assert (await client.connect())[0]
        assert (await client.receive_json_from())['type'] == 'connected'
        await client.disconnect()

    async_to_sync(scenario)()


def test_assigned_desktop_dispatch_and_result_reach_training_subscriber(desktop, user):
    client = authenticated(user)

    async def scenario():
        device = WebsocketCommunicator(DesktopAgentConsumer.as_asgi(), '/')
        device.scope.update(user=user, url_route={'kwargs': {'agent_id': desktop.agent_id}})
        assert (await device.connect())[0]
        await device.receive_json_from()
        response = await database_sync_to_async(client.post)(f'{DESKTOP_URL}dispatch_training/', {
            'agent_id': desktop.agent_id, 'job_config': {'jobId': 'manual-fixture'},
        }, format='json')
        assert response.status_code == 200
        command = await device.receive_json_from()
        assert command['payload']['job_config']['jobId'] == 'manual-fixture'
        job_id = response.data['job_id']
        subscriber = WebsocketCommunicator(TrainingConsumer.as_asgi(), '/')
        subscriber.scope.update(user=user, url_route={'kwargs': {'job_id': job_id}})
        assert (await subscriber.connect())[0]
        await subscriber.receive_json_from()
        await device.send_json_to({'type': 'training_complete', 'jobId': 'manual-fixture',
                                   'success': True, 'result': {'final_metrics': {'mAP50': 0.9}}})
        event = await subscriber.receive_json_from()
        assert event['type'] == 'training_complete'
        await subscriber.disconnect()
        await device.disconnect()
        return job_id

    job = TrainingJob.objects.get(pk=async_to_sync(scenario)())
    assert job.status == 'completed'
    assert job.current_metric == 0.9
    assert job.config[DESKTOP_AGENT_CONFIG_KEY] == desktop.agent_id


def test_another_owned_device_cannot_report_an_unassigned_job(desktop, user):
    from agents.desktop_jobs import apply_training_event
    job = TrainingJob.objects.create(created_by=user, status='running',
                                     config={DESKTOP_AGENT_CONFIG_KEY: 'different-device'})
    assert apply_training_event(user, desktop.agent_id, {
        'type': 'training_complete', 'jobId': str(job.pk), 'result': {'success': True},
    }) is None
    job.refresh_from_db()
    assert job.status == 'running'


def test_desktop_late_success_preserves_cancelled_state(desktop, user):
    from agents.desktop_jobs import apply_training_event
    job = TrainingJob.objects.create(created_by=user, status='cancelled',
                                     config={DESKTOP_AGENT_CONFIG_KEY: desktop.agent_id})
    assert apply_training_event(user, desktop.agent_id, {
        'type': 'training_complete', 'jobId': str(job.pk), 'result': {'success': True},
    }) is None
    job.refresh_from_db()
    assert job.status == 'cancelled'


def test_duplicate_crud_registration_has_a_controlled_response(desktop, user):
    response = authenticated(user).post(DESKTOP_URL, {'agent_id': desktop.agent_id}, format='json')
    assert response.status_code == 200
    assert DesktopAgent.objects.filter(agent_id=desktop.agent_id).count() == 1


def test_failed_dispatch_releases_device_and_marks_job_failed(desktop, user):
    layer = type('UnavailableLayer', (), {'group_send': AsyncMock(side_effect=RuntimeError('channel unavailable'))})()
    with patch('channels.layers.get_channel_layer', return_value=layer):
        response = authenticated(user).post(f'{DESKTOP_URL}dispatch_training/', {
            'agent_id': desktop.agent_id, 'job_config': {'jobId': 'failed-dispatch'},
        }, format='json')
    assert response.status_code == 503
    desktop.refresh_from_db()
    assert desktop.status == 'online'
    assert TrainingJob.objects.get(job_id='failed-dispatch').status == 'failed'


def test_dispatch_reserves_device_even_if_a_heartbeat_reports_online(desktop, user):
    client = authenticated(user)
    request = {'agent_id': desktop.agent_id, 'job_config': {'jobId': 'reserved-first'}}
    assert client.post(f'{DESKTOP_URL}dispatch_training/', request, format='json').status_code == 200
    DesktopAgent.objects.filter(pk=desktop.pk).update(status='online')
    request['job_config']['jobId'] = 'reserved-second'
    assert client.post(f'{DESKTOP_URL}dispatch_training/', request, format='json').status_code == 400
    assert not TrainingJob.objects.filter(job_id='reserved-second').exists()


def test_deleted_device_socket_cannot_receive_replacement_device_commands(desktop, user, foreign_user):
    async def scenario():
        device = WebsocketCommunicator(DesktopAgentConsumer.as_asgi(), '/')
        device.scope.update(user=user, url_route={'kwargs': {'agent_id': desktop.agent_id}})
        assert (await device.connect())[0]
        await device.receive_json_from()
        original_pk = desktop.pk
        await database_sync_to_async(DesktopAgent.objects.filter(pk=original_pk).delete)()
        await database_sync_to_async(DesktopAgent.objects.create)(agent_id=desktop.agent_id, owner=foreign_user)
        await get_channel_layer().group_send(desktop_agent_group(original_pk), {
            'type': 'training_command', 'job_config': {'private': 'replacement-user-data'},
        })
        assert await device.receive_output() == {'type': 'websocket.close', 'code': 4403}
        await device.disconnect()

    async_to_sync(scenario)()


def test_cancel_request_blocks_late_success_until_device_acknowledges(desktop, user):
    from agents.desktop_jobs import apply_training_event
    job = TrainingJob.objects.create(created_by=user, status='running', config={
        DESKTOP_AGENT_CONFIG_KEY: desktop.agent_id,
        DESKTOP_AGENT_RECORD_CONFIG_KEY: str(desktop.pk), CANCEL_REQUEST_KEY: 'requested',
    })
    assert apply_training_event(user, desktop.agent_id, {
        'type': 'training_complete', 'jobId': str(job.pk), 'success': True,
    }, agent_record_id=desktop.pk) is None
    job.refresh_from_db()
    assert job.status == 'running'
    assert apply_training_event(user, desktop.agent_id, {
        'type': 'training_cancelled', 'jobId': str(job.pk),
    }, agent_record_id=desktop.pk)
    job.refresh_from_db()
    assert job.status == 'cancelled'
