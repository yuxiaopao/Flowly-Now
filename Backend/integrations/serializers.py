"""
Integration serializers.
"""

from rest_framework import serializers
from .models import Webhook, WebhookDelivery, Integration, IntegrationTemplate, IntegrationDelivery
from .catalog import CONNECTORS
from .services import validate_config, ConnectorError


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
    config = serializers.JSONField(required=False)
    credentials = serializers.JSONField(write_only=True, required=False)
    configured_fields = serializers.SerializerMethodField()

    class Meta:
        model = Integration
        fields = [
            'id', 'name', 'integration_type', 'integration_type_display',
            'is_active', 'is_connected', 'last_sync_at', 'sync_status',
            'total_syncs', 'failed_syncs', 'created_at', 'updated_at',
            'config', 'credentials', 'configured_fields', 'last_checked_at',
            'verification_status', 'last_error', 'last_result'
        ]
        read_only_fields = ['is_active', 'is_connected', 'last_sync_at', 'sync_status',
                            'total_syncs', 'failed_syncs', 'last_checked_at',
                            'verification_status', 'last_error', 'last_result']

    def get_configured_fields(self, obj):
        try:
            return [key for key, value in obj.get_secrets().items() if value]
        except ValueError:
            return []

    def validate(self, attrs):
        kind = attrs.get('integration_type', getattr(self.instance, 'integration_type', None))
        connector = CONNECTORS.get(kind)
        if not connector:
            raise serializers.ValidationError('不支持的集成类型。')
        if self.instance and kind != self.instance.integration_type:
            raise serializers.ValidationError('不能变更现有连接的服务类型，请新建连接。')
        config = attrs.get('config', self.instance.config if self.instance else {})
        credentials = attrs.get('credentials', {})
        if not isinstance(config, dict) or not isinstance(credentials, dict):
            raise serializers.ValidationError('配置和凭证必须是对象。')
        secret_keys = {f['key'] for f in connector['fields'] if f['secret']}
        if set(config) & secret_keys or set(credentials) - secret_keys:
            raise serializers.ValidationError('敏感字段必须放在凭证中，普通配置不能包含密钥。')
        try:
            try:
                saved = self.instance.get_secrets() if self.instance else {}
            except ValueError:
                # A rotated encryption key must not prevent supplying fresh credentials.
                required = {f['key'] for f in connector['fields'] if f['secret'] and f['required']}
                if not all(credentials.get(key) for key in required):
                    raise
                saved = {}
            # Omitted keys are preserved; an explicit empty value clears an optional secret.
            secrets = {**saved, **credentials}
            validate_config(connector, config, secrets)
        except (ConnectorError, ValueError) as exc:
            raise serializers.ValidationError(str(exc))
        attrs['config'] = config
        attrs['credentials'] = secrets
        return attrs

    def create(self, validated_data):
        secrets = validated_data.pop('credentials')
        instance = Integration(**validated_data)
        instance.set_secrets(secrets)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        secrets = validated_data.pop('credentials')
        try:
            changed = instance.config != validated_data.get('config', instance.config) or instance.get_secrets() != secrets
        except ValueError:
            changed = True
        instance.set_secrets(secrets)
        if changed:
            instance.is_connected = False
            instance.verification_status = 'untested'
            instance.last_checked_at = None
            instance.last_error = ''
            instance.last_result = {}
        return super().update(instance, validated_data)


class IntegrationDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationDelivery
        fields = ['id', 'event', 'status', 'message', 'status_code', 'duration_ms', 'created_at', 'completed_at']


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
