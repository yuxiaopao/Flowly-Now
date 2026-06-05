"""
Serializers for gateway app.
"""

from decimal import Decimal

from rest_framework import serializers
from django.contrib.auth import get_user_model

from workflows.models import APICredential

from .models import ModelProvider, AIModel, APICallLog

User = get_user_model()


class ModelProviderSerializer(serializers.ModelSerializer):
    """Serializer for ModelProvider."""

    class Meta:
        model = ModelProvider
        fields = ['id', 'name', 'slug', 'logo_url', 'website', 'is_active']


class AIModelSerializer(serializers.ModelSerializer):
    """Serializer for AIModel."""

    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_slug = serializers.CharField(source='provider.slug', read_only=True)

    class Meta:
        model = AIModel
        fields = [
            'id', 'provider', 'provider_name', 'provider_slug',
            'name', 'model_id', 'model_type',
            'max_tokens', 'supports_streaming', 'supports_function_calling',
            'supports_vision', 'input_price', 'output_price',
            'default_temperature', 'default_top_p',
            'is_active', 'is_default', 'description',
            'context_window', 'released_at'
        ]


class AIModelListSerializer(serializers.ModelSerializer):
    """Simplified serializer for AIModel list."""

    provider_name = serializers.CharField(source='provider.name', read_only=True)

    class Meta:
        model = AIModel
        fields = [
            'id', 'name', 'model_id', 'model_type',
            'provider_name', 'is_active', 'is_default'
        ]


class UserAPIKeySerializer(serializers.ModelSerializer):
    """Serializer for gateway legacy API key view backed by unified credentials."""

    masked_key = serializers.SerializerMethodField()
    provider_display = serializers.SerializerMethodField()
    endpoint = serializers.SerializerMethodField()
    api_version = serializers.SerializerMethodField()
    total_usage = serializers.SerializerMethodField()

    class Meta:
        model = APICredential
        fields = [
            'id', 'service_type', 'provider_display', 'name',
            'masked_key', 'endpoint', 'api_version',
            'is_active', 'last_used_at', 'total_usage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_masked_key(self, obj):
        return obj.get_masked_value()

    def get_provider_display(self, obj):
        return obj.get_service_type_display() if obj.service_type else ''

    def get_endpoint(self, obj):
        return (obj.service_config or {}).get('endpoint')

    def get_api_version(self, obj):
        return (obj.service_config or {}).get('api_version')

    def get_total_usage(self, obj):
        return obj.usage_count

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['provider'] = data.pop('service_type', '')
        return data


class UserAPIKeyCreateSerializer(serializers.ModelSerializer):
    """Serializer for legacy API key endpoints backed by APICredential."""

    provider = serializers.CharField(write_only=True)
    api_key = serializers.CharField(write_only=True)
    endpoint = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    api_version = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)

    class Meta:
        model = APICredential
        fields = [
            'provider', 'name', 'api_key',
            'endpoint', 'api_version', 'description', 'is_active'
        ]

    def create(self, validated_data):
        request = getattr(self, 'context', {}).get('request')
        provider = validated_data.pop('provider')
        api_key = validated_data.pop('api_key')
        endpoint = validated_data.pop('endpoint', None)
        api_version = validated_data.pop('api_version', None)
        service_config = {}
        if endpoint:
            service_config['endpoint'] = endpoint
        if api_version:
            service_config['api_version'] = api_version

        credential = APICredential.objects.create(
            owner=request.user,
            service_type=provider,
            credential_type='api_key',
            service_config=service_config,
            **validated_data,
        )
        credential.set_encrypted_data(api_key)
        credential.save()
        return credential

    def update(self, instance, validated_data):
        provider = validated_data.pop('provider', instance.service_type)
        api_key = validated_data.pop('api_key', None)
        endpoint = validated_data.pop('endpoint', None)
        api_version = validated_data.pop('api_version', None)

        instance.service_type = provider
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        service_config = dict(instance.service_config or {})
        if endpoint is not None:
            if endpoint:
                service_config['endpoint'] = endpoint
            else:
                service_config.pop('endpoint', None)
        if api_version is not None:
            if api_version:
                service_config['api_version'] = api_version
            else:
                service_config.pop('api_version', None)
        instance.service_config = service_config

        if api_key:
            instance.set_encrypted_data(api_key)

        instance.save()
        return instance


class APICallLogSerializer(serializers.ModelSerializer):
    """Serializer for APICallLog."""

    class Meta:
        model = APICallLog
        fields = [
            'id', 'user', 'provider', 'model', 'endpoint',
            'input_tokens', 'output_tokens', 'total_tokens',
            'latency_ms', 'status_code', 'error_message',
            'cost', 'timestamp'
        ]


class APICallLogAggregateSerializer(serializers.Serializer):
    """Serializer for aggregated API call statistics."""

    total_calls = serializers.IntegerField(min_value=0)
    total_tokens = serializers.IntegerField(min_value=0)
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=6, min_value=Decimal('0'))
    avg_latency = serializers.FloatField(min_value=0)
    by_provider = serializers.DictField()
    by_model = serializers.DictField()


class ProviderHealthSerializer(serializers.Serializer):
    """Serializer for individual provider health status."""

    status = serializers.ChoiceField(choices=['ok', 'error', 'timeout', 'degraded'])
    latency_ms = serializers.IntegerField()
    error = serializers.CharField(required=False, allow_null=True)
    models_count = serializers.IntegerField(required=False, allow_null=True)


class GatewayHealthSerializer(serializers.Serializer):
    """Serializer for gateway health check response."""

    status = serializers.ChoiceField(choices=['ok', 'degraded', 'error'])
    providers = serializers.DictField(child=ProviderHealthSerializer())
