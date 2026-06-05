# -*- coding: utf-8 -*-
"""
Gateway API Tests
Tests for ModelProvider, AIModel, UserAPIKey, APICallLog, and Gateway views.
"""

import pytest
from unittest.mock import patch, MagicMock


pytestmark = pytest.mark.django_db


class TestAIModelSerializer:
    """Test AIModelSerializer validation rules."""

    def test_list_serializer_fields(self):
        from gateway.serializers import AIModelListSerializer
        data = {
            'id': '123e4567-e89b-12d3-a456-426614174000',
            'name': 'GPT-4',
            'model_id': 'gpt-4',
            'model_type': 'chat',
            'provider_name': 'OpenAI',
            'is_active': True,
            'is_default': False,
        }
        serializer = AIModelListSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_list_serializer_rejects_unknown_fields(self):
        from gateway.serializers import AIModelListSerializer
        data = {
            'id': '123e4567-e89b-12d3-a456-426614174000',
            'name': 'GPT-4',
            'unknown_field': 'should be rejected',
        }
        serializer = AIModelListSerializer(data=data)
        assert not serializer.is_valid()

    def test_model_provider_serializer_valid(self):
        from gateway.serializers import ModelProviderSerializer
        data = {
            'name': 'OpenAI',
            'slug': 'openai',
            'logo_url': 'https://example.com/logo.png',
            'website': 'https://openai.com',
            'is_active': True,
        }
        serializer = ModelProviderSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


class TestUserAPIKeySerializer:
    """Test UserAPIKey serializers."""

    def test_create_serializer_requires_name(self):
        from gateway.serializers import UserAPIKeyCreateSerializer
        data = {
            'provider': 'openai',
            'api_key': 'sk-test123',
            'endpoint': 'https://api.openai.com/v1',
        }
        serializer = UserAPIKeyCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'name' in serializer.errors

    def test_create_serializer_requires_provider(self):
        from gateway.serializers import UserAPIKeyCreateSerializer
        data = {
            'name': 'My API Key',
            'api_key': 'sk-test123',
        }
        serializer = UserAPIKeyCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'provider' in serializer.errors

    def test_create_serializer_valid(self):
        from gateway.serializers import UserAPIKeyCreateSerializer
        data = {
            'name': 'My API Key',
            'provider': 'openai',
            'api_key': 'sk-test123',
            'endpoint': 'https://api.openai.com/v1',
        }
        serializer = UserAPIKeyCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_create_serializer_masks_key(self, user):
        from gateway.serializers import UserAPIKeyCreateSerializer
        data = {
            'name': 'My Key',
            'provider': 'openai',
            'api_key': 'sk-very-secret-key-12345',
        }
        serializer = UserAPIKeyCreateSerializer(data=data)
        assert serializer.is_valid()
        instance = serializer.save(user=user)
        masked = instance.get_masked_key()
        # Model implementation: first 4 chars + "..." + last 4 chars
        assert masked.startswith('sk-v')
        assert '...' in masked
        assert masked.endswith('2345')


class TestAPICallLogAggregateSerializer:
    """Test APICallLog aggregate serializer."""

    def test_aggregate_serializer_decimal_precision(self):
        from gateway.serializers import APICallLogAggregateSerializer
        data = {
            'total_calls': 100,
            'total_tokens': 50000,
            'total_cost': 1.234567,
            'avg_latency': 250.5,
            'by_provider': {},
            'by_model': {},
        }
        serializer = APICallLogAggregateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_aggregate_serializer_rejects_negative_cost(self):
        from gateway.serializers import APICallLogAggregateSerializer
        data = {
            'total_calls': 100,
            'total_tokens': 50000,
            'total_cost': -5.0,
            'avg_latency': 250.5,
            'by_provider': {},
            'by_model': {},
        }
        serializer = APICallLogAggregateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'total_cost' in serializer.errors


class TestGatewayHealthSerializer:
    """Test GatewayHealthSerializer."""

    def test_health_ok_status(self):
        from gateway.serializers import GatewayHealthSerializer
        data = {
            'status': 'ok',
            'providers': {
                'openai': {'status': 'ok', 'latency_ms': 100, 'error': None, 'models_count': 5},
                'anthropic': {'status': 'ok', 'latency_ms': 150, 'error': None, 'models_count': 3},
            }
        }
        serializer = GatewayHealthSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_health_invalid_status(self):
        from gateway.serializers import GatewayHealthSerializer
        data = {
            'status': 'super_dead',
            'providers': {},
        }
        serializer = GatewayHealthSerializer(data=data)
        assert not serializer.is_valid()
        assert 'status' in serializer.errors

    def test_health_degraded_status(self):
        from gateway.serializers import GatewayHealthSerializer
        data = {
            'status': 'degraded',
            'providers': {
                'openai': {'status': 'error', 'latency_ms': 5000, 'error': 'Timeout', 'models_count': 0},
            }
        }
        serializer = GatewayHealthSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


class TestGatewayChatValidation:
    """Test Gateway chat endpoint validation."""

    def test_chat_requires_messages(self, api_client, user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            '/api/v1/gateway/chat/',
            data={'model': 'gpt-4'},
            format='json'
        )
        assert response.status_code == 400
        assert 'error' in response.data

    def test_chat_validates_messages_array(self, api_client, user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            '/api/v1/gateway/chat/',
            data={'messages': 'not an array'},
            format='json'
        )
        assert response.status_code == 400

    def test_chat_requires_message_content(self, api_client, user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            '/api/v1/gateway/chat/',
            data={'messages': [{'role': 'user'}]},
            format='json'
        )
        assert response.status_code == 400

    def test_chat_requires_valid_role(self, api_client, user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            '/api/v1/gateway/chat/',
            data={'messages': [{'role': 'invalid_role', 'content': 'hello'}]},
            format='json'
        )
        assert response.status_code == 400

    def test_chat_validates_temperature_range(self, api_client, user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            '/api/v1/gateway/chat/',
            data={
                'messages': [{'role': 'user', 'content': 'hello'}],
                'temperature': 3.0,
            },
            format='json'
        )
        assert response.status_code == 400

    def test_embeddings_requires_texts(self, api_client, user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            '/api/v1/gateway/embeddings/',
            data={'model': 'text-embedding-ada-002'},
            format='json'
        )
        assert response.status_code == 400
        assert 'texts' in str(response.data)


class TestAIModelViewSetFiltering:
    """Test AIModel ViewSet query parameter filtering."""

    def test_filter_by_provider(self, api_client, user):
        client = api_client
        client.force_authenticate(user=user)
        response = client.get('/api/v1/gateway/models/', {'provider': 'openai'})
        assert response.status_code == 200

    def test_filter_by_type(self, api_client, user):
        client = api_client
        client.force_authenticate(user=user)
        response = client.get('/api/v1/gateway/models/', {'type': 'chat'})
        assert response.status_code == 200

    def test_filter_by_capability(self, api_client, user):
        client = api_client
        client.force_authenticate(user=user)
        response = client.get('/api/v1/gateway/models/', {'capability': 'streaming'})
        assert response.status_code == 200


class TestGatewayHealthEndpoint:
    """Test GatewayHealthView (no auth required)."""

    def test_health_check_no_auth(self, api_client):
        response = api_client.get('/api/v1/gateway/health/')
        assert response.status_code == 200
