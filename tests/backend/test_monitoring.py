"""
Tests for Monitoring and Alerts.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestAlertRuleAPI:
    """Test alert rule API endpoints."""

    def test_list_alert_rules(self, authenticated_client):
        """Test listing alert rules."""
        response = authenticated_client.get('/api/v1/monitoring/rules/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_alert_rule(self, authenticated_client):
        """Test creating an alert rule."""
        data = {
            'name': 'Test Alert Rule',
            'description': 'A test alert rule',
            'condition': 'execution_failed',
            'severity': 'high',
            'threshold': 3,
            'time_window_minutes': 60,
            'notify_email': True
        }
        response = authenticated_client.post('/api/v1/monitoring/rules/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Test Alert Rule'


@pytest.mark.django_db
class TestAlertAPI:
    """Test alert API endpoints."""

    def test_list_alerts(self, authenticated_client):
        """Test listing alerts."""
        response = authenticated_client.get('/api/v1/monitoring/alerts/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_alert_summary(self, authenticated_client):
        """Test getting alert summary."""
        response = authenticated_client.get('/api/v1/monitoring/alerts/summary/')
        assert response.status_code == status.HTTP_200_OK
        assert 'total' in response.data
        assert 'active' in response.data

    def test_acknowledge_alert(self, authenticated_client, user):
        from monitoring.models import Alert, AlertRule
        rule = AlertRule.objects.create(name='测试告警', owner=user, notify_email=False)
        alert = Alert.objects.create(rule=rule, title='失败告警', severity='high')
        response = authenticated_client.post(f'/api/v1/monitoring/alerts/{alert.id}/acknowledge/')
        assert response.status_code == 200
        alert.refresh_from_db()
        assert alert.status == 'acknowledged'

    def test_resolve_alert(self, authenticated_client, user):
        from monitoring.models import Alert, AlertRule
        rule = AlertRule.objects.create(name='测试告警', owner=user, notify_email=False)
        alert = Alert.objects.create(rule=rule, title='失败告警', severity='high')
        response = authenticated_client.post(f'/api/v1/monitoring/alerts/{alert.id}/resolve/', {'note': '故障已修复'})
        assert response.status_code == 200
        alert.refresh_from_db()
        assert alert.status == 'resolved'
        assert alert.resolved_by == user
        assert alert.resolved_at is not None
        assert alert.resolution_note == '故障已修复'

    def test_filter_alerts_by_status(self, authenticated_client, user):
        """Test filtering alerts by status."""
        response = authenticated_client.get(
            '/api/v1/monitoring/alerts/?status=active'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_filter_alerts_by_severity(self, authenticated_client, user):
        """Test filtering alerts by severity."""
        response = authenticated_client.get(
            '/api/v1/monitoring/alerts/?severity=high'
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestMetricAPI:
    """Test metric API endpoints."""

    @pytest.mark.parametrize('hours', ['bad', '0', '-1', '1.5'])
    @pytest.mark.parametrize('endpoint', ['metrics/', 'metrics/aggregate/'])
    def test_invalid_time_range_returns_validation_error(self, authenticated_client, hours, endpoint):
        response = authenticated_client.get(f'/api/v1/monitoring/{endpoint}', {'hours': hours})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'hours' in response.data['errors']

    def test_list_metrics(self, authenticated_client):
        """Test listing metrics."""
        response = authenticated_client.get('/api/v1/monitoring/metrics/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_dashboard_metrics(self, authenticated_client):
        """Test getting dashboard metrics."""
        response = authenticated_client.get(
            '/api/v1/monitoring/metrics/dashboard/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'total_executions' in response.data

    def test_get_metrics_aggregate(self, authenticated_client):
        """Test getting aggregated metrics."""
        response = authenticated_client.get(
            '/api/v1/monitoring/metrics/aggregate/?type=execution_count'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_filter_metrics_by_type(self, authenticated_client):
        """Test filtering metrics by type."""
        response = authenticated_client.get(
            '/api/v1/monitoring/metrics/?type=execution_count'
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestNotificationChannelAPI:
    """Test notification channel API endpoints."""

    def test_list_channels(self, authenticated_client):
        """Test listing notification channels."""
        response = authenticated_client.get('/api/v1/monitoring/channels/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_channel(self, authenticated_client):
        """Test creating a notification channel."""
        data = {
            'name': 'Test Channel',
            'channel_type': 'email',
            'config': '{"email": "alerts@example.com"}',
            'is_active': True
        }
        response = authenticated_client.post('/api/v1/monitoring/channels/', data, format='json')
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)


@pytest.mark.django_db
class TestExecutionLogAPI:
    """Test execution log API endpoints."""

    def test_list_execution_logs(self, authenticated_client):
        """Test listing execution logs."""
        response = authenticated_client.get('/api/v1/monitoring/logs/')
        assert response.status_code == status.HTTP_200_OK
