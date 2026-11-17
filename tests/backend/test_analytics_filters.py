"""Every analytics block observes the same real owner/time boundary."""
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from gateway.models import APICallLog
from users.models import User
from workflows.models import Workflow, WorkflowExecution

pytestmark = pytest.mark.django_db
BASE = '/api/v1/monitoring/analytics/'
WINDOW = {'start_date': '2026-10-20T00:00:00Z', 'end_date': '2026-10-21T23:59:59Z'}


def execution(owner, day, status):
    workflow = Workflow.objects.create(owner=owner, name=f'workflow-{day}-{status}')
    return WorkflowExecution.objects.create(workflow=workflow, version=1, status=status,
        started_at=datetime(2026, 10, day, 12, tzinfo=timezone.utc), duration_ms=250)


def test_all_blocks_share_explicit_window_and_owner(authenticated_client, user):
    selected = execution(user, 20, 'completed')
    execution(user, 1, 'failed')
    foreign = User.objects.create_user(username='analytics-foreign')
    execution(foreign, 20, 'failed')
    for owner, day, model in ((user, 20, 'selected'), (user, 1, 'old'), (foreign, 20, 'foreign')):
        row = APICallLog.objects.create(user=owner, provider='openai', model=model,
            endpoint='fixture', total_tokens=17, cost=Decimal('1.25'), latency_ms=40)
        APICallLog.objects.filter(pk=row.pk).update(timestamp=datetime(2026, 10, day, 12, tzinfo=timezone.utc))
    overview = authenticated_client.get(BASE + 'overview/', WINDOW)
    assert overview.status_code == 200
    assert overview.data['total_executions'] == 1
    assert overview.data['success_rate'] == 100
    assert overview.data['total_tokens'] == 17
    assert overview.data['total_cost'] == 1.25
    assert overview.data['cost_currency'] is None
    top = authenticated_client.get(BASE + 'top_workflows/', WINDOW)
    assert top.status_code == 200
    assert [str(row['id']) for row in top.data] == [str(selected.workflow_id)]
    recent = authenticated_client.get(BASE + 'recent_executions/', WINDOW)
    assert [str(row['id']) for row in recent.data] == [str(selected.pk)]
    usage = authenticated_client.get(BASE + 'api_usage/', WINDOW)
    assert [row['model'] for row in usage.data] == ['selected']
    trend = authenticated_client.get(BASE + 'execution_trend/', WINDOW)
    assert trend.status_code == 200
    assert len(trend.data) == 1
    assert trend.data[0]['executions'] == 1
    assert trend.data[0]['cost'] == 1.25


def test_empty_measurements_remain_unknown(authenticated_client):
    response = authenticated_client.get(BASE + 'overview/', WINDOW)
    assert response.status_code == 200
    assert response.data['total_executions'] == 0
    for key in ('total_tokens', 'total_cost', 'avg_latency', 'success_rate', 'executions_trend'):
        assert response.data[key] is None


@pytest.mark.parametrize('params', [
    {'days': 'bad'}, {'days': 0}, {'days': 367}, {'period': 'bad'}, {'period': '0d'},
    {'start_date': 'bad', 'end_date': '2026-10-21'}, {'start_date': '2026-10-20'},
    {'start_date': '2026-10-21T00:00:00Z', 'end_date': '2026-10-20T00:00:00Z'},
])
def test_invalid_periods_fail_with_validation_not_server_error(authenticated_client, params):
    for endpoint in ('overview', 'top_workflows', 'recent_executions', 'api_usage', 'execution_trend'):
        assert authenticated_client.get(f'{BASE}{endpoint}/', params).status_code == 400


@pytest.mark.parametrize('limit', ['bad', 0, -1, 101])
def test_list_limits_are_bounded(authenticated_client, limit):
    for endpoint in ('top_workflows', 'recent_executions'):
        assert authenticated_client.get(f'{BASE}{endpoint}/', {**WINDOW, 'limit': limit}).status_code == 400
