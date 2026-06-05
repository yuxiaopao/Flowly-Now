"""
Anthropic provider adapter for AI gateway.
"""

from typing import Dict, Any, List, Generator, Optional
from decimal import Decimal
import time
import logging

from .base import BaseProvider, ProviderResponse, ModelInfo

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider."""

    provider_name = 'anthropic'
    provider_display_name = 'Anthropic'

    default_model = 'claude-3-5-sonnet-20241022'

    available_models = [
        ModelInfo(
            model_id='claude-3-5-sonnet-20241022',
            name='Claude 3.5 Sonnet',
            provider='anthropic',
            model_type='chat',
            max_tokens=8192,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            input_price=Decimal("3.0"),
            output_price=Decimal("15.0"),
            context_window=200000
        ),
        ModelInfo(
            model_id='claude-3-5-sonnet-latest',
            name='Claude 3.5 Sonnet (Latest)',
            provider='anthropic',
            model_type='chat',
            max_tokens=8192,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            input_price=Decimal("3.0"),
            output_price=Decimal("15.0"),
            context_window=200000
        ),
        ModelInfo(
            model_id='claude-3-opus-latest',
            name='Claude 3 Opus',
            provider='anthropic',
            model_type='chat',
            max_tokens=4096,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            input_price=Decimal("15.0"),
            output_price=Decimal("75.0"),
            context_window=200000
        ),
        ModelInfo(
            model_id='claude-3-haiku-20240307',
            name='Claude 3 Haiku',
            provider='anthropic',
            model_type='chat',
            max_tokens=4096,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            input_price=Decimal("0.25"),
            output_price=Decimal("1.25"),
            context_window=200000
        ),
        ModelInfo(
            model_id='claude-3-sonnet-20240229',
            name='Claude 3 Sonnet',
            provider='anthropic',
            model_type='chat',
            max_tokens=4096,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            input_price=Decimal("3.0"),
            output_price=Decimal("15.0"),
            context_window=200000
        ),
        ModelInfo(
            model_id='claude-3-opus-20240229',
            name='Claude 3 Opus',
            provider='anthropic',
            model_type='chat',
            max_tokens=4096,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            input_price=Decimal("15.0"),
            output_price=Decimal("75.0"),
            context_window=200000
        ),
        ModelInfo(
            model_id='claude-2.1',
            name='Claude 2.1',
            provider='anthropic',
            model_type='chat',
            max_tokens=4096,
            supports_streaming=True,
            supports_function_calling=False,
            supports_vision=False,
            input_price=Decimal("8.0"),
            output_price=Decimal("24.0"),
            context_window=200000
        ),
        ModelInfo(
            model_id='claude-2.0',
            name='Claude 2.0',
            provider='anthropic',
            model_type='chat',
            max_tokens=4096,
            supports_streaming=True,
            supports_function_calling=False,
            supports_vision=False,
            input_price=Decimal("8.0"),
            output_price=Decimal("24.0"),
            context_window=100000
        ),
        ModelInfo(
            model_id='claude-instant-1.2',
            name='Claude Instant',
            provider='anthropic',
            model_type='chat',
            max_tokens=4096,
            supports_streaming=True,
            supports_function_calling=False,
            supports_vision=False,
            input_price=Decimal("0.8"),
            output_price=Decimal("2.4"),
            context_window=100000
        ),
    ]

    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        super().__init__(api_key, base_url, **kwargs)
        self._client = None
        self._anthropic_base_url = base_url or "https://api.anthropic.com/v1"

    def _get_client(self):
        """Get or create Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic
            except ImportError:
                logger.error("Anthropic package not installed. Run: pip install anthropic")
                raise

        return self._client

    def connect(self) -> bool:
        """Test connection to Anthropic API."""
        try:
            import httpx

            headers = {
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }

            with httpx.Client() as client:
                response = client.get(
                    f"{self._anthropic_base_url}/messages",
                    headers=headers,
                    json={'model': self.default_model, 'max_tokens': 1}
                )
                return response.status_code in [200, 400, 401]
        except Exception as e:
            logger.error(f"Anthropic connection test failed: {str(e)}")
            return False

    def _convert_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Convert OpenAI-style messages to Anthropic format.

        Anthropic requires system prompt to be separate from messages.
        """
        system_prompt = ""
        anthropic_messages = []

        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if role == 'system':
                system_prompt += content + "\n\n"
            elif role == 'user':
                anthropic_messages.append({
                    'role': 'user',
                    'content': content
                })
            elif role == 'assistant':
                anthropic_messages.append({
                    'role': 'assistant',
                    'content': content
                })

        return {
            'system': system_prompt.strip() or None,
            'messages': anthropic_messages
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
        """Send chat completion request to Anthropic."""
        start_time = time.time()
        model = model or self.default_model

        try:
            converted = self._convert_messages(messages)

            client = self._get_client()
            api_key = self.api_key

            import httpx

            headers = {
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
                'anthropic-dangerous-direct-browser-access': 'true'
            }

            payload = {
                'model': model,
                'messages': converted['messages'],
                'temperature': temperature,
                'max_tokens': max_tokens,
            }

            if converted['system']:
                payload['system'] = converted['system']

            if top_p < 1.0:
                payload['top_p'] = top_p

            if kwargs.get('stop_sequences'):
                payload['stop_sequences'] = kwargs['stop_sequences']

            with httpx.Client(timeout=120.0) as http_client:
                response = http_client.post(
                    f"{self._anthropic_base_url}/messages",
                    headers=headers,
                    json=payload
                )

                latency_ms = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    error_body = response.json()
                    error_msg = error_body.get('error', {}).get('message', response.text)
                    logger.error(f"Anthropic API error: {error_msg}")

                    self.log_request(
                        model=model,
                        endpoint='messages',
                        input_tokens=0,
                        output_tokens=0,
                        latency_ms=latency_ms,
                        status_code=response.status_code,
                        error_message=error_msg
                    )

                    return ProviderResponse(
                        content="",
                        model=model,
                        provider=self.provider_name,
                        latency_ms=latency_ms,
                        error=error_msg
                    )

                data = response.json()
                content = data.get('content', [{}])[0].get('text', '')
                usage = data.get('usage', {})

                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
                total_tokens = input_tokens + output_tokens

                cost = self.calculate_cost(model, input_tokens, output_tokens)

                self.log_request(
                    model=model,
                    endpoint='messages',
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
                    finish_reason=data.get('stop_reason'),
                    raw_response=data
                )

        except ImportError as e:
            logger.error(f"Anthropic import error: {str(e)}")
            return ProviderResponse(
                content="",
                model=model,
                provider=self.provider_name,
                error=f"Dependencies not installed: {str(e)}"
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Anthropic chat error: {str(e)}")

            self.log_request(
                model=model,
                endpoint='messages',
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status_code=500,
                error_message=str(e)
            )

            return ProviderResponse(
                content="",
                model=model,
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
        """Send streaming chat completion request to Anthropic."""
        start_time = time.time()
        model = model or self.default_model
        content = ""

        try:
            converted = self._convert_messages(messages)

            import httpx

            headers = {
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
                'anthropic-dangerous-direct-browser-access': 'true'
            }

            payload = {
                'model': model,
                'messages': converted['messages'],
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': True
            }

            if converted['system']:
                payload['system'] = converted['system']

            with httpx.Client(timeout=120.0) as http_client:
                with http_client.stream(
                    'POST',
                    f"{self._anthropic_base_url}/messages",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', response.text)
                        yield {'type': 'error', 'error': error_msg}
                        return

                    for line in response.iter_lines():
                        if line.startswith('data: '):
                            data_str = line[6:]

                            if data_str == '[DONE]':
                                latency_ms = int((time.time() - start_time) * 1000)
                                estimated_tokens = len(content.split()) * 1.3
                                cost = self.calculate_cost(
                                    model,
                                    0,
                                    int(estimated_tokens)
                                )

                                yield {
                                    'type': 'done',
                                    'content': content,
                                    'latency_ms': latency_ms,
                                    'estimated_tokens': int(estimated_tokens),
                                    'cost': cost
                                }
                                return

                            try:
                                import json
                                event_data = json.loads(data_str)

                                event_type = event_data.get('type', '')

                                if event_type == 'content_block_delta':
                                    delta = event_data.get('delta', {})
                                    if delta.get('type') == 'text_delta':
                                        text = delta.get('text', '')
                                        content += text
                                        yield {'type': 'content', 'content': text}

                                elif event_type == 'message_delta':
                                    delta = event_data.get('delta', {})
                                    if delta.get('type') == 'stop_delta':
                                        yield {'type': 'finish', 'finish_reason': event_data.get('stop_reason')}

                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Anthropic stream error: {str(e)}")
            yield {'type': 'error', 'error': str(e)}

    def embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """
        Generate embeddings for texts.

        Note: Anthropic does not provide an embeddings API.
        This method uses OpenAI embeddings as a fallback or returns an error.
        """
        logger.warning("Anthropic does not provide embeddings API. Use OpenAI provider instead.")

        try:
            from .openai_provider import OpenAIProvider
            openai_provider = OpenAIProvider(api_key=self.api_key, base_url=self.base_url)
            return openai_provider.embeddings(texts, model='text-embedding-3-small')
        except Exception as e:
            logger.error(f"Fallback embeddings failed: {str(e)}")
            raise NotImplementedError(
                "Anthropic does not have an embeddings API. "
                "Please configure an OpenAI provider for embeddings."
            )

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Decimal:
        """Calculate cost based on Anthropic's pricing."""
        pricing = {
            'claude-3-5-sonnet-20241022': (Decimal("3.0"), Decimal("15.0")),
            'claude-3-5-sonnet-latest': (Decimal("3.0"), Decimal("15.0")),
            'claude-3-opus-latest': (Decimal("15.0"), Decimal("75.0")),
            'claude-3-haiku-20240307': (Decimal("0.25"), Decimal("1.25")),
            'claude-3-sonnet-20240229': (Decimal("3.0"), Decimal("15.0")),
            'claude-3-opus-20240229': (Decimal("15.0"), Decimal("75.0")),
            'claude-2.1': (Decimal("8.0"), Decimal("24.0")),
            'claude-2.0': (Decimal("8.0"), Decimal("24.0")),
            'claude-instant-1.2': (Decimal("0.8"), Decimal("2.4")),
        }

        input_price, output_price = pricing.get(model, (Decimal("3.0"), Decimal("15.0")))

        input_cost = (input_tokens / 1000000) * float(input_price)
        output_cost = (output_tokens / 1000000) * float(output_price)

        return Decimal(str(input_cost + output_cost))

    def list_models(self) -> List[ModelInfo]:
        """Return list of available Anthropic models."""
        return self.available_models

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Anthropic API.
        
        Returns:
            Dict with status and latency_ms
        """
        import httpx
        start = time.time()
        
        try:
            headers = {
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }
            
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self._anthropic_base_url}/messages",
                    headers=headers,
                    json={'model': self.default_model, 'max_tokens': 1}
                )
                latency_ms = int((time.time() - start) * 1000)
                
                if response.status_code in [200, 400, 401]:
                    return {
                        'status': 'ok',
                        'latency_ms': latency_ms
                    }
                else:
                    return {
                        'status': 'error',
                        'latency_ms': latency_ms,
                        'error': f'HTTP {response.status_code}'
                    }
        except httpx.TimeoutException:
            return {
                'status': 'timeout',
                'latency_ms': int((time.time() - start) * 1000),
                'error': 'Connection timeout'
            }
        except Exception as e:
            return {
                'status': 'error',
                'latency_ms': int((time.time() - start) * 1000),
                'error': str(e)
            }
