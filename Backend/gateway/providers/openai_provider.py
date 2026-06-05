"""
OpenAI provider adapter for AI gateway.
"""

from typing import Dict, Any, List, Generator, Optional, Optional
from decimal import Decimal
import time
import logging

from .base import BaseProvider, ProviderResponse, ModelInfo

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI API provider."""

    provider_name = 'openai'
    provider_display_name = 'OpenAI'

    default_model = 'gpt-3.5-turbo'

    available_models = [
        ModelInfo(
            model_id='gpt-4o',
            name='GPT-4o',
            provider='openai',
            model_type='chat',
            max_tokens=128000,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            input_price=Decimal("5.0"),
            output_price=Decimal("15.0"),
            context_window=128000
        ),
        ModelInfo(
            model_id='gpt-4o-mini',
            name='GPT-4o Mini',
            provider='openai',
            model_type='chat',
            max_tokens=128000,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            input_price=Decimal("0.15"),
            output_price=Decimal("0.6"),
            context_window=128000
        ),
        ModelInfo(
            model_id='gpt-4-turbo',
            name='GPT-4 Turbo',
            provider='openai',
            model_type='chat',
            max_tokens=128000,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            input_price=Decimal("10.0"),
            output_price=Decimal("30.0"),
            context_window=128000
        ),
        ModelInfo(
            model_id='gpt-4',
            name='GPT-4',
            provider='openai',
            model_type='chat',
            max_tokens=8192,
            supports_streaming=True,
            supports_function_calling=True,
            input_price=Decimal("30.0"),
            output_price=Decimal("60.0"),
            context_window=8192
        ),
        ModelInfo(
            model_id='gpt-3.5-turbo',
            name='GPT-3.5 Turbo',
            provider='openai',
            model_type='chat',
            max_tokens=16385,
            supports_streaming=True,
            supports_function_calling=True,
            input_price=Decimal("0.5"),
            output_price=Decimal("1.5"),
            context_window=16385
        ),
        ModelInfo(
            model_id='gpt-3.5-turbo-16k',
            name='GPT-3.5 Turbo 16K',
            provider='openai',
            model_type='chat',
            max_tokens=16384,
            supports_streaming=True,
            supports_function_calling=True,
            input_price=Decimal("1.0"),
            output_price=Decimal("2.0"),
            context_window=16384
        ),
        ModelInfo(
            model_id='text-embedding-3-small',
            name='Embedding 3 Small',
            provider='openai',
            model_type='embedding',
            max_tokens=8191,
            supports_streaming=False,
            input_price=Decimal("0.02"),
            output_price=Decimal("0"),
            context_window=8191
        ),
        ModelInfo(
            model_id='text-embedding-3-large',
            name='Embedding 3 Large',
            provider='openai',
            model_type='embedding',
            max_tokens=8191,
            supports_streaming=False,
            input_price=Decimal("0.13"),
            output_price=Decimal("0"),
            context_window=8191
        ),
        ModelInfo(
            model_id='text-embedding-ada-002',
            name='Embedding Ada 002',
            provider='openai',
            model_type='embedding',
            max_tokens=8191,
            supports_streaming=False,
            input_price=Decimal("0.1"),
            output_price=Decimal("0"),
            context_window=8191
        ),
        ModelInfo(
            model_id='dall-e-3',
            name='DALL-E 3',
            provider='openai',
            model_type='image',
            max_tokens=4000,
            supports_streaming=False,
            input_price=Decimal("4.0"),
            output_price=Decimal("0"),
            context_window=4000
        ),
        ModelInfo(
            model_id='dall-e-2',
            name='DALL-E 2',
            provider='openai',
            model_type='image',
            max_tokens=1000,
            supports_streaming=False,
            input_price=Decimal("0.02"),
            output_price=Decimal("0"),
            context_window=1000
        ),
        ModelInfo(
            model_id='tts-1',
            name='Text-to-Speech 1',
            provider='openai',
            model_type='audio',
            max_tokens=4096,
            supports_streaming=False,
            input_price=Decimal("15.0"),
            output_price=Decimal("0"),
            context_window=4096
        ),
        ModelInfo(
            model_id='whisper-1',
            name='Whisper 1',
            provider='openai',
            model_type='audio',
            max_tokens=None,
            supports_streaming=False,
            input_price=Decimal("0.006"),
            output_price=Decimal("0"),
            context_window=None
        ),
    ]

    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        super().__init__(api_key, base_url, **kwargs)
        self._client = None

    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                client_kwargs = {'api_key': self.api_key}
                if self.base_url:
                    client_kwargs['base_url'] = self.base_url

                self._client = OpenAI(**client_kwargs)
            except ImportError:
                logger.error("OpenAI package not installed. Run: pip install openai")
                raise

        return self._client

    def connect(self) -> bool:
        """Test connection to OpenAI API."""
        try:
            client = self._get_client()
            client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {str(e)}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on OpenAI API.
        
        Returns:
            Dict with status and latency_ms
        """
        import time
        start = time.time()
        
        try:
            client = self._get_client()
            client.models.list()
            latency_ms = int((time.time() - start) * 1000)
            return {
                'status': 'ok',
                'latency_ms': latency_ms
            }
        except Exception as e:
            return {
                'status': 'error',
                'latency_ms': int((time.time() - start) * 1000),
                'error': str(e)
            }

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        **kwargs
    ) -> ProviderResponse:
        """Send chat completion request to OpenAI."""
        start_time = time.time()

        try:
            client = self._get_client()
            model = model or self.default_model

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                **kwargs
            )

            latency_ms = int((time.time() - start_time) * 1000)
            choice = response.choices[0]
            content = choice.message.content or ""

            usage = response.usage or {}
            input_tokens = usage.prompt_tokens or 0
            output_tokens = usage.completion_tokens or 0
            total_tokens = usage.total_tokens or 0

            cost = self.calculate_cost(model, input_tokens, output_tokens)

            self.log_request(
                model=model,
                endpoint='chat/completions',
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost=cost
            )

            return ProviderResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost=cost,
                finish_reason=choice.finish_reason,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else {}
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"OpenAI chat error: {str(e)}")

            self.log_request(
                model=model or self.default_model,
                endpoint='chat/completions',
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status_code=500,
                error_message=str(e)
            )

            return ProviderResponse(
                content="",
                model=model or self.default_model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                error=str(e)
            )

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """Send streaming chat completion request to OpenAI."""
        start_time = time.time()
        model = model or self.default_model
        content = ""

        try:
            client = self._get_client()

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    content += token
                    yield {'type': 'content', 'content': token}

                if chunk.choices and chunk.choices[0].finish_reason:
                    yield {
                        'type': 'finish',
                        'finish_reason': chunk.choices[0].finish_reason
                    }

            latency_ms = int((time.time() - start_time) * 1000)
            estimated_tokens = len(content.split()) * 1.3
            cost = self.calculate_cost(
                model,
                int(estimated_tokens * 0.3),
                int(estimated_tokens * 0.7)
            )

            yield {
                'type': 'done',
                'content': content,
                'latency_ms': latency_ms,
                'estimated_tokens': int(estimated_tokens),
                'cost': cost
            }

        except Exception as e:
            logger.error(f"OpenAI stream error: {str(e)}")
            yield {'type': 'error', 'error': str(e)}

    def embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """Generate embeddings using OpenAI's embedding models."""
        model = model or 'text-embedding-ada-002'

        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=model,
                input=texts
            )

            return [item.embedding for item in response.data]

        except Exception as e:
            logger.error(f"OpenAI embeddings error: {str(e)}")
            raise

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Decimal:
        """Calculate cost based on OpenAI's pricing."""
        pricing = {
            'gpt-4o': (Decimal("5.0"), Decimal("15.0")),
            'gpt-4o-mini': (Decimal("0.15"), Decimal("0.6")),
            'gpt-4-turbo': (Decimal("10.0"), Decimal("30.0")),
            'gpt-4': (Decimal("30.0"), Decimal("60.0")),
            'gpt-4-32k': (Decimal("60.0"), Decimal("120.0")),
            'gpt-3.5-turbo': (Decimal("0.5"), Decimal("1.5")),
            'gpt-3.5-turbo-16k': (Decimal("1.0"), Decimal("2.0")),
            'text-embedding-3-small': (Decimal("0.02"), Decimal("0")),
            'text-embedding-3-large': (Decimal("0.13"), Decimal("0")),
            'text-embedding-ada-002': (Decimal("0.1"), Decimal("0")),
            'dall-e-3': (Decimal("4.0"), Decimal("0")),
            'dall-e-2': (Decimal("0.02"), Decimal("0")),
        }

        input_price, output_price = pricing.get(model, (Decimal("0.5"), Decimal("1.5")))

        input_cost = (input_tokens / 1000000) * float(input_price)
        output_cost = (output_tokens / 1000000) * float(output_price)

        return Decimal(str(input_cost + output_cost))

    def list_models(self) -> List[ModelInfo]:
        """List models available from OpenAI API."""
        try:
            client = self._get_client()
            models = client.models.list()

            openai_models = []
            for m in models.data:
                model_id = m.id
                if any(prefix in model_id for prefix in ['gpt-', 'text-', 'dall-', 'tts-', 'whisper-']):
                    model_type = 'chat'
                    if 'embedding' in model_id:
                        model_type = 'embedding'
                    elif 'dall' in model_id:
                        model_type = 'image'
                    elif 'tts' in model_id or 'whisper' in model_id:
                        model_type = 'audio'

                    openai_models.append(ModelInfo(
                        model_id=model_id,
                        name=model_id,
                        provider=self.provider_name,
                        model_type=model_type
                    ))

            return openai_models
        except Exception as e:
            logger.warning(f"Failed to list OpenAI models: {str(e)}")
            return self.available_models


class AzureOpenAIProvider(OpenAIProvider):
    """Azure OpenAI Service provider."""

    provider_name = 'azure-openai'
    provider_display_name = 'Azure OpenAI'

    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        super().__init__(api_key, base_url, **kwargs)
        self.api_version = kwargs.get('api_version', '2024-02-01')
        self.deployment_name = kwargs.get('deployment_name')

    def _get_client(self):
        """Get or create Azure OpenAI client."""
        if self._client is None:
            try:
                from openai import AzureOpenAI

                client_kwargs = {
                    'api_key': self.api_key,
                    'api_version': self.api_version,
                    'azure_endpoint': self.base_url
                }

                self._client = AzureOpenAI(**client_kwargs)
            except ImportError:
                logger.error("OpenAI package not installed")
                raise

        return self._client

    def chat(self, messages, model=None, **kwargs):
        """Send chat completion to Azure OpenAI."""
        model = self.deployment_name or model
        return super().chat(messages, model=model, **kwargs)

    def stream_chat(self, messages, model=None, **kwargs):
        """Send streaming chat to Azure OpenAI."""
        model = self.deployment_name or model
        return super().stream_chat(messages, model=model, **kwargs)
