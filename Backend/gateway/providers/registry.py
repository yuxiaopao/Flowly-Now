"""
Provider registry for AI gateway.
Manages registration and retrieval of AI model providers.
"""

from typing import Dict, Optional, List, Type, Any
from decimal import Decimal
import logging

from .base import BaseProvider, ModelInfo

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry for managing AI model providers.

    Usage:
        registry = ProviderRegistry()
        registry.register('openai', OpenAIProvider, api_key='sk-...')
        provider = registry.get('openai')
        response = provider.chat(messages)
    """

    def __init__(self):
        self._providers: Dict[str, Type[BaseProvider]] = {}
        self._instances: Dict[str, BaseProvider] = {}
        self._configs: Dict[str, Dict] = {}

    def register(
        self,
        name: str,
        provider_class: Type[BaseProvider],
        api_key: str = None,
        base_url: str = None,
        **config
    ):
        """
        Register a provider.

        Args:
            name: Provider name/identifier
            provider_class: Provider class (not instance)
            api_key: API key for the provider
            base_url: Custom base URL (for proxies)
            **config: Additional provider configuration
        """
        if not issubclass(provider_class, BaseProvider):
            raise ValueError(f"{provider_class.__name__} must inherit from BaseProvider")

        self._providers[name] = provider_class
        self._configs[name] = {
            'api_key': api_key,
            'base_url': base_url,
            **config
        }

        logger.info(f"Registered provider: {name}")

    def unregister(self, name: str):
        """
        Unregister a provider.

        Args:
            name: Provider name to unregister
        """
        if name in self._providers:
            del self._providers[name]

        if name in self._instances:
            del self._instances[name]

        if name in self._configs:
            del self._configs[name]

        logger.info(f"Unregistered provider: {name}")

    def get(self, name: str, **override_config) -> Optional[BaseProvider]:
        """
        Get a provider instance.

        Args:
            name: Provider name
            **override_config: Configuration overrides

        Returns:
            Provider instance or None if not registered
        """
        if name not in self._providers:
            logger.warning(f"Provider not registered: {name}")
            return None

        cache_key = f"{name}_{hash(frozenset(override_config.items()))}"

        if cache_key not in self._instances or override_config:
            provider_class = self._providers[name]
            config = {**self._configs.get(name, {}), **override_config}

            try:
                instance = provider_class(
                    api_key=config.get('api_key'),
                    base_url=config.get('base_url'),
                    **{k: v for k, v in config.items() if k not in ['api_key', 'base_url']}
                )
                self._instances[name] = instance
                return instance
            except Exception as e:
                logger.error(f"Failed to create provider instance: {str(e)}")
                return None

        return self._instances.get(name)

    def get_all(self) -> List[str]:
        """Get names of all registered providers."""
        return list(self._providers.keys())

    def list_providers(self) -> List[Dict]:
        """Get information about all registered providers."""
        providers = []
        for name in self._providers:
            provider_class = self._providers[name]
            instance = self._instances.get(name)

            providers.append({
                'name': name,
                'display_name': getattr(provider_class, 'provider_display_name', name),
                'available_models': [m.model_id for m in provider_class.available_models] if hasattr(provider_class, 'available_models') else [],
                'default_model': getattr(provider_class, 'default_model', None),
                'connected': instance.connect() if instance else False,
                'has_api_key': bool(self._configs.get(name, {}).get('api_key'))
            })

        return providers

    def list_models(self, provider_name: str = None) -> List[ModelInfo]:
        """
        List models from specified provider or all providers.

        Args:
            provider_name: Optional provider name to filter by

        Returns:
            List of ModelInfo objects
        """
        models = []

        providers_to_check = [provider_name] if provider_name else list(self._providers.keys())

        for name in providers_to_check:
            if name in self._providers:
                # First try instance method
                provider_instance = self.get(name)
                if provider_instance and hasattr(provider_instance, 'list_models'):
                    try:
                        models.extend(provider_instance.list_models())
                        continue
                    except Exception as e:
                        logger.warning("Failed to list models from provider '%s': %s", name, e)

                # Fall back to class attribute
                provider_class = self._providers[name]
                if hasattr(provider_class, 'available_models'):
                    attr = getattr(provider_class, 'available_models')
                    # Handle @property decorated attributes
                    if callable(attr) and hasattr(attr, 'fget'):
                        try:
                            if provider_instance:
                                models.extend(provider_instance.available_models)
                        except Exception as e:
                            logger.warning("Failed to get available_models from provider '%s': %s", name, e)
                    elif isinstance(attr, list):
                        models.extend(attr)

        return models

    def find_provider_for_model(self, model_id: str) -> Optional[str]:
        """
        Find which provider supports a given model.

        Args:
            model_id: Model identifier

        Returns:
            Provider name or None if not found
        """
        if model_id and model_id.startswith('ep-') and self.get('openai'):
            return 'openai'

        for name, provider_class in self._providers.items():
            available_models = None

            # Check class attribute
            if hasattr(provider_class, 'available_models'):
                attr = getattr(provider_class, 'available_models')
                # Handle @property decorated attributes
                if callable(attr) and hasattr(attr, 'fget'):
                    try:
                        # Try to instantiate and call property
                        instance = self.get(name)
                        if instance:
                            available_models = instance.available_models
                    except Exception:
                        pass
                elif isinstance(attr, list):
                    available_models = attr

            if available_models:
                for model in available_models:
                    if hasattr(model, 'model_id') and model.model_id == model_id:
                        return name
                    elif isinstance(model, str) and model == model_id:
                        return name

        return None

    def update_config(self, name: str, **config):
        """
        Update provider configuration.

        Args:
            name: Provider name
            **config: Configuration updates
        """
        if name not in self._providers:
            logger.warning(f"Cannot update config for unregistered provider: {name}")
            return

        if name in self._configs:
            self._configs[name].update(config)
        else:
            self._configs[name] = config

        if name in self._instances:
            del self._instances[name]

        logger.info(f"Updated config for provider: {name}")

    def clear_cache(self, name: str = None):
        """
        Clear provider instance cache.

        Args:
            name: Optional provider name. If None, clears all.
        """
        if name:
            if name in self._instances:
                del self._instances[name]
        else:
            self._instances.clear()

        logger.debug(f"Cleared provider cache: {name or 'all'}")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all registered providers.
        
        Returns:
            Dict with provider names as keys and health status as values.
            Format: {provider_name: {'status': 'ok'|'error'|'timeout', 'latency_ms': int, ...}}
        """
        import time
        import requests
        
        results = {}
        
        for name in self._providers:
            provider_start = time.time()
            
            try:
                provider_class = self._providers[name]
                instance = self.get(name)
                
                if not instance:
                    results[name] = {
                        'status': 'error',
                        'latency_ms': 0,
                        'error': 'Provider not initialized'
                    }
                    continue
                
                # Check if provider has a health_check method
                if hasattr(instance, 'health_check') and callable(instance.health_check):
                    health_result = instance.health_check()
                    results[name] = health_result
                else:
                    # Fallback to connect() check
                    try:
                        is_connected = instance.connect()
                        latency_ms = int((time.time() - provider_start) * 1000)
                        
                        if is_connected:
                            results[name] = {
                                'status': 'ok',
                                'latency_ms': latency_ms
                            }
                        else:
                            results[name] = {
                                'status': 'error',
                                'latency_ms': latency_ms,
                                'error': 'Connection failed'
                            }
                    except Exception as e:
                        results[name] = {
                            'status': 'error',
                            'latency_ms': int((time.time() - provider_start) * 1000),
                            'error': str(e)
                        }
                            
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'latency_ms': int((time.time() - provider_start) * 1000),
                    'error': str(e)
                }
        
        return results


class UnifiedProvider(BaseProvider):
    """
    Unified provider that routes requests to appropriate providers
    based on model identifier.
    """

    def __init__(self, registry: ProviderRegistry = None, **config):
        super().__init__(**config)
        self.registry = registry or default_registry

    @property
    def provider_name(self) -> str:
        return 'unified'

    @property
    def provider_display_name(self) -> str:
        return 'Unified Gateway'

    @property
    def default_model(self) -> str:
        return 'gpt-3.5-turbo'

    @property
    def available_models(self) -> List[ModelInfo]:
        return self.registry.list_models()

    def connect(self) -> bool:
        """Check if at least one provider is available."""
        for name in self.registry.get_all():
            provider = self.registry.get(name)
            if provider and provider.connect():
                return True
        return False

    def _get_provider_for_model(self, model: str):
        """Get appropriate provider for a model."""
        if model and model.startswith('ep-'):
            openai_provider = self.registry.get('openai')
            if openai_provider:
                return openai_provider

        provider_name = self.registry.find_provider_for_model(model)
        if provider_name:
            return self.registry.get(provider_name)

        for name in self.registry.get_all():
            provider = self.registry.get(name)
            if provider and provider.supports_model(model):
                return provider

        return self.registry.get('openai')

    def chat(self, messages, model=None, **kwargs) -> 'ProviderResponse':
        """Route chat request to appropriate provider."""
        model = model or self.default_model
        provider = self._get_provider_for_model(model)

        if not provider:
            from .base import ProviderResponse
            return ProviderResponse(
                content="",
                model=model,
                provider="unified",
                error=f"No provider available for model: {model}"
            )

        return provider.chat(messages, model=model, **kwargs)

    def stream_chat(self, messages, model=None, **kwargs):
        """Route streaming chat request to appropriate provider."""
        model = model or self.default_model
        provider = self._get_provider_for_model(model)

        if not provider:
            yield {'type': 'error', 'error': f'No provider available for model: {model}'}
            return

        yield from provider.stream_chat(messages, model=model, **kwargs)

    def embeddings(self, texts, model=None) -> List[List[float]]:
        """Route embeddings request to OpenAI provider."""
        openai_provider = self.registry.get('openai')

        if not openai_provider:
            raise ValueError("No OpenAI provider available for embeddings")

        return openai_provider.embeddings(texts, model=model)


default_registry = ProviderRegistry()


def register_default_providers():
    """Register built-in providers with default registry."""
    from django.conf import settings

    openai_key = getattr(settings, 'OPENAI_API_KEY', None)
    openai_base_url = getattr(settings, 'OPENAI_BASE_URL', None)

    anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', None)

    if openai_key:
        from .openai_provider import OpenAIProvider
        default_registry.register(
            'openai',
            OpenAIProvider,
            api_key=openai_key,
            base_url=openai_base_url
        )
        logger.info("Registered OpenAI provider")

    if anthropic_key:
        from .anthropic_provider import AnthropicProvider
        default_registry.register(
            'anthropic',
            AnthropicProvider,
            api_key=anthropic_key
        )
        logger.info("Registered Anthropic provider")

    # 阿里云百炼 DashScope（通义千问系列，OpenAI 兼容模式）
    dashscope_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
    dashscope_compat_base_url = getattr(settings, 'DASHSCOPE_COMPATIBLE_BASE_URL', None)
    if dashscope_key:
        from .openai_provider import OpenAIProvider
        default_registry.register(
            'dashscope',
            OpenAIProvider,
            api_key=dashscope_key,
            base_url=dashscope_compat_base_url
        )
        logger.info("Registered DashScope (Bailian) provider")

    # Agnes AI 多模态 API Hub（OpenAI 兼容）
    agnes_key = getattr(settings, 'AGNES_API_KEY', None)
    agnes_base_url = getattr(settings, 'AGNES_BASE_URL', None)
    if agnes_key:
        from .openai_provider import OpenAIProvider
        default_registry.register(
            'agnes',
            OpenAIProvider,
            api_key=agnes_key,
            base_url=agnes_base_url
        )
        logger.info("Registered Agnes AI provider")

    # Ollama (local) - register if reachable
    ollama_base_url = getattr(settings, 'OLLAMA_BASE_URL', None)
    if ollama_base_url:
        try:
            import requests
            resp = requests.get(f'{ollama_base_url}/api/tags', timeout=3)
            if resp.status_code == 200:
                from .ollama_provider import OllamaProvider
                default_registry.register(
                    'ollama',
                    OllamaProvider,
                    base_url=ollama_base_url
                )
                logger.info("Registered Ollama provider")
        except Exception:
            logger.debug("Ollama not available, skipping")


def get_registry() -> ProviderRegistry:
    """Get the default provider registry."""
    return default_registry


def get_unified_provider() -> UnifiedProvider:
    """Get a unified provider instance."""
    return UnifiedProvider(registry=default_registry)
