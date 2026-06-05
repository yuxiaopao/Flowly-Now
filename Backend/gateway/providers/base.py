"""
Base provider interface for AI model gateway.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Generator, Callable
from dataclasses import dataclass
from decimal import Decimal
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProviderResponse:
    """Standard response from AI provider."""
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost: Decimal = Decimal("0")
    finish_reason: str = None
    raw_response: Dict = None
    error: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'model': self.model,
            'provider': self.provider,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'latency_ms': self.latency_ms,
            'cost': float(self.cost),
            'finish_reason': self.finish_reason,
            'error': self.error
        }


@dataclass
class ModelInfo:
    """Information about a model from a provider."""
    model_id: str
    name: str
    provider: str
    model_type: str = 'chat'
    max_tokens: int = 4096
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False
    input_price: Decimal = Decimal("0")
    output_price: Decimal = Decimal("0")
    context_window: int = 8192


class BaseProvider(ABC):
    """Abstract base class for AI model providers."""

    provider_name: str = None
    provider_display_name: str = None

    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        """
        Initialize the provider.

        Args:
            api_key: API key for authentication
            base_url: Custom base URL (for proxies, etc.)
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs
        self._client = None

    @abstractmethod
    def connect(self) -> bool:
        """
        Test connection to the provider.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        **kwargs
    ) -> ProviderResponse:
        """
        Send a chat completion request.

        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model identifier (provider-specific)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional provider-specific parameters

        Returns:
            ProviderResponse with the model's response
        """
        pass

    @abstractmethod
    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Send a streaming chat completion request.

        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            Dict with 'type' ('content' or 'done') and relevant data
        """
        pass

    @abstractmethod
    def embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Embedding model identifier

        Returns:
            List of embedding vectors
        """
        pass

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Decimal:
        """
        Calculate cost for a request.

        Override this method to provide custom pricing.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        return Decimal("0")

    def log_request(
        self,
        model: str,
        endpoint: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status_code: int = 200,
        cost: Decimal = None,
        error_message: str = ""
    ):
        """
        Log API request to database.

        Args:
            model: Model identifier
            endpoint: API endpoint called
            input_tokens: Input token count
            output_tokens: Output token count
            latency_ms: Request latency
            status_code: HTTP status code
            cost: Request cost
            error_message: Error message if any
        """
        try:
            from ..models import APICallLog
            from django.contrib.auth import get_user_model
            User = get_user_model()

            user = self.config.get('user')
            if user and isinstance(user, User):
                APICallLog.objects.create(
                    user=user,
                    provider=self.provider_name,
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

    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        return self.default_model

    def list_models(self) -> List[ModelInfo]:
        """List available models from this provider."""
        return self.available_models

    def supports_model(self, model_id: str) -> bool:
        """Check if provider supports a specific model."""
        return any(m.model_id == model_id for m in self.available_models)

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider."""
        pass

    @property
    @abstractmethod
    def available_models(self) -> List[ModelInfo]:
        """List of available models for this provider."""
        pass


class StreamingIterator:
    """Helper class to iterate over streaming responses."""

    def __init__(self, generator: Generator, on_chunk: Callable[[str], None] = None):
        self.generator = generator
        self.on_chunk = on_chunk
        self.content = ""

    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = next(self.generator)
            if self.on_chunk and chunk.get('type') == 'content':
                self.content += chunk.get('content', '')
            return chunk
        except StopIteration:
            raise

    def get_content(self) -> str:
        return self.content
