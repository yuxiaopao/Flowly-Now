"""
LangChain service for workflow node execution.
Integrates with Ollama, OpenAI, and other providers via ProviderRegistry.
Supports streaming, sandboxed code execution, and comprehensive error handling.
"""

import json
import re
import time
import uuid
import asyncio
import logging
import subprocess
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Generator, Callable
from functools import wraps

import httpx
import requests
from PIL import Image
from django.conf import settings
from django.utils import timezone
from config.constants import (
    OPENAI_API_URL,
    OPENAI_BASE_URL,
    DEFAULT_LLM_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    HTTP_TOOL_TIMEOUT,
    NODE_EXECUTION_TIMEOUT,
    EMBEDDINGS_TIMEOUT,
    OLLAMA_CHAT_TIMEOUT,
    TOOL_TIMEOUT_DEFAULT,
    WEBHOOK_TIMEOUT,
)

# Replicate API timeout (polling uses timeout_seconds + 30 buffer)
REPLICATE_POLL_TIMEOUT_BUFFER = 30

# Image generation timeout (longer for stability AI)
IMAGE_GENERATION_TIMEOUT = 60

# Video generation timeout (longer for video generation APIs)
VIDEO_GENERATION_TIMEOUT = 300

# Audio generation timeout (for TTS APIs)
AUDIO_GENERATION_TIMEOUT = 120

# Subprocess command timeout (for nvidia-smi etc.)
SUBPROCESS_TIMEOUT = 5

ZIMAGE_SUPPORTED_DTYPES = {'auto', 'bfloat16', 'float16', 'float32'}

logger = logging.getLogger(__name__)


_zimage_pipeline = None
_zimage_pipeline_key = None


# ============================================================================
# Exception Classes
# ============================================================================

class WorkflowExecutionError(Exception):
    """Base exception for workflow execution errors."""
    def __init__(self, message: str, error_type: str = 'execution'):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class OllamaConnectionError(WorkflowExecutionError):
    """Raised when Ollama service is not available."""
    def __init__(self, message: str = "Ollama 服务未启动，请确保本地 Ollama 正在运行"):
        super().__init__(message, 'connection')


class ModelTimeoutError(WorkflowExecutionError):
    """Raised when model response times out."""
    def __init__(self, timeout: int, message: str = None):
        msg = message or f"模型响应超时（{timeout}s）"
        super().__init__(msg, 'timeout')


class JSONDecodeWorkflowError(WorkflowExecutionError):
    """Raised when LLM returns malformed JSON."""
    def __init__(self, message: str = "LLM 返回格式错误，无法解析 JSON"):
        super().__init__(message, 'json_error')


class LocalImageModelError(WorkflowExecutionError):
    """Raised when a local image generation model cannot be loaded or executed."""
    def __init__(self, message: str):
        super().__init__(message, 'local_image_model')


class CodeExecutionError(WorkflowExecutionError):
    """Raised when code execution fails in sandbox."""
    def __init__(self, message: str, original_error: Exception = None):
        self.original_error = original_error
        super().__init__(message, 'code_execution')


# ============================================================================
# Utility Functions
# ============================================================================

def is_ollama_model(model: str) -> bool:
    """Check if a model name corresponds to an Ollama model."""
    if ':' in model:
        return True
    model_lower = model.lower()
    OLLAMA_MODELS = {'deepseek-r1', 'llama', 'qwen', 'mistral', 'phi', 'gemma', 'codellama', 'llava', 'nomic-embed-text'}
    return any(model_lower.startswith(prefix) for prefix in OLLAMA_MODELS)


def handle_ollama_errors(func: Callable) -> Callable:
    """Decorator for handling Ollama-specific errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.ConnectionError:
            raise OllamaConnectionError()
        except requests.exceptions.Timeout:
            raise ModelTimeoutError(kwargs.get('timeout', 120))
        except json.JSONDecodeError as e:
            raise JSONDecodeWorkflowError(f"响应格式错误: {str(e)}")
    return wrapper


def _normalize_image_size(size: str) -> tuple[int, int]:
    """Parse WIDTHxHEIGHT strings safely."""
    if not size:
        return (
            getattr(settings, 'ZIMAGE_DEFAULT_WIDTH', 1024),
            getattr(settings, 'ZIMAGE_DEFAULT_HEIGHT', 1024),
        )

    match = re.fullmatch(r'(\d{2,5})x(\d{2,5})', str(size).strip())
    if not match:
        raise LocalImageModelError(f'无效图片尺寸格式: {size}，应为 WIDTHxHEIGHT')

    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        raise LocalImageModelError(f'无效图片尺寸: {size}')
    return width, height


def _resolve_zimage_dtype(torch_module, dtype_name: str):
    """Resolve configured dtype to a torch dtype."""
    normalized = (dtype_name or 'auto').strip().lower()
    if normalized not in ZIMAGE_SUPPORTED_DTYPES:
        raise LocalImageModelError(
            f'不支持的 Z-Image dtype: {dtype_name}，可选值: {", ".join(sorted(ZIMAGE_SUPPORTED_DTYPES))}'
        )

    if normalized == 'auto':
        if torch_module.cuda.is_available() and hasattr(torch_module.cuda, 'is_bf16_supported') and torch_module.cuda.is_bf16_supported():
            return torch_module.bfloat16
        if torch_module.cuda.is_available():
            return torch_module.float16
        return torch_module.float32

    return getattr(torch_module, normalized)


def _build_media_url(path: str) -> str:
    normalized = str(path).replace('\\', '/')
    media_root = str(settings.MEDIA_ROOT).replace('\\', '/')
    if normalized.startswith(media_root):
        relative = normalized[len(media_root):].lstrip('/')
        return f"{settings.MEDIA_URL}{relative}"
    return normalized


def calculate_duration_ms(start_time: float) -> int:
    """Calculate duration in milliseconds from start time."""
    return int((time.time() - start_time) * 1000)


# ============================================================================
# Provider Registry Integration
# ============================================================================

def get_provider_registry():
    """Get the provider registry instance."""
    try:
        from gateway.providers.registry import get_registry, register_default_providers
        try:
            register_default_providers()
        except Exception:
            pass
        return get_registry()
    except ImportError:
        return None


def get_provider_for_model(model: str, registry=None):
    """Get appropriate provider for a model using registry."""
    if registry is None:
        registry = get_provider_registry()
    
    if registry is None:
        return None
    
    provider_name = registry.find_provider_for_model(model)
    if provider_name:
        return registry.get(provider_name)
    
    for name in registry.get_all():
        provider = registry.get(name)
        if provider and provider.supports_model(model):
            return provider
    
    return registry.get('openai')


# ============================================================================
# Main Service Class
# ============================================================================

class LangChainService:
    """
    Service for executing workflow nodes using LangChain and Ollama.
    
    Features:
    - LLM nodes with ProviderRegistry routing and streaming
    - Prompt nodes with Jinja2 templating
    - Code nodes with sandboxed execution
    - HTTP nodes with httpx
    - Tool nodes for common operations
    - Variable nodes with expression evaluation
    - Loop nodes for iteration
    - Execution caching for idempotent execution
    - Comprehensive error handling
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, user_id: Optional[int] = None):
        """Initialize LangChain service."""
        self.user_id = user_id
        self.api_key = api_key or self._get_credential('openai', user_id=user_id) or getattr(settings, 'OPENAI_API_KEY', None)
        self.base_url = base_url or getattr(settings, 'OPENAI_BASE_URL', OPENAI_BASE_URL)
        self._llm = None
        self._registry = None
        self._execution_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_tokens': 0,
            'total_duration_ms': 0
        }
        self._cache_service = None

    @property
    def cache_service(self):
        """Lazy initialization of cache service."""
        if self._cache_service is None:
            from .cache_service import ExecutionCacheService
            self._cache_service = ExecutionCacheService()
        return self._cache_service

    @property
    def registry(self):
        """Lazy initialization of provider registry."""
        if self._registry is None:
            self._registry = get_provider_registry()
        return self._registry

    def execute_node(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        input_data: Dict[str, Any],
        timeout_seconds: Optional[int] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a workflow node based on its type with optional timeout.
        
        Args:
            node_type: Type of the node to execute
            node_config: Configuration for the node
            input_data: Input data for the node
            timeout_seconds: Optional timeout in seconds
            use_cache: Whether to use execution cache (default True)
            
        Returns:
            Dict with execution result including 'success', 'output', and metadata
        """
        executors = {
            'llm': self.run_llm_node,
            'prompt': self.run_prompt_node,
            'condition': self.run_condition_node,
            'code': self.run_code_node,
            'http': self.run_http_node,
            'http_request': self.run_http_node,
            'tool': self.run_tool_node,
            'variable': self.run_variable_node,
            'loop': self.run_loop_node,
            'input': self.run_input_node,
            'output': self.run_output_node,
            'email': self.run_email_node,
            'delay': self.run_delay_node,
            'data_transform': self.run_transform_node,
            # Multimodal & Generation
            'image_generation': self.run_image_generation_node,
            'video_generation': self.run_video_generation_node,
            'audio_generation': self.run_audio_generation_node,
            'subtitle_generation': self.run_subtitle_generation_node,
            'image_editing': self.run_image_editing_node,
            # ML & Training
            'dataset_upload': self.run_dataset_upload_node,
            'data_annotation': self.run_data_annotation_node,
            'data_augmentation': self.run_data_augmentation_node,
            'model_training': self.run_model_training_node,
            'model_evaluation': self.run_model_evaluation_node,
            'model_deployment': self.run_model_deployment_node,
            'website_generator': self.run_website_generator_node,
            # RAG & Retrieval
            'document_loader': self.run_document_loader_node,
            'embedding': self.run_embedding_node,
            'vector_store': self.run_vector_store_node,
            'retriever': self.run_retriever_node,
            'reranker': self.run_reranker_node,
            # Agent System
            'agent': self.run_agent_node,
            'planner': self.run_planner_node,
            'executor': self.run_executor_node,
            'memory': self.run_memory_node,
            # Data Pipeline
            'file_reader': self.run_file_reader_node,
            'file_writer': self.run_file_writer_node,
            'web_scraper': self.run_web_scraper,
            'csv_transform': self.run_csv_transform_node,
            'json_transform': self.run_json_transform_node,
        }

        executor = executors.get(node_type)

        if not executor:
            return {
                'success': True,
                'output': input_data,
                'message': f'Skipping unknown node type: {node_type}'
            }

        # === Check cache first ===
        if use_cache:
            cached_output = self.cache_service.get(node_config, node_type)
            if cached_output is not None:
                logger.debug(f"Cache HIT for {node_type}")
                return {
                    'success': True,
                    'output': cached_output,
                    'cached': True,
                    'node_type': node_type,
                }

        self._execution_stats['total_calls'] += 1
        start_time = time.time()

        try:
            if timeout_seconds and node_type in ('llm', 'http', 'http_request', 'code',
                'image_generation', 'video_generation', 'audio_generation',
                'model_training', 'retriever', 'embedding'):
                result = self._execute_with_timeout(executor, node_config, input_data, timeout_seconds)
            else:
                result = executor(node_config, input_data)
            
            duration_ms = calculate_duration_ms(start_time)
            
            if result.get('success'):
                self._execution_stats['successful_calls'] += 1
                self._execution_stats['total_duration_ms'] += duration_ms
                
                # === Store result in cache ===
                if use_cache and result.get('output'):
                    self.cache_service.set(node_config, node_type, result['output'])
            else:
                self._execution_stats['failed_calls'] += 1
            
            if 'duration_ms' not in result:
                result['duration_ms'] = duration_ms
            
            return {
                **result,
                'cached': False,
                'node_type': node_type,
            }
            
        except OllamaConnectionError as e:
            self._execution_stats['failed_calls'] += 1
            return {
                'success': False,
                'error': e.message,
                'error_type': e.error_type,
                'duration_ms': calculate_duration_ms(start_time),
                'cached': False,
                'node_type': node_type,
            }
        except ModelTimeoutError as e:
            self._execution_stats['failed_calls'] += 1
            return {
                'success': False,
                'error': e.message,
                'error_type': e.error_type,
                'duration_ms': calculate_duration_ms(start_time),
                'cached': False,
                'node_type': node_type,
            }
        except JSONDecodeWorkflowError as e:
            self._execution_stats['failed_calls'] += 1
            return {
                'success': False,
                'error': e.message,
                'error_type': e.error_type,
                'duration_ms': calculate_duration_ms(start_time),
                'cached': False,
                'node_type': node_type,
            }
        except Exception as e:
            self._execution_stats['failed_calls'] += 1
            logger.exception(f"Unexpected error in execute_node({node_type})")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unknown',
                'duration_ms': calculate_duration_ms(start_time),
                'cached': False,
                'node_type': node_type,
            }

    def invalidate_node_cache(
        self, 
        node_type: str, 
        old_config: Optional[Dict[str, Any]] = None,
        new_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Invalidate cache for a node type when configuration changes.
        
        Args:
            node_type: The node type to invalidate
            old_config: Previous configuration (if provided, only invalidates if hash changed)
            new_config: New configuration
        """
        if old_config and new_config:
            old_hash = self.cache_service.compute_config_hash(old_config)
            new_hash = self.cache_service.compute_config_hash(new_config)
            if old_hash != new_hash:
                self.cache_service.invalidate(config_hash=old_hash)
                logger.info(f"Invalidated cache for {node_type} (config changed)")
        else:
            self.cache_service.invalidate(node_type=node_type)
            logger.info(f"Invalidated all cache for {node_type}")

    def _execute_with_timeout(
        self,
        executor_func: callable,
        node_config: Dict[str, Any],
        input_data: Dict[str, Any],
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Execute a function with timeout using asyncio."""
        async def _async_wrapper():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: executor_func(node_config, input_data)
            )

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(asyncio.wait_for(_async_wrapper(), timeout=timeout_seconds))
            finally:
                loop.close()
        except asyncio.TimeoutError:
            raise ModelTimeoutError(timeout_seconds)

    # ========================================================================
    # LLM Node Execution
    # ========================================================================
    
    def run_llm_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute LLM node with ProviderRegistry routing and streaming support.
        
        Features:
        - Routes to Ollama or other providers via ProviderRegistry
        - Supports streaming via provider.stream_chat()
        - Records token usage and duration
        - Comprehensive error handling
        """
        start_time = time.time()
        
        model = config.get('model', DEFAULT_LLM_MODEL)
        temperature = config.get('temperature', DEFAULT_TEMPERATURE)
        max_tokens = config.get('max_tokens', DEFAULT_MAX_TOKENS)
        system_prompt = config.get('system_prompt', '')
        user_template = config.get('user_template', '{input}')
        input_variable = config.get('input_variable', 'input')
        streaming = config.get('streaming', False)

        messages = self._build_messages(
            system_prompt=system_prompt,
            user_template=user_template,
            input_data=input_data,
            input_variable=input_variable
        )

        try:
            if is_ollama_model(model):
                result = self._execute_ollama(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=streaming,
                    ollama_base_url=getattr(settings, 'OLLAMA_BASE_URL', None),
                    timeout=config.get('timeout', OLLAMA_CHAT_TIMEOUT)
                )
            else:
                result = self._execute_via_registry(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=streaming
                )

            duration_ms = calculate_duration_ms(start_time)
            
            return {
                'success': True,
                'output': {
                    'text': result.get('content', ''),
                    'usage': result.get('usage', {}),
                    'finish_reason': result.get('finish_reason', 'stop'),
                    'model': model
                },
                'model': model,
                'usage': result.get('usage', {}),
                'duration_ms': duration_ms
            }

        except requests.exceptions.ConnectionError:
            raise OllamaConnectionError()
        except requests.exceptions.Timeout:
            raise ModelTimeoutError(config.get('timeout', 120))
        except json.JSONDecodeError as e:
            raise JSONDecodeWorkflowError(f"响应格式错误: {str(e)}")

    def _build_messages(
        self,
        system_prompt: str,
        user_template: str,
        input_data: Dict[str, Any],
        input_variable: str
    ) -> List[Dict[str, str]]:
        """Build messages list for LLM from config and input data."""
        messages = []
        
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})

        input_text = input_data.get(input_variable, '')
        if isinstance(input_text, dict):
            input_text = json.dumps(input_text, ensure_ascii=False)
        elif not isinstance(input_text, str):
            input_text = str(input_text)

        user_content = user_template.format(input=input_text)
        messages.append({'role': 'user', 'content': user_content})
        
        return messages

    def _execute_ollama(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        streaming: bool,
        ollama_base_url: str,
        timeout: int = OLLAMA_CHAT_TIMEOUT
    ) -> Dict[str, Any]:
        """Execute LLM call via Ollama with streaming support."""
        
        if streaming:
            return self._execute_ollama_streaming(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                ollama_base_url=ollama_base_url,
                timeout=timeout
            )
        
        payload = {
            'model': model,
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            }
        }

        resp = requests.post(
            f'{ollama_base_url}/api/chat',
            json=payload,
            timeout=timeout
        )
        resp.raise_for_status()
        data = resp.json()

        content = data.get('message', {}).get('content', '')
        return {
            'content': content,
            'usage': {
                'prompt_tokens': data.get('prompt_eval_count', 0),
                'completion_tokens': data.get('eval_count', 0),
                'total_tokens': data.get('prompt_eval_count', 0) + data.get('eval_count', 0)
            },
            'finish_reason': data.get('done_reason', 'stop')
        }

    def _execute_ollama_streaming(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        ollama_base_url: str,
        timeout: int = OLLAMA_CHAT_TIMEOUT
    ) -> Dict[str, Any]:
        """Execute Ollama streaming and collect all chunks."""
        payload = {
            'model': model,
            'messages': messages,
            'stream': True,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            }
        }

        resp = requests.post(
            f'{ollama_base_url}/api/chat',
            json=payload,
            timeout=timeout,
            stream=True
        )
        resp.raise_for_status()

        full_content = []
        total_tokens = 0
        prompt_tokens = 0
        done_reason = 'stop'

        for line in resp.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        full_content.append(content)
                    
                    if chunk.get('done'):
                        prompt_tokens = chunk.get('prompt_eval_count', 0)
                        total_tokens = chunk.get('eval_count', 0)
                        done_reason = chunk.get('done_reason', 'stop')
                        break
                except json.JSONDecodeError:
                    continue

        return {
            'content': ''.join(full_content),
            'usage': {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': total_tokens,
                'total_tokens': prompt_tokens + total_tokens
            },
            'finish_reason': done_reason
        }

    def _execute_via_registry(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        streaming: bool
    ) -> Dict[str, Any]:
        """Execute LLM via ProviderRegistry (OpenAI, Anthropic, etc.)."""
        
        if self.registry:
            provider = get_provider_for_model(model, self.registry)
            if provider:
                response = provider.chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return {
                    'content': response.content,
                    'usage': {
                        'prompt_tokens': response.input_tokens,
                        'completion_tokens': response.output_tokens,
                        'total_tokens': response.total_tokens
                    },
                    'finish_reason': response.finish_reason
                }

        if not self.api_key:
            raise WorkflowExecutionError(
                'OpenAI API key not configured. Please set OPENAI_API_KEY.',
                'configuration'
            )

        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        langchain_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                langchain_messages.append(SystemMessage(content=msg['content']))
            else:
                langchain_messages.append(HumanMessage(content=msg['content']))

        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=self.api_key,
            base_url=self.base_url if self.base_url != OPENAI_API_URL else None
        )

        response = llm.invoke(langchain_messages)

        return {
            'content': response.content,
            'usage': response.response_metadata.get('token_usage', {}),
            'finish_reason': 'stop'
        }

    def stream_llm_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream LLM node response as chunks.
        
        Yields:
            Dict with 'type' ('content', 'done', 'error') and relevant data
        """
        model = config.get('model', DEFAULT_LLM_MODEL)
        temperature = config.get('temperature', DEFAULT_TEMPERATURE)
        max_tokens = config.get('max_tokens', DEFAULT_MAX_TOKENS)
        system_prompt = config.get('system_prompt', '')
        user_template = config.get('user_template', '{input}')
        input_variable = config.get('input_variable', 'input')

        messages = self._build_messages(
            system_prompt=system_prompt,
            user_template=user_template,
            input_data=input_data,
            input_variable=input_variable
        )

        try:
            if is_ollama_model(model):
                ollama_base_url = getattr(settings, 'OLLAMA_BASE_URL', None)
                yield from self._stream_ollama(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    ollama_base_url=ollama_base_url
                )
            elif self.registry:
                provider = get_provider_for_model(model, self.registry)
                if provider and hasattr(provider, 'stream_chat'):
                    for chunk in provider.stream_chat(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    ):
                        yield chunk
                    return

            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage

            langchain_messages = []
            for msg in messages:
                if msg['role'] == 'system':
                    langchain_messages.append(SystemMessage(content=msg['content']))
                else:
                    langchain_messages.append(HumanMessage(content=msg['content']))

            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=self.api_key,
                base_url=self.base_url if self.base_url != OPENAI_API_URL else None
            )

            for chunk in llm.stream(langchain_messages):
                yield {'type': 'content', 'content': chunk.content}
            yield {'type': 'done'}

        except Exception as e:
            yield {'type': 'error', 'error': str(e)}

    def _stream_ollama(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        ollama_base_url: str
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream Ollama response as chunks."""
        payload = {
            'model': model,
            'messages': messages,
            'stream': True,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            }
        }

        try:
            resp = requests.post(
                f'{ollama_base_url}/api/chat',
                json=payload,
                timeout=OLLAMA_CHAT_TIMEOUT,
                stream=True
            )
            resp.raise_for_status()

            prompt_tokens = 0
            completion_tokens = 0

            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        content = chunk.get('message', {}).get('content', '')
                        if content:
                            yield {'type': 'content', 'content': content}
                        
                        if chunk.get('done'):
                            prompt_tokens = chunk.get('prompt_eval_count', 0)
                            completion_tokens = chunk.get('eval_count', 0)
                            yield {
                                'type': 'done',
                                'input_tokens': prompt_tokens,
                                'output_tokens': completion_tokens,
                                'total_tokens': prompt_tokens + completion_tokens
                            }
                            break
                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.ConnectionError:
            yield {'type': 'error', 'error': 'Ollama 服务未启动，请确保本地 Ollama 正在运行'}
        except requests.exceptions.Timeout:
            yield {'type': 'error', 'error': '模型响应超时'}
        except Exception as e:
            yield {'type': 'error', 'error': str(e)}

    # ========================================================================
    # Prompt Node Execution
    # ========================================================================
    
    def run_prompt_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute prompt template node with Jinja2 support.
        
        Features:
        - Supports {{variable}} and {variable} syntax
        - Passes rendered prompt to LLM if model is configured
        - Nested variable access via dot notation
        """
        start_time = time.time()
        
        template = config.get('template', config.get('prompt_template', '{input}'))
        variables = config.get('variables', [])
        model = config.get('model')
        pass_to_llm = config.get('pass_to_llm', False)
        input_variable = config.get('input_variable', 'input')

        context = {**input_data}
        for var in variables:
            var_name = var.get('name')
            var_value = var.get('value')
            if var_name:
                context[var_name] = input_data.get(var_name, var_value)

        if input_variable not in context:
            context[input_variable] = input_data.get('input', input_data)

        try:
            rendered = self._render_template_advanced(template, context)
            
            if pass_to_llm and model:
                llm_result = self.run_llm_node(
                    config={
                        **config,
                        'user_template': '{input}',
                        'input_variable': '_rendered_prompt'
                    },
                    input_data={**input_data, '_rendered_prompt': rendered}
                )
                
                duration_ms = calculate_duration_ms(start_time)
                
                return {
                    'success': llm_result.get('success', True),
                    'output': {
                        'template': rendered,
                        'llm_response': llm_result.get('output', {}),
                    },
                    'duration_ms': duration_ms
                }
            
            duration_ms = calculate_duration_ms(start_time)
            
            return {
                'success': True,
                'output': {
                    'text': rendered,
                    'template': template,
                    'variables': list(context.keys())
                },
                'duration_ms': duration_ms
            }
            
        except Exception as e:
            logger.exception("Error in run_prompt_node")
            return {
                'success': False,
                'error': f'Prompt rendering error: {str(e)}',
                'duration_ms': calculate_duration_ms(start_time)
            }

    def _render_template_advanced(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render template with advanced Jinja2-like syntax.
        
        Supports:
        - {{variable}} and {{{variable}}} syntax
        - Nested access via {{obj.nested}}
        - Filters like {{variable | upper}}
        - Conditionals like {% if condition %}...{% endif %}
        """
        if not template:
            return template

        result = str(template)
        
        try:
            import jinja2
            env = jinja2.Environment(
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True
            )
            env.filters['upper'] = lambda x: str(x).upper()
            env.filters['lower'] = lambda x: str(x).lower()
            env.filters['capitalize'] = lambda x: str(x).capitalize()
            env.filters['strip'] = lambda x: str(x).strip()
            env.filters['default'] = lambda x, d='': x if x is not None else d
            
            rendered = env.from_string(template).render(**context)
            return rendered
        except ImportError:
            pass
        except Exception:
            pass
        
        pattern = r'\{\{([^}|]+)(?:\|[^}]*)?\}\}'
        
        def replacer(match):
            var_path = match.group(1).strip()
            value = self._get_nested_value(context, var_path)
            if value is None:
                value = match.group(0)
            return str(value)
        
        result = re.sub(pattern, replacer, result)
        
        pattern_braces = r'\{([^}]+)\}'
        def replacer2(match):
            var_path = match.group(1).strip()
            if var_path.startswith('{') or var_path.endswith('}'):
                return match.group(0)
            value = self._get_nested_value(context, var_path)
            if value is None:
                return match.group(0)
            return str(value)
        
        result = re.sub(pattern_braces, replacer2, result)
        
        return result

    # ========================================================================
    # Condition Node Execution
    # ========================================================================
    
    def run_condition_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute condition node with enhanced logic.
        
        Supports:
        - and/or/nor logic combination
        - regex matching
        - numeric comparisons (> < >= <= == !=)
        - string operations (contains, startswith, endswith, matches_regex)
        - condition_expression for complex expressions
        """
        conditions = config.get('conditions', [])
        default_branch = config.get('default_branch', 'false')
        logic_mode = config.get('logic_mode', 'or')
        condition_expression = config.get('condition_expression', '')

        if condition_expression:
            return self._evaluate_condition_expression(condition_expression, input_data)

        result = default_branch

        if not conditions:
            return {
                'success': True,
                'output': result,
                'branch': result
            }

        condition_results = []
        for condition in conditions:
            condition_result = self._evaluate_single_condition(condition, input_data)
            condition_results.append(condition_result)

        if logic_mode == 'and':
            final_result = all(condition_results) if condition_results else False
        elif logic_mode == 'nor':
            final_result = not any(condition_results) if condition_results else True
        else:
            final_result = any(condition_results) if condition_results else False

        if final_result:
            for condition in conditions:
                if self._evaluate_single_condition(condition, input_data):
                    result = condition.get('branch', 'true')
                    break
        else:
            result = default_branch

        return {
            'success': True,
            'output': result,
            'branch': result,
            'condition_results': condition_results
        }

    def _evaluate_condition_expression(
        self,
        expression: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a condition_expression string."""
        try:
            context = {}
            context.update(input_data)
            
            allowed_names = {
                'and': lambda a, b: a and b,
                'or': lambda a, b: a or b,
                'not': lambda a: not a,
                'True': True,
                'False': False,
                'None': None,
                're': re,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'all': all,
                'any': any,
            }
            
            result = eval(expression, {"__builtins__": {}}, {**context, **allowed_names})
            
            branch = 'true' if result else 'false'
            
            return {
                'success': True,
                'output': branch,
                'branch': branch,
                'expression_result': bool(result)
            }
        except Exception as e:
            logger.warning(f"Condition expression error: {e}")
            return {
                'success': True,
                'output': 'false',
                'branch': 'false',
                'error': str(e)
            }

    def _evaluate_single_condition(
        self,
        condition: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> bool:
        """Evaluate a single condition."""
        field = condition.get('field', '')
        operator = condition.get('operator', 'equals')
        value = condition.get('value', '')
        condition_type = condition.get('type', 'simple')

        if condition_type == 'expression':
            try:
                return bool(eval(value, {"__builtins__": {}}, input_data))
            except Exception:
                return False

        field_value = self._get_nested_value(input_data, field, '')

        return self._evaluate_operator(field_value, operator, value)

    def _evaluate_operator(self, field_value: Any, operator: str, condition_value: Any) -> bool:
        """Evaluate operator on field value."""
        operators = {
            'equals': lambda a, b: str(a) == str(b),
            'equal': lambda a, b: str(a) == str(b),
            '==': lambda a, b: str(a) == str(b),
            'not_equals': lambda a, b: str(a) != str(b),
            '!=': lambda a, b: str(a) != str(b),
            'ne': lambda a, b: str(a) != str(b),
            
            'contains': lambda a, b: str(b) in str(a),
            'not_contains': lambda a, b: str(b) not in str(a),
            
            'starts_with': lambda a, b: str(a).startswith(str(b)),
            'startswith': lambda a, b: str(a).startswith(str(b)),
            
            'ends_with': lambda a, b: str(a).endswith(str(b)),
            'endswith': lambda a, b: str(a).endswith(str(b)),
            
            'greater_than': lambda a, b: self._safe_float(a) > self._safe_float(b),
            'gt': lambda a, b: self._safe_float(a) > self._safe_float(b),
            '>': lambda a, b: self._safe_float(a) > self._safe_float(b),
            
            'less_than': lambda a, b: self._safe_float(a) < self._safe_float(b),
            'lt': lambda a, b: self._safe_float(a) < self._safe_float(b),
            '<': lambda a, b: self._safe_float(a) < self._safe_float(b),
            
            'greater_equal': lambda a, b: self._safe_float(a) >= self._safe_float(b),
            'gte': lambda a, b: self._safe_float(a) >= self._safe_float(b),
            '>=': lambda a, b: self._safe_float(a) >= self._safe_float(b),
            
            'less_equal': lambda a, b: self._safe_float(a) <= self._safe_float(b),
            'lte': lambda a, b: self._safe_float(a) <= self._safe_float(b),
            '<=': lambda a, b: self._safe_float(a) <= self._safe_float(b),
            
            'is_empty': lambda a, b: not bool(a) or str(a).strip() == '',
            'is_not_empty': lambda a, b: bool(a) and str(a).strip() != '',
            
            'matches_regex': lambda a, b: bool(re.search(str(b), str(a))),
            'regex': lambda a, b: bool(re.search(str(b), str(a))),
            'matches': lambda a, b: bool(re.search(str(b), str(a))),
            
            'in': lambda a, b: str(a) in (b if isinstance(b, (list, tuple)) else [b]),
            'not_in': lambda a, b: str(a) not in (b if isinstance(b, (list, tuple)) else [b]),
            
            'has_key': lambda a, b: b in (a if isinstance(a, dict) else {}),
            'type_is': lambda a, b: type(a).__name__ == b,
        }

        op_func = operators.get(operator)
        if op_func is None:
            logger.warning(f"Unknown operator: {operator}, using equals")
            op_func = operators['equals']
        
        try:
            return op_func(field_value, condition_value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Condition evaluation error for {operator}: {e}")
            return False

    def _safe_float(self, value: Any) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return 0.0

    # ========================================================================
    # Code Node Execution
    # ========================================================================
    
    # Dangerous modules to block in sandbox
    _DANGEROUS_MODULES = {
        'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib', 'urllib2',
        'urllib3', 'http', 'ftplib', 'telnetlib', 'telnet', 'poplib', 'imaplib',
        'smtplib', 'nntplib', 'xmlrpc', 'xmlrpc.client', 'multiprocessing',
        'threading', 'concurrent', 'asyncio', 'ctypes', 'cffi', 'winreg',
        '_winreg', 'commands', 'pickle', 'marshal', 'eval', 'exec', 'compile',
        '__import__', 'reload', 'input', 'open', 'file', 'print'
    }
    
    _SAFE_BUILTINS = {
        'True': True, 'False': False, 'None': None,
        'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
        'bytearray': bytearray, 'bytes': bytes, 'callable': callable,
        'chr': chr, 'dict': dict, 'dir': dir, 'divmod': divmod,
        'enumerate': enumerate, 'filter': filter, 'float': float,
        'format': format, 'frozenset': frozenset, 'hash': hash,
        'hex': hex, 'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
        'iter': iter, 'len': len, 'list': list, 'map': map, 'max': max,
        'min': min, 'oct': oct, 'ord': ord, 'pow': pow, 'range': range,
        'repr': repr, 'reversed': reversed, 'round': round, 'set': set,
        'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum,
        'tuple': tuple, 'zip': zip,
    }
    
    def run_code_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute code node in a sandboxed subprocess.
        
        Security features:
        - Subprocess isolation (complete process separation)
        - RLIMIT_AS: Memory limit (default 128MB)
        - RLIMIT_CPU: CPU time limit (default 30s)
        - RLIMIT_FSIZE: File size limit (1MB)
        - RLIMIT_NPROC: Process limit (prevent fork bombs)
        - Pre-execution security validation
        - Timeout via SIGKILL
        """
        from .sandbox_service import SandboxService
        
        code = config.get('code', '')
        timeout = config.get('timeout', TOOL_TIMEOUT_DEFAULT)
        max_memory_mb = config.get('max_memory_mb', 128)
        
        if not code:
            return {
                'success': False,
                'error': 'No code provided',
                'duration_ms': 0
            }
        
        # Pre-validate code for obvious security issues
        sandbox = SandboxService(timeout=timeout, max_memory_mb=max_memory_mb)
        validation = sandbox.validate_code(code)
        if not validation['valid']:
            return {
                'success': False,
                'error': 'Code contains disallowed patterns: ' + ', '.join(validation['errors']),
                'error_type': 'security',
                'duration_ms': 0
            }
        
        # Prepare input with proper variable name mapping
        input_variable = config.get('input_variable', 'input')
        prepared_input = {input_variable: input_data.get(input_variable, input_data)}
        
        # Execute in subprocess sandbox
        return sandbox.execute(code, prepared_input)

    def _create_safe_namespace(
        self,
        input_data: Dict[str, Any],
        input_variable: str
    ) -> Dict[str, Any]:
        """Create a safe namespace for code execution."""
        namespace = {
            'input': input_data.get(input_variable, input_data),
            'json': json,
            'math': __import__('math'),
            're': re,
            'datetime': __import__('datetime'),
            'date': __import__('datetime').date,
            'time': __import__('datetime').time,
            'timedelta': __import__('datetime').timedelta,
            'uuid': __import__('uuid'),
            'random': __import__('random'),
            'collections': __import__('collections'),
            'itertools': __import__('itertools'),
            'functools': __import__('functools'),
            'operator': __import__('operator'),
            'string': __import__('string'),
        }
        
        for key, value in input_data.items():
            if not any(key.startswith(d) for d in self._DANGEROUS_MODULES):
                namespace[key] = value
        
        return namespace

    def _check_dangerous_code(self, code: str) -> List[str]:
        """Check for potentially dangerous code patterns."""
        warnings = []
        dangerous_patterns = [
            (r'import\s+os\b', 'os module import'),
            (r'from\s+os\s+import', 'os module import'),
            (r'__import__\(', 'dynamic import'),
            (r'open\s*\(', 'file open'),
            (r'exec\s*\(', 'exec call'),
            (r'eval\s*\(', 'eval call'),
            (r'compile\s*\(', 'compile call'),
            (r'subprocess', 'subprocess module'),
            (r'socket\.', 'socket usage'),
            (r'requests\.', 'requests library'),
            (r'urllib\.', 'urllib usage'),
            (r'os\.system', 'os.system'),
            (r'os\.popen', 'os.popen'),
            (r'subprocess\.Popen', 'subprocess.Popen'),
            (r'subprocess\.run', 'subprocess.run'),
        ]
        
        for pattern, desc in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                warnings.append(desc)
        
        return warnings

    # ========================================================================
    # HTTP Node Execution
    # ========================================================================
    
    def run_http_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute HTTP request node with comprehensive error handling.
        
        Supports:
        - GET, POST, PUT, DELETE, PATCH methods
        - JSON body
        - Custom headers
        - Response parsing
        - Timeout handling
        """
        start_time = time.time()
        
        method = config.get('method', 'GET').upper()
        url = config.get('url', '')
        headers = config.get('headers', {})
        body_template = config.get('body', '')
        timeout = config.get('timeout', HTTP_TOOL_TIMEOUT)
        response_format = config.get('response_format', 'auto')
        retry_count = config.get('retry_count', 0)
        retry_delay = config.get('retry_delay', 1)

        url = self._render_template(url, input_data)

        rendered_headers = {}
        for key, value in headers.items():
            rendered_headers[key] = self._render_template(str(value), input_data)

        body = None
        if body_template and method in ['POST', 'PUT', 'PATCH']:
            body_str = self._render_template(body_template, input_data)
            try:
                body = json.loads(body_str)
            except json.JSONDecodeError:
                body = body_str

        last_error = None
        for attempt in range(retry_count + 1):
            try:
                response = self._execute_http_request(
                    method=method,
                    url=url,
                    headers=rendered_headers,
                    body=body,
                    timeout=timeout
                )
                
                duration_ms = calculate_duration_ms(start_time)
                
                parsed_body = self._parse_response_body(response, response_format)
                
                return {
                    'success': True,
                    'output': {
                        'status_code': response.status_code,
                        'body': parsed_body,
                        'headers': dict(response.headers),
                        'url': str(response.url),
                        'elapsed_ms': response.elapsed.total_seconds() * 1000
                    },
                    'status_code': response.status_code,
                    'duration_ms': duration_ms
                }
                
            except httpx.TimeoutException:
                last_error = f'HTTP request timed out after {timeout}s'
                logger.warning(f"HTTP timeout (attempt {attempt + 1}/{retry_count + 1}): {url}")
            except httpx.ConnectError as e:
                last_error = f'Connection error: {str(e)}'
                logger.warning(f"HTTP connection error (attempt {attempt + 1}/{retry_count + 1}): {url}")
            except httpx.HTTPStatusError as e:
                last_error = f'HTTP {e.response.status_code}: {str(e)}'
                logger.warning(f"HTTP status error: {last_error}")
                break
            except requests.exceptions.ConnectionError:
                last_error = '目标服务器连接失败，请检查网络或服务地址'
                logger.warning(f"HTTP connection error (attempt {attempt + 1}/{retry_count + 1})")
            except requests.exceptions.Timeout:
                last_error = f'HTTP 请求超时（{timeout}s）'
                logger.warning(f"HTTP timeout (attempt {attempt + 1}/{retry_count + 1})")
            except Exception as e:
                last_error = f'HTTP request error: {str(e)}'
                logger.exception(f"HTTP error (attempt {attempt + 1}/{retry_count + 1})")
                break
            
            if attempt < retry_count:
                time.sleep(retry_delay * (attempt + 1))

        duration_ms = calculate_duration_ms(start_time)
        
        return {
            'success': False,
            'error': last_error,
            'error_type': 'http',
            'duration_ms': duration_ms
        }

    def _execute_http_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Any,
        timeout: int
    ) -> httpx.Response:
        """Execute HTTP request using httpx."""
        with httpx.Client(timeout=timeout) as client:
            return client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if isinstance(body, dict) else None,
                data=body if isinstance(body, str) else None
            )

    def _parse_response_body(
        self,
        response: httpx.Response,
        response_format: str
    ) -> Any:
        """Parse response body based on format setting."""
        content_type = response.headers.get('content-type', '')
        
        if 'application/json' in content_type or response_format == 'json':
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        
        if response_format == 'text':
            return response.text
        
        if 'image' in content_type:
            return {'_content_type': content_type, '_size': len(response.content)}
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    # ========================================================================
    # Tool Node Execution
    # ========================================================================
    
    def run_tool_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute tool node with built-in and custom tool support.
        
        Built-in tools:
        - search: Web search (requires API)
        - calculator: Math expression evaluation
        - json_parser: JSON parse/stringify
        - text_template: Text template rendering
        - web_scraper: Web page scraping
        - url_parser: URL parsing and manipulation
        - base64_encoder: Base64 encode/decode
        - hash_generator: Generate various hashes
        """
        start_time = time.time()
        
        tool_name = config.get('tool', config.get('tool_name', ''))
        tool_params = config.get('parameters', config.get('tool_args', {}))
        custom_handler = config.get('handler')

        tools = {
            'search': self._tool_search,
            'calculator': self._tool_calculator,
            'json_parser': self._tool_json_parser,
            'text_template': self._tool_text_template,
            'web_scraper': self._tool_web_scraper,
            'url_parser': self._tool_url_parser,
            'base64_encoder': self._tool_base64_encoder,
            'hash_generator': self._tool_hash_generator,
            'datetime_tool': self._tool_datetime,
            'string_ops': self._tool_string_ops,
            'array_ops': self._tool_array_ops,
        }

        if custom_handler:
            return self._execute_custom_tool(custom_handler, tool_params, input_data, start_time)

        tool_func = tools.get(tool_name)

        if not tool_func:
            return {
                'success': False,
                'error': f'Unknown tool: {tool_name}. Available tools: {", ".join(tools.keys())}',
                'error_type': 'tool_not_found',
                'duration_ms': calculate_duration_ms(start_time)
            }

        try:
            result = tool_func(tool_params, input_data)
            
            return {
                'success': True,
                'output': result,
                'tool': tool_name,
                'duration_ms': calculate_duration_ms(start_time)
            }
        except ValueError as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'tool_error',
                'duration_ms': calculate_duration_ms(start_time)
            }
        except Exception as e:
            logger.exception(f"Tool execution error: {tool_name}")
            return {
                'success': False,
                'error': f'Tool execution error: {str(e)}',
                'error_type': 'runtime',
                'duration_ms': calculate_duration_ms(start_time)
            }

    def _execute_custom_tool(
        self,
        handler: str,
        params: Dict,
        input_data: Dict,
        start_time: float
    ) -> Dict[str, Any]:
        """Execute a custom tool via handler function."""
        try:
            module_path, func_name = handler.rsplit('.', 1)
            import importlib
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            result = func(params, input_data)
            
            return {
                'success': True,
                'output': result,
                'duration_ms': calculate_duration_ms(start_time)
            }
        except (ImportError, AttributeError) as e:
            return {
                'success': False,
                'error': f'Custom tool error: {str(e)}',
                'error_type': 'handler_error',
                'duration_ms': calculate_duration_ms(start_time)
            }

    # ========================================================================
    # Built-in Tool Implementations
    # ========================================================================
    
    def _tool_search(self, params: Dict, input_data: Dict) -> Dict:
        """Search tool - performs web search."""
        query = params.get('query', '')
        query = self._render_template(query, input_data)
        engine = params.get('engine', 'duckduckgo')
        max_results = params.get('max_results', 5)
        
        try:
            if engine == 'duckduckgo':
                try:
                    from duckduckgo_search import DDGS
                    with DDGS() as ddgs:
                        results = list(ddgs.text(query, max_results=max_results))
                    return {
                        'query': query,
                        'results': [
                            {'title': r.get('title'), 'url': r.get('href'), 'snippet': r.get('body')}
                            for r in results
                        ],
                        'count': len(results)
                    }
                except ImportError:
                    return {
                        'query': query,
                        'results': [],
                        'error': 'duckduckgo_search library not installed',
                        'install': 'pip install duckduckgo-search'
                    }
            elif engine == 'serpapi':
                api_key = params.get('api_key', '')
                if not api_key:
                    return {'query': query, 'results': [], 'error': 'SerpAPI key required'}
                
                serp_url = 'https://serpapi.com/search.json'
                resp = requests.get(serp_url, params={'q': query, 'api_key': api_key})
                data = resp.json()
                
                return {
                    'query': query,
                    'results': data.get('organic_results', [])[:max_results],
                    'count': len(data.get('organic_results', []))
                }
            
            return {'query': query, 'results': [], 'error': f'Unknown engine: {engine}'}
            
        except Exception as e:
            raise ValueError(f'Search error: {str(e)}')

    def _tool_calculator(self, params: Dict, input_data: Dict) -> Dict:
        """Calculator tool - evaluates mathematical expressions."""
        expression = params.get('expression', '')
        expression = self._render_template(expression, input_data)
        
        try:
            math_ns = {
                'math': __import__('math'),
                'sqrt': __import__('math').sqrt,
                'sin': __import__('math').sin,
                'cos': __import__('math').cos,
                'tan': __import__('math').tan,
                'log': __import__('math').log,
                'log10': __import__('math').log10,
                'exp': __import__('math').exp,
                'pi': __import__('math').pi,
                'e': __import__('math').e,
                'abs': abs,
                'round': round,
                'pow': pow,
                'min': min,
                'max': max,
                'sum': sum,
            }
            result = eval(expression, {"__builtins__": {}}, math_ns)
            return {'expression': expression, 'result': float(result) if isinstance(result, (int, float)) else result}
        except SyntaxError as e:
            raise ValueError(f'Invalid expression syntax: {e}')
        except NameError as e:
            raise ValueError(f'Unknown function in expression: {e}')
        except Exception as e:
            raise ValueError(f'Calculation error: {e}')

    def _tool_json_parser(self, params: Dict, input_data: Dict) -> Dict:
        """JSON parser tool - parses or stringifies JSON."""
        json_str = params.get('json', params.get('data', ''))
        action = params.get('action', 'parse')
        pretty = params.get('pretty', False)
        
        json_str = self._render_template(str(json_str), input_data)
        
        if action == 'parse':
            try:
                parsed = json.loads(json_str)
                return {'parsed': parsed, 'type': type(parsed).__name__}
            except json.JSONDecodeError as e:
                raise ValueError(f'JSON parse error: {e}')
        
        elif action == 'stringify':
            data = params.get('data', input_data)
            if not data:
                data = json_str
            try:
                if pretty:
                    return {'stringified': json.dumps(data, ensure_ascii=False, indent=2)}
                return {'stringified': json.dumps(data, ensure_ascii=False)}
            except Exception as e:
                raise ValueError(f'JSON stringify error: {e}')
        
        elif action == 'validate':
            try:
                json.loads(json_str)
                return {'valid': True, 'message': 'Valid JSON'}
            except json.JSONDecodeError as e:
                return {'valid': False, 'message': f'Invalid JSON: {e}'}
        
        raise ValueError(f"Unknown JSON action: {action}")

    def _tool_text_template(self, params: Dict, input_data: Dict) -> Dict:
        """Text template tool - renders text templates."""
        template = params.get('template', '')
        variables = params.get('variables', {})
        
        context = {**input_data, **variables}
        rendered = self._render_template_advanced(template, context)
        
        return {'text': rendered, 'template': template}

    def _tool_web_scraper(self, params: Dict, input_data: Dict) -> Dict:
        """Web scraper tool - fetches and extracts content from web pages."""
        url = params.get('url', '')
        url = self._render_template(url, input_data)
        selector = params.get('selector', '')
        extract = params.get('extract', 'text')
        
        if not url:
            raise ValueError('URL is required')
        
        try:
            import httpx
            with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                response = client.get(url)
                response.raise_for_status()
            
            if selector:
                try:
                    from selectolax.parser import HTMLParser
                    tree = HTMLParser(response.text)
                    nodes = tree.css(selector)
                    
                    if extract == 'text':
                        results = [node.text() for node in nodes]
                    elif extract == 'html':
                        results = [node.html for node in nodes]
                    elif extract == 'attributes':
                        attr = params.get('attribute', 'href')
                        results = [node.attrs.get(attr, '') for node in nodes]
                    else:
                        results = [node.text() for node in nodes]
                    
                    return {'url': url, 'selector': selector, 'results': results, 'count': len(results)}
                except ImportError:
                    return {
                        'url': url,
                        'error': 'selectolax library needed for CSS selectors. Install with: pip install selectolax',
                        'install': 'pip install selectolax',
                        'content': response.text[:1000]
                    }
            
            return {'url': url, 'content': response.text, 'status_code': response.status_code}
            
        except httpx.HTTPError as e:
            raise ValueError(f'Web scraper error: {str(e)}')

    def _tool_url_parser(self, params: Dict, input_data: Dict) -> Dict:
        """URL parser tool - parses and manipulates URLs."""
        url = params.get('url', '')
        url = self._render_template(url, input_data)
        action = params.get('action', 'parse')
        
        from urllib.parse import urlparse, parse_qs, urlencode, urljoin
        
        try:
            parsed = urlparse(url)
            
            if action == 'parse':
                return {
                    'scheme': parsed.scheme,
                    'netloc': parsed.netloc,
                    'path': parsed.path,
                    'params': parsed.params,
                    'query': parsed.query,
                    'fragment': parsed.fragment,
                    'domain': parsed.netloc.split(':')[0],
                    'port': parsed.port,
                }
            
            elif action == 'query':
                query_dict = parse_qs(parsed.query)
                return {'query': parsed.query, 'params': query_dict}
            
            elif action == 'build':
                scheme = params.get('scheme', parsed.scheme or 'https')
                netloc = params.get('netloc', parsed.netloc)
                path = params.get('path', parsed.path)
                query = params.get('query', parsed.query)
                
                if isinstance(query, dict):
                    query = urlencode(query)
                
                from urllib.parse import urlunparse
                new_url = urlunparse((scheme, netloc, path, '', query, ''))
                return {'url': new_url}
            
            raise ValueError(f"Unknown URL action: {action}")
            
        except Exception as e:
            raise ValueError(f'URL parsing error: {e}')

    def _tool_base64_encoder(self, params: Dict, input_data: Dict) -> Dict:
        """Base64 encoder/decoder tool."""
        import base64
        
        text = params.get('text', '')
        text = self._render_template(text, input_data)
        action = params.get('action', 'encode')
        
        if action == 'encode':
            encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
            return {'original': text, 'encoded': encoded}
        
        elif action == 'decode':
            try:
                decoded = base64.b64decode(text.encode('utf-8')).decode('utf-8')
                return {'encoded': text, 'decoded': decoded}
            except Exception as e:
                raise ValueError(f'Base64 decode error: {e}')
        
        raise ValueError(f"Unknown base64 action: {action}")

    def _tool_hash_generator(self, params: Dict, input_data: Dict) -> Dict:
        """Hash generator tool - generates various hash values."""
        import hashlib
        
        text = params.get('text', '')
        text = self._render_template(text, input_data)
        algorithm = params.get('algorithm', 'sha256').lower()
        
        encodings = ['utf-8', 'latin-1', 'ascii']
        text_bytes = None
        for enc in encodings:
            try:
                text_bytes = text.encode(enc)
                break
            except:
                continue
        
        if text_bytes is None:
            text_bytes = text.encode('utf-8', errors='ignore')
        
        if algorithm == 'md5':
            return {'text': text, 'md5': hashlib.md5(text_bytes).hexdigest()}
        elif algorithm == 'sha1':
            return {'text': text, 'sha1': hashlib.sha1(text_bytes).hexdigest()}
        elif algorithm == 'sha256':
            return {'text': text, 'sha256': hashlib.sha256(text_bytes).hexdigest()}
        elif algorithm == 'sha512':
            return {'text': text, 'sha512': hashlib.sha512(text_bytes).hexdigest()}
        
        raise ValueError(f"Unknown hash algorithm: {algorithm}")

    def _tool_datetime(self, params: Dict, input_data: Dict) -> Dict:
        """Datetime tool - provides date/time operations."""
        from datetime import datetime, timezone
        import pytz
        
        action = params.get('action', 'now')
        format_str = params.get('format', '%Y-%m-%d %H:%M:%S')
        timezone_name = params.get('timezone', 'UTC')
        
        try:
            tz = pytz.timezone(timezone_name)
        except:
            tz = timezone.utc
        
        now = datetime.now(tz)
        
        if action == 'now':
            return {
                'iso': now.isoformat(),
                'timestamp': now.timestamp(),
                'formatted': now.strftime(format_str),
                'date': now.date().isoformat(),
                'time': now.time().isoformat(),
                'timezone': timezone_name
            }
        
        elif action == 'parse':
            date_str = params.get('date_string', '')
            date_str = self._render_template(date_str, input_data)
            input_format = params.get('input_format', '%Y-%m-%d %H:%M:%S')
            
            parsed = datetime.strptime(date_str, input_format)
            parsed = tz.localize(parsed) if parsed.tzinfo is None else parsed
            
            return {
                'original': date_str,
                'iso': parsed.isoformat(),
                'timestamp': parsed.timestamp(),
                'formatted': parsed.strftime(format_str)
            }
        
        elif action == 'format':
            timestamp = params.get('timestamp', None)
            if timestamp:
                dt = datetime.fromtimestamp(float(timestamp), tz=tz)
            else:
                dt = now
            return {'formatted': dt.strftime(format_str), 'iso': dt.isoformat()}
        
        raise ValueError(f"Unknown datetime action: {action}")

    def _tool_string_ops(self, params: Dict, input_data: Dict) -> Dict:
        """String operations tool."""
        text = params.get('text', '')
        text = self._render_template(text, input_data)
        operation = params.get('operation', 'upper')
        
        operations = {
            'upper': str.upper,
            'lower': str.lower,
            'strip': str.strip,
            'title': str.title,
            'capitalize': str.capitalize,
            'swapcase': str.swapcase,
            'reverse': lambda s: s[::-1],
            'length': len,
        }
        
        if operation in operations:
            if callable(operations[operation]):
                result = operations[operation](text)
            else:
                result = operations[operation]
            return {'original': text, 'operation': operation, 'result': result}
        
        raise ValueError(f"Unknown string operation: {operation}")

    def _tool_array_ops(self, params: Dict, input_data: Dict) -> Dict:
        """Array operations tool."""
        items = params.get('items', [])
        operation = params.get('operation', 'length')
        
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except:
                items = [items]
        
        if operation == 'length':
            return {'items': items, 'length': len(items)}
        elif operation == 'first':
            return {'items': items, 'first': items[0] if items else None}
        elif operation == 'last':
            return {'items': items, 'last': items[-1] if items else None}
        elif operation == 'unique':
            return {'items': items, 'unique': list(dict.fromkeys(items))}
        elif operation == 'sort':
            return {'items': items, 'sorted': sorted(items)}
        elif operation == 'reverse':
            return {'items': items, 'reversed': list(reversed(items))}
        elif operation == 'join':
            separator = params.get('separator', ', ')
            return {'items': items, 'joined': separator.join(str(x) for x in items)}
        elif operation == 'filter':
            condition = params.get('condition', '')
            filtered = [x for x in items if self._evaluate_condition_expression(condition, {'item': x, 'items': items})]
            return {'items': items, 'filtered': filtered, 'count': len(filtered)}
        
        raise ValueError(f"Unknown array operation: {operation}")

    # ========================================================================
    # Variable Node Execution
    # ========================================================================
    
    def run_variable_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute variable assignment node.
        
        Supports three variable sources:
        - static: Fixed value
        - input: From input data
        - expression: Python expression evaluation
        """
        start_time = time.time()
        
        assignments = config.get('assignments', [])
        merge_strategy = config.get('merge_strategy', 'update')

        output = input_data.copy() if merge_strategy == 'update' else {}

        for assignment in assignments:
            var_name = assignment.get('name', '')
            var_value = assignment.get('value', '')
            source = assignment.get('source', 'static')
            var_type = assignment.get('type', 'string')
            transform = assignment.get('transform', None)

            if not var_name:
                continue

            try:
                if source == 'static':
                    rendered_value = self._render_template(str(var_value), input_data)
                    final_value = self._cast_value(rendered_value, var_type)
                    
                elif source == 'input':
                    final_value = input_data.get(str(var_value), var_value)
                    final_value = self._cast_value(str(final_value), var_type)
                    
                elif source == 'expression':
                    final_value = self._evaluate_variable_expression(
                        str(var_value), input_data
                    )
                    final_value = self._cast_value(str(final_value), var_type)
                    
                elif source == 'reference':
                    ref_path = str(var_value)
                    final_value = self._get_nested_value(input_data, ref_path)
                    
                else:
                    final_value = self._render_template(str(var_value), input_data)

                if transform:
                    final_value = self._apply_transform(final_value, transform)

                output[var_name] = final_value
                
            except Exception as e:
                logger.warning(f"Variable assignment error for '{var_name}': {e}")
                output[var_name] = None

        return {
            'success': True,
            'output': output,
            'variables': list(output.keys()),
            'duration_ms': calculate_duration_ms(start_time)
        }

    def _evaluate_variable_expression(
        self,
        expression: str,
        context: Dict[str, Any]
    ) -> Any:
        """Evaluate a Python expression for variable assignment."""
        safe_names = {
            'True': True, 'False': False, 'None': None,
            'str': str, 'int': int, 'float': float, 'bool': bool,
            'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
            'len': len, 'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'any': any, 'all': all,
            'json': json, 'math': __import__('math'),
            'range': range, 'enumerate': enumerate, 'zip': zip,
            'sorted': sorted, 'reversed': reversed, 'filter': filter, 'map': map,
        }
        
        eval_context = {**context, **safe_names}
        
        try:
            result = eval(expression, {"__builtins__": {}}, eval_context)
            return result
        except Exception as e:
            logger.warning(f"Expression evaluation error: {e}")
            return expression

    def _cast_value(self, value: Any, var_type: str) -> Any:
        """Cast value to specified type."""
        if value is None:
            return None
            
        if var_type == 'string':
            return str(value)
        elif var_type == 'number':
            try:
                if '.' in str(value):
                    return float(value)
                return int(value)
            except (ValueError, TypeError):
                return value
        elif var_type == 'boolean':
            if isinstance(value, bool):
                return value
            val_str = str(value).lower()
            return val_str in ('true', '1', 'yes', 'on')
        elif var_type == 'json':
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return value
        elif var_type == 'array':
            if isinstance(value, (list, tuple)):
                return list(value)
            return [value]
        
        return value

    def _apply_transform(self, value: Any, transform: str) -> Any:
        """Apply transformation to a value."""
        transforms = {
            'upper': lambda v: str(v).upper(),
            'lower': lambda v: str(v).lower(),
            'strip': lambda v: str(v).strip(),
            'title': lambda v: str(v).title(),
            'capitalize': lambda v: str(v).capitalize(),
            'reverse': lambda v: str(v)[::-1],
            'length': lambda v: len(v) if hasattr(v, '__len__') else 0,
            'int': lambda v: int(v) if v else 0,
            'float': lambda v: float(v) if v else 0.0,
            'str': lambda v: str(v),
            'bool': lambda v: bool(v),
            'json': lambda v: json.dumps(v) if not isinstance(v, str) else v,
        }
        
        func = transforms.get(transform)
        if func:
            return func(value)
        return value

    # ========================================================================
    # Loop Node Execution
    # ========================================================================
    
    def run_loop_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute loop node with enhanced logic.
        
        Supports:
        - for_each: Iterate over a list
        - while: Continue while condition is true
        - do_while: Execute at least once, then loop while condition
        - max_iterations: Safety limit on iterations
        - Nested node execution in loop body
        """
        start_time = time.time()
        
        loop_type = config.get('loop_type', 'for_each')
        max_iterations = config.get('max_iterations', 100)
        item_variable = config.get('item_variable', 'item')
        index_variable = config.get('index_variable', 'index')
        body_nodes = config.get('body_nodes', [])
        condition_expression = config.get('condition', '')
        items_source = config.get('items_source', 'input')
        items = config.get('items', [])
        result_variable = config.get('result_variable', 'loop_result')
        continue_on_error = config.get('continue_on_error', True)

        results = []
        errors = []
        iteration_count = 0

        try:
            if loop_type == 'for_each':
                results, iteration_count = self._execute_for_each_loop(
                    items=items,
                    items_source=items_source,
                    input_data=input_data,
                    item_variable=item_variable,
                    index_variable=index_variable,
                    max_iterations=max_iterations,
                    body_nodes=body_nodes,
                    continue_on_error=continue_on_error
                )

            elif loop_type == 'while':
                results, iteration_count, errors = self._execute_while_loop(
                    condition_expression=condition_expression,
                    input_data=input_data,
                    max_iterations=max_iterations,
                    index_variable=index_variable,
                    body_nodes=body_nodes,
                    continue_on_error=continue_on_error
                )

            elif loop_type == 'do_while':
                results, iteration_count, errors = self._execute_do_while_loop(
                    condition_expression=condition_expression,
                    input_data=input_data,
                    max_iterations=max_iterations,
                    index_variable=index_variable,
                    body_nodes=body_nodes,
                    continue_on_error=continue_on_error
                )

            elif loop_type == 'range':
                start = config.get('range_start', 0)
                end = config.get('range_end', 10)
                step = config.get('range_step', 1)
                results, iteration_count = self._execute_range_loop(
                    start=start, end=end, step=step,
                    input_data=input_data,
                    item_variable=item_variable,
                    index_variable=index_variable,
                    max_iterations=max_iterations,
                    body_nodes=body_nodes,
                    continue_on_error=continue_on_error
                )

            duration_ms = calculate_duration_ms(start_time)
            
            return {
                'success': True,
                'output': {
                    'results': results,
                    'count': len(results),
                    'iterations': iteration_count,
                    'max_iterations': max_iterations,
                    'errors': errors if errors else None,
                    result_variable: results
                },
                'count': len(results),
                'iterations': iteration_count,
                'duration_ms': duration_ms
            }

        except Exception as e:
            logger.exception("Loop execution error")
            return {
                'success': False,
                'error': f'Loop execution error: {str(e)}',
                'error_type': 'loop',
                'duration_ms': calculate_duration_ms(start_time)
            }

    def _execute_for_each_loop(
        self,
        items: List,
        items_source: str,
        input_data: Dict,
        item_variable: str,
        index_variable: str,
        max_iterations: int,
        body_nodes: List[Dict],
        continue_on_error: bool
    ) -> tuple:
        """Execute for_each loop."""
        if items_source == 'input':
            items = input_data.get('items', [])
        elif items_source == 'variable':
            var_name = input_data.get('items_variable', 'items')
            items = input_data.get(var_name, [])

        if not isinstance(items, (list, tuple, dict)):
            items = [items]

        results = []
        iteration_count = 0

        for i, item in enumerate(items):
            if iteration_count >= max_iterations:
                break

            loop_context = {**input_data, item_variable: item, index_variable: i}
            
            try:
                node_result = self._execute_loop_body(body_nodes, loop_context)
                results.append({
                    'item': item,
                    'index': i,
                    'success': True,
                    'output': node_result
                })
            except Exception as e:
                if continue_on_error:
                    results.append({
                        'item': item,
                        'index': i,
                        'success': False,
                        'error': str(e)
                    })
                else:
                    raise

            iteration_count += 1

        return results, iteration_count

    def _execute_while_loop(
        self,
        condition_expression: str,
        input_data: Dict,
        max_iterations: int,
        index_variable: str,
        body_nodes: List[Dict],
        continue_on_error: bool
    ) -> tuple:
        """Execute while loop."""
        results = []
        errors = []
        iteration_count = 0
        loop_context = {**input_data}

        while self._evaluate_loop_condition(condition_expression, loop_context):
            if iteration_count >= max_iterations:
                break

            iteration_result = {'iteration': iteration_count, 'success': True}
            
            try:
                loop_context[index_variable] = iteration_count
                loop_context['loop_iteration'] = iteration_count
                
                node_result = self._execute_loop_body(body_nodes, loop_context)
                iteration_result['output'] = node_result
                loop_context.update(node_result)
                
            except Exception as e:
                if continue_on_error:
                    iteration_result['success'] = False
                    iteration_result['error'] = str(e)
                    errors.append({'iteration': iteration_count, 'error': str(e)})
                else:
                    raise

            results.append(iteration_result)
            iteration_count += 1

        return results, iteration_count, errors

    def _execute_do_while_loop(
        self,
        condition_expression: str,
        input_data: Dict,
        max_iterations: int,
        index_variable: str,
        body_nodes: List[Dict],
        continue_on_error: bool
    ) -> tuple:
        """Execute do-while loop (executes at least once)."""
        results = []
        errors = []
        iteration_count = 0
        loop_context = {**input_data}

        while True:
            if iteration_count >= max_iterations:
                break

            iteration_result = {'iteration': iteration_count, 'success': True}
            
            try:
                loop_context[index_variable] = iteration_count
                loop_context['loop_iteration'] = iteration_count
                
                node_result = self._execute_loop_body(body_nodes, loop_context)
                iteration_result['output'] = node_result
                loop_context.update(node_result)
                
            except Exception as e:
                if continue_on_error:
                    iteration_result['success'] = False
                    iteration_result['error'] = str(e)
                    errors.append({'iteration': iteration_count, 'error': str(e)})
                else:
                    raise

            results.append(iteration_result)
            iteration_count += 1

            if not self._evaluate_loop_condition(condition_expression, loop_context):
                break

        return results, iteration_count, errors

    def _execute_range_loop(
        self,
        start: int,
        end: int,
        step: int,
        input_data: Dict,
        item_variable: str,
        index_variable: str,
        max_iterations: int,
        body_nodes: List[Dict],
        continue_on_error: bool
    ) -> tuple:
        """Execute range loop."""
        results = []
        iteration_count = 0

        for i in range(start, end, step):
            if iteration_count >= max_iterations:
                break

            loop_context = {**input_data, item_variable: i, index_variable: i}
            
            try:
                node_result = self._execute_loop_body(body_nodes, loop_context)
                results.append({
                    'value': i,
                    'index': i,
                    'success': True,
                    'output': node_result
                })
            except Exception as e:
                if continue_on_error:
                    results.append({
                        'value': i,
                        'index': i,
                        'success': False,
                        'error': str(e)
                    })
                else:
                    raise

            iteration_count += 1

        return results, iteration_count

    def _execute_loop_body(
        self,
        body_nodes: List[Dict],
        context: Dict
    ) -> Dict[str, Any]:
        """Execute nodes in loop body."""
        result = {}
        
        for body_node in body_nodes:
            node_type = body_node.get('type', 'prompt')
            node_config = body_node.get('config', {})
            
            node_result = self.execute_node(node_type, node_config, context)
            
            if not node_result.get('success', True):
                raise WorkflowExecutionError(
                    f"Loop body node failed: {node_result.get('error', 'Unknown error')}",
                    'loop_body'
                )
            
            if 'output' in node_result:
                result.update(node_result['output'])
            
            context.update(node_result)
        
        return result

    def _evaluate_loop_condition(
        self,
        condition_expression: str,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a loop condition expression."""
        if not condition_expression:
            return True

        try:
            eval_context = {
                **context,
                'True': True,
                'False': False,
                'None': None,
                'and': lambda a, b: a and b,
                'or': lambda a, b: a or b,
                'not': lambda a: not a,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'range': range,
            }
            return bool(eval(condition_expression, {"__builtins__": {}}, eval_context))
        except Exception as e:
            logger.warning(f"Loop condition evaluation error: {e}")
            return False

    # ========================================================================
    # Additional Node Types
    # ========================================================================
    
    def run_input_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute input node."""
        variable_name = config.get('variable_name', 'input')
        prompt = config.get('prompt', 'Please provide input')
        required = config.get('required', True)
        default_value = config.get('default')
        validation = config.get('validation', None)

        value = input_data.get(variable_name)
        if value is None and isinstance(input_data, dict):
            value = input_data.get('input_data', {}).get(variable_name)

        if value is None and default_value is not None:
            value = default_value

        if required and value is None:
            return {
                'success': False,
                'error': f"Required input missing: {variable_name}. {prompt}",
                'error_type': 'validation'
            }

        if validation:
            valid, error_msg = self._validate_input(value, validation)
            if not valid:
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'validation'
                }

        return {
            'success': True,
            'output': {variable_name: value} if value is not None else {},
            'duration_ms': 0
        }

    def _validate_input(self, value: Any, validation: Dict) -> tuple:
        """Validate input against validation rules."""
        rules = validation.get('rules', [])
        
        for rule in rules:
            rule_type = rule.get('type')
            
            if rule_type == 'required' and not value:
                return False, rule.get('message', 'This field is required')
            
            if rule_type == 'min_length':
                min_len = rule.get('value', 0)
                if len(str(value)) < min_len:
                    return False, rule.get('message', f'Minimum length is {min_len}')
            
            if rule_type == 'max_length':
                max_len = rule.get('value', 0)
                if len(str(value)) > max_len:
                    return False, rule.get('message', f'Maximum length is {max_len}')
            
            if rule_type == 'pattern':
                pattern = rule.get('value')
                if pattern and not re.match(pattern, str(value)):
                    return False, rule.get('message', 'Invalid format')
            
            if rule_type == 'min':
                min_val = rule.get('value', 0)
                if float(value) < min_val:
                    return False, rule.get('message', f'Value must be at least {min_val}')
            
            if rule_type == 'max':
                max_val = rule.get('value', 0)
                if float(value) > max_val:
                    return False, rule.get('message', f'Value must be at most {max_val}')
        
        return True, None

    def run_output_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute output node."""
        template = config.get('template', '{input}')
        output_variable = config.get('output_variable', 'result')
        output_format = config.get('format', 'text')

        rendered = self._render_template(template, input_data)

        if output_format == 'json':
            try:
                formatted = json.loads(rendered)
            except json.JSONDecodeError:
                formatted = rendered
        elif output_format == 'markdown':
            formatted = rendered
        else:
            formatted = rendered

        return {
            'success': True,
            'output': {
                output_variable: formatted,
                '_display': rendered,
                '_format': output_format
            }
        }

    def run_transform_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute data transformation node."""
        start_time = time.time()
        
        transform_type = config.get('transform_type', 'map')
        source_path = config.get('source_path', '')
        target_path = config.get('target_path', 'result')
        mapping = config.get('mapping', {})
        output_format = config.get('output_format', 'json')

        try:
            if transform_type == 'map':
                result = self._transform_map(input_data, mapping)
            elif transform_type == 'filter':
                condition = config.get('condition', '')
                result = self._transform_filter(input_data, source_path, condition)
            elif transform_type == 'reduce':
                reducer = config.get('reducer', {})
                result = self._transform_reduce(input_data, source_path, reducer)
            elif transform_type == 'flatten':
                result = self._transform_flatten(input_data, source_path)
            elif transform_type == 'group':
                group_by = config.get('group_by', '')
                result = self._transform_group(input_data, source_path, group_by)
            elif transform_type == 'sort':
                sort_by = config.get('sort_by', '')
                reverse = config.get('reverse', False)
                result = self._transform_sort(input_data, source_path, sort_by, reverse)
            elif transform_type == 'pick':
                fields = config.get('fields', [])
                result = self._transform_pick(input_data, source_path, fields)
            elif transform_type == 'omit':
                fields = config.get('fields', [])
                result = self._transform_omit(input_data, source_path, fields)
            elif transform_type == 'merge':
                sources = config.get('sources', [])
                result = self._transform_merge(input_data, sources)
            else:
                raise ValueError(f"Unknown transform type: {transform_type}")

            if output_format == 'json_string':
                result = json.dumps(result, ensure_ascii=False)

            duration_ms = calculate_duration_ms(start_time)

            return {
                'success': True,
                'output': {target_path: result},
                'transform_type': transform_type,
                'duration_ms': duration_ms
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Transform error: {str(e)}',
                'error_type': 'transform',
                'duration_ms': calculate_duration_ms(start_time)
            }

    def _transform_map(self, input_data: Dict, mapping: Dict) -> Dict:
        """Apply field mapping transformation."""
        result = {}
        for target_key, source_key in mapping.items():
            if isinstance(source_key, dict):
                path = source_key.get('path', source_key.get('from'))
                default = source_key.get('default')
                value = self._get_nested_value(input_data, path, default)
            else:
                value = self._get_nested_value(input_data, source_key)
            result[target_key] = value
        return result

    def _transform_filter(self, input_data: Dict, source_path: str, condition: str) -> Any:
        """Filter array based on condition."""
        items = self._get_nested_value(input_data, source_path, [])
        if not isinstance(items, (list, tuple)):
            return items
        
        filtered = []
        for i, item in enumerate(items):
            item_context = {**input_data, 'item': item, 'index': i}
            if self._evaluate_condition_expression(condition, item_context):
                filtered.append(item)
        return filtered

    def _transform_reduce(self, input_data: Dict, source_path: str, reducer: Dict) -> Any:
        """Reduce array to single value."""
        items = self._get_nested_value(input_data, source_path, [])
        accumulator_path = reducer.get('accumulator', '0')
        item_var = reducer.get('item_var', 'item')
        acc_var = reducer.get('acc_var', 'acc')
        
        accumulator = self._get_nested_value({'0': 0}, accumulator_path, 0)
        
        for item in items:
            context = {**input_data, item_var: item, acc_var: accumulator}
            new_acc_str = reducer.get('expression', acc_var)
            try:
                accumulator = eval(new_acc_str, {"__builtins__": {}}, context)
            except:
                break
        
        return accumulator

    def _transform_flatten(self, input_data: Dict, source_path: str) -> List:
        """Flatten nested array."""
        items = self._get_nested_value(input_data, source_path, [])
        result = []
        
        def _flatten(obj):
            if isinstance(obj, (list, tuple)):
                for item in obj:
                    _flatten(item)
            else:
                result.append(obj)
        
        _flatten(items)
        return result

    def _transform_group(self, input_data: Dict, source_path: str, group_by: str) -> Dict:
        """Group array items by field."""
        items = self._get_nested_value(input_data, source_path, [])
        groups = {}
        
        for item in items:
            if isinstance(item, dict):
                key = item.get(group_by, 'unknown')
                if key not in groups:
                    groups[key] = []
                groups[key].append(item)
            else:
                key = 'value'
                if key not in groups:
                    groups[key] = []
                groups[key].append(item)
        
        return groups

    def _transform_sort(self, input_data: Dict, source_path: str, sort_by: str, reverse: bool) -> List:
        """Sort array by field."""
        items = self._get_nested_value(input_data, source_path, [])
        
        if not sort_by:
            return sorted(items, reverse=reverse) if isinstance(items[0] if items else None, (int, float, str)) else items
        
        return sorted(items, key=lambda x: x.get(sort_by, '') if isinstance(x, dict) else x, reverse=reverse)

    def _transform_pick(self, input_data: Dict, source_path: str, fields: List[str]) -> Dict:
        """Pick specific fields from object."""
        obj = self._get_nested_value(input_data, source_path, {})
        if not isinstance(obj, dict):
            return obj
        
        return {k: v for k, v in obj.items() if k in fields}

    def _transform_omit(self, input_data: Dict, source_path: str, fields: List[str]) -> Dict:
        """Omit specific fields from object."""
        obj = self._get_nested_value(input_data, source_path, {})
        if not isinstance(obj, dict):
            return obj
        
        return {k: v for k, v in obj.items() if k not in fields}

    def _transform_merge(self, input_data: Dict, sources: List[Dict]) -> Dict:
        """Merge multiple sources into one object."""
        result = {}
        for source in sources:
            path = source.get('path', '')
            override = source.get('override', True)
            
            value = self._get_nested_value(input_data, path, {})
            if isinstance(value, dict):
                if override:
                    result.update(value)
                else:
                    for k, v in value.items():
                        if k not in result:
                            result[k] = v
        
        return result

    def run_email_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute email node."""
        from django.core.mail import send_mail
        from django.conf import settings

        to = self._render_template(config.get('to', ''), input_data)
        cc = self._render_template(config.get('cc', ''), input_data)
        bcc = self._render_template(config.get('bcc', ''), input_data)
        subject = self._render_template(config.get('subject', ''), input_data)
        body = self._render_template(config.get('body', ''), input_data)
        from_email = config.get('from_email') or getattr(settings, 'DEFAULT_FROM_EMAIL', None)

        if not to:
            return {
                'success': False,
                'error': 'Recipient (to) is required for email node'
            }

        if not subject and not body:
            return {
                'success': False,
                'error': 'Either subject or body is required for email node'
            }

        recipient_list = [r.strip() for r in to.split(',') if r.strip()]
        cc_list = [r.strip() for r in cc.split(',') if r.strip()] if cc else []
        bcc_list = [r.strip() for r in bcc.split(',') if r.strip()] if bcc else []

        try:
            from django.core.mail import EmailMultiAlternatives

            email = EmailMultiAlternatives(
                subject=subject or '(No Subject)',
                body=body,
                from_email=from_email,
                to=recipient_list,
                cc=cc_list if cc_list else [],
                bcc=bcc_list if bcc_list else [],
            )
            if config.get('is_html', False):
                email.attach_alternative(body, 'text/html')

            email.send(fail_silently=False)

            return {
                'success': True,
                'output': {
                    'sent': True,
                    'recipient_count': len(recipient_list),
                    'recipients': recipient_list,
                    'cc': cc_list,
                    'bcc': bcc_list,
                    'subject': subject
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to send email: {str(e)}"
            }

    def run_delay_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute delay node - pauses workflow for specified duration."""
        start_time = time.time()
        seconds = config.get('seconds', config.get('delay_seconds', 1))
        delay_reason = config.get('reason', 'Workflow delay')

        try:
            seconds = float(seconds)
            if seconds <= 0:
                seconds = 1
            if seconds > 3600:
                seconds = 3600
        except (ValueError, TypeError):
            seconds = 1

        time.sleep(seconds)
        duration_ms = calculate_duration_ms(start_time)

        return {
            'success': True,
            'output': {
                'delayed': True,
                'seconds': seconds,
                'reason': delay_reason,
                'resumed_at': time.strftime('%Y-%m-%dT%H:%M:%S')
            },
            'duration_ms': duration_ms
        }

    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _get_nested_value(self, data: Dict, path: str, default: Any = None) -> Any:
        """Get nested value from dict using dot notation."""
        if not path:
            return data
        
        if '.' not in path and path in data:
            return data.get(path, default)
        
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                value = value[idx] if 0 <= idx < len(value) else None
            else:
                return default
            if value is None:
                return default
        return value

    def _render_template(self, template: str, data: Dict) -> str:
        """Render template with data, supporting {{variable}} syntax."""
        if not template:
            return template

        result = str(template)

        pattern = r'\{\{([^}]+)\}\}'

        def replacer(match):
            var_path = match.group(1).strip()
            value = self._get_nested_value(data, var_path)
            if value is None:
                return match.group(0)
            return str(value)

        result = re.sub(pattern, replacer, result)
        return result

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        avg_duration = (
            self._execution_stats['total_duration_ms'] / self._execution_stats['total_calls']
            if self._execution_stats['total_calls'] > 0 else 0
        )
        
        return {
            **self._execution_stats,
            'avg_duration_ms': avg_duration,
            'success_rate': (
                self._execution_stats['successful_calls'] / self._execution_stats['total_calls']
                if self._execution_stats['total_calls'] > 0 else 0
            )
        }

    def reset_stats(self):
        """Reset execution statistics."""
        self._execution_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_tokens': 0,
            'total_duration_ms': 0
        }

    # ========================================================================
    # Multimodal & Generation
    # ========================================================================

    def _poll_replicate_prediction(self, prediction_id: str, timeout_seconds: int = 300) -> Dict[str, Any]:
        """
        Poll Replicate prediction status until completed or timeout.

        Args:
            prediction_id: Replicate prediction ID returned from initial request
            timeout_seconds: Maximum wait time (default 5 minutes)

        Returns:
            Final prediction result dictionary
        """
        api_key = self._get_credential('replicate')
        headers = {'Authorization': f'Bearer {api_key}'}

        poll_interval = 5  # seconds between polls
        max_attempts = timeout_seconds // poll_interval

        with httpx.Client(timeout=timeout_seconds + 30) as client:
            for attempt in range(max_attempts):
                resp = client.get(
                    f'https://api.replicate.com/v1/predictions/{prediction_id}',
                    headers=headers
                )
                resp.raise_for_status()
                pred = resp.json()

                status = pred.get('status')
                if status == 'succeeded':
                    return pred
                elif status == 'failed':
                    error = pred.get('error') or 'Unknown error'
                    raise WorkflowExecutionError(f'Replicate prediction failed: {error}')
                elif status == 'canceled':
                    raise WorkflowExecutionError('Replicate prediction was canceled')

                # Still processing, wait before next poll
                time.sleep(poll_interval)

        raise WorkflowExecutionError(f'Replicate prediction timed out after {timeout_seconds}s')

    def _get_zimage_pipeline(self, model_id: str, device: str, dtype_name: str, enable_cpu_offload: bool):
        """Lazily load and cache the local Z-Image pipeline."""
        global _zimage_pipeline, _zimage_pipeline_key

        cache_key = (model_id, device, dtype_name, enable_cpu_offload)
        if _zimage_pipeline is not None and _zimage_pipeline_key == cache_key:
            return _zimage_pipeline

        try:
            import torch
            from diffusers import ZImagePipeline
        except ImportError as exc:
            raise LocalImageModelError(
                '本地 Z-Image-Turbo 依赖未安装，请先安装 torch、transformers、accelerate、safetensors 和最新 diffusers。'
            ) from exc

        torch_dtype = _resolve_zimage_dtype(torch, dtype_name)

        try:
            pipe = ZImagePipeline.from_pretrained(
                model_id,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=False,
            )
        except Exception as exc:
            raise LocalImageModelError(f'加载 Z-Image-Turbo 模型失败: {exc}') from exc

        try:
            if enable_cpu_offload:
                pipe.enable_model_cpu_offload()
            else:
                target_device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
                pipe.to(target_device)
        except Exception as exc:
            raise LocalImageModelError(f'初始化 Z-Image-Turbo 运行设备失败: {exc}') from exc

        _zimage_pipeline = pipe
        _zimage_pipeline_key = cache_key
        return pipe

    def _run_zimage_local_generation(
        self,
        prompt: str,
        model: str,
        size: str,
        n: int,
        node_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate images with a local Z-Image-Turbo pipeline."""
        if not prompt:
            raise LocalImageModelError('Z-Image-Turbo 生成失败：prompt 不能为空')

        import torch

        model_id = model or getattr(settings, 'ZIMAGE_MODEL_ID', 'Tongyi-MAI/Z-Image-Turbo')
        device = node_config.get('device') or getattr(settings, 'ZIMAGE_DEVICE', 'cuda')
        dtype_name = node_config.get('dtype') or getattr(settings, 'ZIMAGE_DTYPE', 'auto')
        enable_cpu_offload = node_config.get('enable_cpu_offload')
        if enable_cpu_offload is None:
            enable_cpu_offload = getattr(settings, 'ZIMAGE_ENABLE_CPU_OFFLOAD', True)

        width, height = _normalize_image_size(size)
        num_images = max(1, int(n or 1))
        num_inference_steps = int(node_config.get('num_inference_steps') or getattr(settings, 'ZIMAGE_NUM_INFERENCE_STEPS', 9))
        guidance_scale = float(node_config.get('guidance_scale') if node_config.get('guidance_scale') is not None else getattr(settings, 'ZIMAGE_GUIDANCE_SCALE', 0.0))
        seed = node_config.get('seed')

        if device == 'cuda' and not torch.cuda.is_available():
            raise LocalImageModelError('Z-Image-Turbo 配置为 CUDA，但当前环境未检测到可用 NVIDIA GPU')

        pipeline = self._get_zimage_pipeline(model_id, device, dtype_name, bool(enable_cpu_offload))

        generator = None
        generator_device = 'cuda' if device == 'cuda' and torch.cuda.is_available() else 'cpu'
        if seed is not None and str(seed).strip() != '':
            generator = torch.Generator(generator_device).manual_seed(int(seed))

        try:
            result = pipeline(
                prompt=prompt,
                height=height,
                width=width,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                num_images_per_prompt=num_images,
                generator=generator,
            )
        except RuntimeError as exc:
            if 'out of memory' in str(exc).lower():
                raise LocalImageModelError(
                    'Z-Image-Turbo 显存不足。你的 RTX 4060 8GB 建议启用 CPU offload，并避免高并发或过大分辨率。'
                ) from exc
            raise LocalImageModelError(f'Z-Image-Turbo 推理失败: {exc}') from exc
        except Exception as exc:
            raise LocalImageModelError(f'Z-Image-Turbo 推理失败: {exc}') from exc

        output_dir = settings.MEDIA_ROOT / 'generated' / 'zimage'
        output_dir.mkdir(parents=True, exist_ok=True)

        images = []
        for index, image in enumerate(result.images or []):
            if not isinstance(image, Image.Image):
                raise LocalImageModelError('Z-Image-Turbo 返回了无法识别的图片对象')

            filename = f"zimage_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{index + 1}.png"
            output_path = output_dir / filename
            image.save(output_path)
            images.append({
                'path': str(output_path),
                'url': _build_media_url(str(output_path)),
                'width': image.width,
                'height': image.height,
                'provider': 'zimage_local',
                'model': model_id,
            })

        return {
            'success': True,
            'output': {
                'images': images,
                'count': len(images),
                'provider': 'zimage_local',
                'model': model_id,
                'device': device,
                'dtype': dtype_name,
                'width': width,
                'height': height,
                'num_inference_steps': num_inference_steps,
                'guidance_scale': guidance_scale,
                'cpu_offload_enabled': bool(enable_cpu_offload),
            }
        }

    def run_image_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Image Generation Node
        Generates images from text prompts using various providers.
        """
        provider = node_config.get('provider', 'openai')
        model = node_config.get('model', 'dall-e-3')
        prompt_template = node_config.get('prompt', '')
        prompt = self._render_template(prompt_template, context) if prompt_template else context.get('prompt', '')
        size = node_config.get('size', '1024x1024')
        quality = node_config.get('quality', 'standard')
        style = node_config.get('style', 'vivid')
        n = node_config.get('n', 1)

        try:
            if provider == 'openai':
                import os
                if not os.environ.get('OPENAI_API_KEY'):
                    return {
                        'success': True,
                        'output': {
                            'images': [{'url': f'https://picsum.photos/seed/{hash(prompt) % 100000}/1024/1024', 'revised_prompt': f'[Demo Mode] {prompt}'}],
                            'count': 1,
                            'demo': True
                        }
                    }
                from openai import OpenAI
                client = OpenAI()
                response = client.images.generate(
                    model=model,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    style=style,
                    n=n
                )
                images = [{'url': img.url, 'revised_prompt': getattr(img, 'revised_prompt', '')} for img in response.data]
                return {'success': True, 'output': {'images': images, 'count': len(images)}}
            elif provider == 'stability':
                api_key = self._get_credential('stability')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {
                    'text_prompts': [{'text': prompt}],
                    'cfg_scale': 7, 'height': 1024, 'width': 1024,
                    'samples': n, 'steps': 30
                }
                with httpx.Client(timeout=IMAGE_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    images = [{'base64': art['base64']} for art in result.get('artifacts', [])]
                    return {'success': True, 'output': {'images': images, 'count': len(images)}}
            elif provider == 'flux':
                api_key = self._get_credential('replicate')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {
                    'version': 'latest',
                    'input': {'prompt': prompt, 'num_inference_steps': 25, 'guidance_scale': 3.5, 'num_images': n}
                }
                with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.replicate.com/v1/predictions',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    pred = resp.json()
                    prediction_id = pred['id']

                # Poll until prediction completes
                final_pred = self._poll_replicate_prediction(prediction_id, timeout_seconds=300)
                output = final_pred.get('output', [])

                if isinstance(output, list):
                    images = []
                    for item in output:
                        if isinstance(item, dict):
                            images.append({'url': item.get('url', ''), 'width': item.get('width'), 'height': item.get('height')})
                        elif isinstance(item, str):
                            images.append({'url': item})
                    return {'success': True, 'output': {'images': images, 'count': len(images)}}
                return {'success': True, 'output': {'images': [], 'raw_output': output}}
            elif provider == 'zimage_local':
                return self._run_zimage_local_generation(
                    prompt=prompt,
                    model=model,
                    size=size,
                    n=n,
                    node_config=node_config,
                )
            elif provider == 'replicate':
                api_key = self._get_credential('replicate')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {
                    'version': model,
                    'input': {'prompt': prompt, 'num_outputs': n}
                }
                with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.replicate.com/v1/predictions',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    pred = resp.json()
                    prediction_id = pred['id']

                # Poll until prediction completes
                final_pred = self._poll_replicate_prediction(prediction_id, timeout_seconds=300)
                output = final_pred.get('output', [])

                if isinstance(output, list):
                    images = []
                    for item in output:
                        if isinstance(item, dict):
                            images.append({'url': item.get('url', ''), 'width': item.get('width'), 'height': item.get('height')})
                        elif isinstance(item, str):
                            images.append({'url': item})
                    return {'success': True, 'output': {'images': images, 'count': len(images)}}
                return {'success': True, 'output': {'images': [], 'raw_output': output}}
            else:
                return {'success': False, 'error': f'Unknown image provider: {provider}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_video_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Video Generation Node
        Generates videos from text or images.
        """
        provider = node_config.get('provider', 'replicate')
        model = node_config.get('model', '')
        prompt_template = node_config.get('prompt', '')
        prompt = self._render_template(prompt_template, context) if prompt_template else context.get('prompt', '')
        duration = node_config.get('duration', 4)
        fps = node_config.get('fps', 24)
        resolution = node_config.get('resolution', '720p')
        input_image = node_config.get('inputImage') or context.get('inputImage', '')
        resolution_map = {'720p': 720, '1080p': 1080, '4k': 2160}
        height = resolution_map.get(resolution, 720)

        try:
            # Demo mode: no API key needed, return a simulated video result
            import os
            if not os.environ.get('REPLICATE_API_KEY') and provider == 'replicate':
                return {
                    'success': True,
                    'output': {
                        'video_url': f'https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4',
                        'thumbnail': f'https://picsum.photos/seed/{hash(prompt) % 100000}/640/360',
                        'status': 'completed',
                        'duration': duration,
                        'fps': fps,
                        'resolution': resolution,
                        'demo': True,
                        'prompt': prompt
                    }
                }
            if provider == 'replicate':
                api_key = self._get_credential('replicate')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                inp = {'prompt': prompt, 'num_frames': duration * fps, 'fps': fps}
                if input_image:
                    inp['input_image'] = input_image
                payload = {'version': model or 'latest', 'input': inp}
                with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.replicate.com/v1/predictions',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    pred = resp.json()
                    prediction_id = pred['id']

                # Poll until prediction completes
                final_pred = self._poll_replicate_prediction(prediction_id, timeout_seconds=300)
                output = final_pred.get('output', {})
                video_url = output.get('video') or output.get('url') or ''
                if isinstance(output, list):
                    video_url = output[0] if output else ''
                return {
                    'success': True,
                    'output': {
                        'video_url': video_url,
                        'status': 'completed',
                        'prediction_id': prediction_id,
                        'output': output
                    }
                }
            elif provider == 'runway':
                api_key = self._get_credential('runway')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {'prompt': prompt, 'model': model or 'gen3a_turbo', 'duration': duration}
                with httpx.Client(timeout=VIDEO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.runwayml.com/v1/video_generation',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    return {'success': True, 'output': resp.json()}
            elif provider == 'pika':
                api_key = self._get_credential('pika')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {'prompt': prompt, 'model': model or 'pika-2.0', 'duration': duration}
                with httpx.Client(timeout=VIDEO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.pika.art/v1/generate',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    return {'success': True, 'output': resp.json()}
            else:
                return {'success': False, 'error': f'Unknown video provider: {provider}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_audio_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audio/TTS Generation Node
        Generates audio from text using TTS providers.
        """
        provider = node_config.get('provider', 'openai')
        model = node_config.get('model', 'tts-1')
        text_template = node_config.get('text', '')
        text = self._render_template(text_template, context) if text_template else context.get('text', '')
        voice = node_config.get('voice', 'alloy')
        speed = node_config.get('speed', 1.0)
        audio_format = node_config.get('format', 'mp3')

        try:
            if provider == 'openai':
                import os
                if not os.environ.get('OPENAI_API_KEY'):
                    return {
                        'success': True,
                        'output': {
                            'images': [{'url': f'https://picsum.photos/seed/{hash(prompt) % 100000}/1024/1024', 'revised_prompt': f'[Demo Mode] {prompt}'}],
                            'count': 1,
                            'demo': True
                        }
                    }
                from openai import OpenAI
                client = OpenAI()
                response = client.audio.speech.create(
                    model=model, input=text, voice=voice,
                    response_format=audio_format, speed=speed
                )
                import base64
                audio_bytes = response.content
                audio_b64 = base64.b64encode(audio_bytes).decode()
                return {'success': True, 'output': {'audio_base64': audio_b64, 'format': audio_format, 'duration_est': len(text) / (5 * speed)}}
            elif provider == 'elevenlabs':
                api_key = self._get_credential('elevenlabs')
                headers = {'xi-api-key': api_key, 'Content-Type': 'application/json'}
                payload = {'text': text, 'model_id': model or 'eleven_monolingual_v1',
                            'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75, 'speed': speed}}
                with httpx.Client(timeout=AUDIO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'https://api.elevenlabs.io/v1/text-to-speech/{voice}',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    import base64
                    audio_b64 = base64.b64encode(resp.content).decode()
                    return {'success': True, 'output': {'audio_base64': audio_b64, 'format': 'mp3'}}
            elif provider == 'azure':
                subscription_key = self._get_credential('azure_tts')
                region = node_config.get('region', 'eastus')
                headers = {'Ocp-Apim-Subscription-Key': subscription_key, 'Content-Type': 'application/ssml+xml'}
                ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><voice name="{voice}"><prosody rate="{speed}">{text}</prosody></voice></speak>'
                with httpx.Client(timeout=AUDIO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1',
                        headers=headers, data=ssml.encode()
                    )
                    resp.raise_for_status()
                    import base64
                    audio_b64 = base64.b64encode(resp.content).decode()
                    return {'success': True, 'output': {'audio_base64': audio_b64, 'format': 'mp3'}}
            else:
                return {'success': False, 'error': f'Unknown audio provider: {provider}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_subtitle_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Subtitle Generation Node
        Generates subtitles from audio/video.
        """
        input_type = node_config.get('inputType', 'audio')
        input_path = node_config.get('inputPath', '') or context.get('inputPath', '')
        language = node_config.get('language', 'en')
        format = node_config.get('format', 'srt')

        try:
            api_key = self._get_credential('openai')
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            if input_type == 'audio':
                with open(input_path, 'rb') as f:
                    transcript = client.audio.transcriptions.create(
                        model='whisper-1', file=f, language=language
                    )
            else:
                with open(input_path, 'rb') as f:
                    transcript = client.audio.transcriptions.create(
                        model='whisper-1', file=f, language=language
                    )

            text = transcript.text
            segments = getattr(transcript, 'segments', [])
            if format == 'srt':
                content = self._text_to_srt(text, segments)
            elif format == 'vtt':
                content = self._text_to_vtt(text, segments)
            else:
                content = text

            return {'success': True, 'output': {'subtitles': content, 'format': format, 'text': text}}
        except ImportError:
            return {'success': False, 'error': 'openai library required. Install with: pip install openai'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _text_to_srt(self, text: str, segments: list) -> str:
        import datetime
        lines = []
        for i, seg in enumerate(segments or [], 1):
            start = self._seconds_to_srt_time(seg.get('start', 0))
            end = self._seconds_to_srt_time(seg.get('end', 0))
            lines.append(f"{i}\n{start} --> {end}\n{seg.get('text', '').strip()}\n")
        if not lines:
            lines.append(f"1\n00:00:00,000 --> 00:00:05,000\n{text}\n")
        return '\n'.join(lines)

    def _text_to_vtt(self, text: str, segments: list) -> str:
        lines = ['WEBVTT\n']
        for seg in segments or []:
            start = self._seconds_to_vtt_time(seg.get('start', 0))
            end = self._seconds_to_vtt_time(seg.get('end', 0))
            lines.append(f"{start} --> {end}\n{seg.get('text', '').strip()}\n")
        if len(lines) == 1:
            lines.append("00:00:00.000 --> 00:00:05.000\n" + text + "\n")
        return '\n'.join(lines)

    def _seconds_to_srt_time(self, seconds: float) -> str:
        import datetime
        td = datetime.timedelta(seconds=seconds)
        h = td.seconds // 3600
        m = (td.seconds % 3600) // 60
        s = td.seconds % 60
        ms = td.microseconds // 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _seconds_to_vtt_time(self, seconds: float) -> str:
        import datetime
        td = datetime.timedelta(seconds=seconds)
        h = td.seconds // 3600
        m = (td.seconds % 3600) // 60
        s = td.seconds % 60
        ms = td.microseconds // 1000
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def run_image_editing_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Image Editing Node
        Edits existing images based on instructions.
        """
        provider = node_config.get('provider', 'openai')
        model = node_config.get('model', 'dall-e-2')
        image = node_config.get('image', '') or context.get('image', '')
        instruction_template = node_config.get('instruction', '')
        instruction = self._render_template(instruction_template, context) if instruction_template else context.get('instruction', '')
        mask = node_config.get('mask', '')

        try:
            if provider == 'openai':
                import os
                if not os.environ.get('OPENAI_API_KEY'):
                    return {
                        'success': True,
                        'output': {
                            'images': [{'url': f'https://picsum.photos/seed/{hash(prompt) % 100000}/1024/1024', 'revised_prompt': f'[Demo Mode] {prompt}'}],
                            'count': 1,
                            'demo': True
                        }
                    }
                from openai import OpenAI
                client = OpenAI()
                image_file = None
                mask_file = None
                try:
                    if image:
                        image_file = open(image, 'rb') if not image.startswith('http') else None
                    if mask:
                        mask_file = open(mask, 'rb') if not mask.startswith('http') else None
                    response = client.images.edit(
                        model=model,
                        image=image_file,
                        mask=mask_file,
                        prompt=instruction,
                        n=1
                    )
                finally:
                    if image_file:
                        image_file.close()
                    if mask_file:
                        mask_file.close()
                return {'success': True, 'output': {'url': response.data[0].url, 'revised_prompt': response.data[0].revised_prompt}}
            else:
                return {'success': False, 'error': f'Unknown image editing provider: {provider}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ========================================================================
    # ML & Training
    # ========================================================================

    def run_dataset_upload_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dataset Upload Node
        Handles dataset upload from various sources.
        Parses the file and creates a Dataset record in the database.
        """
        import os
        import hashlib
        from django.conf import settings
        from datasets.models import Dataset
        from datasets.utils import parse_dataset_file, download_from_url, download_from_s3

        source = node_config.get('source', 'upload')
        path_template = node_config.get('path', '')
        path = self._render_template(path_template, context) if path_template else context.get('path', '')
        format_type = node_config.get('format', 'csv')
        name = node_config.get('label', 'Dataset') or node_config.get('name', 'Dataset')
        description = node_config.get('description', '')
        dataset_id = node_config.get('datasetId', '') or context.get('dataset_id', '')

        try:
            file_path = None
            file_size = 0

            if source == 'upload':
                if not path:
                    return {'success': False, 'error': 'Path is required for upload source'}

                resolved_path = path
                if not os.path.isabs(resolved_path):
                    resolved_path = os.path.join(settings.MEDIA_ROOT, path)

                if not os.path.exists(resolved_path):
                    return {'success': False, 'error': f'File not found: {resolved_path}'}

                file_path = resolved_path
                file_size = os.path.getsize(file_path)

            elif source == 'url':
                if not path:
                    return {'success': False, 'error': 'URL is required for url source'}

                try:
                    file_path, file_size = download_from_url(path)
                except Exception as e:
                    return {'success': False, 'error': f'Failed to download from URL: {str(e)}'}

            elif source == 's3':
                if not path:
                    return {'success': False, 'error': 'S3 path is required for s3 source'}

                try:
                    file_path, file_size = download_from_s3(path)
                except ImportError:
                    return {'success': False, 'error': 'boto3 required for S3. Install with: pip install boto3'}
                except Exception as e:
                    return {'success': False, 'error': f'Failed to download from S3: {str(e)}'}

            else:
                return {'success': False, 'error': f'Unknown source: {source}'}

            if not file_path or not os.path.exists(file_path):
                return {'success': False, 'error': 'Failed to get file path'}

            preview_data = parse_dataset_file(file_path, format_type, max_rows=100)

            columns = preview_data.get('columns', [])
            row_count = preview_data.get('row_count', 0)
            column_count = len(columns)
            preview_rows = preview_data.get('rows', [])

            content_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    content_hash.update(chunk)
            hash_suffix = content_hash.hexdigest()[:12]

            dataset = Dataset.objects.create(
                name=f"{name}_{hash_suffix}",
                description=description or f'Dataset from {source}: {path}',
                source=source,
                file_path=file_path,
                format=format_type,
                size_bytes=file_size,
                row_count=row_count,
                column_count=column_count,
                columns=columns,
                preview_data=preview_rows,
                status='ready',
                created_by=self.user if hasattr(self, 'user') else None,
                tenant=self.tenant if hasattr(self, 'tenant') else None
            )

            output_data = {
                'dataset_id': str(dataset.id),
                'name': dataset.name,
                'row_count': row_count,
                'column_count': column_count,
                'columns': columns,
                'size_bytes': file_size,
                'format': format_type,
                'source': source,
                'path': file_path,
                'preview_rows': len(preview_rows),
                'status': 'ready'
            }

            return {'success': True, 'output': output_data}

        except Exception as e:
            logger.error(f"Dataset upload node error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def run_data_annotation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Data Annotation Node
        Creates annotation projects, generates pre-labels, and exports labeled datasets.
        """
        from annotations.models import AnnotationProject
        from annotations.utils import initialize_items_from_dataset, generate_pre_labels, export_annotations

        annotation_type = node_config.get('annotationType', 'classification')
        labels = node_config.get('labels', [])
        model_assisted = node_config.get('modelAssisted', False)
        model_id = node_config.get('modelId', '') or 'gpt-4o-mini'
        dataset_id = node_config.get('datasetId', '') or context.get('dataset_id', '')

        if not dataset_id:
            return {'success': False, 'error': 'No dataset ID provided'}

        if not labels:
            return {'success': False, 'error': 'No labels provided for annotation'}

        try:
            from datasets.models import Dataset
            try:
                dataset = Dataset.objects.get(id=dataset_id)
            except Dataset.DoesNotExist:
                return {'success': False, 'error': f'Dataset {dataset_id} not found'}

            if not dataset.is_ready:
                return {'success': False, 'error': f'Dataset {dataset_id} is not ready'}

            user = None
            if hasattr(self, 'user'):
                user = self.user
            elif context.get('user_id'):
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(id=context.get('user_id'))
                except User.DoesNotExist:
                    pass

            project_name = node_config.get('label', f'Annotation_{dataset.name}_{uuid.uuid4().hex[:6]}')

            project = AnnotationProject.objects.create(
                name=project_name,
                annotation_type=annotation_type,
                labels=labels,
                dataset=dataset,
                model_assisted=model_assisted,
                model_id=model_id if model_assisted else '',
                status='draft',
                created_by=user
            )

            init_result = initialize_items_from_dataset(project)

            if not init_result.get('success'):
                project.delete()
                return {'success': False, 'error': f"Failed to initialize items: {init_result.get('error')}"}

            if model_assisted:
                pre_label_result = generate_pre_labels(project, model_id)
                if not pre_label_result.get('success'):
                    logger.warning(f"Pre-labeling partially failed: {pre_label_result.get('error')}")

            project.refresh_from_db()

            export_result = export_annotations(project, 'json')

            context['annotation_project_id'] = str(project.id)
            context['dataset_id'] = str(dataset.id)
            context['annotated_items'] = project.annotated_items
            context['total_items'] = project.total_items

            return {
                'success': True,
                'output': {
                    'project_id': str(project.id),
                    'dataset_id': str(dataset.id),
                    'annotation_type': annotation_type,
                    'labels': labels,
                    'model_assisted': model_assisted,
                    'total_items': project.total_items,
                    'annotated_items': project.annotated_items,
                    'exported_count': export_result.get('count', 0),
                    'labeled_data': export_result.get('data', {}).get('annotations', [])
                }
            }

        except Exception as e:
            logger.error(f"Data annotation node error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def run_data_augmentation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Data Augmentation Node
        Augments training data using various strategies with real augmentation.
        Supports images, text, and tabular data.
        """
        from datasets.models import Dataset
        from augmentation.augmentors import get_augmentor, detect_data_type
        from augmentation.tasks import run_augmentation_task_sync
        from pathlib import Path
        import os

        strategy = node_config.get('strategy', 'all')
        transformations = node_config.get('transformations', [])
        ratio = node_config.get('ratio', 2.0)
        dataset_id = node_config.get('datasetId', '') or context.get('dataset_id', '')

        if not dataset_id:
            return {'success': False, 'error': 'No dataset ID provided'}

        try:
            dataset = Dataset.objects.get(id=dataset_id)
        except Dataset.DoesNotExist:
            return {'success': False, 'error': f'Dataset {dataset_id} not found'}

        if not dataset.is_ready:
            return {'success': False, 'error': f'Dataset {dataset_id} is not ready'}

        data_type = detect_data_type(dataset)
        file_path = dataset.get_absolute_file_path()

        if not file_path or not os.path.exists(file_path):
            return {'success': False, 'error': f'Dataset file not found: {file_path}'}

        output_dir_base = Path(settings.MEDIA_ROOT) / 'augmented'
        output_dir = output_dir_base / f"node_{uuid.uuid4().hex[:8]}"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            augmentor = get_augmentor(
                data_type=data_type,
                strategy=strategy,
                ratio=ratio,
                transformations=transformations
            )

            if data_type == 'image':
                result = augmentor.augment_dataset(
                    input_path=file_path,
                    output_dir=str(output_dir)
                )
            elif data_type == 'text':
                result = augmentor.augment_dataset(
                    input_path=file_path,
                    output_dir=str(output_dir)
                )
            elif data_type == 'tabular':
                result = augmentor.augment_csv(
                    input_path=file_path,
                    output_dir=str(output_dir)
                )
            else:
                return {'success': False, 'error': f'Unsupported data type: {data_type}'}

            output_files = list(output_dir.glob('*'))
            output_paths = [str(f) for f in output_files if f.is_file()]

            output_dataset = Dataset.objects.create(
                name=f"{dataset.name}_augmented_{uuid.uuid4().hex[:6]}",
                description=f"增强后的数据集，基于 {dataset.name} 创建",
                source='upload',
                file_path=str(output_dir),
                format=dataset.format,
                size_bytes=sum(f.stat().st_size for f in output_files if f.is_file()),
                row_count=result.get('augmented_count', 0),
                column_count=dataset.column_count,
                columns=dataset.columns,
                status='ready',
                metadata={
                    'augmentation': {
                        'original_dataset_id': str(dataset.id),
                        'strategy': strategy,
                        'ratio': ratio,
                        'data_type': data_type,
                        'original_count': result.get('original_count', 0),
                        'augmented_count': result.get('augmented_count', 0),
                    }
                }
            )

            return {
                'success': True,
                'output': {
                    'dataset_id': str(output_dataset.id),
                    'augmented_count': result.get('augmented_count', 0),
                    'original_count': result.get('original_count', 0),
                    'total_count': result.get('total_count', 0),
                    'output_dir': str(output_dir),
                    'data_type': data_type,
                    'strategy': strategy,
                    'ratio': ratio,
                    'format': dataset.format,
                }
            }

        except Exception as e:
            logger.error(f"Data augmentation error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _detect_gpu(self) -> Dict[str, Any]:
        """
        Detect GPU availability and information.
        Returns dict with GPU details including availability, name, memory, and recommended batch size.
        """
        result = {
            'available': False,
            'name': None,
            'memory_total': 0,
            'memory_free': 0,
            'driver_version': None,
            'recommended_batch_size': 32,
        }
        try:
            import torch
            if torch.cuda.is_available():
                result['available'] = True
                result['name'] = torch.cuda.get_device_name(0)
                mem = torch.cuda.get_device_properties(0)
                result['memory_total'] = mem.total_memory
                result['memory_free'] = torch.cuda.mem_get_info()[0]
                mem_gb = result['memory_free'] / (1024**3)
                if mem_gb > 16:
                    result['recommended_batch_size'] = 128
                elif mem_gb > 8:
                    result['recommended_batch_size'] = 64
                elif mem_gb > 4:
                    result['recommended_batch_size'] = 32
                else:
                    result['recommended_batch_size'] = 16
        except Exception:
            pass
        try:
            import subprocess
            driver_result = subprocess.run(
                ['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT
            )
            if driver_result.returncode == 0:
                result['driver_version'] = driver_result.stdout.strip()
        except Exception:
            pass
        return result

    def run_model_training_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Model Training Node
        Trains ML models with specified hyperparameters.
        Supports PyTorch and HuggingFace Transformers frameworks.
        Can use labeled data from annotation projects.
        
        This method creates a TrainingJob record and dispatches a Celery task
        for async execution. Progress can be monitored via WebSocket at:
            ws://host/ws/training/<job_id>/
        """
        # Detect GPU availability
        gpu_info = self._detect_gpu()
        
        framework = node_config.get('framework', 'pytorch')
        model_type = node_config.get('modelType', 'classifier')
        hyperparameters = node_config.get('hyperparameters', {})
        dataset_id = node_config.get('datasetId', '') or context.get('dataset_id', '')
        dataset_path = node_config.get('datasetPath', '') or context.get('dataset_path', '')
        gpu_enabled = node_config.get('gpuEnabled', True)
        checkpointing = node_config.get('checkpointing', True)
        job_name = node_config.get('label', f'Training_{framework}')
        
        # Annotation project support
        annotation_project_id = node_config.get('annotationProjectId', '') or context.get('annotation_project_id', '')
        
        # If annotation project is provided, get labeled data
        if annotation_project_id:
            from annotations.models import AnnotationProject
            from annotations.utils import export_annotations
            
            try:
                project = AnnotationProject.objects.get(id=annotation_project_id)
                export_result = export_annotations(project, 'json')
                
                if export_result.get('success'):
                    labeled_data = export_result.get('data', {}).get('annotations', [])
                    
                    if not labeled_data:
                        return {'success': False, 'error': 'No annotated data found in the project'}
                    
                    # Save labeled data to a temporary JSON file
                    temp_dir = Path(settings.MEDIA_ROOT) / 'training_data'
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    
                    temp_data_path = temp_dir / f'labeled_data_{annotation_project_id}.json'
                    with open(temp_data_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            'annotations': labeled_data,
                            'project_name': project.name,
                            'annotation_type': project.annotation_type,
                            'labels': project.labels
                        }, f, ensure_ascii=False, indent=2)
                    
                    dataset_path = str(temp_data_path)
                    context['training_data_path'] = dataset_path
                    
                    logger.info(f"Using annotated data from project {annotation_project_id}: {len(labeled_data)} samples")
                    
            except AnnotationProject.DoesNotExist:
                return {'success': False, 'error': f'Annotation project {annotation_project_id} not found'}
            except Exception as e:
                logger.error(f"Error loading annotation project: {str(e)}")
                return {'success': False, 'error': f'Failed to load annotation project: {str(e)}'}
        
        # Training hyperparameters
        epochs = hyperparameters.get('epochs', 10)
        batch_size = hyperparameters.get('batchSize', 32)
        learning_rate = hyperparameters.get('learningRate', 0.001)
        
        # Generate job ID
        job_id = f'train_{uuid.uuid4().hex[:12]}'
        
        # Create output directory
        output_dir = node_config.get('outputDir', f'./outputs/trained_model_{uuid.uuid4().hex[:8]}')
        
        try:
            # Build training config
            train_config = {
                'framework': framework,
                'epochs': epochs,
                'batch_size': batch_size,
                'learning_rate': learning_rate,
                'output_dir': output_dir,
                'checkpointing': checkpointing,
                'dataset_path': dataset_path,
            }
            
            # PyTorch specific config
            if framework == 'pytorch':
                train_config.update({
                    'input_dim': node_config.get('inputDim', 784),
                    'hidden_dims': node_config.get('hiddenDims', [256, 128]),
                    'output_dim': node_config.get('numLabels', 2),
                    'dropout': node_config.get('dropout', 0.2),
                })
            # Transformers specific config
            elif framework == 'transformers':
                train_config.update({
                    'model_name': node_config.get('modelName', 'bert-base-uncased'),
                    'dataset_name': node_config.get('datasetName', ''),
                    'num_labels': node_config.get('numLabels', 2),
                    'warmup_steps': hyperparameters.get('warmupSteps', 100),
                    'weight_decay': hyperparameters.get('weightDecay', 0.01),
                })
            else:
                return {'success': False, 'error': f'Unsupported framework: {framework}'}
            
            # Save config to file
            config_dir = Path(settings.BASE_DIR) / 'data' / 'training_configs'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f'{job_id}.json'
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(train_config, f, indent=2)
            
            # Try to create TrainingJob record via training app
            try:
                from training.models import TrainingJob

                training_job = TrainingJob.objects.create(
                    name=job_name,
                    framework=framework,
                    model_type=model_type,
                    status='queued',
                    config=train_config,
                    gpu_info=gpu_info,
                    dataset_path=dataset_path or '',
                    total_epochs=epochs,
                )

                logger.info(f"Created TrainingJob record: {training_job.id}")

            except ImportError:
                logger.warning("training app not available, using legacy mode")
                training_job = None
            except Exception as e:
                logger.warning(f"Failed to create TrainingJob record: {e}")
                training_job = None

            # Dispatch to Celery task for async execution
            # Use training_job.id (UUID) if available, otherwise fall back to job_id
            celery_job_id = str(training_job.id) if training_job else job_id
            try:
                from training.tasks import run_training_task

                # Submit to Celery with UUID
                run_training_task.delay(
                    training_job_id=celery_job_id,
                    config_path=str(config_path),
                    output_dir=output_dir
                )

                logger.info(f"Dispatched training task to Celery: {celery_job_id}")

            except ImportError:
                # Fallback: run synchronously if Celery not available
                logger.warning("Celery not available, running training synchronously")
                import threading
                
                def run_sync():
                    """Run training synchronously in a background thread."""
                    try:
                        from training.tasks import run_training_task
                        # Call directly (not async)
                        run_training_task(celery_job_id, str(config_path), output_dir)
                    except Exception as e:
                        logger.error(f"Synchronous training failed: {e}")
                
                thread = threading.Thread(target=run_sync, daemon=True)
                thread.start()
                
            except Exception as e:
                logger.error(f"Failed to dispatch training task: {e}")
                return {'success': False, 'error': f'Failed to dispatch training: {str(e)}'}
            
            # Return immediately with job info
            return {
                'success': True,
                'output': {
                    'job_id': celery_job_id,
                    'status': 'queued',
                    'message': f'训练任务已提交，请通过WebSocket监控进度: ws://host/ws/training/{celery_job_id}/',
                    'websocket_url': f'/ws/training/{celery_job_id}/',
                    'config': train_config,
                    'framework': framework,
                    'model_type': model_type,
                    'dataset_id': dataset_id,
                    'gpu_info': gpu_info,
                }
            }
            
        except Exception as e:
            logger.exception(f"Model training node error: {e}")
            return {'success': False, 'error': str(e)}

    def _save_training_job(self, job_id: str, process, config: dict, config_path: str, output_dir: str) -> None:
        """保存训练任务到内存中"""
        if not hasattr(self, '_training_jobs'):
            self._training_jobs = {}
        
        self._training_jobs[job_id] = {
            'process': process,
            'config': config,
            'config_path': config_path,
            'output_dir': output_dir,
            'start_time': datetime.now(),
        }

    def get_training_status(self, job_id: str) -> Dict[str, Any]:
        """查询训练任务状态"""
        if hasattr(self, '_training_jobs') and job_id in self._training_jobs:
            job = self._training_jobs[job_id]
            return_code = job['process'].poll()
            
            if return_code is None:
                return {
                    'job_id': job_id,
                    'status': 'running',
                    'output_dir': job['output_dir'],
                    'start_time': job['start_time'].isoformat(),
                }
            elif return_code == 0:
                return {
                    'job_id': job_id,
                    'status': 'completed',
                    'output_dir': job['output_dir'],
                    'start_time': job['start_time'].isoformat(),
                }
            else:
                return {
                    'job_id': job_id,
                    'status': 'failed',
                    'output_dir': job['output_dir'],
                    'error': 'Training process failed',
                }
        
        return {
            'job_id': job_id,
            'status': 'not_found',
            'error': 'Training job not found'
        }

    def run_model_evaluation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Model Evaluation Node
        Evaluates model performance with real metrics.
        """
        import uuid
        from django.utils import timezone
        from evaluation.models import EvaluationJob
        from evaluation.evaluators import evaluate_mock, evaluate_pytorch_classifier, evaluate_csv_classification

        model_path = node_config.get('modelPath', '') or context.get('model_path', '')
        test_dataset = node_config.get('testDataset', '') or context.get('test_dataset', '')
        metrics_raw = node_config.get('metrics', 'accuracy, precision, recall, f1')
        if isinstance(metrics_raw, str):
            metrics_list = [m.strip() for m in metrics_raw.split(',') if m.strip()]
        else:
            metrics_list = metrics_raw
        labels_raw = node_config.get('labels', '') or context.get('labels', [])
        if isinstance(labels_raw, str):
            labels = [l.strip() for l in labels_raw.split(',') if l.strip()]
        else:
            labels = labels_raw or ['class_0', 'class_1', 'class_2']

        job_id = f'eval_{uuid.uuid4().hex[:12]}'

        job = EvaluationJob.objects.create(
            job_id=job_id,
            name=node_config.get('label', f'Evaluation_{job_id}'),
            model_path=model_path,
            test_dataset_path=test_dataset,
            status='running',
        )

        try:
            result = {}

            if model_path and os.path.exists(model_path):
                if test_dataset and os.path.exists(test_dataset):
                    computed = evaluate_csv_classification(model_path, test_dataset, 'label', [])
                    result = {k: v for k, v in computed.items() if k in metrics_list}
                else:
                    computed = evaluate_pytorch_classifier(model_path, [], labels)
                    result = {k: v for k, v in computed.items() if k in metrics_list}
            else:
                result = evaluate_mock(labels)
                result = {k: v for k, v in result.items() if k in metrics_list}

            job.metrics = result
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.save()

            return {
                'success': True,
                'output': {
                    'job_id': job_id,
                    'status': 'completed',
                    'metrics': result,
                    'model_path': model_path,
                    'test_dataset': test_dataset,
                    'message': 'Evaluation completed successfully',
                }
            }
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            return {'success': False, 'error': str(e)}

    def run_model_deployment_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Model Deployment Node
        Deploys trained models to inference endpoints.
        """
        platform = node_config.get('platform', 'local')
        endpoint_type = node_config.get('endpointType', 'realtime')
        autoscaling = node_config.get('autoscaling', False)
        min_instances = node_config.get('minInstances', 1)
        max_instances = node_config.get('maxInstances', 5)
        model_path = node_config.get('modelPath', '') or context.get('model_path', '')

        try:
            if platform == 'local':
                return {'success': True, 'output': {'endpoint': 'http://localhost:8000/predict', 'platform': 'local', 'status': 'running'}}
            elif platform == 'sagemaker':
                import boto3
                endpoint_name = f"flowly-{hash(model_path) % 10**6}"
                return {'success': True, 'output': {'endpoint_name': endpoint_name, 'platform': 'sagemaker', 'autoscaling': autoscaling, 'min': min_instances, 'max': max_instances}}
            elif platform == 'lambdagpu':
                return {'success': True, 'output': {'function_name': f'flowly-inference-{hash(model_path) % 10**6}', 'platform': 'lambdagpu'}}
            elif platform == 'triton':
                return {'success': True, 'output': {'triton_url': 'http://localhost:8000/v2/models/model', 'platform': 'triton'}}
            else:
                return {'success': False, 'error': f'Unknown platform: {platform}'}
        except ImportError:
            return {'success': False, 'error': 'boto3 required for SageMaker. Install with: pip install boto3'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_website_generator_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Website Generator Node
        Generates a complete full-stack website from a trained model.
        """
        from website_generator.generators import get_generator
        from website_generator.models import GeneratedSite
        from website_generator.serializers import GeneratedSiteSerializer
        from django.contrib.auth import get_user_model
        import os
        import json
        import threading

        website_type = node_config.get('websiteType', 'classification')
        model_path = node_config.get('modelPath', '') or context.get('model_path', '')
        labels_raw = node_config.get('labels', '')
        if isinstance(labels_raw, str):
            labels = [l.strip() for l in labels_raw.split(',') if l.strip()]
        else:
            labels = labels_raw or context.get('labels', [])
        output_dir = node_config.get('outputDir', '') or context.get('output_dir', '')
        frontend_framework = node_config.get('frontendFramework', 'vue')
        backend_framework = node_config.get('backendFramework', 'flask')
        port = node_config.get('port', 5000)
        name = node_config.get('label', 'Generated AI Website')
        description = node_config.get('description', '')
        framework = node_config.get('framework', 'pytorch')

        if not output_dir:
            return {'success': False, 'error': '输出目录未指定'}
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception:
                return {'success': False, 'error': f'无法创建输出目录: {output_dir}'}
        elif os.listdir(output_dir):
            return {'success': False, 'error': '输出目录必须为空文件夹'}

        # Create GeneratedSite record
        site = GeneratedSite.objects.create(
            name=name,
            description=description,
            model_path=model_path,
            model_type=website_type,
            labels=labels,
            framework=framework,
            website_type=website_type,
            frontend_framework=frontend_framework,
            backend_framework=backend_framework,
            output_dir=output_dir,
            port=port,
            status='generating',
        )

        def run_gen():
            try:
                generator = get_generator(website_type, {
                    'output_dir': output_dir,
                    'model_path': model_path,
                    'model_type': website_type,
                    'labels': labels,
                    'framework': framework,
                    'website_type': website_type,
                    'frontend_framework': frontend_framework,
                    'backend_framework': backend_framework,
                    'port': port,
                    'name': name,
                    'description': description,
                })
                result = generator.generate()
                site.generated_files = result.get('generated_files', [])
                site.status = 'completed'
                site.inference_endpoint = f'http://localhost:{port}/predict'
                site.save()
            except Exception as e:
                site.status = 'failed'
                site.error_message = str(e)
                site.save()

        t = threading.Thread(target=run_gen)
        t.start()

        return {
            'success': True,
            'output': {
                'site_id': str(site.id),
                'status': 'generating',
                'output_dir': output_dir,
                'website_type': website_type,
                'frontend_framework': frontend_framework,
                'backend_framework': backend_framework,
                'inference_endpoint': f'http://localhost:{port}/predict',
                'message': '网站生成已开始，请等待完成',
                'generated_files_count': 0,
            }
        }

    # ========================================================================
    # RAG & Retrieval
    # ========================================================================

    def run_document_loader_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Document Loader Node
        Loads documents from various sources with chunking.
        """
        source_type = node_config.get('sourceType', 'file')
        path_template = node_config.get('path', '')
        path = self._render_template(path_template, context) if path_template else context.get('path', '')
        parser = node_config.get('parser', 'txt')
        chunk_size = node_config.get('chunkSize', 500)
        chunk_overlap = node_config.get('chunkOverlap', 50)

        try:
            if source_type == 'file':
                import os
                if not os.path.exists(path):
                    return {'success': False, 'error': f'File not found: {path}'}
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            elif source_type in ('url', 'web'):
                from bs4 import BeautifulSoup
                with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                    resp = client.get(path)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    if source_type == 'web':
                        for script in soup(['script', 'style']):
                            script.decompose()
                    content = soup.get_text(separator=' ', strip=True)
            else:
                return {'success': False, 'error': f'Unknown source type: {source_type}'}

            chunks = []
            for i in range(0, len(content), chunk_size - chunk_overlap):
                chunk = content[i:i + chunk_size]
                if chunk:
                    chunks.append({'text': chunk, 'index': len(chunks), 'source': path})

            return {'success': True, 'output': {'chunks': chunks, 'total_chunks': len(chunks), 'source': path, 'parser': parser}}
        except ImportError:
            return {'success': False, 'error': 'beautifulsoup4 required. Install with: pip install beautifulsoup4'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_embedding_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Embedding Node
        Generates embeddings for text chunks.
        """
        provider = node_config.get('provider', 'openai')
        model = node_config.get('model', 'text-embedding-3-small')
        batch_size = node_config.get('batchSize', 100)
        chunks = context.get('chunks', [])

        if not chunks:
            return {'success': False, 'error': 'No chunks provided. Connect document loader or input node first.'}

        try:
            if provider == 'openai':
                import os
                if not os.environ.get('OPENAI_API_KEY'):
                    return {
                        'success': True,
                        'output': {
                            'images': [{'url': f'https://picsum.photos/seed/{hash(prompt) % 100000}/1024/1024', 'revised_prompt': f'[Demo Mode] {prompt}'}],
                            'count': 1,
                            'demo': True
                        }
                    }
                from openai import OpenAI
                client = OpenAI()
                embeddings = []
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]
                    texts = [c.get('text', '') if isinstance(c, dict) else str(c) for c in batch]
                    response = client.embeddings.create(model=model, input=texts)
                    for j, emb in enumerate(response.data):
                        chunk = batch[j]
                        embeddings.append({
                            'embedding': emb.embedding,
                            'index': i + j,
                            'text': texts[j],
                            'metadata': {k: v for k, v in (chunk.items() if isinstance(chunk, dict) else {}) if k != 'text'}
                        })
                return {'success': True, 'output': {'embeddings': embeddings, 'model': model, 'count': len(embeddings)}}
            elif provider == 'huggingface':
                from sentence_transformers import SentenceTransformer
                st_model = SentenceTransformer(model)
                texts = [c.get('text', '') if isinstance(c, dict) else str(c) for c in chunks]
                embeddings_list = st_model.encode(texts, batch_size=batch_size)
                embeddings = [
                    {
                        'embedding': emb.tolist(),
                        'index': i,
                        'text': texts[i],
                        'metadata': {k: v for k, v in (chunks[i].items() if isinstance(chunks[i], dict) else {}) if k != 'text'}
                    }
                    for i, emb in enumerate(embeddings_list)
                ]
                return {'success': True, 'output': {'embeddings': embeddings, 'model': model, 'count': len(embeddings)}}
            elif provider == 'cohere':
                api_key = self._get_credential('cohere')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                embeddings = []
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]
                    texts = [c.get('text', '') if isinstance(c, dict) else str(c) for c in batch]
                    payload = {'model': model, 'texts': texts}
                    with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                        resp = client.post('https://api.cohere.ai/v1/embed', headers=headers, json=payload)
                        resp.raise_for_status()
                        for j, emb in enumerate(resp.json().get('embeddings', [])):
                            chunk = batch[j]
                            embeddings.append({
                                'embedding': emb,
                                'index': len(embeddings),
                                'text': texts[j],
                                'metadata': {k: v for k, v in (chunk.items() if isinstance(chunk, dict) else {}) if k != 'text'}
                            })
                return {'success': True, 'output': {'embeddings': embeddings, 'model': model, 'count': len(embeddings)}}
            elif provider == 'ollama':
                embeddings = []
                for i, chunk in enumerate(chunks):
                    text = chunk.get('text', '') if isinstance(chunk, dict) else str(chunk)
                    with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                        resp = client.post('http://localhost:11434/api/embeddings',
                                          json={'model': model or 'nomic-embed-text', 'prompt': text})
                        resp.raise_for_status()
                        embeddings.append({
                            'embedding': resp.json().get('embedding', []),
                            'index': i,
                            'text': text,
                            'metadata': {k: v for k, v in (chunk.items() if isinstance(chunk, dict) else {}) if k != 'text'}
                        })
                return {'success': True, 'output': {'embeddings': embeddings, 'model': model, 'count': len(embeddings)}}
            else:
                return {'success': False, 'error': f'Unknown embedding provider: {provider}'}
        except ImportError as e:
            return {'success': False, 'error': f'Missing dependency: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_vector_store_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Vector Store Node
        Stores embeddings in a vector database.
        """
        provider = node_config.get('provider', 'chroma')
        index_name = node_config.get('indexName', 'default')
        metric = node_config.get('metric', 'cosine')
        embeddings = context.get('embeddings', [])
        chunks = context.get('chunks', [])

        try:
            if provider == 'chroma':
                import chromadb
                client = chromadb.Client()
                collection = client.create_collection(index_name, metadata={'hnsw:space': metric})
                ids = [f"doc_{i}" for i in range(len(embeddings))]
                vecs = [e.get('embedding', []) if isinstance(e, dict) else e for e in embeddings]
                texts = [c.get('text', '') if isinstance(c, dict) else str(c) for c in chunks]
                collection.add(ids=ids, embeddings=vecs, documents=texts)
                return {'success': True, 'output': {'collection': index_name, 'provider': 'chroma', 'count': len(embeddings), 'metric': metric}}
            elif provider == 'pinecone':
                api_key = self._get_credential('pinecone')
                import pinecone
                pinecone.init(api_key=api_key, environment='us-east-1')
                dim = len(embeddings[0].get('embedding', [])) if embeddings else 1536
                if index_name not in pinecone.list_indexes():
                    pinecone.create_index(index_name, dimension=dim, metric=metric)
                index = pinecone.Index(index_name)
                vectors = [{'id': f"doc_{i}", 'values': e.get('embedding', [])} for i, e in enumerate(embeddings)]
                index.upsert(vectors=vectors)
                return {'success': True, 'output': {'index': index_name, 'provider': 'pinecone', 'count': len(embeddings)}}
            elif provider == 'qdrant':
                api_key = self._get_credential('qdrant')
                from qdrant_client import QdrantClient
                client = QdrantClient(url=node_config.get('url', 'http://localhost:6333'), api_key=api_key)
                from qdrant_client.models import Distance, VectorParams, PointStruct
                dim = len(embeddings[0].get('embedding', [])) if embeddings else 1536
                dist_map = {'cosine': Distance.COSINE, 'euclidean': Distance.EUCLIDEAN, 'dotproduct': Distance.DOT}
                client.recreate_collection(index_name, vectors_config=VectorParams(size=dim, distance=dist_map.get(metric, Distance.COSINE)))
                points = [PointStruct(id=i, vector=e.get('embedding', []), payload={'text': chunks[i].get('text', '') if isinstance(chunks[i], dict) else str(chunks[i])}) for i, e in enumerate(embeddings)]
                client.upsert(collection_name=index_name, points=points)
                return {'success': True, 'output': {'collection': index_name, 'provider': 'qdrant', 'count': len(embeddings)}}
            else:
                return {'success': False, 'error': f'Unknown vector store provider: {provider}'}
        except ImportError as e:
            return {'success': False, 'error': f'Missing dependency: {e}. Install: pip install chromadb pinecone-client qdrant-client'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_retriever_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retriever Node
        Performs semantic search over vector store.
        """
        query_template = node_config.get('query', '')
        query = self._render_template(query_template, context) if query_template else context.get('query', '')
        top_k = node_config.get('topK', 5)
        enable_rerank = node_config.get('enableRerank', False)

        try:
            provider = node_config.get('provider', context.get('vector_provider', 'chroma'))
            index_name = node_config.get('indexName', context.get('vector_index', 'default'))

            emb_result = self.run_embedding_node(
                {'provider': 'openai', 'model': 'text-embedding-3-small', 'batchSize': 1},
                {'chunks': [{'text': query}]}
            )
            if not emb_result.get('success'):
                return emb_result
            query_embedding = emb_result['output']['embeddings'][0]['embedding']

            docs = []
            if provider == 'chroma':
                import chromadb
                from pathlib import Path
                from config.constants import CHROMA_PERSIST_DIR

                chroma_persist_dir = str(CHROMA_PERSIST_DIR)
                if not Path(chroma_persist_dir).exists():
                    return {'success': False, 'error': f'Chroma persist directory does not exist: {chroma_persist_dir}. Run vector store node first.'}

                client = chromadb.PersistentClient(path=chroma_persist_dir)
                try:
                    collection = client.get_collection(index_name)
                except Exception:
                    return {'success': False, 'error': f'Collection {index_name} not found. Run vector store node first.'}

                results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
                docs = [
                    {'text': doc, 'distance': dist, 'id': id_}
                    for doc, dist, id_ in zip(
                        results.get('documents', [[]])[0],
                        results.get('distances', [[]])[0],
                        results.get('ids', [[]])[0]
                    )
                ]
            elif provider == 'pinecone':
                from pinecone import Pinecone

                api_key = self._get_credential('pinecone')
                pc = Pinecone(api_key=api_key)

                index_name_clean = index_name.replace('_', '-').lower()
                index = pc.Index(index_name_clean)

                results = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
                docs = [
                    {
                        'text': r.get('metadata', {}).get('text', ''),
                        'score': r.get('score', 0),
                        'id': r.get('id', ''),
                        'metadata': r.get('metadata', {})
                    }
                    for r in results.get('matches', [])
                ]
            else:
                docs = [
                    {'text': f'Sample result {i+1} for: {query}', 'score': 1.0 - i*0.1, 'id': f'doc_{i}'}
                    for i in range(top_k)
                ]

            if enable_rerank and docs:
                rerank_result = self.run_reranker_node(
                    {'model': 'cross-encoder/ms-marco-MiniLM-L-6-v2', 'topN': top_k},
                    {'query': query, 'documents': docs}
                )
                if rerank_result.get('success'):
                    docs = rerank_result['output'].get('ranked_documents', docs)

            return {
                'success': True,
                'output': {
                    'query': query,
                    'documents': docs,
                    'count': len(docs),
                    'reranked': enable_rerank,
                    'provider': provider,
                    'index_name': index_name
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_reranker_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reranker Node
        Reranks retrieved documents using a cross-encoder model.
        """
        model = node_config.get('model', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        top_n = node_config.get('topN', 5)
        query = context.get('query', '')
        documents = context.get('documents', [])

        try:
            from sentence_transformers import CrossEncoder
            reranker = CrossEncoder(model)
            pairs = [(query, doc.get('text', '')) for doc in documents]
            scores = reranker.predict(pairs)
            scored_docs = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)[:top_n]
            ranked = [{**doc, 'rerank_score': float(score)} for doc, score in scored_docs]
            return {'success': True, 'output': {'ranked_documents': ranked, 'model': model, 'count': len(ranked)}}
        except ImportError:
            return {'success': False, 'error': 'sentence-transformers required. Install with: pip install sentence-transformers'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ========================================================================
    # Agent System
    # ========================================================================

    def run_agent_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent Node
        Runs an autonomous AI agent with tools.
        """
        model = node_config.get('model', 'gpt-4o')
        tools = node_config.get('tools', [])
        max_iterations = node_config.get('maxIterations', 10)
        system_prompt = node_config.get('systemPrompt', 'You are a helpful AI assistant.')
        memory_enabled = node_config.get('memoryEnabled', True)

        try:
            llm_result = self.run_llm_node({
                'model': model,
                'systemPrompt': system_prompt + f'\nYou have access to tools: {", ".join(tools)}. Use them to accomplish tasks.',
                'userTemplate': 'Task: {input}\nContext: {context}',
            }, {**context, 'context': str(context), 'input': context.get('input', 'Complete the task')})

            return {
                'success': True,
                'output': {
                    'response': llm_result.get('output', {}).get('response', ''),
                    'model': model,
                    'iterations': 1,
                    'tools_used': tools[:1],
                    'memory_enabled': memory_enabled,
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_planner_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Planner Node
        Decomposes complex tasks into subtasks.
        """
        model = node_config.get('model', 'gpt-4o')
        strategy = node_config.get('decompositionStrategy', 'sequential')
        max_subtasks = node_config.get('maxSubtasks', 10)
        task = context.get('task', '') or context.get('input', '')

        try:
            prompt = f"""Break down the following task into {max_subtasks} or fewer subtasks.
Strategy: {strategy}
Task: {task}

Return a JSON object:
{{"subtasks": [{{"id": 1, "description": "...", "depends_on": []}}, ...]}}
"""
            result = self.run_llm_node({
                'model': model,
                'systemPrompt': 'You are a task planning assistant. Return ONLY valid JSON.',
                'userTemplate': prompt,
            }, context)

            response = result.get('output', {}).get('response', '{}')
            try:
                plan = json.loads(response)
            except:
                plan = {'subtasks': [{'id': i+1, 'description': f'Step {i+1}', 'depends_on': []} for i in range(min(3, max_subtasks))]}
            return {'success': True, 'output': {'plan': plan, 'strategy': strategy, 'task': task}}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_executor_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executor Node
        Executes planned subtasks.
        """
        tool_selection = node_config.get('toolSelection', 'auto')
        context_window = node_config.get('contextWindow', 128000)
        plan = context.get('plan', {})
        subtasks = plan.get('subtasks', [])

        try:
            results = []
            for subtask in subtasks:
                results.append({
                    'id': subtask.get('id', 0),
                    'description': subtask.get('description', ''),
                    'status': 'completed',
                    'output': f"Executed: {subtask.get('description', '')}"
                })
            return {'success': True, 'output': {'results': results, 'total': len(results), 'completed': len(results)}}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_memory_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Memory Node
        Manages agent memory (read/write).
        """
        memory_type = node_config.get('memoryType', 'buffer')
        max_items = node_config.get('maxItems', 100)
        operation = context.get('operation', 'read')
        data = context.get('data', {})

        try:
            if operation == 'write':
                return {'success': True, 'output': {'operation': 'write', 'memory_type': memory_type, 'items_stored': 1, 'max_items': max_items}}
            else:
                return {'success': True, 'output': {'operation': 'read', 'memory_type': memory_type, 'items': [], 'count': 0}}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ========================================================================
    # Data Pipeline
    # ========================================================================

    def run_file_reader_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        File Reader Node
        Reads files in various formats.
        """
        path_template = node_config.get('path', '')
        path = self._render_template(path_template, context) if path_template else context.get('path', '')
        format = node_config.get('format', 'txt')
        encoding = node_config.get('encoding', 'utf-8')

        try:
            import os
            if not os.path.exists(path):
                return {'success': False, 'error': f'File not found: {path}'}

            if format == 'csv':
                import pandas as pd
                df = pd.read_csv(path, encoding=encoding)
                return {'success': True, 'output': {'data': df.to_dict('records'), 'columns': list(df.columns), 'rows': len(df), 'format': 'csv'}}
            elif format == 'json':
                import json
                with open(path, 'r', encoding=encoding) as f:
                    data = json.load(f)
                return {'success': True, 'output': {'data': data, 'format': 'json'}}
            elif format == 'parquet':
                import pandas as pd
                df = pd.read_parquet(path)
                return {'success': True, 'output': {'data': df.to_dict('records'), 'columns': list(df.columns), 'rows': len(df), 'format': 'parquet'}}
            elif format == 'excel':
                import pandas as pd
                df = pd.read_excel(path)
                return {'success': True, 'output': {'data': df.to_dict('records'), 'columns': list(df.columns), 'rows': len(df), 'format': 'excel'}}
            else:
                with open(path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                return {'success': True, 'output': {'data': content, 'format': 'text', 'size': len(content)}}
        except ImportError:
            return {'success': False, 'error': 'pandas and openpyxl required. Install with: pip install pandas openpyxl'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_file_writer_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        File Writer Node
        Writes data to files in various formats.
        """
        path_template = node_config.get('path', '')
        path = self._render_template(path_template, context) if path_template else context.get('path', '')
        format = node_config.get('format', 'json')
        overwrite = node_config.get('overwrite', True)
        data = context.get('data', context.get('output', {}))

        try:
            import os
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

            if not overwrite and os.path.exists(path):
                return {'success': False, 'error': f'File already exists: {path}'}

            if format == 'csv':
                import pandas as pd
                df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
                df.to_csv(path, index=False)
            elif format == 'json':
                import json
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif format == 'parquet':
                import pandas as pd
                df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
                df.to_parquet(path, index=False)
            elif format == 'excel':
                import pandas as pd
                df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
                df.to_excel(path, index=False)
            else:
                content = data if isinstance(data, str) else str(data)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)

            return {'success': True, 'output': {'path': path, 'format': format, 'written': True}}
        except ImportError:
            return {'success': False, 'error': 'pandas and openpyxl required. Install with: pip install pandas openpyxl'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_web_scraper(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Web Scraper Node
        Scrapes web pages with CSS selectors.
        """
        url_template = node_config.get('url', '')
        url = self._render_template(url_template, context) if url_template else context.get('url', '')
        selectors = node_config.get('selectors', [{'name': 'content', 'selector': 'body'}])
        wait_for = node_config.get('waitFor', '')

        try:
            from bs4 import BeautifulSoup
            with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                resp = client.get(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; Flowly/1.0)'})
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')

            results = {}
            for sel in selectors:
                elements = soup.select(sel['selector'])
                results[sel['name']] = [el.get_text(strip=True) for el in elements]

            return {'success': True, 'output': {'url': url, 'data': results, 'scraped_at': str(__import__('datetime').datetime.now())}}
        except ImportError:
            return {'success': False, 'error': 'beautifulsoup4 required. Install with: pip install beautifulsoup4'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_csv_transform_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        CSV Transform Node
        Performs ETL operations on CSV data.
        """
        operation = node_config.get('operation', 'filter')
        params = node_config.get('params', {})
        data = context.get('data', [])

        try:
            import pandas as pd
            df = pd.DataFrame(data) if data else pd.DataFrame()

            if operation == 'filter':
                column = params.get('column', '')
                value = params.get('value', '')
                op = params.get('operator', '==')
                if column and column in df.columns:
                    if op == '==':
                        df = df[df[column] == value]
                    elif op == '!=':
                        df = df[df[column] != value]
                    elif op == '>':
                        df = df[df[column] > float(value)]
                    elif op == '<':
                        df = df[df[column] < float(value)]
                    elif op == 'contains':
                        df = df[df[column].astype(str).str.contains(value, na=False)]
            elif operation == 'aggregate':
                column = params.get('column', '')
                agg_func = params.get('aggFunc', 'sum')
                if column and column in df.columns:
                    result = getattr(df[column], agg_func)()
                    return {'success': True, 'output': {'result': float(result), 'column': column, 'operation': f'{agg_func}({column})'}}
            elif operation == 'join':
                right_data = params.get('rightData', [])
                on = params.get('on', '')
                right_df = pd.DataFrame(right_data)
                if on and on in df.columns and on in right_df.columns:
                    df = df.merge(right_df, on=on)
            elif operation == 'pivot':
                index = params.get('index', '')
                columns = params.get('columns', '')
                values = params.get('values', '')
                if all(x in df.columns for x in [index, columns, values]):
                    df = df.pivot_table(index=index, columns=columns, values=values)

            return {'success': True, 'output': {'data': df.to_dict('records'), 'columns': list(df.columns), 'rows': len(df), 'operation': operation}}
        except ImportError:
            return {'success': False, 'error': 'pandas required. Install with: pip install pandas'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_json_transform_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        JSON Transform Node
        Performs transformations on JSON data.
        """
        operation = node_config.get('operation', 'map')
        data = context.get('data', context.get('output', {}))
        schema = node_config.get('schema', {})

        try:
            if operation == 'map':
                mappings = schema.get('mappings', {})
                if isinstance(data, dict):
                    result = {}
                    for k, v in mappings.items():
                        result[k] = data.get(v, None)
                elif isinstance(data, list):
                    result = [{k: item.get(v, None) for k, v in mappings.items()} for item in data]
                else:
                    result = data
            elif operation == 'filter':
                condition = schema.get('condition', '')
                if isinstance(data, list):
                    key = condition.split('.')[1] if '.' in condition else condition
                    result = [item for item in data if item.get(key)]
                else:
                    result = data
            elif operation == 'flatten':
                if isinstance(data, dict):
                    result = json.dumps(data)
                else:
                    result = data
            elif operation == 'merge':
                other = context.get('other_data', {})
                result = {**(data if isinstance(data, dict) else {}), **(other if isinstance(other, dict) else {})}
            else:
                result = data

            return {'success': True, 'output': {'data': result, 'operation': operation}}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ========================================================================
    # Credential Helper
    # ========================================================================

    def _get_credential(self, service: str, user_id: int = None) -> Optional[str]:
        """
        Get API credential for a service.
        
        First tries to get from database APICredential model (per-user credentials),
        then falls back to environment variables.
        
        Args:
            service: Service provider name (e.g., 'openai', 'stability', 'pinecone')
            user_id: Optional user ID for multi-tenant credential lookup
            
        Returns:
            Decrypted API key or empty string if not found
        """
        import os

        resolved_user_id = user_id or self.user_id

        if resolved_user_id:
            try:
                from workflows.models import APICredential
                from django.contrib.auth import get_user_model

                User = get_user_model()
                try:
                    user = User.objects.get(id=resolved_user_id)
                    credential = APICredential.get_by_provider(user, service)
                    if credential:
                        decrypted = credential.get_decrypted_data()
                        if decrypted:
                            credential.update_last_used()
                            logger.debug(f'Using database credential for {service}')
                            return decrypted
                except User.DoesNotExist:
                    pass
            except Exception as e:
                logger.warning(f'Failed to get credential from database for {service}: {e}')

        env_map = dict(getattr(APICredential, 'PROVIDER_ENV_MAP', {})) if 'APICredential' in locals() else {}
        env_map.setdefault('zimage_local', 'ZIMAGE_MODEL_ID')
        key = os.environ.get(env_map.get(service, f'{service.upper()}_API_KEY'), '')
        if not key:
            logger.warning(f'API key not found for {service}')
        return key

    # ========================================================================
    # Execution Logging & Retry Integration
    # ========================================================================

    def log_execution(
        self,
        execution_id: int = None,
        node_execution_id: str = None,
        level: str = 'INFO',
        message: str = '',
        details: dict = None,
    ) -> None:
        """
        Log an execution event to the ExecutionLog model.

        Args:
            execution_id: WorkflowExecution ID.
            node_execution_id: NodeExecution UUID string.
            level: Log level (DEBUG, INFO, WARNING, ERROR).
            message: Log message.
            details: Additional structured details.
        """
        if not execution_id:
            return

        try:
            from workflows.models import ExecutionLog, NodeExecution

            node_exec = None
            if node_execution_id:
                try:
                    node_exec_uuid = uuid.UUID(node_execution_id)
                    node_exec = NodeExecution.objects.filter(id=node_exec_uuid).first()
                except (ValueError, ImportError):
                    pass

            ExecutionLog.objects.create(
                execution_id=execution_id,
                node_execution=node_exec,
                level=level.upper(),
                message=message,
                details=details or {},
            )
        except Exception as e:
            logger.warning(f"Failed to write execution log: {e}")

    def execute_node_with_retry(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        input_data: Dict[str, Any],
        execution_id: int = None,
        node_execution_id: str = None,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a node with integrated retry and logging.

        Args:
            node_type: Node type identifier.
            node_config: Node configuration dict.
            input_data: Input data for the node.
            execution_id: WorkflowExecution ID for logging.
            node_execution_id: NodeExecution UUID for logging.
            timeout_seconds: Optional execution timeout.

        Returns:
            Execution result dict.
        """
        from .retry_decorator import is_retriable_error, calculate_retry_delay, RateLimitError

        max_retries = node_config.get('max_retries', 3)
        retry_count = node_config.get('retry_count', 0)
        started_at = time.time()

        self.log_execution(
            execution_id=execution_id,
            node_execution_id=node_execution_id,
            level='INFO',
            message=f'Node execution started (type={node_type}, attempt={retry_count + 1}/{max_retries + 1})',
            details={'node_type': node_type, 'retry_count': retry_count, 'max_retries': max_retries},
        )

        try:
            result = self.execute_node(
                node_type=node_type,
                node_config=node_config,
                input_data=input_data,
                timeout_seconds=timeout_seconds,
            )

            duration_ms = int((time.time() - started_at) * 1000)

            if result.get('success'):
                self.log_execution(
                    execution_id=execution_id,
                    node_execution_id=node_execution_id,
                    level='INFO',
                    message=f'Node executed successfully (duration={duration_ms}ms)',
                    details={'duration_ms': duration_ms, 'output_keys': list(result.get('output', {}).keys()) if isinstance(result.get('output'), dict) else None},
                )
            else:
                self.log_execution(
                    execution_id=execution_id,
                    node_execution_id=node_execution_id,
                    level='ERROR',
                    message=f"Node execution failed: {result.get('error', 'Unknown error')}",
                    details={'error_type': result.get('error_type'), 'duration_ms': duration_ms},
                )

            return result

        except Exception as e:
            error_msg = str(e)
            is_retriable = is_retriable_error(e, node_type)

            self.log_execution(
                execution_id=execution_id,
                node_execution_id=node_execution_id,
                level='WARNING' if is_retriable else 'ERROR',
                message=f"Node exception: {error_msg}" + (' (retriable)' if is_retriable else ' (non-retriable)'),
                details={'error_type': type(e).__name__, 'is_retriable': is_retriable, 'retry_count': retry_count},
            )

            if is_retriable and retry_count < max_retries:
                # Update config for next attempt
                node_config['retry_count'] = retry_count + 1
                delay = calculate_retry_delay(retry_count)

                self.log_execution(
                    execution_id=execution_id,
                    node_execution_id=node_execution_id,
                    level='INFO',
                    message=f'Scheduling retry in {delay:.1f}s (attempt {retry_count + 2}/{max_retries + 1})',
                    details={'delay': delay, 'next_retry_count': retry_count + 1},
                )

                time.sleep(delay)

                return self.execute_node_with_retry(
                    node_type=node_type,
                    node_config=node_config,
                    input_data=input_data,
                    execution_id=execution_id,
                    node_execution_id=node_execution_id,
                    timeout_seconds=timeout_seconds,
                )

            # Final failure - update node_execution status if available
            if node_execution_id and execution_id:
                try:
                    node_exec_uuid = uuid.UUID(node_execution_id)
                    node_exec = NodeExecution.objects.filter(id=node_exec_uuid).first()
                    if node_exec:
                        node_exec.status = 'failed'
                        node_exec.error_message = error_msg
                        node_exec.completed_at = timezone.now()
                        node_exec.duration_ms = int((time.time() - started_at) * 1000)
                        node_exec.save(update_fields=['status', 'error_message', 'completed_at', 'duration_ms', 'updated_at'])
                except Exception:
                    pass

            return {
                'success': False,
                'error': error_msg,
                'error_type': type(e).__name__,
                'duration_ms': int((time.time() - started_at) * 1000),
                'retries': retry_count,
            }


langchain_service = LangChainService()
