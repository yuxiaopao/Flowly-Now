"""
Model router service for unified AI gateway.
Routes requests to appropriate providers based on model or configuration.
"""

from typing import Dict, Any, List, Optional, Generator
from decimal import Decimal
import logging

from ..providers.base import BaseProvider, ProviderResponse, ModelInfo
from ..providers.registry import (
    ProviderRegistry,
    default_registry,
    get_registry,
    get_unified_provider,
    register_default_providers
)

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Routes LLM requests to appropriate providers.

    Features:
    - Automatic model-to-provider mapping
    - Cost-based routing
    - Fallback providers
    - Request logging
    """

    def __init__(self, registry: ProviderRegistry = None, user=None):
        """
        Initialize model router.

        Args:
            registry: Provider registry instance
            user: Django user for request logging
        """
        self.registry = registry or get_registry()
        self.user = user
        self._unified_provider = None

    @property
    def unified_provider(self) -> BaseProvider:
        """Get or create unified provider."""
        if self._unified_provider is None:
            self._unified_provider = get_unified_provider()
        return self._unified_provider

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        provider: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> ProviderResponse:
        """
        Send chat request through the router.

        Args:
            messages: List of messages
            model: Model identifier
            provider: Specific provider to use
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            top_p: Nucleus sampling
            stream: Enable streaming
            **kwargs: Additional parameters

        Returns:
            ProviderResponse from the model
        """
        try:
            if provider:
                return self._chat_with_provider(
                    provider, messages, model, temperature,
                    max_tokens, top_p, stream, **kwargs
                )

            return self._chat_auto_route(
                messages, model, temperature,
                max_tokens, top_p, stream, **kwargs
            )

        except Exception as e:
            logger.error(f"ModelRouter.chat error: {str(e)}")
            return ProviderResponse(
                content="",
                model=model or "unknown",
                provider="router",
                error=str(e)
            )

    def _chat_with_provider(
        self,
        provider_name: str,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> ProviderResponse:
        """Route request to specific provider."""
        provider = self.registry.get(provider_name)

        if not provider:
            return ProviderResponse(
                content="",
                model=model or "unknown",
                provider=provider_name,
                error=f"Provider not found: {provider_name}"
            )

        return provider.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs
        )

    def _chat_auto_route(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> ProviderResponse:
        """Auto-route request based on model or default."""
        if model:
            provider_name = self.registry.find_provider_for_model(model)

            if provider_name:
                provider = self.registry.get(provider_name)
                if provider:
                    return provider.chat(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        **kwargs
                    )

        return self.unified_provider.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs
        )

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        provider: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Send streaming chat request through the router.

        Args:
            messages: List of messages
            model: Model identifier
            provider: Specific provider to use
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional parameters

        Yields:
            Streaming response chunks
        """
        try:
            if provider:
                provider_instance = self.registry.get(provider)
                if provider_instance:
                    yield from provider_instance.stream_chat(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    return

            if model:
                provider_name = self.registry.find_provider_for_model(model)
                if provider_name:
                    provider_instance = self.registry.get(provider_name)
                    if provider_instance:
                        yield from provider_instance.stream_chat(
                            messages=messages,
                            model=model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            **kwargs
                        )
                        return

            yield from self.unified_provider.stream_chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

        except Exception as e:
            logger.error(f"ModelRouter.stream_chat error: {str(e)}")
            yield {'type': 'error', 'error': str(e)}

    def embeddings(
        self,
        texts: List[str],
        model: str = 'text-embedding-ada-002',
        provider: str = None
    ) -> List[List[float]]:
        """
        Generate embeddings.

        Args:
            texts: Texts to embed
            model: Embedding model
            provider: Specific provider

        Returns:
            List of embedding vectors
        """
        try:
            if provider:
                provider_instance = self.registry.get(provider)
                if provider_instance:
                    return provider_instance.embeddings(texts, model=model)

            openai_provider = self.registry.get('openai')
            if openai_provider:
                return openai_provider.embeddings(texts, model=model)

            return self.unified_provider.embeddings(texts, model=model)

        except Exception as e:
            logger.error(f"ModelRouter.embeddings error: {str(e)}")
            raise

    def list_available_models(
        self,
        provider: str = None,
        model_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        List available models.

        Args:
            provider: Filter by provider
            model_type: Filter by type (chat, embedding, etc.)

        Returns:
            List of model info dictionaries
        """
        models = self.registry.list_models(provider)

        if model_type:
            models = [m for m in models if m.model_type == model_type]

        return [
            {
                'model_id': m.model_id,
                'name': m.name,
                'provider': m.provider,
                'model_type': m.model_type,
                'max_tokens': m.max_tokens,
                'supports_streaming': m.supports_streaming,
                'supports_function_calling': m.supports_function_calling,
                'supports_vision': m.supports_vision,
                'input_price': float(m.input_price),
                'output_price': float(m.output_price),
                'context_window': m.context_window
            }
            for m in models
        ]

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.

        Args:
            model_id: Model identifier

        Returns:
            Model info dictionary or None
        """
        for model in self.registry.list_models():
            if model.model_id == model_id:
                return {
                    'model_id': model.model_id,
                    'name': model.name,
                    'provider': model.provider,
                    'model_type': model.model_type,
                    'max_tokens': model.max_tokens,
                    'supports_streaming': model.supports_streaming,
                    'supports_function_calling': model.supports_function_calling,
                    'supports_vision': model.supports_vision,
                    'input_price': float(model.input_price),
                    'output_price': float(model.output_price),
                    'context_window': model.context_window
                }

        return None

    def test_provider_connection(self, provider_name: str) -> Dict[str, Any]:
        """
        Test connection to a provider.

        Args:
            provider_name: Provider name

        Returns:
            Dict with success status and details
        """
        provider = self.registry.get(provider_name)

        if not provider:
            return {
                'success': False,
                'error': f"Provider not found: {provider_name}"
            }

        try:
            success = provider.connect()
            return {
                'success': success,
                'provider': provider_name,
                'message': 'Connected successfully' if success else 'Connection failed'
            }
        except Exception as e:
            return {
                'success': False,
                'provider': provider_name,
                'error': str(e)
            }

    def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get usage statistics from API call logs.

        Args:
            days: Number of days to look back

        Returns:
            Usage statistics dictionary
        """
        from django.db.models import Sum, Avg, Count
        from django.utils import timezone
        from ..models import APICallLog

        cutoff = timezone.now() - timezone.timedelta(days=days)

        base_query = APICallLog.objects.all()
        if self.user:
            base_query = base_query.filter(user=self.user)

        stats = base_query.filter(
            timestamp__gte=cutoff
        ).aggregate(
            total_calls=Count('id'),
            total_input_tokens=Sum('input_tokens'),
            total_output_tokens=Sum('output_tokens'),
            total_cost=Sum('cost'),
            avg_latency=Avg('latency_ms')
        )

        by_provider = base_query.filter(
            timestamp__gte=cutoff
        ).values('provider').annotate(
            calls=Count('id'),
            tokens=Sum('total_tokens'),
            cost=Sum('cost')
        )

        by_model = base_query.filter(
            timestamp__gte=cutoff
        ).values('model').annotate(
            calls=Count('id'),
            tokens=Sum('total_tokens'),
            cost=Sum('cost')
        ).order_by('-calls')[:10]

        return {
            'period_days': days,
            'total_calls': stats['total_calls'] or 0,
            'total_input_tokens': stats['total_input_tokens'] or 0,
            'total_output_tokens': stats['total_output_tokens'] or 0,
            'total_tokens': (stats['total_input_tokens'] or 0) + (stats['total_output_tokens'] or 0),
            'total_cost': float(stats['total_cost'] or 0),
            'avg_latency': round(stats['avg_latency'] or 0, 2),
            'by_provider': list(by_provider),
            'by_model': list(by_model)
        }


def get_model_router(user=None) -> ModelRouter:
    """
    Factory function to get a model router instance.

    Args:
        user: Django user for request logging

    Returns:
        Configured ModelRouter instance
    """
    if not default_registry.get_all():
        register_default_providers()

    return ModelRouter(registry=default_registry, user=user)
