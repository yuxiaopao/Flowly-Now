"""
Ollama provider for local LLM inference.
"""

import time
import logging
import json
import requests
from typing import Dict, Any, List, Generator, Optional
from decimal import Decimal

from .base import BaseProvider, ProviderResponse, ModelInfo

logger = logging.getLogger(__name__)

# Import constants for default values
from config.constants import (
    OLLAMA_BASE_URL,
    OLLAMA_HEALTH_CHECK_TIMEOUT,
    OLLAMA_CHAT_TIMEOUT,
    OLLAMA_EMBEDDINGS_TIMEOUT,
    OLLAMA_CONNECT_TIMEOUT,
    OLLAMA_LIST_MODELS_TIMEOUT,
    DEFAULT_OLLAMA_MODEL,
)


class OllamaProvider(BaseProvider):
    """Provider for Ollama local models."""

    provider_name = 'ollama'
    provider_display_name = 'Ollama (本地)'

    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        from django.conf import settings
        super().__init__(
            api_key=api_key or '',
            base_url=base_url or getattr(settings, 'OLLAMA_BASE_URL', None),
            **kwargs
        )
        self._cached_models: List[ModelInfo] = None
        # Resolve base_url: fall back to settings value or constant default
        if not self.base_url:
            self.base_url = getattr(settings, 'OLLAMA_BASE_URL', OLLAMA_BASE_URL)

    @property
    def default_model(self) -> str:
        models = self.list_models()
        return models[0].model_id if models else DEFAULT_OLLAMA_MODEL

    @property
    def available_models(self) -> List[ModelInfo]:
        return self.list_models()

    def connect(self) -> bool:
        """Test connection to Ollama server."""
        try:
            resp = requests.get(f'{self.base_url}/api/tags', timeout=OLLAMA_CONNECT_TIMEOUT)
            return resp.status_code == 200
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Ollama server.
        
        Returns:
            Dict with status, latency_ms, and models_count
        """
        start = time.time()
        try:
            resp = requests.get(f'{self.base_url}/api/tags', timeout=OLLAMA_HEALTH_CHECK_TIMEOUT)
            latency_ms = int((time.time() - start) * 1000)
            
            if resp.status_code == 200:
                data = resp.json()
                models_count = len(data.get('models', []))
                return {
                    'status': 'ok',
                    'latency_ms': latency_ms,
                    'models_count': models_count
                }
            else:
                return {
                    'status': 'error',
                    'latency_ms': latency_ms,
                    'error': f'HTTP {resp.status_code}'
                }
        except requests.exceptions.Timeout:
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

    def supports_model(self, model_id: str) -> bool:
        """Check if provider supports a specific model."""
        if self._cached_models is None:
            self.list_models()
        if self._cached_models:
            return any(m.model_id == model_id for m in self._cached_models)
        return True

    def list_models(self) -> List[ModelInfo]:
        """
        List available models from Ollama server.
        
        Uses /api/tags endpoint to discover locally available models.
        """
        try:
            resp = requests.get(f'{self.base_url}/api/tags', timeout=OLLAMA_LIST_MODELS_TIMEOUT)
            if resp.status_code != 200:
                self._cached_models = []
                return []
            data = resp.json()
            models = []
            for m in data.get('models', []):
                name = m.get('name', '')
                details = m.get('details', {})
                param_size = details.get('parameter_size', '')
                # Check capabilities from model info
                capabilities = details.get('capabilities', [])
                supports_functions = 'tools' in capabilities or 'function calling' in capabilities
                
                models.append(ModelInfo(
                    model_id=name,
                    name=f"{name} ({param_size})" if param_size else name,
                    provider='ollama',
                    model_type='chat',
                    max_tokens=4096,
                    supports_streaming=True,
                    supports_function_calling=supports_functions,
                    supports_vision='vision' in name.lower() or 'llava' in name.lower(),
                    input_price=Decimal("0"),
                    output_price=Decimal("0"),
                    context_window=int(details.get('context_length', 8192) or 8192),
                ))
            self._cached_models = models
            return models
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            self._cached_models = []
            return []

    def invalidate_cache(self):
        """Invalidate the cached model list."""
        self._cached_models = None

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        tools: List[Dict] = None,
        stream: bool = False,
        **kwargs
    ) -> ProviderResponse:
        """
        Send chat completion request to Ollama.
        
        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model identifier (e.g., 'llama3', 'mistral')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            tools: Optional list of tools/functions for function calling
            stream: Whether to stream the response (not used in non-stream mode)
            **kwargs: Additional provider-specific parameters
        """
        start = time.time()
        model = model or self.default_model
        
        try:
            # Build request payload
            payload = {
                'model': model,
                'messages': messages,
                'stream': False,
                'options': {
                    'temperature': temperature,
                    'num_predict': max_tokens,
                    'top_p': top_p,
                }
            }
            
            # Add tools/function calling support if provided
            if tools:
                # Ollama uses 'tools' parameter for function calling
                # Convert OpenAI-style tools to Ollama format
                ollama_tools = self._convert_tools(tools)
                payload['tools'] = ollama_tools
            
            resp = requests.post(
                f'{self.base_url}/api/chat',
                json=payload,
                timeout=OLLAMA_CHAT_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            latency = int((time.time() - start) * 1000)
            
            # Handle tool calls if present
            if 'tool_calls' in data.get('message', {}):
                # Model wants to call a function
                tool_calls = data['message']['tool_calls']
                content = data.get('message', {}).get('content', '')
                return ProviderResponse(
                    content=content,
                    model=model,
                    provider=self.provider_name,
                    input_tokens=data.get('prompt_eval_count', 0),
                    output_tokens=data.get('eval_count', 0),
                    total_tokens=data.get('prompt_eval_count', 0) + data.get('eval_count', 0),
                    latency_ms=latency,
                    cost=Decimal("0"),
                    finish_reason=data.get('done_reason', 'tool_calls'),
                    raw_response={'tool_calls': tool_calls, 'content': content},
                )
            
            content = data.get('message', {}).get('content', '')
            return ProviderResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                input_tokens=data.get('prompt_eval_count', 0),
                output_tokens=data.get('eval_count', 0),
                total_tokens=data.get('prompt_eval_count', 0) + data.get('eval_count', 0),
                latency_ms=latency,
                cost=Decimal("0"),
                finish_reason=data.get('done_reason', 'stop'),
                raw_response=data,
            )
        except requests.exceptions.HTTPError as e:
            latency = int((time.time() - start) * 1000)
            error_msg = str(e)
            # Try to extract error from response
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
                    pass
            return ProviderResponse(
                content='', model=model, provider=self.provider_name,
                latency_ms=latency, error=error_msg
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return ProviderResponse(
                content='', model=model, provider=self.provider_name,
                latency_ms=latency, error=str(e)
            )

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """
        Convert OpenAI-style tools to Ollama format.
        
        Ollama expects tools in a specific format:
        {
            "type": "function",
            "function": {
                "name": "function_name",
                "description": "description",
                "parameters": {...}
            }
        }
        """
        ollama_tools = []
        for tool in tools:
            if tool.get('type') == 'function':
                # Already in OpenAI format, extract function details
                func = tool.get('function', {})
                ollama_tools.append({
                    'type': 'function',
                    'function': {
                        'name': func.get('name'),
                        'description': func.get('description'),
                        'parameters': func.get('parameters', {'type': 'object', 'properties': {}})
                    }
                })
            elif 'function' in tool:
                # Direct function definition
                ollama_tools.append(tool)
        return ollama_tools

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: List[Dict] = None,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Send streaming chat completion request to Ollama.
        
        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional list of tools/functions for function calling
            **kwargs: Additional provider-specific parameters
        
        Yields:
            Dict with 'type' ('content', 'tool_call', 'done', or 'error') and relevant data
        """
        import json as json_mod
        model = model or self.default_model
        
        try:
            # Build request payload
            payload = {
                'model': model,
                'messages': messages,
                'stream': True,
                'options': {
                    'temperature': temperature,
                    'num_predict': max_tokens,
                }
            }
            
            # Add tools/function calling support if provided
            if tools:
                ollama_tools = self._convert_tools(tools)
                payload['tools'] = ollama_tools
            
            resp = requests.post(
                f'{self.base_url}/api/chat',
                json=payload,
                timeout=OLLAMA_CHAT_TIMEOUT, stream=True
            )
            resp.raise_for_status()
            
            tool_calls_buffer = []
            
            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json_mod.loads(line)
                        
                        # Check for tool calls
                        if 'message' in chunk and 'tool_calls' in chunk['message']:
                            # Model wants to call a function
                            for tc in chunk['message']['tool_calls']:
                                tool_calls_buffer.append(tc)
                                yield {
                                    'type': 'tool_call',
                                    'tool_call': tc
                                }
                        
                        # Regular content
                        content = chunk.get('message', {}).get('content', '')
                        if content:
                            yield {'type': 'content', 'content': content}
                        
                        # Stream done
                        if chunk.get('done'):
                            input_tokens = chunk.get('prompt_eval_count', 0)
                            output_tokens = chunk.get('eval_count', 0)
                            
                            # If we had tool calls, include them in the done response
                            done_payload = {
                                'type': 'done',
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'total_tokens': input_tokens + output_tokens,
                            }
                            
                            if tool_calls_buffer:
                                done_payload['tool_calls'] = tool_calls_buffer
                            
                            yield done_payload
                            
                    except json_mod.JSONDecodeError:
                        continue
                        
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
                    pass
            yield {'type': 'error', 'error': error_msg}
        except Exception as e:
            yield {'type': 'error', 'error': str(e)}

    def embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """
        Generate embeddings for texts using Ollama's embedding API.
        
        Args:
            texts: List of texts to embed
            model: Embedding model identifier (default: 'nomic-embed-text')
        
        Returns:
            List of embedding vectors
        """
        results = []
        embed_model = model or 'nomic-embed-text'
        
        for text in texts:
            try:
                resp = requests.post(
                    f'{self.base_url}/api/embeddings',
                    json={'model': embed_model, 'prompt': text},
                    timeout=OLLAMA_EMBEDDINGS_TIMEOUT
                )
                resp.raise_for_status()
                embedding = resp.json().get('embedding', [])
                results.append(embedding)
            except requests.exceptions.HTTPError as e:
                logger.warning(f"Ollama embeddings error for model {embed_model}: {e}")
                results.append([])
            except Exception as e:
                logger.warning(f"Ollama embeddings error: {e}")
                results.append([])
        
        return results

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Decimal:
        """Calculate cost for Ollama - always returns 0 since Ollama is free."""
        return Decimal("0")
    
    def get_model_info(self, model: str = None) -> Optional[ModelInfo]:
        """
        Get detailed info for a specific model.
        
        Args:
            model: Model identifier
            
        Returns:
            ModelInfo or None if model not found
        """
        model = model or self.default_model
        for m in self.list_models():
            if m.model_id == model:
                return m
        return None
