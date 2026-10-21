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
        super().__init__(
            api_key=(api_key or '').strip() or None,
            base_url=(base_url or '').strip().rstrip('/') or None,
            **kwargs,
        )
        self._client = None

    def _is_volcengine_ark(self) -> bool:
        """Whether this provider targets Volcengine Ark (Doubao)."""
        url = (self.base_url or '').lower()
        return 'volces.com' in url or 'volcengine' in url

    def _is_dashscope(self) -> bool:
        """Whether this provider targets Alibaba Cloud Bailian/DashScope (compatible-mode)."""
        url = (self.base_url or '').lower()
        return 'dashscope' in url or 'compatible-mode' in url or '.maas.aliyuncs.com' in url

    def _is_agnes(self) -> bool:
        """Whether this provider targets Agnes AI API Hub."""
        url = (self.base_url or '').lower()
        return 'agnes-ai.com' in url or 'apihub.agnes' in url

    def _agnes_catalog_models(self) -> List[ModelInfo]:
        if not self._is_agnes():
            return []
        catalog = [
            ('agnes-2.0-flash', 'Agnes 2.0 Flash'),
            ('agnes-image-2.1-flash', 'Agnes Image 2.1 Flash'),
            ('agnes-image-2.0-flash', 'Agnes Image 2.0 Flash'),
            ('agnes-video-v2.0', 'Agnes Video v2.0'),
        ]
        return [
            ModelInfo(
                model_id=model_id,
                name=name,
                provider=self.provider_name,
                model_type='chat' if model_id.startswith('agnes-2') else (
                    'image' if 'image' in model_id else 'video'
                ),
                max_tokens=32768,
                supports_streaming=True,
                context_window=32768,
            )
            for model_id, name in catalog
        ]

    def supports_model(self, model_id: str) -> bool:
        """Support OpenAI models, Volcengine Ark endpoint IDs (ep-*), DashScope Qwen, and Agnes models."""
        if model_id and model_id.startswith('ep-') and self._is_volcengine_ark():
            return True
        if model_id and self._is_dashscope() and (
            model_id.startswith('qwen') or model_id.startswith('qwq') or model_id.startswith('qvq')
        ):
            return True
        if model_id and self._is_agnes() and model_id.startswith('agnes-'):
            return True
        return super().supports_model(model_id)

    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                if not self.api_key:
                    raise ValueError('OpenAI API key is not configured')

                client_kwargs = {'api_key': self.api_key}
                if self.base_url:
                    client_kwargs['base_url'] = self.base_url
                try:
                    from httpx import Timeout
                    client_kwargs['timeout'] = Timeout(180.0, connect=15.0)
                except ImportError:
                    client_kwargs['timeout'] = 180.0

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
        model = model or self.default_model

        try:
            client = self._get_client()

            # Agnes chat models spend completion budget on reasoning_content first.
            # Prefer disabling thinking so workflow nodes get usable text output.
            create_kwargs = dict(kwargs)
            if self._is_agnes() and str(model or '').startswith('agnes-'):
                extra_body = dict(create_kwargs.pop('extra_body', None) or {})
                extra_body.setdefault('enable_thinking', False)
                create_kwargs['extra_body'] = extra_body
                # Keep enough budget if thinking cannot be disabled by the gateway.
                if max_tokens is None or int(max_tokens) < 8192:
                    max_tokens = 8192

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                **create_kwargs
            )

            latency_ms = int((time.time() - start_time) * 1000)
            choice = response.choices[0]
            message = choice.message
            content = (message.content or "").strip()
            if not content:
                # Some gateways put the visible answer only after reasoning tokens.
                # If content is still empty, surface a hard failure instead of silent blank.
                reasoning = getattr(message, 'reasoning_content', None) or ''
                if reasoning and choice.finish_reason == 'length':
                    raise RuntimeError(
                        f'Agnes model {model} exhausted max_tokens on reasoning with empty content. '
                        f'Increase max_tokens (current={max_tokens}) or disable thinking.'
                    )

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

            # Do not swallow provider failures as empty successful completions.
            # Workflow LLM nodes must fail loudly so upstream/downstream configs can be fixed.
            raise

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

    def _volcengine_catalog_models(self) -> List[ModelInfo]:
        """Known Volcengine Ark chat endpoints from project constants."""
        try:
            from nl_to_workflow.constants import VOLCENGINE_ARK_CHAT_MODELS
        except ImportError:
            return []

        catalog = []
        for item in VOLCENGINE_ARK_CHAT_MODELS:
            catalog.append(ModelInfo(
                model_id=item['model_id'],
                name=item.get('name', item['model_id']),
                provider=self.provider_name,
                model_type='chat',
                max_tokens=item.get('max_tokens', 32768),
                supports_streaming=item.get('supports_streaming', True),
                context_window=item.get('context_window', 32768),
            ))
        return catalog

    def list_models(self) -> List[ModelInfo]:
        """List models available from OpenAI API."""
        volcengine_catalog = self._volcengine_catalog_models() if self._is_volcengine_ark() else []
        agnes_catalog = self._agnes_catalog_models() if self._is_agnes() else []

        try:
            client = self._get_client()
            models = client.models.list()

            openai_models = []
            seen_ids = set()
            chat_prefixes = ('gpt-', 'text-', 'dall-', 'tts-', 'whisper-', 'ep-', 'doubao')

            for m in models.data:
                model_id = m.id
                if any(model_id.startswith(prefix) or prefix in model_id for prefix in chat_prefixes):
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
                    seen_ids.add(model_id)

            for item in volcengine_catalog:
                if item.model_id not in seen_ids:
                    openai_models.append(item)

            for item in agnes_catalog:
                if item.model_id not in seen_ids:
                    openai_models.append(item)

            if openai_models:
                return openai_models
        except Exception as e:
            logger.warning(f"Failed to list OpenAI models: {str(e)}")

        if volcengine_catalog:
            return volcengine_catalog
        if agnes_catalog:
            return agnes_catalog
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
