"""
Serializers for monitoring app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ExecutionLog, AlertRule, Alert, Metric, NotificationChannel, Notification

User = get_user_model()


class MetricQuerySerializer(serializers.Serializer):
    hours = serializers.IntegerField(required=False, min_value=1, error_messages={
        'invalid': '查询小时数必须是整数', 'min_value': '查询小时数必须大于零',
    })


class ExecutionLogSerializer(serializers.ModelSerializer):
    """Serializer for ExecutionLog."""

    class Meta:
        model = ExecutionLog
        fields = [
            'id', 'workflow_execution', 'node_id', 'node_name',
            'level', 'message', 'details', 'timestamp'
        ]


class AlertRuleSerializer(serializers.ModelSerializer):
    """Serializer for AlertRule."""

    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    enabled = serializers.BooleanField(source='is_active', required=False)

    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'condition', 'condition_display',
            'severity', 'severity_display', 'threshold', 'time_window_minutes',
            'notify_email', 'notify_webhook', 'webhook_url',
            'is_active', 'enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AlertRuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating AlertRule."""

    id = serializers.UUIDField(read_only=True)
    enabled = serializers.BooleanField(source='is_active', required=False, default=True)

    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'condition', 'severity',
            'threshold', 'time_window_minutes',
            'notify_email', 'notify_webhook', 'webhook_url',
            'enabled'
        ]


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert."""

    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.username', read_only=True)

    class Meta:
        model = Alert
        fields = [
            'id', 'rule', 'severity', 'severity_display',
            'title', 'message',
            'triggered_by_type', 'triggered_by_id',
            'status', 'status_display',
            'resolved_by', 'resolved_by_name',
            'resolved_at', 'resolution_note',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AlertCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Alert."""

    class Meta:
        model = Alert
        fields = [
            'rule', 'severity', 'title', 'message',
            'triggered_by_type', 'triggered_by_id'
        ]


class MetricSerializer(serializers.ModelSerializer):
    """Serializer for Metric."""

    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)

    class Meta:
        model = Metric
        fields = [
            'id', 'metric_type', 'metric_type_display',
            'value', 'unit', 'tags',
            'user', 'workflow',
            'timestamp'
        ]


class MetricAggregateSerializer(serializers.Serializer):
    """Serializer for aggregated metrics."""

    metric_type = serializers.CharField()
    value = serializers.FloatField()
    period = serializers.CharField()
    count = serializers.IntegerField()


class NotificationChannelSerializer(serializers.ModelSerializer):
    """Serializer for NotificationChannel."""

    channel_type_display = serializers.CharField(source='get_channel_type_display', read_only=True)

    class Meta:
        model = NotificationChannel
        fields = [
            'id', 'name', 'channel_type', 'channel_type_display',
            'config', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationChannelCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating NotificationChannel."""

    class Meta:
        model = NotificationChannel
        fields = ['name', 'channel_type', 'config', 'is_active']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification."""

    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'content', 'notification_type', 'type_display',
            'is_read', 'link', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
