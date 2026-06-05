"""
Integration serializers.
"""

from rest_framework import serializers
from .models import Webhook, WebhookDelivery, Integration, IntegrationTemplate


class WebhookDeliverySerializer(serializers.ModelSerializer):
    """Serializer for webhook deliveries."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            'id', 'event', 'event_id', 'status', 'status_display',
            'status_code', 'error_message', 'attempt',
            'duration_ms', 'created_at', 'sent_at', 'completed_at'
        ]


class WebhookSerializer(serializers.ModelSerializer):
    """Serializer for webhooks."""

    events_display = serializers.SerializerMethodField()
    success_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Webhook
        fields = [
            'id', 'name', 'description', 'url', 'events', 'events_display',
            'headers', 'is_active', 'is_verified', 'retry_count',
            'timeout_seconds', 'content_type', 'total_deliveries',
            'successful_deliveries', 'failed_deliveries', 'success_rate',
            'workflow_filter', 'tag_filter', 'created_at', 'updated_at',
            'last_triggered_at'
        ]

    def get_events_display(self, obj):
        return [Webhook._meta.get_field('events').choices.get(e, e) for e in obj.events]


class WebhookCreateSerializer(serializers.Serializer):
    """Serializer for creating webhooks."""

    name = serializers.CharField(max_length=200)
    url = serializers.URLField(max_length=2000)
    events = serializers.ListField(child=serializers.CharField())
    secret = serializers.CharField(max_length=500, required=False, allow_blank=True)
    headers = serializers.DictField(required=False, default=dict)
    retry_count = serializers.IntegerField(min_value=0, max_value=10, default=3)
    timeout_seconds = serializers.IntegerField(min_value=5, max_value=300, default=30)


class IntegrationSerializer(serializers.ModelSerializer):
    """Serializer for integrations."""

    integration_type_display = serializers.CharField(
        source='get_integration_type_display',
        read_only=True
    )

    class Meta:
        model = Integration
        fields = [
            'id', 'name', 'integration_type', 'integration_type_display',
            'is_active', 'is_connected', 'last_sync_at', 'sync_status',
            'total_syncs', 'failed_syncs', 'created_at', 'updated_at'
        ]


class IntegrationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for integration templates."""

    integration_type_display = serializers.CharField(
        source='get_integration_type_display',
        read_only=True
    )

    class Meta:
        model = IntegrationTemplate
        fields = [
            'id', 'name', 'description', 'integration_type',
            'integration_type_display', 'category', 'icon', 'color',
            'config_template', 'required_config', 'optional_config',
            'trigger_events', 'supported_actions', 'documentation_url',
            'setup_guide', 'is_active', 'is_featured', 'usage_count'
        ]
