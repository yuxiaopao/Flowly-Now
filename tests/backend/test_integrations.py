"""Connector contracts through real serializers, persistence and HTTP responses."""
import hashlib
import hmac
import json
import socket
from unittest.mock import patch

import httpx
import pytest
from django.test import override_settings
from django.utils import timezone

from integrations.catalog import CATALOG, CONNECTORS
from integrations.models import Integration, IntegrationDelivery
from integrations.services import ConnectorError, _request, _webhook_request, run_check, deliver
from integrations.tasks import deliver_integration_event

pytestmark = pytest.mark.django_db
URL = '/api/v1/integrations/integrations/'
WEBHOOK_URLS = {
    'feishu': 'https://open.feishu.cn/open-apis/bot/v2/hook/test',
    'dingtalk': 'https://oapi.dingtalk.com/robot/send?access_token=test',
    'wechat_work': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test',
    'slack': 'https://hooks.slack.com/services/test',
    'discord': 'https://discord.com/api/webhooks/test',
    'microsoft_teams': 'https://test.logic.azure.com/workflows/test',
    'zapier': 'https://hooks.zapier.com/hooks/catch/test',
    'make': 'https://hook.eu2.make.com/test',
    'n8n': 'https://n8n.example.org/webhook/test',
    'powerautomate': 'https://test.logic.azure.com/workflows/test',
    'custom': 'https://example.org/webhook',
}


def values(kind):
    config, secrets = {'events': []}, {}
    for field in CONNECTORS[kind]['fields']:
        value = {'webhook_url': WEBHOOK_URLS.get(kind), 'token': '123456:testing_token' if kind == 'telegram' else 'secret_token',
                 'secret': '', 'keyword': '', 'chat_id': '123', 'range': 'Sheet1!A1:B20', 'spreadsheet_id': 'sheet_id'}.get(field['key'], '')
        (secrets if field['secret'] else config)[field['key']] = value
    return config, secrets


def connection(user, kind='custom', verified=False):
    config, secrets = values(kind)
    item = Integration(user=user, name=kind, integration_type=kind, config=config,
                       is_connected=verified, verification_status='success' if verified else 'untested',
                       last_checked_at=timezone.now() if verified else None)
    item.set_secrets(secrets)
    item.save()
    return item


def create(client, kind='custom'):
    config, secrets = values(kind)
    return client.post(URL, {'name': kind, 'integration_type': kind, 'config': config, 'credentials': secrets}, format='json')


def success_body(kind, read=False):
    if kind == 'slack': return 'ok'
    if kind == 'feishu': return '{"code":0}'
    if kind in ('wechat_work', 'dingtalk'): return '{"errcode":0}'
    if kind == 'telegram': return '{"ok":true}'
    if CONNECTORS[kind]['mode'] != 'api': return '{"accepted":true}'
    if not read:
        return json.dumps({'google_sheets': {'spreadsheetId': 'sheet_id'}, 'google_drive': {'user': {'displayName': 'tester'}}}.get(kind, {'id': 'test_user'}))
    return json.dumps({'github': [{'id': 1, 'full_name': 'org/repo'}], 'gitlab': [{'id': 1, 'name': 'project'}],
                       'notion': {'results': [{'id': 'p1', 'title': [{'plain_text': 'Page'}]}]},
                       'airtable': {'bases': [{'id': 'b1', 'name': 'Base'}]},
                       'google_drive': {'files': [{'id': 'f1', 'name': 'File'}]},
                       'google_sheets': {'range': 'Sheet1!A1:B20', 'values': [['name', 'value']]}}[kind])


def test_catalog_is_available_without_seed_and_requires_login(authenticated_client, api_client):
    assert api_client.get(URL + 'available/').status_code == 401
    data = authenticated_client.get(URL + 'available/').data
    assert len(data) == 18
    assert len({row['id'] for row in data}) == len(data)
    assert all(row['fields'] and row['documentation_url'].startswith('https://') for row in data)
    assert all('usage_count' not in row for row in data)


@pytest.mark.parametrize('kind', list(CONNECTORS))
def test_create_test_disconnect_lifecycle(authenticated_client, kind):
    response = create(authenticated_client, kind)
    assert response.status_code == 201, response.data
    data = response.data
    assert not data['is_connected'] and data['verification_status'] == 'untested'
    assert 'credentials' not in data and 'secret_token' not in json.dumps(data)
    item = Integration.objects.get(pk=data['id'])
    assert 'encrypted' in item.credentials
    with patch('integrations.services._request', return_value=(200, success_body(kind))) as request:
        tested = authenticated_client.post(f'{URL}{item.pk}/test/').data
        assert tested['result']['success'], tested
        assert tested['integration']['verification_status'] == 'success'
        assert request.call_count == 1
    disconnected = authenticated_client.post(f'{URL}{item.pk}/disconnect/').data
    assert not disconnected['is_active'] and not disconnected['is_connected']
    assert authenticated_client.post(f'{URL}{item.pk}/sync/').status_code == 400


@pytest.mark.parametrize('kind', [row['id'] for row in CATALOG if row['mode'] == 'api'])
def test_real_resource_pull_and_no_secret_echo(user, kind):
    item = connection(user, kind, True)
    with patch('integrations.services._request', return_value=(200, success_body(kind, True))) as request:
        result = run_check(item, read=True)
    assert result['success'], result
    assert result['data']['count'] == 1
    assert item.total_syncs == 1 and item.last_sync_at
    assert 'secret_token' not in json.dumps(item.last_result)
    assert request.call_args.args[0] in ('GET', 'POST')


@pytest.mark.parametrize('status', [301, 400, 401, 403, 404, 429, 500])
def test_http_failure_never_sets_connected(user, status):
    item = connection(user, 'custom', True)
    with patch('integrations.services._request', return_value=(status, 'secret_token')):
        result = run_check(item)
    assert not result['success'] and not item.is_connected
    assert item.verification_status == 'failed'
    assert 'secret_token' not in item.last_error


@pytest.mark.parametrize('kind,body', [('feishu', '{"code":19021}'), ('dingtalk', '{"errcode":310000}'),
                                    ('wechat_work', '{"errcode":93000}'), ('telegram', '{"ok":false}'),
                                    ('slack', 'invalid_token'), ('github', '{}'), ('google_drive', '<html>login</html>')])
def test_http_200_business_errors_fail(user, kind, body):
    item = connection(user, kind)
    with patch('integrations.services._request', return_value=(200, body)):
        result = run_check(item)
    assert not result['success'] and not item.is_connected


def test_credentials_preserved_and_configuration_change_invalidates(authenticated_client):
    item_id = create(authenticated_client).data['id']
    item = Integration.objects.get(pk=item_id)
    with patch('integrations.services._request', return_value=(200, '{}')):
        authenticated_client.post(f'{URL}{item_id}/test/')
    edited = authenticated_client.patch(f'{URL}{item_id}/', {'config': {'events': ['execution.failed']}}, format='json')
    assert edited.status_code == 200, edited.data
    assert edited.data['verification_status'] == 'untested'
    item.refresh_from_db()
    assert item.get_secrets()['webhook_url'] == WEBHOOK_URLS['custom']
    assert not item.is_connected and item.last_checked_at is None


def test_edit_keeps_encrypted_legacy_archive(user):
    item = connection(user)
    item.credentials['legacy_encrypted'] = 'archived-ciphertext'
    item.set_secrets({'webhook_url': WEBHOOK_URLS['custom']})
    assert item.credentials['legacy_encrypted'] == 'archived-ciphertext'
    assert item.get_secrets() == {'webhook_url': WEBHOOK_URLS['custom']}
    item.set_secrets({})
    assert item.get_secrets() == {}
    assert item.credentials == {'legacy_encrypted': 'archived-ciphertext'}


def test_corrupt_credentials_require_replacement_and_can_be_recovered(authenticated_client):
    item_id = create(authenticated_client).data['id']
    Integration.objects.filter(pk=item_id).update(credentials={'encrypted': 'not-decryptable'})
    assert authenticated_client.patch(f'{URL}{item_id}/', {'name': 'rename'}, format='json').status_code == 400
    restored = authenticated_client.patch(f'{URL}{item_id}/', {'credentials': {'webhook_url': WEBHOOK_URLS['custom']}}, format='json')
    assert restored.status_code == 200
    assert restored.data['verification_status'] == 'untested'
    assert Integration.objects.get(pk=item_id).get_secrets()['webhook_url'] == WEBHOOK_URLS['custom']


@pytest.mark.parametrize('payload', [
    {'name': 'bad', 'integration_type': 'unknown'},
    {'name': 'bad', 'integration_type': 'slack', 'credentials': {'webhook_url': 'https://example.org/hooks'}},
    {'name': 'bad', 'integration_type': 'custom', 'credentials': {'webhook_url': 'file:///etc/passwd'}},
    {'name': 'bad', 'integration_type': 'custom', 'config': {'webhook_url': 'https://example.org'}},
    {'name': 'bad', 'integration_type': 'custom', 'config': [], 'credentials': []},
    {'name': 'bad', 'integration_type': 'custom', 'config': {'events': [{}]}, 'credentials': {'webhook_url': 'https://example.org'}},
])
def test_invalid_config_is_rejected(authenticated_client, payload):
    assert authenticated_client.post(URL, payload, format='json').status_code == 400
    assert not Integration.objects.exists()


def test_cannot_forge_connected_or_access_another_users_connection(authenticated_client, admin_user):
    other = connection(admin_user)
    assert authenticated_client.get(f'{URL}{other.pk}/').status_code == 404
    assert authenticated_client.post(f'{URL}{other.pk}/test/').status_code == 404
    assert authenticated_client.get(f'{URL}{other.pk}/deliveries/').status_code == 404
    record = create(authenticated_client).data
    forged = authenticated_client.patch(f'{URL}{record["id"]}/', {'is_connected': True, 'verification_status': 'success'}, format='json')
    assert not forged.data['is_connected']


def test_stale_response_cannot_reconnect_after_disconnect(user):
    item = connection(user)
    def request(*args, **kwargs):
        Integration.objects.filter(pk=item.pk).update(is_active=False, updated_at=timezone.now(), verification_status='disconnected')
        return 200, '{}'
    with patch('integrations.services._request', side_effect=request):
        result = run_check(item)
    assert not result['success'] and not item.is_connected and not item.is_active


def test_custom_signature_covers_exact_sent_bytes():
    _, _, headers, _, body = _webhook_request('custom', {'webhook_url': WEBHOOK_URLS['custom'], 'secret': 'sign-key'}, {'event': 'test', 'message': '中文'})
    assert headers['X-Webhook-Signature'] == hmac.new(b'sign-key', body, hashlib.sha256).hexdigest()


def test_delivery_log_and_event_id_are_idempotent(user):
    item = connection(user, verified=True)
    with patch('integrations.services._request', return_value=(200, '{}')) as request:
        first = deliver(item, event_key='one')
        second = deliver(item, event_key='one')
    assert first.pk == second.pk and first.status == 'success' and request.call_count == 1
    assert IntegrationDelivery.objects.count() == 1 and item.total_syncs == 1


def test_execution_outbox_owner_scope_and_no_output_leak(user, admin_user, workflow, django_capture_on_commit_callbacks):
    from workflows.models import WorkflowExecution
    owner = connection(user, verified=True)
    other = connection(admin_user, verified=True)
    for item in (owner, other):
        item.config['events'] = ['execution.completed']; item.save()
    with patch('integrations.signals.enqueue_delivery') as enqueue, django_capture_on_commit_callbacks(execute=True):
        execution = WorkflowExecution.objects.create(workflow=workflow, version=1, status='pending', input_data={'secret': 'private'})
        execution.mark_completed({'secret': 'private-output'})
        execution.save()
    records = IntegrationDelivery.objects.all()
    assert len(records) == 1 and records[0].integration_id == owner.pk
    assert 'private' not in json.dumps(records[0].payload)
    assert enqueue.call_count == 1
    owner.is_active = False; owner.save()
    with patch('integrations.services._request') as request:
        assert deliver_integration_event(records[0].pk)['status'] == 'cancelled'
        request.assert_not_called()


def test_private_network_and_redirects_are_not_followed():
    with patch('integrations.services.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]):
        with pytest.raises(ConnectorError, match='内网'):
            _request('GET', 'https://example.org')


def test_http_transport_timeout_is_actionable():
    with override_settings(INTEGRATIONS_ALLOWED_PRIVATE_HOSTS=['localhost']), patch('integrations.services.httpx.Client.send', side_effect=httpx.ReadTimeout('secret_url')):
        with pytest.raises(ConnectorError, match='超时') as exc:
            _request('GET', 'http://localhost')
    assert 'secret_url' not in str(exc.value)


def test_trusted_proxy_resolves_official_host_without_leaking_tokens():
    response = httpx.Response(401, json={'message': 'requires authentication'})
    with override_settings(INTEGRATIONS_HTTP_PROXY='http://127.0.0.1:9999'), \
            patch('integrations.services.socket.getaddrinfo') as dns, \
            patch('integrations.services.httpx.Client.send', return_value=response) as send:
        status, _ = _request('GET', 'https://api.github.com/user')
        assert status == 401
        assert send.call_args.args[0].url.host == 'api.github.com'
        dns.assert_not_called()


@pytest.mark.parametrize('host', ['custom.example', 'evil-api.github.com', 'api.github.com.evil.example'])
def test_proxy_does_not_bypass_private_network_checks_for_custom_hosts(host):
    with override_settings(INTEGRATIONS_HTTP_PROXY='http://127.0.0.1:9999'), \
            patch('integrations.services.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('198.18.0.1', 443))]):
        with pytest.raises(ConnectorError, match='内网'):
            _request('GET', f'https://{host}/webhook')
