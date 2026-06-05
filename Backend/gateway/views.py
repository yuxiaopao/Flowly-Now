"""
Views for gateway app.
"""

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Sum, Count, Avg

from workflows.models import APICredential
from .gateway_service import GatewayService, PROVIDER_DISPLAY_NAMES

from .models import ModelProvider, AIModel, APICallLog
from .serializers import (
    ModelProviderSerializer, AIModelSerializer, AIModelListSerializer,
    UserAPIKeySerializer, UserAPIKeyCreateSerializer,
    APICallLogSerializer, APICallLogAggregateSerializer
)


class ModelProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ModelProvider."""

    queryset = ModelProvider.objects.filter(is_active=True)
    serializer_class = ModelProviderSerializer
    permission_classes = [IsAuthenticated]


class AIModelViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for AIModel."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = AIModel.objects.filter(is_active=True)

        # Filter by provider
        provider = self.request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider__slug=provider)

        # Filter by type
        model_type = self.request.query_params.get('type')
        if model_type:
            queryset = queryset.filter(model_type=model_type)

        # Filter by capability
        capability = self.request.query_params.get('capability')
        if capability == 'streaming':
            queryset = queryset.filter(supports_streaming=True)
        elif capability == 'function_calling':
            queryset = queryset.filter(supports_function_calling=True)
        elif capability == 'vision':
            queryset = queryset.filter(supports_vision=True)

        return queryset.select_related('provider')

    def get_serializer_class(self):
        if self.action == 'list':
            return AIModelListSerializer
        return AIModelSerializer

    @action(detail=False, methods=['get'])
    def default_models(self, request):
        """Get default models by type."""
        defaults = AIModel.objects.filter(is_active=True, is_default=True)
        by_type = {}
        for model in defaults:
            if model.model_type not in by_type:
                by_type[model.model_type] = AIModelSerializer(model).data
        return Response(by_type)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get all available models from all providers (registered + static catalogs)."""
        from .providers.registry import get_registry, register_default_providers
        from .providers.openai_provider import OpenAIProvider
        from .providers.anthropic_provider import AnthropicProvider

        registry = get_registry()
        if not registry.get_all():
            register_default_providers()

        models = registry.list_models()
        seen_providers = {m.provider for m in models}

        provider_display = getattr(OpenAIProvider, 'provider_display_name', PROVIDER_DISPLAY_NAMES.get('openai', 'OpenAI'))
        anthropic_display = getattr(AnthropicProvider, 'provider_display_name', PROVIDER_DISPLAY_NAMES.get('anthropic', 'Anthropic'))

        if 'openai' not in seen_providers and 'OpenAI' not in seen_providers:
            models.extend(OpenAIProvider.available_models)
        if 'anthropic' not in seen_providers and 'Anthropic' not in seen_providers:
            models.extend(AnthropicProvider.available_models)

        # Filter by type
        model_type = request.query_params.get('type')
        if model_type:
            models = [m for m in models if m.model_type == model_type]

        # Filter by capability
        capability = request.query_params.get('capability')
        if capability == 'streaming':
            models = [m for m in models if m.supports_streaming]
        elif capability == 'function_calling':
            models = [m for m in models if m.supports_function_calling]
        elif capability == 'vision':
            models = [m for m in models if m.supports_vision]

        data = [{
            'model_id': m.model_id,
            'name': m.name,
            'provider': PROVIDER_DISPLAY_NAMES.get((m.provider or '').lower(), m.provider or 'Unknown'),
            'model_type': m.model_type,
            'max_tokens': m.max_tokens,
            'supports_streaming': m.supports_streaming,
            'supports_function_calling': m.supports_function_calling,
            'supports_vision': m.supports_vision,
            'context_window': m.context_window,
            'input_price': float(m.input_price) if m.input_price else 0,
            'output_price': float(m.output_price) if m.output_price else 0,
        } for m in models]

        return Response(data)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test model connectivity."""
        model = self.get_object()
        gateway = GatewayService(user=request.user)

        try:
            response = gateway.chat(
                messages=[{"role": "user", "content": "Hello"}],
                model=model.model_id,
                max_tokens=10
            )
            return Response({
                'success': True,
                'model': model.name,
                'response': response.content
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserAPIKeyViewSet(viewsets.ModelViewSet):
    """Legacy gateway API key endpoints backed by unified credentials."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return APICredential.objects.filter(
            owner=self.request.user,
            credential_type='api_key'
        ).order_by('-created_at')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserAPIKeyCreateSerializer
        return UserAPIKeySerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify API key is valid."""
        credential = self.get_object()
        decrypted_key = credential.get_decrypted_data()
        gateway = GatewayService(user=request.user, api_key=decrypted_key)

        try:
            response = gateway.chat(
                messages=[{"role": "user", "content": "test"}],
                model='gpt-3.5-turbo',
                max_tokens=5
            )
            return Response({'valid': True, 'response': getattr(response, 'content', '')})
        except Exception as e:
            return Response({
                'valid': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class APICallLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for APICallLog."""

    serializer_class = APICallLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return APICallLog.objects.filter(user=self.request.user).order_by('-timestamp')

    @action(detail=False, methods=['get'])
    def aggregate(self, request):
        """Get aggregated statistics."""
        from django.db.models.functions import TruncHour, TruncDay

        days = int(request.query_params.get('days', 7))
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=days)

        queryset = self.get_queryset().filter(timestamp__gte=cutoff)

        # Overall stats
        overall = queryset.aggregate(
            total_calls=Count('id'),
            total_tokens=Sum('total_tokens'),
            total_cost=Sum('cost'),
            avg_latency=Avg('latency_ms')
        )

        # By provider
        by_provider = queryset.values('provider').annotate(
            calls=Count('id'),
            tokens=Sum('total_tokens'),
            cost=Sum('cost')
        )

        # By model
        by_model = queryset.values('model').annotate(
            calls=Count('id'),
            tokens=Sum('total_tokens'),
            cost=Sum('cost')
        ).order_by('-calls')[:10]

        return Response({
            'period_days': days,
            'overall': {
                'total_calls': overall['total_calls'] or 0,
                'total_tokens': overall['total_tokens'] or 0,
                'total_cost': float(overall['total_cost'] or 0),
                'avg_latency': round(overall['avg_latency'] or 0, 2)
            },
            'by_provider': list(by_provider),
            'by_model': list(by_model)
        })

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent API calls."""
        limit = int(request.query_params.get('limit', 20))
        logs = self.get_queryset()[:limit]
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


class GatewayChatView(APIView):
    """Unified chat endpoint through gateway."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Send chat request."""
        messages = request.data.get('messages')
        model = request.data.get('model', 'gpt-3.5-turbo')
        temperature = request.data.get('temperature', 0.7)
        max_tokens = request.data.get('max_tokens', 2048)
        stream = request.data.get('stream', False)

        # Validate messages is provided
        if messages is None:
            return Response(
                {'error': 'messages is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate messages is a list
        if not isinstance(messages, list):
            return Response(
                {'error': 'messages must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate messages is not empty
        if not messages:
            return Response(
                {'error': 'messages cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate each message has required fields
        valid_roles = {'user', 'assistant', 'system', 'developer'}
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return Response(
                    {'error': f'messages[{i}] must be an object'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if 'role' not in msg:
                return Response(
                    {'error': f'messages[{i}] requires a role'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if msg['role'] not in valid_roles:
                return Response(
                    {'error': f'messages[{i}] has invalid role: {msg["role"]}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if 'content' not in msg or not msg['content']:
                return Response(
                    {'error': f'messages[{i}] requires content'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate temperature range
        try:
            temperature = float(temperature)
            if temperature < 0 or temperature > 2:
                return Response(
                    {'error': 'temperature must be between 0 and 2'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (TypeError, ValueError):
            return Response(
                {'error': 'temperature must be a number'},
                status=status.HTTP_400_BAD_REQUEST
            )

        gateway = GatewayService(user=request.user)

        try:
            if stream:
                return self._stream_response(gateway, messages, model, temperature, max_tokens)
            else:
                response = gateway.chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return Response({
                    'content': response.content,
                    'model': response.model,
                    'usage': {
                        'input_tokens': response.input_tokens,
                        'output_tokens': response.output_tokens,
                        'total_tokens': response.total_tokens
                    },
                    'latency_ms': response.latency_ms,
                    'cost': float(response.cost)
                })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _stream_response(self, gateway, messages, model, temperature, max_tokens):
        """Stream chat response."""
        from django.http import StreamingHttpResponse
        import json

        def generate():
            try:
                for chunk in gateway.stream_chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingHttpResponse(
            generate(),
            content_type='text/event-stream'
        )


class GatewayEmbeddingsView(APIView):
    """Unified embeddings endpoint through gateway."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Get embeddings."""
        texts = request.data.get('texts')
        model = request.data.get('model', 'text-embedding-ada-002')

        # Validate texts is provided
        if texts is None:
            return Response(
                {'error': 'texts is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate texts is a list
        if not isinstance(texts, list):
            return Response(
                {'error': 'texts must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate texts is not empty
        if not texts:
            return Response(
                {'error': 'texts cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        gateway = GatewayService(user=request.user)

        try:
            embeddings = gateway.embeddings(texts=texts, model=model)
            return Response({
                'embeddings': embeddings,
                'model': model,
                'count': len(embeddings)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GatewayHealthView(APIView):
    """
    Health check endpoint for all AI providers.
    
    GET /api/v1/gateway/health/
    
    Returns status of all registered providers including latency and model counts.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get health status of all AI providers.
        
        Returns:
            {
                "openai": {"status": "ok", "latency_ms": 120},
                "anthropic": {"status": "ok", "latency_ms": 200},
                "ollama": {"status": "ok", "latency_ms": 15, "models_count": 3}
            }
        """
        from .providers.registry import get_registry, register_default_providers
        
        registry = get_registry()
        
        # Initialize providers if not already done
        if not registry.get_all():
            register_default_providers()
        
        # Get health status from registry
        health_status = registry.health_check()
        
        # Determine overall status
        overall_status = 'ok'
        for provider_name, status in health_status.items():
            if status.get('status') != 'ok':
                overall_status = 'degraded'
                break
        
        return Response({
            'status': overall_status,
            'providers': health_status
        })
