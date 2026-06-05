"""
Gateway service for AI model management.
"""

import time
import logging
from typing import Dict, Any, Optional, List, Generator
from decimal import Decimal

from workflows.models import APICredential

from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Avg, Count

from workflows.models import APICredential

logger = logging.getLogger(__name__)


class LLMResponse:
    """LLM Response wrapper."""

    def __init__(
        self,
        content: str,
        model: str,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: int = 0,
        cost: Decimal = None,
        finish_reason: str = None,
        raw_response: Dict = None
    ):
        self.content = content
        self.model = model
        self.provider = provider
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.latency_ms = latency_ms
        self.cost = cost or Decimal("0")
        self.finish_reason = finish_reason
        self.raw_response = raw_response or {}


_ollama_provider = None


PROVIDER_DISPLAY_NAMES = {
    service_type: label
    for service_type, label in APICredential.SERVICE_TYPE_CHOICES
}
PROVIDER_DISPLAY_NAMES.update({
    'ollama': 'Ollama (本地)',
})


def _get_ollama_provider():
    """Get or create the Ollama provider instance."""
    global _ollama_provider
    if _ollama_provider is None:
        from gateway.providers.ollama_provider import OllamaProvider
        base_url = getattr(settings, 'OLLAMA_BASE_URL', None)
        _ollama_provider = OllamaProvider(base_url=base_url)
    return _ollama_provider


def _is_ollama_model(model: str) -> bool:
    """Check if a model is typically served by Ollama."""
    if not model:
        return False
    model_lower = model.lower()
    ollama_common = {
        'llama', 'mistral', 'codellama', 'qwen', 'phi', 'deepseek',
        'gemma', 'nomic', 'smollm', 'phi3', 'llava', 'moondream',
        'mixtral', 'neural-chat', 'wizardlm', 'orca', 'stablelm',
        'qwen2', 'qwen3', 'qwen2.5', 'aya', 'command-r'
    }
    return any(prefix in model_lower for prefix in ollama_common)


class LLMService:
    """Service for interacting with LLM providers."""

    PROVIDER_ENV_MAP = {
        **APICredential.PROVIDER_ENV_MAP,
        'google': 'GOOGLE_API_KEY',
        'ollama': 'OLLAMA_BASE_URL',
        'custom': 'OPENAI_API_KEY',
    }

    # Pricing map: model -> (input_price_per_million, output_price_per_million)
    # Kept here for cost calculation - update when model pricing changes
    MODEL_PRICING = {
        "gpt-4": (Decimal("0.03"), Decimal("0.06")),
        "gpt-4-32k": (Decimal("0.06"), Decimal("0.12")),
        "gpt-3.5-turbo": (Decimal("0.001"), Decimal("0.002")),
        "gpt-3.5-turbo-16k": (Decimal("0.002"), Decimal("0.004")),
    }

    def __init__(self, user=None, api_key: str = None):
        self.user = user
        self.api_key = api_key or self._get_user_api_key()

    def _get_user_api_key(self, provider: str = 'openai') -> Optional[str]:
        """Get user's API key from unified credential source or settings fallback."""
        if self.user and getattr(self.user, 'is_authenticated', False):
            credential = APICredential.get_by_provider(self.user, provider)
            if credential:
                decrypted = credential.get_decrypted_data()
                if decrypted:
                    credential.update_last_used()
                    return decrypted

        env_var = self.PROVIDER_ENV_MAP.get(provider, f'{provider.upper()}_API_KEY')
        return getattr(settings, env_var, None) or __import__('os').environ.get(env_var)

    def _get_base_url(self, provider: str = 'openai') -> Optional[str]:
        """Get base URL for API."""
        if self.user and getattr(self.user, 'is_authenticated', False):
            credential = APICredential.get_by_provider(self.user, provider)
            if credential and credential.service_config:
                return (
                    credential.service_config.get('base_url')
                    or credential.service_config.get('endpoint')
                    or getattr(settings, "OPENAI_BASE_URL", None)
                )
        return getattr(settings, "OPENAI_BASE_URL", None)

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ):
        """Send chat completion request, routing to Ollama for local models."""
        if _is_ollama_model(model) or model in ('llama3', 'llama2', 'mistral', 'codellama'):
            return self._chat_ollama(messages, model, temperature, max_tokens, stream)

        return self._chat_openai(messages, model, temperature, max_tokens, top_p, stream, **kwargs)

    def _chat_ollama(self, messages, model, temperature, max_tokens, stream):
        """Handle chat via Ollama provider."""
        start_time = time.time()
        provider = _get_ollama_provider()

        try:
            if stream:
                return self._handle_ollama_stream(provider, model, messages, temperature, max_tokens, start_time)
            else:
                response = provider.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
                return self._handle_ollama_response(response, model, start_time)
        except Exception as e:
            logger.error(f"Ollama API error: {str(e)}")
            raise

    def _handle_ollama_response(self, response, model, start_time):
        """Handle non-streaming Ollama response."""
        latency_ms = int((time.time() - start_time) * 1000)
        return LLMResponse(
            content=response.content,
            model=model,
            provider="ollama",
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
            latency_ms=latency_ms,
            cost=Decimal("0"),
            finish_reason=response.finish_reason,
            raw_response={}
        )

    def _handle_ollama_stream(self, provider, model, messages, temperature, max_tokens, start_time):
        """Handle streaming Ollama response."""
        content_parts = []
        for chunk in provider.stream_chat(messages, model=model, temperature=temperature, max_tokens=max_tokens):
            if chunk.get('type') == 'content':
                content_parts.append(chunk.get('content', ''))
                yield {'type': 'content', 'content': chunk['content']}
            elif chunk.get('type') == 'done':
                latency_ms = int((time.time() - start_time) * 1000)
                content = ''.join(content_parts)
                estimated = len(content.split()) * 1.3
                yield {
                    'type': 'done',
                    'content': content,
                    'latency_ms': latency_ms,
                    'estimated_tokens': int(estimated),
                    'cost': float(Decimal('0'))
                }

    def _chat_openai(self, messages, model, temperature, max_tokens, top_p, stream, **kwargs):
        """Handle chat via OpenAI-compatible API."""
        from openai import OpenAI

        start_time = time.time()

        try:
            api_key = self.api_key or getattr(settings, "OPENAI_API_KEY", None)
            base_url = self._get_base_url()

            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            client = OpenAI(**client_kwargs)

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=stream,
                **kwargs
            )

            if stream:
                return self._handle_stream_response(response, model, start_time)
            else:
                return self._handle_response(response, model, start_time)

        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            raise

    def _handle_response(self, response, model: str, start_time: float) -> LLMResponse:
        """Handle non-streaming response."""
        latency_ms = int((time.time() - start_time) * 1000)

        choice = response.choices[0]
        content = choice.message.content or ""

        usage = response.usage or {}
        input_tokens = usage.prompt_tokens or 0
        output_tokens = usage.completion_tokens or 0
        total_tokens = usage.total_tokens or 0

        cost = self._calculate_cost(model, input_tokens, output_tokens)

        self._log_api_call(
            provider="openai",
            model=model,
            endpoint="chat/completions",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status_code=200,
            cost=cost
        )

        return LLMResponse(
            content=content,
            model=model,
            provider="openai",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost=cost,
            finish_reason=choice.finish_reason,
            raw_response={}
        )

    def _handle_stream_response(self, response, model: str, start_time: float):
        """Handle streaming response."""
        content_parts = []

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                content_parts.append(token)
                yield {"type": "content", "content": token}

        latency_ms = int((time.time() - start_time) * 1000)
        content = ''.join(content_parts)

        estimated_tokens = len(content.split()) * 1.3
        cost = self._calculate_cost(model, int(estimated_tokens * 0.3), int(estimated_tokens * 0.7))

        yield {
            "type": "done",
            "content": content,
            "latency_ms": latency_ms,
            "estimated_tokens": int(estimated_tokens),
            "cost": cost
        }

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Decimal:
        """Calculate API call cost based on model pricing."""
        input_price, output_price = self.MODEL_PRICING.get(
            model, (Decimal("0.001"), Decimal("0.002"))
        )

        input_cost = (input_tokens / 1000) * float(input_price)
        output_cost = (output_tokens / 1000) * float(output_price)

        return Decimal(str(input_cost + output_cost))

    def _log_api_call(
        self,
        provider: str,
        model: str,
        endpoint: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status_code: int = 200,
        cost: Decimal = None,
        error_message: str = ""
    ):
        """Log API call to database."""
        try:
            from .models import APICallLog

            APICallLog.objects.create(
                user=self.user,
                provider=provider,
                model=model,
                endpoint=endpoint,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=latency_ms,
                status_code=status_code,
                cost=cost or Decimal("0"),
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to log API call: {str(e)}")

    def embeddings(self, texts: List[str], model: str = "text-embedding-ada-002") -> List[List[float]]:
        """Get embeddings for texts."""
        from openai import OpenAI

        api_key = self.api_key or getattr(settings, "OPENAI_API_KEY", None)
        base_url = self._get_base_url()

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)

        response = client.embeddings.create(
            model=model,
            input=texts
        )

        return [item.embedding for item in response.data]


class GatewayService:
    """Unified gateway service for all AI operations."""

    def __init__(self, user=None, api_key: str = None):
        self.user = user
        self.llm_service = LLMService(user=user, api_key=api_key)

    def chat(self, messages: List[Dict], **kwargs):
        """Send chat request through gateway."""
        return self.llm_service.chat(messages, **kwargs)

    def stream_chat(self, messages: List[Dict], **kwargs):
        """Send streaming chat request."""
        return self.llm_service.chat(messages, stream=True, **kwargs)

    def embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Get embeddings through gateway."""
        return self.llm_service.embeddings(texts, **kwargs)

    def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for user."""
        from .models import APICallLog

        cutoff = timezone.now() - timezone.timedelta(days=days)

        stats = APICallLog.objects.filter(
            user=self.user,
            timestamp__gte=cutoff
        ).aggregate(
            total_calls=Count("id"),
            total_input_tokens=Sum("input_tokens"),
            total_output_tokens=Sum("output_tokens"),
            total_cost=Sum("cost"),
            avg_latency=Avg("latency_ms")
        )

        return {
            "total_calls": stats["total_calls"] or 0,
            "total_input_tokens": stats["total_input_tokens"] or 0,
            "total_output_tokens": stats["total_output_tokens"] or 0,
            "total_tokens": (stats["total_input_tokens"] or 0) + (stats["total_output_tokens"] or 0),
            "total_cost": stats["total_cost"] or Decimal("0"),
            "avg_latency": stats["avg_latency"] or 0,
            "days": days
        }
