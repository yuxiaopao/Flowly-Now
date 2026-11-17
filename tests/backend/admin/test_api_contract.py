"""Real HTTP contracts replacing orphaned mock-only admin API client tests.

Admin API keys support listing/revocation, not creation; usage uses ``days``.
Only external health probes are stubbed, while routing, permissions and ORM run.
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from admin.constants import DEFAULT_SYSTEM_SETTINGS
from admin.models import SystemSetting
from agents.models import Agent
from gateway.models import UserAPIKey
from users.models import User
from workflows.models import Workflow

BASE_URL = '/api/v1/admin/'
pytestmark = pytest.mark.django_db


@pytest.fixture
def client(admin_user):
    api = APIClient()
    api.force_authenticate(admin_user)
    return api


@pytest.fixture
def key(user):
    return UserAPIKey.objects.create(user=user, provider='openai', name='contract key', api_key='test-only-unused-key')


def payload(response, expected_status=200):
    assert response.status_code == expected_status, response.content
    if expected_status == 204:
        return None
    result = response.json()
    assert result['code'] == expected_status
    return result['data']


def test_user_list_returns_pagination_and_real_users(client, user):
    data = payload(client.get(f'{BASE_URL}users/'))
    assert data['total'] == User.objects.count()
    assert user.pk in {item['id'] for item in data['results']}
    assert data['page'] == 1


def test_user_search_filters_real_queryset(client, user):
    data = payload(client.get(f'{BASE_URL}users/', {'search': user.username}))
    assert [row['id'] for row in data['results']] == [user.pk]
    assert data['total'] == 1


def test_user_detail_returns_requested_user(client, user):
    data = payload(client.get(f'{BASE_URL}users/{user.pk}/'))
    assert data['id'] == user.pk
    assert data['username'] == user.username
    assert 'password' not in data


def test_user_patch_persists_role_change(client, user):
    data = payload(client.patch(f'{BASE_URL}users/{user.pk}/', {'role': 'admin'}, format='json'))
    user.refresh_from_db()
    assert data['role'] == 'admin'
    assert user.role == 'admin'


def test_user_delete_removes_selected_non_admin(client, user):
    payload(client.delete(f'{BASE_URL}users/{user.pk}/'), 204)
    assert not User.objects.filter(pk=user.pk).exists()


def test_workflow_list_returns_real_workflows(client, workflow):
    data = payload(client.get(f'{BASE_URL}workflows/'))
    assert data['total'] == Workflow.objects.count()
    assert str(workflow.pk) in {row['id'] for row in data['results']}


def test_workflow_list_filters_requested_status(client, workflow):
    published = Workflow.objects.create(owner=workflow.owner, name='Published', status='published')
    data = payload(client.get(f'{BASE_URL}workflows/', {'status': 'published'}))
    assert [row['id'] for row in data['results']] == [str(published.pk)]
    assert data['total'] == 1


def test_workflow_detail_uses_complete_real_serializer(client, workflow_with_nodes):
    data = payload(client.get(f'{BASE_URL}workflows/{workflow_with_nodes.pk}/'))
    assert data['id'] == str(workflow_with_nodes.pk)
    assert len(data['nodes']) == 3
    assert len(data['edges']) == 2


def test_agent_list_returns_owned_records_to_superuser(client, user):
    agent = Agent.objects.create(owner=user, name='Contract agent')
    data = payload(client.get(f'{BASE_URL}agents/'))
    assert data['total'] == 1
    assert data['results'][0]['id'] == str(agent.pk)
    assert data['results'][0]['owner_name'] == user.username


def test_usage_returns_real_model_counts(client, workflow):
    data = payload(client.get(f'{BASE_URL}usage/'))
    assert data['period_days'] == 30
    assert data['users']['total'] == User.objects.count()
    assert data['workflows']['total'] == Workflow.objects.count()


def test_usage_days_filters_time_window_without_losing_total(client, workflow):
    old = Workflow.objects.create(owner=workflow.owner, name='Old')
    Workflow.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=8))
    recent = payload(client.get(f'{BASE_URL}usage/', {'days': 7}))
    broad = payload(client.get(f'{BASE_URL}usage/', {'days': 30}))
    assert recent['period_days'] == 7
    assert recent['workflows'] == {'total': 2, 'new': 1}
    assert broad['workflows'] == {'total': 2, 'new': 2}


def test_health_checks_real_database_and_reports_external_probe_results(client):
    with patch('redis.Redis.ping', return_value=True), \
            patch('celery.app.control.Inspect.stats', return_value={'worker': {'pool': {}}}):
        data = payload(client.get(f'{BASE_URL}health/'))
    assert data['api'] is True
    assert data['database'] is True
    assert data['redis'] is True
    assert data['celery'] is True
    assert data['timestamp']


def test_settings_get_merges_persisted_values_with_defaults(client):
    SystemSetting.objects.create(key='site_name', value='Contract site')
    data = payload(client.get(f'{BASE_URL}settings/'))
    assert data['site_name'] == 'Contract site'
    assert data['default_execution_limit'] == DEFAULT_SYSTEM_SETTINGS['default_execution_limit']


def test_settings_patch_persists_supported_key(client, admin_user):
    data = payload(client.patch(f'{BASE_URL}settings/', {'default_execution_limit': 200}, format='json'))
    setting = SystemSetting.objects.get(key='default_execution_limit')
    assert setting.value == 200
    assert setting.updated_by == admin_user
    assert data['settings']['default_execution_limit'] == 200


def test_api_key_list_omits_secret_values(client, key):
    data = payload(client.get(f'{BASE_URL}api-keys/'))
    assert data['total'] == 1
    assert data['results'][0]['id'] == str(key.pk)
    assert 'api_key' not in data['results'][0]
    assert key.api_key not in str(data)


def test_api_key_create_is_explicitly_unsupported(client):
    count = UserAPIKey.objects.count()
    response = client.post(f'{BASE_URL}api-keys/', {'name': 'unsupported', 'scopes': ['read']}, format='json')
    assert response.status_code == 405
    assert UserAPIKey.objects.count() == count


def test_api_key_revoke_deactivates_real_record(client, key):
    assert payload(client.post(f'{BASE_URL}api-keys/{key.pk}/revoke/'))['success'] is True
    key.refresh_from_db()
    assert key.is_active is False


def test_unknown_setting_is_rejected_without_partial_write(client):
    response = client.patch(f'{BASE_URL}settings/', {'max_executions_per_user': 200}, format='json')
    assert response.status_code == 400
    assert not SystemSetting.objects.filter(key='max_executions_per_user').exists()


@pytest.mark.parametrize('route', ['users/', 'workflows/', 'agents/', 'usage/', 'settings/', 'api-keys/'])
def test_regular_user_cannot_read_admin_resources(user, route):
    client = APIClient()
    client.force_authenticate(user)
    assert client.get(f'{BASE_URL}{route}').status_code == 403


def test_health_exposes_failed_dependencies_without_failing_http_contract(client):
    with patch('redis.Redis.ping', side_effect=ConnectionError('offline')), \
            patch('celery.app.control.Inspect.stats', return_value=None):
        data = payload(client.get(f'{BASE_URL}health/'))
    assert data['database'] is True
    assert data['redis'] is False
    assert data['celery'] is False
