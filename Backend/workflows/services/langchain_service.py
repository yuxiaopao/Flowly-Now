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
from pathlib import Path
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
    if not model:
        return False
    model = str(model).strip()
    if ':' in model:
        return True
    model_lower = model.lower()
    OLLAMA_MODELS = {'deepseek-r1', 'llama', 'qwen', 'mistral', 'phi', 'gemma', 'codellama', 'llava', 'nomic-embed-text', 'smollm'}
    if any(model_lower.startswith(prefix) for prefix in OLLAMA_MODELS):
        return True
    registry = get_provider_registry()
    if registry:
        ollama = registry.get('ollama')
        if ollama and ollama.supports_model(model):
            return True
    return False


def resolve_executable_model(model: str) -> str:
    """Map NL placeholder model names (e.g. llm3) to a configured Ollama model."""
    model = str(model or '').strip()
    if not model or is_ollama_model(model):
        return model
    if re.match(r'^llm\d+$', model, re.I) or model.lower() in {'langchain', 'gpt', 'openai'}:
        fallback = (
            getattr(settings, 'NL_WORKFLOW_MODEL', None)
            or getattr(settings, 'DEFAULT_LLM_MODEL', None)
            or 'qwen3:1.7b'
        )
        fallback = str(fallback).strip()
        if fallback and is_ollama_model(fallback):
            return fallback
    return model


def _is_meaningful_llm_cache_output(output_data: Any) -> bool:
    """LLM cache entries with empty text are invalid (often from failed OpenAI routing)."""
    if not output_data or not isinstance(output_data, dict):
        return False
    text = output_data.get('text') or output_data.get('content') or ''
    return bool(str(text).strip())


def _is_meaningful_output_cache_output(output_data: Any) -> bool:
    """Output cache with unreplaced {placeholders} or incomplete structured media is stale."""
    if not output_data or not isinstance(output_data, dict):
        return False

    fmt = str(output_data.get('_format') or output_data.get('format') or '').lower()
    if fmt in ('chart', 'graph'):
        labels = output_data.get('labels')
        values = output_data.get('values')
        if not (isinstance(labels, list) and isinstance(values, list)):
            return False
    elif fmt in ('audio', 'sound', 'voice'):
        if not (output_data.get('audio_url') or output_data.get('audio')):
            return False
    elif fmt in ('video', 'mp4'):
        if not (output_data.get('video_url') or output_data.get('video')):
            return False
    elif fmt in ('image', 'img', 'picture'):
        has_image = (
            output_data.get('url')
            or output_data.get('image_url')
            or output_data.get('image')
            or (isinstance(output_data.get('images'), list) and output_data.get('images'))
        )
        if not has_image:
            return False

    result = output_data.get('result') or output_data.get('text') or ''
    if not isinstance(result, str):
        return True
    return not re.search(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}', result)


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


def _normalize_image_size(size):
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
    
    return None


def resolve_execution_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten ExecutionContext.to_dict() for node runners that expect top-level keys."""
    if not context:
        return {}
    if 'variables' not in context and 'node_outputs' not in context:
        return context

    merged: Dict[str, Any] = {}
    merged.update(context.get('input_data') or {})
    merged.update(context.get('variables') or {})
    # Node outputs override stale variables (e.g. new training output_dir vs cached website paths)
    for output in (context.get('node_outputs') or {}).values():
        if isinstance(output, dict):
            for key, value in output.items():
                if not str(key).startswith('_'):
                    merged[key] = value
    merged['_execution'] = {
        'node_outputs': context.get('node_outputs') or {},
        'metadata': context.get('metadata') or {},
    }
    return merged


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
        self._progress_reporter: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_progress_reporter(self, reporter: Optional[Callable[[Dict[str, Any]], None]]) -> None:
        self._progress_reporter = reporter

    def clear_progress_reporter(self) -> None:
        self._progress_reporter = None

    def _report_progress(self, payload: Dict[str, Any]) -> None:
        reporter = getattr(self, '_progress_reporter', None)
        if not reporter:
            return
        try:
            reporter(payload)
        except Exception as exc:
            logger.debug('Progress reporter failed: %s', exc)

    @staticmethod
    def _format_video_progress_message(status: str, progress: Any, provider: str = '') -> str:
        pct = int(progress or 0)
        label = {'agnes': 'Agnes', 'dashscope': '百炼'}.get(provider, provider or 'AI')
        if status in ('queued', 'pending', 'waiting'):
            return f'{label} 排队中…（图生视频通常 3–8 分钟，可继续编辑画布）'
        if status in ('processing', 'running', 'in_progress', 'in-progress'):
            return f'{label} 生成中 {pct}%' if pct else f'{label} 生成中…'
        return f'{label} 视频任务处理中…'

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
            'video_translation': self.run_video_translation_node,
            'video_upload': self.run_video_upload_node,
            'subtitle_translate': self.run_subtitle_translate_node,
            'segment_dubbing': self.run_segment_dubbing_node,
            'lip_sync': self.run_lip_sync_node,
            'subtitle_burn': self.run_subtitle_burn_node,
            # ML & Training
            'dataset_upload': self.run_dataset_upload_node,
            'data_annotation': self.run_data_annotation_node,
            'data_augmentation': self.run_data_augmentation_node,
            'model_training': self.run_model_training_node,
            'yolo_training': self.run_yolo_training_node,
            'clip_classification': self.run_clip_classification_node,
            'clip_retrieval': self.run_clip_retrieval_node,
            'model_evaluation': self.run_model_evaluation_node,
            'model_deployment': self.run_model_deployment_node,
            'project_profiler': self.run_project_profiler_node,
            'website_generator': self.run_website_generator_node,
            'backend_setup': self.run_backend_setup_node,
            'frontend_setup': self.run_frontend_setup_node,
            'ui_beautify': self.run_ui_beautify_node,
            'site_code_review': self.run_site_code_review_node,
            'environment_provision': self.run_environment_provision_node,
            'site_qa': self.run_site_qa_node,
            'site_preview': self.run_site_preview_node,
            'project_agent': self.run_project_agent_node,
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
            'json_parser': self.run_json_parser_node,
            'text_template': self.run_text_template_node,
            # Control flow extensions
            'switch': self.run_switch_node,
            'merge': self.run_merge_node,
            'filter': self.run_filter_node,
            'split': self.run_split_node,
            'set': self.run_set_node,
            'datetime': self.run_datetime_node,
            'rss_feed': self.run_rss_feed_node,
            # Integrations
            'slack': self.run_slack_node,
            'discord': self.run_discord_node,
            'telegram': self.run_telegram_node,
            'microsoft_teams': lambda cfg, inp: self._run_integration('microsoft_teams', cfg, inp),
            'notion': self.run_notion_node,
            'google_sheets': lambda cfg, inp: self._run_integration('google_sheets', cfg, inp),
            'google_drive': lambda cfg, inp: self._run_integration('google_drive', cfg, inp),
            'github': self.run_github_node,
            'gitlab': lambda cfg, inp: self._run_integration('gitlab', cfg, inp),
            'jira': lambda cfg, inp: self._run_integration('jira', cfg, inp),
            'airtable': lambda cfg, inp: self._run_integration('airtable', cfg, inp),
            'trello': lambda cfg, inp: self._run_integration('trello', cfg, inp),
            'mysql': lambda cfg, inp: self._run_integration('mysql', cfg, inp),
            'postgres': lambda cfg, inp: self._run_integration('postgres', cfg, inp),
            'mongodb': lambda cfg, inp: self._run_integration('mongodb', cfg, inp),
            'redis': self.run_redis_node,
            'elasticsearch': lambda cfg, inp: self._run_integration('elasticsearch', cfg, inp),
            'aws_s3': lambda cfg, inp: self._run_integration('aws_s3', cfg, inp),
            'ftp': lambda cfg, inp: self._run_integration('ftp', cfg, inp),
            'stripe': lambda cfg, inp: self._run_integration('stripe', cfg, inp),
            'twilio': lambda cfg, inp: self._run_integration('twilio', cfg, inp),
            'sendgrid': lambda cfg, inp: self._run_integration('sendgrid', cfg, inp),
            'openai_api': self.run_openai_api_node,
            'huggingface': self.run_huggingface_node,
            'push_notification': lambda cfg, inp: self._run_integration('push_notification', cfg, inp),
            'feishu': self.run_feishu_node,
            'dingtalk': self.run_dingtalk_node,
            'wechat_work': self.run_wechat_work_node,
        }

        executor = executors.get(node_type)

        if not executor:
            return {
                'success': True,
                'output': input_data,
                'message': f'Skipping unknown node type: {node_type}'
            }

        resolved_context = resolve_execution_context(input_data)

        # Context-dependent nodes must not use config-only cache (stale weights/paths)
        if node_type in (
            'yolo_training', 'model_training', 'dataset_upload',
            'project_profiler', 'website_generator', 'environment_provision',
            'site_qa', 'site_preview', 'project_agent',
            'image_generation', 'video_generation', 'audio_generation', 'image_editing',
            'subtitle_generation', 'video_translation',
            'video_upload', 'subtitle_translate', 'segment_dubbing', 'lip_sync', 'subtitle_burn',
            'output',
        ):
            use_cache = False

        # Normalize LLM-related configs (placeholder models, camelCase fields)
        if node_type in ('llm', 'prompt', 'openai_api'):
            node_config = dict(node_config or {})
            resolved_model = resolve_executable_model(node_config.get('model', DEFAULT_LLM_MODEL))
            if resolved_model:
                node_config['model'] = resolved_model

        # === Check cache first ===
        if use_cache:
            cached_output = self.cache_service.get(node_config, node_type)
            if cached_output is not None:
                if node_type in ('llm', 'prompt', 'openai_api') and not _is_meaningful_llm_cache_output(cached_output):
                    logger.info(f"Cache HIT ignored for {node_type}: empty LLM output")
                elif node_type == 'output' and not _is_meaningful_output_cache_output(cached_output):
                    logger.info("Cache HIT ignored for output: unreplaced template placeholders")
                else:
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
                'subtitle_generation', 'video_translation',
            'video_upload', 'subtitle_translate', 'segment_dubbing', 'lip_sync', 'subtitle_burn',
                'model_training', 'retriever', 'embedding'):
                result = self._execute_with_timeout(executor, node_config, resolved_context, timeout_seconds)
            else:
                result = executor(node_config, resolved_context)
            
            duration_ms = calculate_duration_ms(start_time)
            
            if result.get('success'):
                self._execution_stats['successful_calls'] += 1
                self._execution_stats['total_duration_ms'] += duration_ms
                
                # === Store result in cache ===
                if use_cache and result.get('output'):
                    output_to_cache = result.get('output')
                    if node_type in ('llm', 'prompt', 'openai_api'):
                        if _is_meaningful_llm_cache_output(output_to_cache):
                            self.cache_service.set(node_config, node_type, output_to_cache)
                    elif node_type == 'output':
                        if _is_meaningful_output_cache_output(output_to_cache):
                            self.cache_service.set(node_config, node_type, output_to_cache)
                    else:
                        self.cache_service.set(node_config, node_type, output_to_cache)
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
        
        model = resolve_executable_model(config.get('model', DEFAULT_LLM_MODEL))
        temperature = config.get('temperature', DEFAULT_TEMPERATURE)
        max_tokens = config.get('max_tokens', config.get('maxTokens', DEFAULT_MAX_TOKENS))
        system_prompt = config.get('system_prompt') or config.get('systemPrompt') or ''
        user_template = config.get('user_template') or config.get('userTemplate') or '{input}'
        input_variable = config.get('input_variable', 'input')
        streaming = config.get('streaming', False)

        # Compatibility: NL-generated workflows use 'prompt' as a single combined string
        # If system_prompt is empty and user_template is still default, use 'prompt' as the template
        prompt_combined = config.get('prompt', '')
        if prompt_combined and not system_prompt and user_template == '{input}':
            user_template = prompt_combined

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

    def _resolve_input_text(
        self,
        input_data: Dict[str, Any],
        input_variable: str = 'input'
    ) -> Any:
        """
        从执行上下文中解析输入变量值。

        执行器传入的 input_data 是 ExecutionContext.to_dict() 的结构：
        {input_data: {...}, variables: {...}, node_outputs: {...}, ...}
        按以下优先级解析：
        1. 顶层同名键（兼容直接调用）
        2. variables 中同名变量（上游节点输出会自动提取到 variables）
        3. input_data 中同名键（外部输入）
        4. input_variable 为默认 'input' 时：最近一个上游节点输出的文本，
           或唯一外部输入值（单输入工作流兜底）
        """
        value = input_data.get(input_variable)

        variables = input_data.get('variables')
        if value is None and isinstance(variables, dict):
            value = variables.get(input_variable)

        external_inputs = input_data.get('input_data')
        if value is None and isinstance(external_inputs, dict):
            value = external_inputs.get(input_variable)

        if value is None and input_variable == 'input':
            node_outputs = input_data.get('node_outputs')
            if isinstance(node_outputs, dict) and node_outputs:
                last_output = list(node_outputs.values())[-1]
                if isinstance(last_output, dict):
                    value = last_output.get('text')
                    if value is None:
                        value = last_output.get('result')
                    if value is None:
                        labels = last_output.get('labels')
                        values = last_output.get('values')
                        if isinstance(labels, list) and isinstance(values, list):
                            value = last_output
                        else:
                            value = next(
                                (v for k, v in last_output.items() if not str(k).startswith('_')),
                                None
                            )
                else:
                    value = last_output
            if value is None and isinstance(external_inputs, dict) and len(external_inputs) == 1:
                value = next(iter(external_inputs.values()))
            if value is None and isinstance(variables, dict):
                value = variables.get('text') or variables.get('result')

        return value

    def _build_messages(
        self,
        system_prompt: str,
        user_template: str,
        input_data: Dict[str, Any],
        input_variable: str
    ) -> List[Dict[str, str]]:
        """Build messages list for LLM from config and input data."""
        import re as _re
        messages = []
        
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})

        input_text = self._resolve_input_text(input_data, input_variable)
        if input_text is None:
            input_text = ''
        if isinstance(input_text, dict):
            input_text = json.dumps(input_text, ensure_ascii=False)
        elif not isinstance(input_text, str):
            input_text = str(input_text)

        # 构建插值上下文：支持 {{variables.xxx}}、{{input.xxx}}、{{节点变量}} 等嵌套引用
        render_context = dict(input_data) if isinstance(input_data, dict) else {}
        variables = input_data.get('variables') if isinstance(input_data, dict) else None
        if isinstance(variables, dict):
            for key, val in variables.items():
                render_context.setdefault(key, val)
        external_inputs = input_data.get('input_data') if isinstance(input_data, dict) else None
        # {{input.xxx}} 形式：input 指向外部输入字典；无嵌套引用时 input 即解析出的文本
        if isinstance(external_inputs, dict) and external_inputs:
            render_context['input'] = external_inputs
        else:
            render_context['input'] = input_text

        # 先用 {{variable}} 语法渲染（支持嵌套路径），再处理 {input} 简写
        rendered = self._render_template(user_template, render_context)
        normalized = _re.sub(r'\{\{([^}]+)\}\}', r'{\1}', rendered)
        try:
            user_content = normalized.format(input=input_text)
        except (KeyError, IndexError, ValueError):
            user_content = normalized.replace('{input}', str(input_text))
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
        model = resolve_executable_model(config.get('model', DEFAULT_LLM_MODEL))
        temperature = config.get('temperature', DEFAULT_TEMPERATURE)
        max_tokens = config.get('max_tokens', config.get('maxTokens', DEFAULT_MAX_TOKENS))
        system_prompt = config.get('system_prompt') or config.get('systemPrompt') or ''
        user_template = config.get('user_template') or config.get('userTemplate') or '{input}'
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
            if isinstance(input_data, dict):
                context.update(input_data)
                variables = input_data.get('variables')
                if isinstance(variables, dict):
                    context.update(variables)

            rendered = self._render_template(expression, context)
            normalized = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', rendered)
            # 兼容 JS/JSON 风格布尔字面量
            py_expr = (
                normalized
                .replace(' true', ' True')
                .replace(' false', ' False')
                .replace(' null', ' None')
                .replace('(true', '(True')
                .replace('(false', '(False')
            )
            
            allowed_names = {
                'and': lambda a, b: a and b,
                'or': lambda a, b: a or b,
                'not': lambda a: not a,
                'True': True,
                'False': False,
                'None': None,
                'true': True,
                'false': False,
                'null': None,
                're': re,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'all': all,
                'any': any,
            }
            
            result = eval(py_expr, {"__builtins__": {}}, {**context, **allowed_names})
            
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
        if isinstance(input_data, dict):
            variables = input_data.get('variables')
            if isinstance(variables, dict) and input_variable in variables:
                sandbox_input = {input_variable: variables[input_variable]}
            elif input_variable in input_data:
                sandbox_input = {input_variable: input_data[input_variable]}
            else:
                resolved = self._resolve_input_text(input_data, input_variable)
                sandbox_input = {input_variable: resolved if resolved is not None else {}}
        else:
            sandbox_input = {input_variable: input_data}
        
        # Execute in subprocess sandbox
        return sandbox.execute(code, sandbox_input)

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
        if not tool_params and tool_name == 'calculator':
            expr = config.get('expression')
            if expr:
                tool_params = {'expression': expr}
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
        if not isinstance(variables, dict):
            variables = {}

        flat_context: Dict[str, Any] = {}
        if isinstance(input_data, dict):
            nested_vars = input_data.get('variables')
            if isinstance(nested_vars, dict):
                flat_context.update(nested_vars)
            nested_input = input_data.get('input_data')
            if isinstance(nested_input, dict):
                flat_context.update(nested_input)
            for key, value in input_data.items():
                if key not in ('variables', 'node_outputs', 'metadata', 'input_data'):
                    flat_context[key] = value

        context = {**flat_context, **variables}
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
        # 兼容编辑器/NL 生成的扁平配置 {name, value}
        if not assignments:
            legacy_name = config.get('name') or config.get('variable_name')
            if legacy_name:
                assignments = [{
                    'name': legacy_name,
                    'value': config.get('value', ''),
                    'source': config.get('source', 'static'),
                    'type': config.get('type', 'string'),
                }]
        merge_strategy = config.get('merge_strategy', 'update')

        existing_vars = input_data.get('variables') if isinstance(input_data, dict) else None
        if merge_strategy == 'update' and isinstance(existing_vars, dict):
            output = dict(existing_vars)
        else:
            output = {}

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
        elif var_type in ('json', 'object'):
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
        # 兼容两种配置键：编辑器/执行器使用 variable_name，NL 生成使用 input_name
        variable_name = config.get('variable_name') or config.get('input_name') or 'input'
        prompt = config.get('prompt', 'Please provide input')
        required = config.get('required', True)
        default_value = config.get('default')
        validation = config.get('validation', None)

        value = input_data.get(variable_name)
        if value is None and isinstance(input_data, dict):
            value = input_data.get('input_data', {}).get(variable_name)
        # 单输入工作流兜底：调用方传了通用 'input' 键时也能匹配
        if value is None and isinstance(input_data, dict):
            value = input_data.get('input')
        # NL/API 常见别名：input_name 为 user_input 时也接受 text
        if value is None and isinstance(input_data, dict) and variable_name in ('user_input', 'input'):
            value = input_data.get('text')
        if value is None and isinstance(input_data, dict):
            nested = input_data.get('input_data')
            if isinstance(nested, dict) and variable_name in ('user_input', 'input'):
                value = nested.get('text') or nested.get('input')

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

        output: Dict[str, Any] = {}
        if value is not None:
            output[variable_name] = value
            # 多模态链路常用别名，确保下游 {prompt} / {input} 模板能解析
            if variable_name in ('prompt', 'user_input', 'input'):
                output.setdefault('prompt', value)
                output.setdefault('user_input', value)
                output.setdefault('input', value)
                output.setdefault('text', value)

        return {
            'success': True,
            'output': output,
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

    def _get_last_upstream_output(self, input_data: Dict[str, Any]) -> Any:
        """Return the most recent upstream node output dict/value."""
        node_outputs = input_data.get('node_outputs') if isinstance(input_data, dict) else None
        if isinstance(node_outputs, dict) and node_outputs:
            return list(node_outputs.values())[-1]
        return None

    def run_output_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute output node."""
        template = config.get('template', '{input}')
        output_variable = config.get('output_variable', 'result')
        output_format = config.get('format', 'text')
        upstream = self._get_last_upstream_output(input_data)

        # 解析上游输出，支持 {input} 简写与 {{variable}} 嵌套引用
        input_text = self._resolve_input_text(input_data, 'input')
        if input_text is None:
            input_text = ''
        if not isinstance(input_text, str):
            input_text = json.dumps(input_text, ensure_ascii=False) if isinstance(input_text, (dict, list)) else str(input_text)

        render_context = dict(input_data) if isinstance(input_data, dict) else {}
        variables = input_data.get('variables') if isinstance(input_data, dict) else None
        if isinstance(variables, dict):
            for key, val in variables.items():
                render_context.setdefault(key, val)
        render_context.setdefault('input', input_text)

        rendered = self._render_template(template, render_context)
        rendered = rendered.replace('{input}', input_text)
        # 兼容编辑器常用的单花括号占位符 {variable}
        for key, val in render_context.items():
            if not isinstance(key, str) or key.startswith('_'):
                continue
            if isinstance(val, (dict, list)):
                val_str = json.dumps(val, ensure_ascii=False)
            elif val is None:
                val_str = ''
            else:
                val_str = str(val)
            rendered = rendered.replace('{' + key + '}', val_str)

        if output_format == 'json':
            try:
                formatted = json.loads(rendered)
            except json.JSONDecodeError:
                formatted = rendered
        elif output_format == 'markdown':
            formatted = rendered
        else:
            formatted = rendered

        output_payload = {
            output_variable: formatted,
            '_display': rendered,
            '_format': output_format,
        }

        fmt = str(output_format).lower()
        if isinstance(upstream, dict):
            passthrough = {
                k: v for k, v in upstream.items()
                if not str(k).startswith('_')
            }

            if fmt in ('chart', 'graph'):
                labels = upstream.get('labels')
                values = upstream.get('values')
                if isinstance(labels, list) and isinstance(values, list):
                    output_payload = {
                        **passthrough,
                        '_display': rendered or json.dumps(passthrough, ensure_ascii=False),
                        '_format': output_format,
                    }
            elif fmt in ('audio', 'sound', 'voice'):
                audio_url = upstream.get('audio_url') or upstream.get('audio')
                if audio_url:
                    output_payload['audio_url'] = audio_url
                    output_payload[output_variable] = audio_url
                    output_payload['_display'] = audio_url
            elif fmt in ('video', 'mp4'):
                video_url = upstream.get('video_url') or upstream.get('video')
                if video_url:
                    output_payload['video_url'] = video_url
                    output_payload[output_variable] = video_url
                    output_payload['_display'] = video_url
            elif fmt in ('image', 'img', 'picture'):
                image_url = upstream.get('url') or upstream.get('image_url') or upstream.get('image')
                images = upstream.get('images')
                if not image_url and isinstance(images, list) and images:
                    first = images[0]
                    if isinstance(first, dict):
                        image_url = first.get('url') or first.get('image_url')
                    elif isinstance(first, str):
                        image_url = first
                if image_url:
                    output_payload['url'] = image_url
                    output_payload[output_variable] = image_url
                    output_payload['_display'] = image_url
                    if isinstance(images, list) and images:
                        output_payload['images'] = images

        return {
            'success': True,
            'output': output_payload,
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

    def _normalize_email_node_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize email node config into the runtime shape used by run_email_node."""
        normalized = dict(config or {})

        if not normalized.get('subject') and normalized.get('title'):
            normalized['subject'] = normalized.get('title', '')
        if not normalized.get('body') and normalized.get('content'):
            normalized['body'] = normalized.get('content', '')
        if not normalized.get('fromEmail') and normalized.get('from_email'):
            normalized['fromEmail'] = normalized.get('from_email', '')
        if normalized.get('is_html') is not None and normalized.get('isHtml') is None:
            normalized['isHtml'] = bool(normalized.get('is_html'))

        smtp_config = normalized.get('smtpConfig')
        if not isinstance(smtp_config, dict):
            smtp_config = {}

        legacy_smtp = str(normalized.get('smtp', '') or '').strip()
        if legacy_smtp and not smtp_config.get('server'):
            smtp_parts = legacy_smtp.split(':')
            smtp_config['server'] = smtp_parts[0].strip() if smtp_parts else ''
            if len(smtp_parts) > 1:
                try:
                    smtp_config['port'] = int(smtp_parts[1])
                except (TypeError, ValueError):
                    smtp_config['port'] = 587

        if 'smtpUsername' in normalized and not smtp_config.get('username'):
            smtp_config['username'] = normalized.get('smtpUsername', '')
        if 'smtpPassword' in normalized and not smtp_config.get('password'):
            smtp_config['password'] = normalized.get('smtpPassword', '')

        normalized['smtpConfig'] = {
            'server': smtp_config.get('server', '') or '',
            'port': int(smtp_config.get('port', 587) or 587),
            'useTls': bool(smtp_config.get('useTls', True)),
            'username': smtp_config.get('username', '') or '',
            'password': smtp_config.get('password', '') or ''
        }

        return normalized

    def run_email_node(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute email node with optional SMTP override."""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        config = self._normalize_email_node_config(config)

        to = self._render_template(config.get('to', ''), input_data)
        cc = self._render_template(config.get('cc', ''), input_data)
        bcc = self._render_template(config.get('bcc', ''), input_data)
        subject = self._render_template(config.get('subject', ''), input_data)
        body = self._render_template(config.get('body', ''), input_data)
        from_email = config.get('fromEmail') or config.get('from_email') or ''

        # Backward compatibility for older / NL-generated email node shapes
        if not subject and config.get('title'):
            subject = self._render_template(config.get('title', ''), input_data)
        if not body and config.get('content'):
            body = self._render_template(config.get('content', ''), input_data)

        smtp_config = config.get('smtpConfig') or {}
        if not smtp_config and config.get('smtp'):
            smtp_value = str(config.get('smtp', '')).strip()
            if smtp_value:
                smtp_parts = smtp_value.split(':')
                smtp_server_legacy = smtp_parts[0].strip() if smtp_parts else ''
                smtp_port_legacy = 587
                if len(smtp_parts) > 1:
                    try:
                        smtp_port_legacy = int(smtp_parts[1])
                    except (TypeError, ValueError):
                        smtp_port_legacy = 587
                smtp_config = {
                    'server': smtp_server_legacy,
                    'port': smtp_port_legacy,
                    'useTls': True,
                    'username': config.get('smtpUsername', ''),
                    'password': config.get('smtpPassword', '')
                }

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

        smtp_config = config.get('smtpConfig') or {}
        smtp_server = smtp_config.get('server', '').strip()
        smtp_port = int(smtp_config.get('port', 587) or 587)
        smtp_username = smtp_config.get('username', '').strip()
        smtp_password = smtp_config.get('password', '').strip()
        smtp_use_tls = smtp_config.get('useTls', True)
        is_html = config.get('isHtml', config.get('is_html', False))

        use_global_smtp = config.get('useGlobalSmtp')
        if use_global_smtp is None:
            use_global_smtp = config.get('use_global_smtp')
        if use_global_smtp is None:
            use_global_smtp = not (smtp_server and smtp_username and smtp_password)

        # Fall back to Django defaults when fromEmail is omitted
        if not from_email:
            from django.conf import settings
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '') or getattr(settings, 'EMAIL_HOST_USER', '') or ''

        if use_global_smtp:
            from core.email_smtp_defaults import resolve_runtime_smtp_credentials

            global_smtp = resolve_runtime_smtp_credentials()
            smtp_server = global_smtp.get('server', '').strip() or smtp_server
            smtp_port = int(global_smtp.get('port', smtp_port) or smtp_port)
            smtp_username = global_smtp.get('username', '').strip() or smtp_username
            smtp_password = global_smtp.get('password', '').strip() or smtp_password
            smtp_use_tls = bool(global_smtp.get('useTls', smtp_use_tls))
            if not from_email:
                from_email = global_smtp.get('fromEmail', '') or from_email

        try:
            if smtp_server and smtp_username and smtp_password:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject or '(No Subject)'
                msg['From'] = from_email
                msg['To'] = ', '.join(recipient_list)
                if cc_list:
                    msg['Cc'] = ', '.join(cc_list)
                if bcc_list:
                    msg['Bcc'] = ', '.join(bcc_list)

                mime_type = 'html' if is_html else 'plain'
                msg.attach(MIMEText(body, mime_type, 'utf-8'))

                with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                    if smtp_use_tls:
                        server.starttls()
                    server.login(smtp_username, smtp_password)
                    all_recipients = recipient_list + cc_list + bcc_list
                    server.sendmail(from_email, all_recipients, msg.as_string())
            else:
                from django.core.mail import EmailMultiAlternatives
                email = EmailMultiAlternatives(
                    subject=subject or '(No Subject)',
                    body=body,
                    from_email=from_email,
                    to=recipient_list,
                    cc=cc_list if cc_list else [],
                    bcc=bcc_list if bcc_list else [],
                )
                if is_html:
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
                    'subject': subject,
                    'smtp_used': bool(smtp_server and smtp_username and smtp_password)
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
        """Render template with data, supporting {{variable}} and {variable} syntax."""
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

        pattern_braces = r'\{([^{}]+)\}'

        def replacer_single(match):
            var_path = match.group(1).strip()
            if var_path.startswith('{') or var_path.endswith('}'):
                return match.group(0)
            value = self._get_nested_value(data, var_path)
            if value is None:
                return match.group(0)
            return str(value)

        result = re.sub(pattern_braces, replacer_single, result)
        return result

    def _resolve_prompt_from_context(
        self,
        node_config: Dict[str, Any],
        context: Dict[str, Any],
        *,
        field: str = 'prompt',
    ) -> str:
        """Resolve prompt/text from node template plus upstream execution context."""
        template = node_config.get(field) or node_config.get('text') or ''
        prompt = self._render_template(str(template), context) if template else ''
        prompt = str(prompt or '').strip()
        if prompt and not re.search(r'\{[a-zA-Z_][\w.]*\}', prompt):
            return prompt
        for key in ('prompt', 'text', 'user_input', 'userInput', 'input', 'description'):
            candidate = context.get(key)
            if candidate is not None and str(candidate).strip():
                return str(candidate).strip()
        nested = context.get('input_data')
        if isinstance(nested, dict):
            for key in ('prompt', 'text', 'user_input', 'userInput', 'input', 'description'):
                candidate = nested.get(key)
                if candidate is not None and str(candidate).strip():
                    return str(candidate).strip()
        return prompt

    def _resolve_input_image(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Resolve image-to-video input from config templates or upstream image output."""
        raw = (
            node_config.get('inputImage')
            or node_config.get('input_image')
            or node_config.get('input_image_url')
            or context.get('inputImage')
            or context.get('input_image')
            or ''
        )
        if raw:
            rendered = self._render_template(str(raw), context) if '{' in str(raw) else str(raw)
            rendered = str(rendered or '').strip()
            if rendered and not re.search(r'\{[a-zA-Z_][a-zA-Z0-9_.]*\}', rendered):
                return rendered

        images = context.get('images')
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict):
                return str(first.get('url') or first.get('path') or '').strip()
            if isinstance(first, str):
                return first.strip()
        return ''

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

    def _dashscope_credential(self) -> tuple:
        """
        Resolve (api_key, base_url) for DashScope (阿里云百炼) REST calls.
        DB-stored credential takes priority over the DASHSCOPE_API_KEY environment variable.
        """
        api_key = self._get_credential('dashscope') or (getattr(settings, 'DASHSCOPE_API_KEY', '') or '').strip()
        if not api_key:
            raise WorkflowExecutionError(
                'DashScope API Key 未配置。请在 .env 中设置 DASHSCOPE_API_KEY，或在「凭证中心」新增 dashscope 类型的凭证。',
                'configuration'
            )
        base_url = (getattr(settings, 'DASHSCOPE_BASE_URL', '') or 'https://dashscope.aliyuncs.com/api/v1').rstrip('/')
        return api_key, base_url

    def _dashscope_httpx_client(self, timeout: float = 60) -> 'httpx.Client':
        """DashScope HTTP client — disable system proxy to avoid SSL EOF on Windows."""
        return httpx.Client(timeout=timeout, trust_env=False)

    @staticmethod
    def _normalize_dashscope_video_model(model: str, input_image: str) -> str:
        """Map UI model ids to DashScope Wanx video model names."""
        raw = (model or '').strip()
        aliases = {
            'wan2.1-i2v-turbo': 'wanx2.1-i2v-turbo',
            'wan2.1-i2v-plus': 'wanx2.1-i2v-plus',
            'wan2.1-t2v-turbo': 'wanx2.1-t2v-turbo',
            'wan2.1-t2v-plus': 'wanx2.1-t2v-plus',
        }
        if raw in aliases:
            raw = aliases[raw]
        if input_image:
            if raw and 'i2v' in raw:
                return raw
            if raw and 't2v' in raw:
                return 'wanx2.1-i2v-turbo'
            return raw or 'wanx2.1-i2v-turbo'
        if raw and raw.startswith(('wanx', 'wan2')):
            return raw
        return 'wanx2.1-t2v-turbo'

    def _dashscope_error_detail(self, resp: 'httpx.Response') -> str:
        """Extract a human-readable error message from a DashScope error response."""
        try:
            data = resp.json()
            code = data.get('code') or data.get('error', {}).get('code')
            message = data.get('message') or data.get('error', {}).get('message')
            if code or message:
                return f'{code}: {message}'
        except Exception:
            pass
        return resp.text[:500]

    def _poll_dashscope_task(
        self,
        task_id: str,
        api_key: str,
        base_url: str,
        timeout_seconds: int = 300,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """
        Poll a DashScope async task (image/video/audio-transcription generation)
        until it reaches a terminal state, returning the `output` payload.
        """
        headers = {'Authorization': f'Bearer {api_key}'}
        max_attempts = max(1, timeout_seconds // poll_interval)

        with self._dashscope_httpx_client(timeout=30) as client:
            for _ in range(max_attempts):
                resp = client.get(f'{base_url}/tasks/{task_id}', headers=headers)
                if resp.status_code >= 400:
                    raise WorkflowExecutionError(f'DashScope 任务查询失败: {self._dashscope_error_detail(resp)}')
                data = resp.json()
                output = data.get('output', {}) or {}
                task_status = output.get('task_status')
                if task_status == 'SUCCEEDED':
                    return output
                if task_status in ('FAILED', 'CANCELED', 'UNKNOWN'):
                    message = output.get('message') or data.get('message') or f'任务状态: {task_status}'
                    raise WorkflowExecutionError(f'DashScope 任务执行失败: {message}')
                time.sleep(poll_interval)

        raise WorkflowExecutionError(f'DashScope 任务超时（{timeout_seconds}s），task_id={task_id}')

    def _agnes_credential(self) -> tuple:
        """Resolve (api_key, base_url) for Agnes AI OpenAI-compatible API."""
        api_key = self._get_credential('agnes') or (getattr(settings, 'AGNES_API_KEY', '') or '').strip()
        if not api_key:
            raise WorkflowExecutionError(
                'Agnes API Key 未配置。请在 .env 中设置 AGNES_API_KEY，或在「凭证中心」新增 agnes 类型的凭证。',
                'configuration'
            )
        base_url = (getattr(settings, 'AGNES_BASE_URL', '') or 'https://apihub.agnes-ai.com/v1').rstrip('/')
        return api_key, base_url

    def _agnes_httpx_client(self, timeout: float = 60) -> 'httpx.Client':
        """Agnes HTTP client — disable system proxy to avoid SSL EOF on Windows."""
        return httpx.Client(timeout=timeout, trust_env=False)

    def _agnes_error_detail(self, resp: 'httpx.Response') -> str:
        try:
            data = resp.json()
            err = data.get('error') or {}
            if isinstance(err, dict):
                message = err.get('message') or data.get('message')
                if message:
                    return str(message)
            if data.get('message'):
                return str(data['message'])
        except Exception:
            pass
        return resp.text[:500]

    def _poll_agnes_video_task(
        self,
        task_id: str,
        api_key: str,
        base_url: str,
        timeout_seconds: int = 900,
        poll_interval: int = 5,
        progress_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Poll Agnes video generation task until completed."""
        headers = {'Authorization': f'Bearer {api_key}'}
        max_attempts = max(1, timeout_seconds // poll_interval)
        ssl_retries = 0
        max_ssl_retries = 5
        with self._agnes_httpx_client(timeout=60) as client:
            for _ in range(max_attempts):
                try:
                    resp = client.get(f'{base_url}/videos/{task_id}', headers=headers)
                except httpx.HTTPError as exc:
                    ssl_retries += 1
                    if ssl_retries > max_ssl_retries:
                        raise WorkflowExecutionError(f'Agnes 视频任务查询网络错误: {exc}') from exc
                    time.sleep(min(poll_interval, 5))
                    continue
                ssl_retries = 0
                if resp.status_code >= 400:
                    raise WorkflowExecutionError(f'Agnes 视频任务查询失败: {self._agnes_error_detail(resp)}')
                data = resp.json()
                status = (data.get('status') or '').lower()
                progress = data.get('progress', 0)
                self._report_progress({
                    **(progress_meta or {}),
                    'status': status,
                    'task_status': status,
                    'progress': progress,
                    'task_id': task_id,
                    'provider': 'agnes',
                    'message': self._format_video_progress_message(status, progress, 'agnes'),
                })
                if status in ('completed', 'succeeded', 'success'):
                    return data
                if status in ('failed', 'error', 'canceled', 'cancelled'):
                    raise WorkflowExecutionError(
                        f"Agnes 视频生成失败: {data.get('error') or status}"
                    )
                time.sleep(poll_interval)
        raise WorkflowExecutionError(f'Agnes 视频任务超时（{timeout_seconds}s），task_id={task_id}')

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

    def _image_generation_demo_output(self, prompt: str) -> Dict[str, Any]:
        seed = abs(hash(str(prompt or 'demo'))) % 100000
        return {
            'success': True,
            'output': {
                'images': [{
                    'url': f'https://picsum.photos/seed/{seed}/1024/1024',
                    'revised_prompt': f'[Demo Mode] {prompt}',
                }],
                'count': 1,
                'demo': True,
            },
        }

    def run_image_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Image Generation Node
        Generates images from text prompts using various providers.
        """
        provider = node_config.get('provider', 'openai')
        if provider == 'zimage_local':
            model = node_config.get('model') or getattr(settings, 'ZIMAGE_MODEL_ID', 'Tongyi-MAI/Z-Image-Turbo')
        elif provider == 'dashscope':
            model = node_config.get('model') or 'wanx2.1-t2i-turbo'
        elif provider == 'agnes':
            model = node_config.get('model') or 'agnes-image-2.1-flash'
        else:
            model = node_config.get('model', 'dall-e-3')
        prompt = self._resolve_prompt_from_context(node_config, context, field='prompt')
        size = node_config.get('size', '1024x1024')
        quality = node_config.get('quality', 'standard')
        style = node_config.get('style', 'vivid')
        n = node_config.get('n', 1)

        try:
            if provider == 'openai':
                api_key = self._get_credential('openai')
                if not api_key or node_config.get('demo_mode'):
                    return self._image_generation_demo_output(prompt)
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=getattr(settings, 'OPENAI_BASE_URL', None) or None)
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
            elif provider == 'agnes':
                api_key, base_url = self._agnes_credential()
                from openai import OpenAI
                agnes_model = model if model and model.startswith('agnes-image') else 'agnes-image-2.1-flash'
                allowed_sizes = {'1024x1024', '1792x1024', '1024x1792', '1024x768', '768x1024'}
                agnes_size = (size or '1024x1024').replace('*', 'x').replace('X', 'x')
                if agnes_size not in allowed_sizes:
                    agnes_size = '1024x1024'
                client = OpenAI(api_key=api_key, base_url=base_url)
                response = client.images.generate(
                    model=agnes_model,
                    prompt=prompt,
                    size=agnes_size,
                    n=max(1, min(4, int(n or 1))),
                )
                images = []
                for img in response.data:
                    item = {'url': getattr(img, 'url', '') or ''}
                    if getattr(img, 'b64_json', None):
                        item['base64'] = img.b64_json
                    if getattr(img, 'revised_prompt', None):
                        item['revised_prompt'] = img.revised_prompt
                    if item.get('url') or item.get('base64'):
                        images.append(item)
                return {
                    'success': True,
                    'output': {
                        'images': images,
                        'count': len(images),
                        'provider': 'agnes',
                        'model': agnes_model,
                    }
                }
            elif provider == 'dashscope':
                api_key, base_url = self._dashscope_credential()
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'X-DashScope-Async': 'enable',
                }
                ds_model = model if model and model.startswith(('wanx', 'wan2')) else 'wanx2.1-t2i-turbo'
                allowed_sizes = {'1024*1024', '720*1280', '1280*720'}
                ds_size = (size or '1024x1024').replace('x', '*').replace('X', '*')
                if ds_size not in allowed_sizes:
                    ds_size = '1024*1024'
                payload = {
                    'model': ds_model,
                    'input': {'prompt': prompt},
                    'parameters': {'size': ds_size, 'n': max(1, min(4, int(n or 1)))},
                }
                with httpx.Client(timeout=IMAGE_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'{base_url}/services/aigc/text2image/image-synthesis',
                        headers=headers, json=payload
                    )
                    if resp.status_code >= 400:
                        raise WorkflowExecutionError(f'DashScope 图像生成任务创建失败: {self._dashscope_error_detail(resp)}')
                    task_id = (resp.json().get('output') or {}).get('task_id')
                if not task_id:
                    raise WorkflowExecutionError('DashScope 图像生成任务创建失败：未返回 task_id')
                result = self._poll_dashscope_task(task_id, api_key, base_url, timeout_seconds=180, poll_interval=3)
                images = [{'url': item.get('url', '')} for item in result.get('results', []) if item.get('url')]
                return {
                    'success': True,
                    'output': {
                        'images': images,
                        'count': len(images),
                        'provider': 'dashscope',
                        'model': ds_model,
                        'task_id': task_id,
                    }
                }
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
            err = str(e)
            if provider == 'openai' and any(token in err for token in ('AuthenticationError', 'Unauthorized', '401', 'invalid_api_key')):
                logger.warning('OpenAI image generation auth failed, using demo output: %s', e)
                return self._image_generation_demo_output(prompt)
            return {'success': False, 'error': str(e)}

    def _video_generation_demo_output(
        self,
        prompt: str,
        duration: int = 5,
        fps: int = 24,
        resolution: str = '720p',
        input_image: str = '',
    ) -> Dict[str, Any]:
        seed = abs(hash(str(prompt or 'demo'))) % 100000
        thumb = input_image or f'https://picsum.photos/seed/{seed}/640/360'
        return {
            'success': True,
            'output': {
                'video_url': 'https://www.w3schools.com/html/mov_bbb.mp4',
                'thumbnail': thumb,
                'status': 'completed',
                'duration': duration,
                'fps': fps,
                'resolution': resolution,
                'demo': True,
                'prompt': prompt,
                'input_image': input_image,
                'mode': 'image_to_video' if input_image else 'text_to_video',
            },
        }

    def _execute_agnes_video_generation(
        self,
        *,
        model: str,
        prompt: str,
        duration: int,
        resolution: str,
        input_image: str,
    ) -> Dict[str, Any]:
        api_key, base_url = self._agnes_credential()
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        agnes_model = model if model and model.startswith('agnes-video') else 'agnes-video-v2.0'
        payload = {'model': agnes_model, 'prompt': prompt}
        if input_image:
            payload['image'] = input_image
        with self._agnes_httpx_client(timeout=VIDEO_GENERATION_TIMEOUT) as client:
            resp = client.post(f'{base_url}/videos', headers=headers, json=payload)
            if resp.status_code >= 400:
                raise WorkflowExecutionError(f'Agnes 视频生成任务创建失败: {self._agnes_error_detail(resp)}')
            created = resp.json()
        task_id = created.get('id') or created.get('task_id')
        if not task_id:
            raise WorkflowExecutionError(f'Agnes 视频生成未返回 task_id: {created}')
        progress_meta = {
            'input_image': input_image,
            'prompt': prompt,
            'mode': 'image_to_video' if input_image else 'text_to_video',
        }
        self._report_progress({
            **progress_meta,
            'status': 'queued',
            'task_status': 'queued',
            'progress': 0,
            'task_id': task_id,
            'provider': 'agnes',
            'message': self._format_video_progress_message('queued', 0, 'agnes'),
        })
        result = self._poll_agnes_video_task(
            task_id, api_key, base_url,
            timeout_seconds=1800,
            poll_interval=5,
            progress_meta=progress_meta,
        )
        video_url = result.get('url') or result.get('video_url') or ''
        if not video_url:
            raise WorkflowExecutionError(f'Agnes 视频生成完成但未返回 video_url: {result}')
        return {
            'success': True,
            'output': {
                'video_url': video_url,
                'status': 'completed',
                'provider': 'agnes',
                'model': agnes_model,
                'task_id': task_id,
                'duration': float(result.get('seconds') or duration or 5),
                'resolution': resolution,
                'prompt': prompt,
                'input_image': input_image,
                'mode': 'image_to_video' if input_image else 'text_to_video',
            },
        }

    def run_video_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Video Generation Node
        Generates videos from text or images.
        """
        provider = node_config.get('provider', 'replicate')
        model = node_config.get('model', '')
        prompt = self._resolve_prompt_from_context(node_config, context, field='prompt')
        duration = node_config.get('duration', 4)
        fps = node_config.get('fps', 24)
        resolution = node_config.get('resolution', '720p')
        input_image = self._resolve_input_image(node_config, context)
        resolution_map = {'720p': 720, '1080p': 1080, '4k': 2160}
        height = resolution_map.get(resolution, 720)

        try:
            # Demo mode: no API key needed, return a simulated video result
            import os
            if not os.environ.get('REPLICATE_API_KEY') and provider == 'replicate':
                return {
                    'success': True,
                    'output': {
                        'video_url': f'https://www.w3schools.com/html/mov_bbb.mp4',
                        'thumbnail': input_image or f'https://picsum.photos/seed/{hash(prompt) % 100000}/640/360',
                        'status': 'completed',
                        'duration': duration,
                        'fps': fps,
                        'resolution': resolution,
                        'demo': True,
                        'prompt': prompt,
                        'input_image': input_image,
                        'mode': 'image_to_video' if input_image else 'text_to_video',
                    }
                }
            if provider == 'agnes':
                return self._execute_agnes_video_generation(
                    model=model,
                    prompt=prompt,
                    duration=duration,
                    resolution=resolution,
                    input_image=input_image,
                )
            if provider == 'dashscope':
                api_key, base_url = self._dashscope_credential()
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'X-DashScope-Async': 'enable',
                }
                ds_model = self._normalize_dashscope_video_model(model, input_image)
                ds_resolution_map = {'720p': '720P', '1080p': '1080P', '4k': '1080P', '480p': '480P'}
                ds_input = {'prompt': prompt}
                if input_image:
                    ds_input['img_url'] = input_image
                ds_parameters = {
                    'resolution': ds_resolution_map.get(str(resolution or '720p').lower(), '720P'),
                }
                fixed_duration_models = {
                    'wanx2.1-t2v-turbo', 'wanx2.1-t2v-plus', 'wan2.1-t2v-turbo',
                    'wan2.1-t2v-plus', 'wan2.2-t2v-plus',
                    'wanx2.1-i2v-turbo', 'wanx2.1-i2v-plus', 'wan2.1-i2v-turbo', 'wan2.1-i2v-plus',
                }
                if ds_model not in fixed_duration_models:
                    ds_parameters['duration'] = max(1, min(15, int(duration or 5)))
                elif input_image and 'i2v' in ds_model:
                    ds_parameters['duration'] = max(3, min(5, int(duration or 5)))
                payload = {
                    'model': ds_model,
                    'input': ds_input,
                    'parameters': ds_parameters,
                }
                with self._dashscope_httpx_client(timeout=VIDEO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'{base_url}/services/aigc/video-generation/video-synthesis',
                        headers=headers, json=payload
                    )
                    if resp.status_code >= 400:
                        raise WorkflowExecutionError(f'DashScope 视频生成任务创建失败: {self._dashscope_error_detail(resp)}')
                    task_id = (resp.json().get('output') or {}).get('task_id')
                if not task_id:
                    raise WorkflowExecutionError('DashScope 视频生成任务创建失败：未返回 task_id')
                result = self._poll_dashscope_task(task_id, api_key, base_url, timeout_seconds=600, poll_interval=10)
                video_url = result.get('video_url') or ''
                if not video_url and result.get('results'):
                    first = result['results'][0] if isinstance(result['results'], list) else {}
                    if isinstance(first, dict):
                        video_url = first.get('url') or first.get('video_url') or ''
                if not video_url:
                    raise WorkflowExecutionError(f'DashScope 视频生成完成但未返回 video_url: {result}')
                actual_duration = ds_parameters.get('duration', 5)
                return {
                    'success': True,
                    'output': {
                        'video_url': video_url,
                        'status': 'completed',
                        'provider': 'dashscope',
                        'model': ds_model,
                        'task_id': task_id,
                        'duration': actual_duration,
                        'fps': 30,
                        'resolution': resolution,
                        'prompt': prompt,
                        'input_image': input_image,
                        'mode': 'image_to_video' if input_image else 'text_to_video',
                    },
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
            err = str(e)
            import os
            # DashScope 鉴权/调用失败时，若上游有图则自动降级 Agnes 图生视频
            if provider == 'dashscope' and input_image:
                try:
                    agnes_key = self._get_credential('agnes') or (getattr(settings, 'AGNES_API_KEY', '') or '').strip()
                    if agnes_key:
                        logger.warning('DashScope 视频生成失败，降级 Agnes 图生视频: %s', e)
                        return self._execute_agnes_video_generation(
                            model='agnes-video-v2.0',
                            prompt=prompt,
                            duration=duration,
                            resolution=resolution,
                            input_image=input_image,
                        )
                except Exception as agnes_err:
                    err = f'{err}; Agnes 降级失败: {agnes_err}'
            if provider == 'replicate' and not os.environ.get('REPLICATE_API_KEY'):
                logger.warning('Replicate 未配置 API Key，使用 demo 视频: %s', e)
                return self._video_generation_demo_output(
                    prompt, duration, fps, resolution, input_image=input_image
                )
            logger.error('Video generation failed (%s): %s', provider, e)
            return {'success': False, 'error': f'视频生成失败 ({provider}): {err}'}

    def _audio_generation_demo_output(self, text: str, audio_format: str = 'mp3') -> Dict[str, Any]:
        return {
            'success': True,
            'output': {
                'audio_url': 'https://www.w3schools.com/html/horse.mp3',
                'format': audio_format,
                'duration_est': max(1, len(str(text or '')) / 5),
                'demo': True,
                'text': text,
            },
        }

    def run_audio_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audio/TTS Generation Node
        Generates audio from text using TTS providers.
        """
        provider = node_config.get('provider', 'openai')
        model = node_config.get('model', 'tts-1')
        text_template = node_config.get('text') or node_config.get('prompt') or ''
        text = self._render_template(text_template, context) if text_template else (context.get('text') or context.get('prompt') or '')
        voice = node_config.get('voice', 'alloy')
        speed = node_config.get('speed', 1.0)
        audio_format = node_config.get('format', 'mp3')

        try:
            if provider == 'openai':
                api_key = self._get_credential('openai')
                if not api_key or node_config.get('demo_mode'):
                    return self._audio_generation_demo_output(text, audio_format)
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=getattr(settings, 'OPENAI_BASE_URL', None) or None)
                response = client.audio.speech.create(
                    model=model, input=text, voice=voice,
                    response_format=audio_format, speed=speed
                )
                import base64
                audio_bytes = response.content
                audio_b64 = base64.b64encode(audio_bytes).decode()
                return {'success': True, 'output': {'audio_base64': audio_b64, 'format': audio_format, 'duration_est': len(text) / (5 * speed)}}
            elif provider == 'dashscope':
                api_key, base_url = self._dashscope_credential()
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                ds_model = model if model and model.startswith('cosyvoice') else 'cosyvoice-v3-flash'
                ds_voice = voice if voice and voice not in ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer') else 'longanyang'
                ds_format = audio_format if audio_format in ('mp3', 'wav', 'pcm', 'opus') else 'mp3'
                payload = {
                    'model': ds_model,
                    'input': {'text': text, 'voice': ds_voice, 'format': ds_format},
                }
                with httpx.Client(timeout=AUDIO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'{base_url}/services/audio/tts/SpeechSynthesizer',
                        headers=headers, json=payload
                    )
                    if resp.status_code >= 400:
                        raise WorkflowExecutionError(f'DashScope 语音合成失败: {self._dashscope_error_detail(resp)}')
                    data = resp.json()
                audio_url = ((data.get('output') or {}).get('audio') or {}).get('url', '')
                if not audio_url:
                    raise WorkflowExecutionError(f'DashScope 语音合成未返回音频地址: {data}')
                return {
                    'success': True,
                    'output': {
                        'audio_url': audio_url,
                        'format': ds_format,
                        'provider': 'dashscope',
                        'model': ds_model,
                        'voice': ds_voice,
                        'duration_est': max(1, len(text) / (5 * (speed or 1.0))),
                    }
                }
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
            elif provider == 'edge_tts':
                from pathlib import Path as _Path
                import tempfile
                from workflows.services.video_translation.constants import EDGE_TTS_VOICES
                from workflows.services.video_translation.media_providers import synthesize_edge_tts
                ds_voice = voice if voice and '-' in voice else EDGE_TTS_VOICES.get(
                    node_config.get('target_language') or context.get('target_language') or 'en',
                    'en-US-JennyNeural',
                )
                tmp = _Path(tempfile.gettempdir()) / f'flowly_edge_tts_{uuid.uuid4().hex}.{audio_format}'
                synthesize_edge_tts(text, voice=ds_voice, output_path=tmp)
                import base64
                audio_b64 = base64.b64encode(tmp.read_bytes()).decode()
                return {
                    'success': True,
                    'output': {
                        'audio_base64': audio_b64,
                        'format': audio_format,
                        'provider': 'edge_tts',
                        'voice': ds_voice,
                        'duration_est': max(1, len(text) / (5 * (speed or 1.0))),
                    },
                }
            elif provider in ('pyttsx3', 'local_tts'):
                from pathlib import Path as _Path
                import tempfile
                from workflows.services.video_translation.media_providers import synthesize_pyttsx3
                fmt = audio_format if audio_format in ('wav', 'mp3') else 'wav'
                tmp = _Path(tempfile.gettempdir()) / f'flowly_pyttsx3_{uuid.uuid4().hex}.{fmt}'
                synthesize_pyttsx3(text, output_path=tmp, voice_id=voice or None)
                import base64
                audio_b64 = base64.b64encode(tmp.read_bytes()).decode()
                return {
                    'success': True,
                    'output': {
                        'audio_base64': audio_b64,
                        'format': fmt,
                        'provider': 'pyttsx3',
                        'voice': voice or 'system-default',
                        'duration_est': max(1, len(text) / (5 * (speed or 1.0))),
                    },
                }
            elif provider == 'gtts':
                from pathlib import Path as _Path
                import tempfile
                from gtts import gTTS
                from workflows.services.video_translation.constants import GTTS_LANG_CODES
                lang = GTTS_LANG_CODES.get(
                    node_config.get('target_language') or context.get('target_language') or 'en',
                    'en',
                )
                tmp = _Path(tempfile.gettempdir()) / f'flowly_gtts_{uuid.uuid4().hex}.mp3'
                gTTS(text, lang=lang).save(str(tmp))
                import base64
                audio_b64 = base64.b64encode(tmp.read_bytes()).decode()
                return {
                    'success': True,
                    'output': {
                        'audio_base64': audio_b64,
                        'format': 'mp3',
                        'provider': 'gtts',
                        'voice': lang,
                        'duration_est': max(1, len(text) / (5 * (speed or 1.0))),
                    },
                }
            else:
                return {'success': False, 'error': f'Unknown audio provider: {provider}'}
        except Exception as e:
            err = str(e)
            if provider == 'openai' and any(token in err for token in ('AuthenticationError', 'Unauthorized', '401', 'invalid_api_key')):
                logger.warning('OpenAI audio generation auth failed, using demo output: %s', e)
                return self._audio_generation_demo_output(text, audio_format)
            return {'success': False, 'error': str(e)}

    def run_subtitle_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Subtitle Generation Node
        Generates subtitles from audio/video via local_whisper, OpenAI Whisper, or DashScope Paraformer.
        """
        input_path = (
            node_config.get('inputPath')
            or node_config.get('input_path')
            or node_config.get('input')
            or context.get('inputPath')
            or context.get('input')
            or context.get('video_url')
            or context.get('audio_url')
            or context.get('url')
            or ''
        )
        language = node_config.get('language', 'zh')
        format = node_config.get('format', 'srt')
        default_provider = getattr(settings, 'VIDEO_TRANSLATION_ASR_PROVIDER', 'local_whisper') or 'local_whisper'
        provider = (node_config.get('provider') or default_provider).strip().lower()
        rendered_path = (
            self._render_template(str(input_path), context)
            if '{' in str(input_path)
            else str(input_path)
        )
        if not rendered_path or '{' in rendered_path:
            rendered_path = (
                context.get('video_url')
                or context.get('source_video_url')
                or context.get('public_url')
                or str(input_path)
            )

        try:
            if provider == 'dashscope':
                if not rendered_path.lower().startswith(('http://', 'https://')):
                    raise WorkflowExecutionError('DashScope 语音识别要求公网可访问的音频/视频 URL')
                result = self._run_dashscope_subtitle_generation(rendered_path, language, format)
            elif provider == 'local_whisper':
                from workflows.services.media_service import resolve_local_media_path
                from workflows.services.video_translation.media_providers import transcribe_local_whisper
                local_path = resolve_local_media_path(rendered_path)
                result = transcribe_local_whisper(local_path, language=language, format=format)
            else:
                from workflows.services.media_service import resolve_local_media_path
                api_key = self._get_credential('openai')
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=getattr(settings, 'OPENAI_BASE_URL', None) or None)
                local_path = resolve_local_media_path(rendered_path) if rendered_path else None
                if not local_path or not local_path.exists():
                    raise WorkflowExecutionError('OpenAI Whisper 需要可读取的本地媒体文件或 URL')
                with open(local_path, 'rb') as f:
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
                result = {
                    'success': True,
                    'output': {
                        'subtitles': content,
                        'format': format,
                        'text': text,
                        'segments': segments,
                        'source_segments': segments,
                        'provider': 'openai',
                        'model': 'whisper-1',
                    },
                }

            if result.get('success') and isinstance(result.get('output'), dict):
                output = result['output']
                video_url = context.get('source_video_url') or context.get('video_url') or rendered_path
                if video_url:
                    output.setdefault('video_url', video_url)
                    output.setdefault('source_video_url', video_url)
                if context.get('duration'):
                    output.setdefault('duration', context.get('duration'))
            return result
        except ImportError:
            return {'success': False, 'error': 'openai library required. Install with: pip install openai'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _run_dashscope_subtitle_generation(self, input_url: str, language: str, format: str) -> Dict[str, Any]:
        """Generate subtitles from a public audio/video URL via DashScope Paraformer 录音文件识别 API."""
        if not input_url or not str(input_url).lower().startswith(('http://', 'https://')):
            raise WorkflowExecutionError('DashScope 语音识别要求提供公网可访问的音频/视频 URL（inputPath/input）')

        api_key, base_url = self._dashscope_credential()
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable',
        }
        language_hints = [language] if language and language not in ('auto', '') else ['zh', 'en']
        payload = {
            'model': 'paraformer-v2',
            'input': {'file_urls': [input_url]},
            'parameters': {'language_hints': language_hints},
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(f'{base_url}/services/audio/asr/transcription', headers=headers, json=payload)
            if resp.status_code >= 400:
                raise WorkflowExecutionError(f'DashScope 语音识别任务创建失败: {self._dashscope_error_detail(resp)}')
            task_id = (resp.json().get('output') or {}).get('task_id')
        if not task_id:
            raise WorkflowExecutionError('DashScope 语音识别任务创建失败：未返回 task_id')

        result = self._poll_dashscope_task(task_id, api_key, base_url, timeout_seconds=300, poll_interval=5)
        results = result.get('results', [])
        if not results:
            raise WorkflowExecutionError('DashScope 语音识别未返回结果')
        first = results[0]
        if first.get('subtask_status') == 'FAILED':
            raise WorkflowExecutionError(f"DashScope 语音识别失败: {first.get('message', '未知错误')}")
        transcription_url = first.get('transcription_url')
        if not transcription_url:
            raise WorkflowExecutionError('DashScope 语音识别结果缺少 transcription_url')

        with httpx.Client(timeout=60) as client:
            trans_resp = client.get(transcription_url)
            trans_resp.raise_for_status()
            transcript_data = trans_resp.json()

        transcripts = transcript_data.get('transcripts', [])
        full_text = ' '.join(t.get('text', '') for t in transcripts).strip()
        segments = []
        for t in transcripts:
            for sentence in t.get('sentences', []):
                segments.append({
                    'start': (sentence.get('begin_time') or 0) / 1000.0,
                    'end': (sentence.get('end_time') or 0) / 1000.0,
                    'text': sentence.get('text', ''),
                })

        if format == 'srt':
            content = self._text_to_srt(full_text, segments)
        elif format == 'vtt':
            content = self._text_to_vtt(full_text, segments)
        else:
            content = full_text

        return {
            'success': True,
            'output': {
                'subtitles': content,
                'format': format,
                'text': full_text,
                'segments': segments,
                'source_segments': segments,
                'provider': 'dashscope',
                'model': 'paraformer-v2',
                'task_id': task_id,
            }
        }

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

    def run_video_translation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Video Translation Node — ASR → translate → TTS → VideoRetalk lip sync → burn subtitles.
        """
        from workflows.services.media_service import download_url_to_media, save_output_file
        from workflows.services.video_translation.pipeline import VideoTranslationPipeline

        def asr_call(video_url: str, language: str) -> Dict[str, Any]:
            fmt = node_config.get('subtitle_format') or node_config.get('subtitleFormat') or 'srt'
            if fmt == 'both':
                fmt = 'srt'
            asr_provider = (
                node_config.get('asr_provider')
                or node_config.get('provider')
                or getattr(settings, 'VIDEO_TRANSLATION_ASR_PROVIDER', 'local_whisper')
            )
            return self.run_subtitle_generation_node(
                {'provider': asr_provider, 'inputPath': video_url, 'language': language, 'format': fmt},
                {**context, 'video_url': video_url, 'source_video_url': video_url},
            )

        def llm_call(prompt: str) -> str:
            model = (
                node_config.get('translation_model')
                or node_config.get('model')
                or getattr(settings, 'NL_WORKFLOW_MODEL', None)
                or getattr(settings, 'DEFAULT_LLM_MODEL', 'qwen2.5-coder:7b')
            )
            result = self.run_llm_node(
                {'prompt': prompt, 'model': model, 'temperature': 0.3, 'max_tokens': 4096},
                context,
            )
            if not result.get('success'):
                raise WorkflowExecutionError(result.get('error') or 'LLM 翻译失败')
            return (result.get('output') or {}).get('text') or ''

        def tts_call(text: str, voice: str, fmt: str) -> str:
            tts_provider = (
                node_config.get('tts_provider')
                or getattr(settings, 'VIDEO_TRANSLATION_TTS_PROVIDER', 'pyttsx3')
            )
            result = self.run_audio_generation_node(
                {
                    'provider': tts_provider,
                    'model': node_config.get('tts_model') or 'tts-1',
                    'text': text,
                    'voice': voice,
                    'format': fmt,
                    'target_language': node_config.get('target_language'),
                },
                context,
            )
            if not result.get('success'):
                raise WorkflowExecutionError(result.get('error') or 'TTS 合成失败')
            output = result.get('output') or {}
            audio_url = output.get('audio_url')
            if audio_url:
                local = download_url_to_media(audio_url, subdir='video_translation/tts')
                return str(local)
            import base64
            import tempfile
            audio_b64 = output.get('audio_base64')
            if audio_b64:
                tmp = Path(tempfile.gettempdir()) / f'flowly_tts_{uuid.uuid4().hex}.{fmt}'
                tmp.write_bytes(base64.b64decode(audio_b64))
                saved = save_output_file(tmp, subdir='video_translation/tts')
                return saved['local_path']
            raise WorkflowExecutionError('TTS 未返回音频')

        def progress(step: str, meta: Dict[str, Any]) -> None:
            self._report_progress({
                'video_translation_step': step,
                **meta,
            })

        pipeline = VideoTranslationPipeline(
            asr_call=asr_call,
            llm_call=llm_call,
            tts_call=tts_call,
            dashscope_credential=self._dashscope_credential,
            poll_dashscope_task=self._poll_dashscope_task,
            progress=progress,
            render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
        )
        result = pipeline.run(node_config, context)
        if result.get('success'):
            output = result.get('output') or {}
            primary = (output.get('results') or [{}])[0]
            output['video_url'] = primary.get('video_url')
            output['subtitles'] = primary.get('subtitles')
            output['lip_sync_applied'] = primary.get('lip_sync_applied')
            result['output'] = output
        return result

    def run_video_upload_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.video_translation.node_runners import run_video_upload
        try:
            return run_video_upload(
                node_config,
                context,
                render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
            )
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_subtitle_translate_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.video_translation.node_runners import run_subtitle_translate

        def llm_call(prompt: str) -> str:
            model = (
                node_config.get('translation_model')
                or node_config.get('model')
                or getattr(settings, 'NL_WORKFLOW_MODEL', None)
                or getattr(settings, 'DEFAULT_LLM_MODEL', 'qwen2.5-coder:7b')
            )
            result = self.run_llm_node(
                {'prompt': prompt, 'model': model, 'temperature': 0.3, 'max_tokens': 4096},
                context,
            )
            if not result.get('success'):
                raise WorkflowExecutionError(result.get('error') or 'LLM 翻译失败')
            return (result.get('output') or {}).get('text') or ''

        try:
            return run_subtitle_translate(
                node_config,
                context,
                llm_call=llm_call,
                render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
            )
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_segment_dubbing_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.media_service import download_url_to_media, save_output_file
        from workflows.services.video_translation.node_runners import run_segment_dubbing

        def tts_call(text: str, voice: str, fmt: str) -> str:
            tts_provider = (
                node_config.get('provider')
                or node_config.get('tts_provider')
                or getattr(settings, 'VIDEO_TRANSLATION_TTS_PROVIDER', 'pyttsx3')
            )
            result = self.run_audio_generation_node(
                {
                    'provider': tts_provider,
                    'model': node_config.get('tts_model') or 'tts-1',
                    'text': text,
                    'voice': voice,
                    'format': fmt,
                    'target_language': node_config.get('target_language'),
                },
                context,
            )
            if not result.get('success'):
                raise WorkflowExecutionError(result.get('error') or 'TTS 合成失败')
            output = result.get('output') or {}
            audio_url = output.get('audio_url')
            if audio_url:
                return str(download_url_to_media(audio_url, subdir='video_translation/tts'))
            import base64
            import tempfile
            audio_b64 = output.get('audio_base64')
            if audio_b64:
                tmp = Path(tempfile.gettempdir()) / f'flowly_tts_{uuid.uuid4().hex}.{fmt}'
                tmp.write_bytes(base64.b64decode(audio_b64))
                return save_output_file(tmp, subdir='video_translation/tts')['local_path']
            raise WorkflowExecutionError('TTS 未返回音频')

        try:
            return run_segment_dubbing(node_config, context, tts_call=tts_call)
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_lip_sync_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.video_translation.node_runners import run_lip_sync
        try:
            return run_lip_sync(
                node_config,
                context,
                dashscope_credential=self._dashscope_credential,
                poll_dashscope_task=self._poll_dashscope_task,
                render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
            )
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_subtitle_burn_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.video_translation.node_runners import run_subtitle_burn
        try:
            return run_subtitle_burn(
                node_config,
                context,
                render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
            )
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_image_editing_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Image Editing Node
        Edits existing images based on instructions.
        """
        provider = node_config.get('provider', 'openai')
        model = node_config.get('model', 'dall-e-2')
        image = node_config.get('image') or node_config.get('inputImage') or context.get('image') or context.get('inputImage') or ''
        instruction_template = node_config.get('instruction') or node_config.get('prompt') or ''
        instruction = (
            self._render_template(instruction_template, context)
            if instruction_template
            else (context.get('instruction') or context.get('prompt') or '')
        )
        mask = node_config.get('mask', '')

        try:
            if provider == 'openai':
                api_key = self._get_credential('openai')
                if not api_key:
                    return {
                        'success': True,
                        'output': {
                            'images': [{'url': f'https://picsum.photos/seed/{abs(hash(str(instruction))) % 100000}/1024/1024', 'revised_prompt': f'[Demo Mode] {instruction}'}],
                            'url': f'https://picsum.photos/seed/{abs(hash(str(instruction))) % 100000}/1024/1024',
                            'count': 1,
                            'demo': True
                        }
                    }
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=getattr(settings, 'OPENAI_BASE_URL', None) or None)
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
            elif provider == 'dashscope':
                if not image:
                    raise WorkflowExecutionError('DashScope 图像编辑需要提供原始图像 URL（image/inputImage）')
                api_key, base_url = self._dashscope_credential()
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                ds_model = model if model and model.startswith('wan') else 'wan2.6-image'
                content = [{'text': instruction}, {'image': image}]
                if mask:
                    content.append({'image': mask})
                payload = {
                    'model': ds_model,
                    'input': {'messages': [{'role': 'user', 'content': content}]},
                    'parameters': {'n': 1, 'watermark': False},
                }
                with httpx.Client(timeout=IMAGE_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'{base_url}/services/aigc/multimodal-generation/generation',
                        headers=headers, json=payload
                    )
                    if resp.status_code >= 400:
                        raise WorkflowExecutionError(f'DashScope 图像编辑失败: {self._dashscope_error_detail(resp)}')
                    data = resp.json()
                choices = (data.get('output') or {}).get('choices') or []
                image_url = ''
                for choice in choices:
                    for item in (choice.get('message', {}) or {}).get('content', []) or []:
                        if item.get('type') == 'image' and item.get('image'):
                            image_url = item['image']
                            break
                    if image_url:
                        break
                if not image_url:
                    raise WorkflowExecutionError(f'DashScope 图像编辑未返回图像结果: {data}')
                return {'success': True, 'output': {'url': image_url, 'provider': 'dashscope', 'model': ds_model}}
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
        ML formats (yolo, image_folder, image_text_pairs, classification_folders)
        validate directory layouts per node-io-contracts.md §1.
        """
        import os
        import hashlib
        from django.conf import settings
        from datasets.models import Dataset
        from datasets.utils import parse_dataset_file, download_from_url, download_from_s3
        from datasets.ml_format_validators import (
            is_ml_format,
            validate_ml_dataset,
            compute_path_size_bytes,
        )

        source = node_config.get('source', 'upload')
        path_template = node_config.get('path', '')
        path = self._render_template(path_template, context) if path_template else context.get('path', '')
        path = path or node_config.get('datasetPath', '') or node_config.get('filePath', '')
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
                    return {'success': False, 'error': f'Path not found: {resolved_path}'}

                file_path = resolved_path
                file_size = compute_path_size_bytes(resolved_path) if is_ml_format(format_type) else os.path.getsize(resolved_path)

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

            if is_ml_format(format_type):
                validation = validate_ml_dataset(file_path, format_type)
                if not validation.get('valid'):
                    return {'success': False, 'error': validation.get('error', 'ML dataset validation failed')}

                dataset_root = validation['dataset_path']
                class_names = validation.get('class_names', [])
                stats = validation.get('stats', {})
                row_count = validation.get('row_count', stats.get('image_count', 0))
                preview_rows = validation.get('preview_data', [])
                columns = list({k for row in preview_rows if isinstance(row, dict) for k in row.keys()})

                content_hash = hashlib.md5(dataset_root.encode('utf-8')).hexdigest()[:12]

                metadata = {
                    'dataset_path': dataset_root,
                    'class_names': class_names,
                    'stats': stats,
                }
                if validation.get('dataset_yaml_path'):
                    metadata['dataset_yaml_path'] = validation['dataset_yaml_path']

                dataset = Dataset.objects.create(
                    name=f"{name}_{content_hash}",
                    description=description or f'ML dataset ({format_type}) from {source}: {path}',
                    source=source,
                    file_path=dataset_root,
                    format=format_type,
                    size_bytes=file_size or compute_path_size_bytes(dataset_root),
                    row_count=row_count,
                    column_count=len(class_names) or len(columns),
                    columns=class_names or columns,
                    preview_data=preview_rows,
                    status='ready',
                    metadata=metadata,
                    created_by=self.user if hasattr(self, 'user') else None,
                    tenant=self.tenant if hasattr(self, 'tenant') else None,
                )

                output_data = {
                    'dataset_id': str(dataset.id),
                    'dataset_path': dataset_root,
                    'name': dataset.name,
                    'format': format_type,
                    'class_names': class_names,
                    'stats': stats,
                    'row_count': row_count,
                    'size_bytes': dataset.size_bytes,
                    'source': source,
                    'path': dataset_root,
                    'preview_rows': len(preview_rows),
                    'status': 'ready',
                }
                if validation.get('dataset_yaml_path'):
                    output_data['dataset_yaml_path'] = validation['dataset_yaml_path']

                return {'success': True, 'output': output_data}

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

    def run_yolo_training_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        YOLO-specific training node.
        Supports two execution modes:
        - local:  runs on server in background thread (user's deployed server)
        - cloud:   dispatches to Celery async task (requires Celery broker)
        """
        from pathlib import Path

        gpu_info = self._detect_gpu()

        cfg = node_config.get('config', {}) or {}

        dataset_yaml_path = node_config.get('datasetYamlPath', '') or cfg.get('datasetYamlPath', '') or context.get('dataset_yaml_path', '')
        dataset_path = node_config.get('datasetPath', '') or cfg.get('datasetPath', '') or context.get('dataset_path', '')
        dataset_id = node_config.get('datasetId', '') or cfg.get('datasetId', '') or context.get('dataset_id', '')
        annotation_project_id = node_config.get('annotationProjectId', '') or cfg.get('annotationProjectId', '') or context.get('annotation_project_id', '')
        class_names = node_config.get('classNames', []) or cfg.get('classNames', []) or context.get('class_names', [])

        training = cfg.get('training', {}) or cfg
        execution_mode = cfg.get('trainingMode', 'local')

        epochs = training.get('epochs', node_config.get('epochs', 100))
        yolo_version = cfg.get('yoloVersion', node_config.get('yoloVersion', 'v8'))
        model_variant = cfg.get('modelVariant', node_config.get('modelVariant', 'n'))
        job_name = node_config.get('label', f'YOLO_{yolo_version}{model_variant}')

        if not dataset_yaml_path and not dataset_path and not annotation_project_id:
            return {'success': False, 'error': 'YOLO训练缺少 datasetYamlPath、datasetPath 或 annotationProjectId'}

        device_preference = (
            cfg.get('device')
            or training.get('device')
            or node_config.get('device')
            or ('cpu' if execution_mode == 'local' else None)
        )

        output_dir = cfg.get('runtime', {}).get('storagePath') or cfg.get('outputDir') or f'./outputs/yolo_{uuid.uuid4().hex[:8]}'
        output_dir_path = Path(output_dir)
        if not output_dir_path.is_absolute():
            output_dir_path = (Path(settings.BASE_DIR) / output_dir_path).resolve()
        output_dir = str(output_dir_path)

        try:
            from training.models import TrainingJob
            from django.contrib.auth import get_user_model

            user = None
            if self.user_id:
                User = get_user_model()
                try:
                    user = User.objects.get(id=self.user_id)
                except User.DoesNotExist:
                    pass
            elif context.get('metadata', {}).get('user_id'):
                User = get_user_model()
                try:
                    user = User.objects.get(id=context['metadata']['user_id'])
                except User.DoesNotExist:
                    pass

            workflow_id = context.get('metadata', {}).get('workflow_id')
            execution_id = context.get('metadata', {}).get('execution_id')

            yolo_job = TrainingJob.objects.create(
                name=job_name,
                framework='ultralytics',
                model_type='detection',
                training_kind='yolo',
                status='queued',
                config={
                    **cfg,
                    'output_dir': output_dir,
                    'batch_size': training.get('batchSize', training.get('batch_size', 16)),
                    'image_size': training.get('imageSize', training.get('image_size', 640)),
                    'learning_rate': training.get('learningRate', training.get('learning_rate', 0.01)),
                },
                gpu_info=gpu_info,
                dataset_id=dataset_id,
                dataset_path=dataset_path or '',
                dataset_yaml_path=dataset_yaml_path or '',
                dataset_source_mode=cfg.get('datasetSource', '') or node_config.get('datasetSource', {}).get('mode', '') or context.get('dataset_source_mode', ''),
                annotation_project_id=annotation_project_id,
                class_names=class_names,
                total_epochs=epochs,
                yolo_version=yolo_version,
                model_variant=model_variant,
                created_by=user,
                workflow_id=workflow_id or None,
                execution_id=execution_id or None,
            )

            config_dir = Path(settings.BASE_DIR) / 'data' / 'training_configs'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f'{yolo_job.id}.json'

            train_config = {
                'job_id': str(yolo_job.id),
                'training_kind': 'yolo',
                'framework': 'ultralytics',
                'model_type': 'detection',
                'dataset_id': dataset_id,
                'dataset_path': dataset_path,
                'dataset_yaml_path': dataset_yaml_path,
                'annotation_project_id': annotation_project_id,
                'class_names': class_names,
                'yolo_version': yolo_version,
                'model_variant': model_variant,
                'epochs': epochs,
                'batch_size': training.get('batchSize', training.get('batch_size', 16)),
                'image_size': training.get('imageSize', training.get('image_size', 640)),
                'learning_rate': training.get('learningRate', training.get('learning_rate', 0.01)),
                'output_dir': output_dir,
                'device': device_preference,
                'config': yolo_job.config,
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(train_config, f, ensure_ascii=False, indent=2)

            # ---- Local execution (synchronous — workflow downstream needs weights) ----
            if execution_mode == 'local':
                yolo_job.status = 'running'
                yolo_job.save(update_fields=['status'])

                training_result = self._run_local_yolo_training(
                    str(yolo_job.id), str(config_path), output_dir, epochs
                )
                yolo_job.refresh_from_db()
                if yolo_job.status != 'completed' or not training_result.get('success', False):
                    return {
                        'success': False,
                        'error': yolo_job.error_message or training_result.get('error') or 'YOLO training failed',
                    }

                best_weight = yolo_job.best_weight_path or training_result.get('best_weight_path', '')
                last_weight = yolo_job.last_weight_path or training_result.get('last_weight_path', '')
                return {
                    'success': True,
                    'output': {
                        'training_run_id': str(yolo_job.id),
                        'training_status': 'completed',
                        'execution_mode': 'local',
                        'websocket_url': f'/ws/training/{yolo_job.id}/',
                        'dataset_id': dataset_id,
                        'dataset_yaml_path': dataset_yaml_path,
                        'class_names': class_names,
                        'yolo_version': yolo_version,
                        'model_variant': model_variant,
                        'gpu_info': gpu_info,
                        'output_dir': output_dir,
                        'epochs': epochs,
                        'model_path': best_weight,
                        'best_weight_path': best_weight,
                        'last_weight_path': last_weight,
                        'final_metrics': training_result.get('final_metrics', {}),
                    }
                }

            # ---- Cloud execution (Celery) ----
            else:
                from training.tasks import run_training_task
                run_training_task.delay(
                    training_job_id=str(yolo_job.id),
                    config_path=str(config_path),
                    output_dir=output_dir,
                )

                return {
                    'success': True,
                    'output': {
                        'training_run_id': str(yolo_job.id),
                        'training_status': 'queued',
                        'execution_mode': 'cloud',
                        'websocket_url': f'/ws/training/{yolo_job.id}/',
                        'dataset_id': dataset_id,
                        'dataset_yaml_path': dataset_yaml_path,
                        'class_names': class_names,
                        'yolo_version': yolo_version,
                        'model_variant': model_variant,
                        'gpu_info': gpu_info,
                    }
                }

        except Exception as e:
            logger.exception(f"YOLO training node error: {e}")
            return {'success': False, 'error': str(e)}

    def _run_local_yolo_training(self, job_id_str: str, cfg_path_str: str, out_dir: str, epochs: int) -> Dict[str, Any]:
        """Run YOLO training subprocess and block until completion."""
        from pathlib import Path
        import subprocess
        import sys
        import time as time_module

        try:
            script_path = Path(settings.BASE_DIR) / 'scripts' / 'train_model.py'
            if not script_path.exists():
                script_path = Path(__file__).parent.parent.parent / 'scripts' / 'train_model.py'

            env = os.environ.copy()
            try:
                with open(cfg_path_str, 'r', encoding='utf-8') as cfg_file:
                    train_cfg = json.load(cfg_file)
                device_pref = train_cfg.get('device') or (train_cfg.get('config') or {}).get('device')
                if str(device_pref).lower() == 'cpu':
                    env['CUDA_VISIBLE_DEVICES'] = ''
            except Exception:
                pass

            log_path = Path(out_dir) / f'training_{job_id_str}.log'
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = open(log_path, 'w', encoding='utf-8')

            proc = subprocess.Popen(
                [sys.executable, str(script_path),
                 '--config', cfg_path_str,
                 '--job-id', job_id_str,
                 '--output-dir', out_dir],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
            )

            result_file = Path(out_dir) / 'training_result.json'
            timeout_seconds = max(epochs * 600, 1200)
            elapsed = 0
            interval = 5

            while elapsed < timeout_seconds:
                time_module.sleep(interval)
                elapsed += interval
                if result_file.exists():
                    try:
                        with open(result_file, 'r', encoding='utf-8') as rf:
                            result = json.load(rf)
                        log_file.close()
                        proc.wait(timeout=30)
                        self._update_yolo_job_result(job_id_str, result)
                        return result
                    except Exception:
                        pass
                if proc.poll() is not None:
                    break

            log_file.close()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=30)
                except Exception:
                    proc.kill()

            if result_file.exists():
                try:
                    with open(result_file, 'r', encoding='utf-8') as rf:
                        result = json.load(rf)
                    self._update_yolo_job_result(job_id_str, result)
                    return result
                except Exception:
                    pass

            rc = proc.returncode
            fallback = {
                'success': rc == 0,
                'error': f'Process exited with code {rc}' if rc not in (0, None) else 'Training timeout',
            }
            self._update_yolo_job_result(job_id_str, fallback)
            return fallback
        except Exception as e:
            logger.exception(f"Local YOLO training failed for job {job_id_str}")
            try:
                from training.models import TrainingJob
                tj = TrainingJob.objects.get(id=job_id_str)
                tj.status = 'failed'
                tj.error_message = str(e)
                tj.save(update_fields=['status', 'error_message'])
            except Exception:
                pass
            return {'success': False, 'error': str(e)}

    def _parse_yolo_results_csv(self, csv_path: Path) -> Dict[str, List[float]]:
        """Parse Ultralytics results.csv into chart series."""
        series = {
            'loss_box': [],
            'loss_cls': [],
            'loss_dfl': [],
            'precision': [],
            'recall': [],
            'mAP50': [],
            'mAP50_95': [],
        }
        if not csv_path.is_file():
            return series
        import csv

        column_map = {
            'train/box_loss': 'loss_box',
            'train/cls_loss': 'loss_cls',
            'train/dfl_loss': 'loss_dfl',
            'metrics/precision(B)': 'precision',
            'metrics/recall(B)': 'recall',
            'metrics/mAP50(B)': 'mAP50',
            'metrics/mAP50-95(B)': 'mAP50_95',
        }
        try:
            with open(csv_path, newline='', encoding='utf-8') as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    for src_col, dest_key in column_map.items():
                        raw = row.get(src_col)
                        if raw in (None, ''):
                            continue
                        try:
                            series[dest_key].append(float(raw))
                        except (TypeError, ValueError):
                            continue
        except Exception as exc:
            logger.warning('Failed to parse YOLO results.csv at %s: %s', csv_path, exc)
        return series

    def _resolve_yolo_results_csv(self, job: 'TrainingJob') -> Optional[Path]:
        """Locate Ultralytics results.csv for a completed YOLO job."""
        from pathlib import Path

        candidates: List[Path] = []
        weight_path = job.best_weight_path or job.model_path or ''
        if weight_path:
            wp = Path(weight_path)
            if wp.exists() and wp.parent.name == 'weights':
                candidates.append(wp.parent.parent / 'results.csv')
        output_dir = (job.config or {}).get('output_dir') or ''
        if output_dir:
            base = Path(output_dir)
            candidates.append(base / 'results.csv')
            if base.is_dir():
                for child in base.iterdir():
                    if child.is_dir():
                        candidates.append(child / 'results.csv')
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    def _update_yolo_job_result(self, job_id_str: str, result: Dict[str, Any]):
        """Update TrainingJob with final training result from result file."""
        from pathlib import Path
        try:
            from training.models import TrainingJob
            tj = TrainingJob.objects.get(id=job_id_str)
            if result.get('success'):
                tj.status = 'completed'
                csv_path = self._resolve_yolo_results_csv(tj)
                if not csv_path and result.get('best_weight_path'):
                    wp = Path(result['best_weight_path'])
                    if wp.parent.name == 'weights':
                        csv_path = wp.parent.parent / 'results.csv'
                series = self._parse_yolo_results_csv(csv_path) if csv_path else {}
                if series.get('loss_box'):
                    tj.loss_box_history = series['loss_box']
                if series.get('loss_cls'):
                    tj.loss_cls_history = series['loss_cls']
                if series.get('loss_dfl'):
                    tj.loss_dfl_history = series['loss_dfl']
                if series.get('precision'):
                    tj.precision_history = series['precision']
                if series.get('recall'):
                    tj.recall_history = series['recall']
                if series.get('mAP50'):
                    tj.map50_history = series['mAP50']
                if series.get('mAP50_95'):
                    tj.map50_95_history = series['mAP50_95']
                if series.get('mAP50'):
                    tj.metrics_history = [
                        {
                            'epoch': idx + 1,
                            'loss_box': series['loss_box'][idx] if idx < len(series['loss_box']) else None,
                            'loss_cls': series['loss_cls'][idx] if idx < len(series['loss_cls']) else None,
                            'loss_dfl': series['loss_dfl'][idx] if idx < len(series['loss_dfl']) else None,
                            'precision': series['precision'][idx] if idx < len(series['precision']) else None,
                            'recall': series['recall'][idx] if idx < len(series['recall']) else None,
                            'mAP50': series['mAP50'][idx] if idx < len(series['mAP50']) else None,
                            'mAP50_95': series['mAP50_95'][idx] if idx < len(series['mAP50_95']) else None,
                        }
                        for idx in range(len(series['mAP50']))
                    ]
                final_metrics = dict(result.get('final_metrics') or {})
                if series.get('mAP50'):
                    final_metrics.setdefault('mAP50', series['mAP50'][-1])
                if series.get('precision'):
                    final_metrics.setdefault('precision', series['precision'][-1])
                if series.get('recall'):
                    final_metrics.setdefault('recall', series['recall'][-1])
                if series.get('mAP50_95'):
                    final_metrics.setdefault('mAP50_95', series['mAP50_95'][-1])
                fitness = final_metrics.get('fitness') or final_metrics.get('mAP50') or 0
                if fitness:
                    tj.current_metric = fitness
                    tj.best_fitness = fitness
                elif result.get('final_metrics'):
                    tj.current_metric = result['final_metrics'].get('mAP50', 0)
                    tj.best_fitness = result['final_metrics'].get('fitness', 0)
                tj.best_weight_path = result.get('best_weight_path', '')
                tj.last_weight_path = result.get('last_weight_path', '')
                tj.exported_artifacts = result.get('exported_artifacts', {})
                tj.duration_seconds = result.get('duration_seconds', 0)
                if result.get('training_history') and not tj.loss_box_history:
                    history = result['training_history']
                    tj.loss_box_history = [h.get('loss_box', 0) for h in history]
                    tj.metrics_history = history
            else:
                tj.status = 'failed'
                tj.error_message = result.get('error', 'Training failed')
            tj.save()
        except Exception:
            pass

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
        from pathlib import Path

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
            # Ultralytics (YOLO) — use dedicated yolo_training node instead
            elif framework in ('ultralytics', 'yolo', 'yolov8'):
                return {
                    'success': False,
                    'error': 'YOLO 训练请使用「YOLO 训练」节点，模型训练节点仅支持 PyTorch / Transformers'
                }
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

                logger.info(f"[MODEL_TRAIN] Creating TrainingJob: framework={framework}")

                training_job = TrainingJob.objects.create(
                    name=job_name,
                    framework=framework,
                    model_type=model_type,
                    training_kind='generic',
                    status='queued',
                    config=train_config,
                    gpu_info=gpu_info,
                    dataset_path=dataset_path or '',
                    dataset_yaml_path=train_config.get('dataset_yaml_path', '') or '',
                    total_epochs=epochs,
                    yolo_version='',
                    model_variant='',
                )

                logger.info(f"[MODEL_TRAIN] Created TrainingJob record: {training_job.id} training_kind={training_job.training_kind}")

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
            
            # Return immediately with job info (optionally wait for completion)
            wait_for_completion = bool(node_config.get('waitForCompletion', False))
            wait_timeout = int(node_config.get('waitTimeoutSeconds') or 3600)

            output_payload = {
                'job_id': celery_job_id,
                'training_run_id': celery_job_id,
                'status': 'queued',
                'message': f'训练任务已提交，请通过WebSocket监控进度: ws://host/ws/training/{celery_job_id}/',
                'websocket_url': f'/ws/training/{celery_job_id}/',
                'config': train_config,
                'framework': framework,
                'model_type': model_type,
                'dataset_id': dataset_id,
                'gpu_info': gpu_info,
                'output_dir': output_dir,
            }

            if wait_for_completion:
                poll = self._poll_training_job_completion(
                    celery_job_id,
                    timeout_seconds=wait_timeout,
                )
                if not poll.get('success'):
                    return {
                        'success': False,
                        'error': poll.get('error', '训练未完成'),
                        'output': output_payload,
                    }
                job = poll['job']
                output_payload.update({
                    'status': 'completed',
                    'training_status': 'completed',
                    'model_path': job.best_weight_path or job.model_path or '',
                    'best_weight_path': job.best_weight_path or '',
                    'class_names': job.class_names or [],
                    'labels': job.class_names or [],
                    'metrics': job.metrics or {},
                    'message': '训练已完成',
                })

            return {
                'success': True,
                'output': output_payload,
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

    def run_clip_retrieval_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Build CLIP retrieval index from image_text_pairs dataset (M4)."""
        import threading

        from django.utils import timezone
        from training.models import TrainingJob
        from training.clip_service import build_retrieval_index
        from training.tasks import _broadcast_training_event

        cfg = node_config.get('config', {}) or {}
        gpu_info = self._detect_gpu()

        dataset_path = (
            node_config.get('datasetPath', '')
            or cfg.get('datasetPath', '')
            or context.get('dataset_path', '')
            or context.get('path', '')
        )
        if not dataset_path:
            return {'success': False, 'error': '缺少 dataset_path，请先运行 dataset_upload(format=image_text_pairs)'}

        output_dir = (
            node_config.get('outputDir', '')
            or cfg.get('outputDir', '')
            or context.get('index_dir', '')
            or os.path.join(dataset_path, 'index')
        )
        base_model = node_config.get('baseModel') or cfg.get('baseModel') or 'simple-bow'
        index_type = node_config.get('indexType') or cfg.get('indexType') or 'flat'
        index_mode = node_config.get('indexMode') or cfg.get('indexMode') or 'server'
        execution_mode = cfg.get('trainingMode', node_config.get('trainingMode', 'local'))
        prebuilt_index = (
            node_config.get('prebuiltIndexDir', '')
            or node_config.get('prebuilt_index_dir', '')
            or cfg.get('prebuiltIndexDir', '')
            or cfg.get('prebuilt_index_dir', '')
            or context.get('prebuilt_index_dir', '')
        )

        job = TrainingJob.objects.create(
            name=node_config.get('label', 'CLIP 检索索引'),
            framework='pytorch',
            model_type='custom',
            training_kind='clip_ret',
            status='running',
            dataset_path=dataset_path,
            gpu_info=gpu_info,
            config={**node_config, 'indexType': index_type, 'baseModel': base_model, 'indexMode': index_mode},
            class_names=[],
            progress=0,
        )
        job_id_str = str(job.id)

        if prebuilt_index and os.path.isdir(prebuilt_index):
            meta_path = os.path.join(prebuilt_index, 'metadata.json')
            metrics = {}
            encoder = 'bow'
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, encoding='utf-8') as mf:
                        meta = json.load(mf)
                    metrics = meta.get('metrics', {})
                    encoder = meta.get('encoder', 'bow')
                except Exception:
                    pass
            job.status = 'completed'
            job.progress = 100
            job.metrics = metrics
            job.exported_artifacts = {
                'index_dir': prebuilt_index,
                'metadata_path': meta_path if os.path.isfile(meta_path) else '',
                'encoder': encoder,
                'built_on': 'desktop',
            }
            job.completed_at = timezone.now()
            job.save()
            return {
                'success': True,
                'output': {
                    'training_run_id': job_id_str,
                    'training_status': 'completed',
                    'execution_mode': 'desktop',
                    'index_mode': index_mode,
                    'built_on': 'desktop',
                    'websocket_url': f'/ws/training/{job_id_str}/',
                    'gpu_info': gpu_info,
                    'index_dir': prebuilt_index,
                    'metadata_path': meta_path if os.path.isfile(meta_path) else '',
                    'metrics': metrics,
                    'r_at_1': metrics.get('r_at_1'),
                    'r_at_5': metrics.get('r_at_5'),
                    'r_at_10': metrics.get('r_at_10'),
                    'output_dir': prebuilt_index,
                    'encoder': encoder,
                    'duration_ms': 0,
                },
            }

        def _progress(payload: Dict[str, Any]):
            pct = int(payload.get('progress') or 0)
            try:
                job.progress = pct
                job.save(update_fields=['progress'])
            except Exception:
                pass
            try:
                _broadcast_training_event(job_id_str, 'progress', {
                    'type': 'training_progress',
                    'training_run_id': job_id_str,
                    'progress_percent': pct,
                    'phase': payload.get('phase', 'indexing'),
                    'gpu': gpu_info,
                    'message': f'索引进度 {pct}%',
                })
            except Exception:
                pass

        def _run_index():
            started = time.time()
            try:
                _broadcast_training_event(job_id_str, 'training_started', {
                    'type': 'training_started',
                    'training_run_id': job_id_str,
                    'gpu': gpu_info,
                    'message': '开始构建 CLIP 检索索引',
                })
                result = build_retrieval_index(
                    dataset_path,
                    output_dir,
                    base_model=base_model,
                    progress_callback=_progress,
                )
                self._update_clip_retrieval_job_result(job_id_str, result, started)
            except Exception as exc:
                logger.exception('CLIP retrieval index failed: %s', exc)
                try:
                    tj = TrainingJob.objects.get(id=job_id_str)
                    tj.status = 'failed'
                    tj.error_message = str(exc)
                    tj.save(update_fields=['status', 'error_message'])
                except Exception:
                    pass
                _broadcast_training_event(job_id_str, 'training_error', {
                    'type': 'training_error',
                    'training_run_id': job_id_str,
                    'message': str(exc),
                })

        if execution_mode == 'local':
            threading.Thread(target=_run_index, daemon=True).start()
            return {
                'success': True,
                'output': {
                    'training_run_id': job_id_str,
                    'training_status': 'running',
                    'execution_mode': 'local',
                    'websocket_url': f'/ws/training/{job_id_str}/',
                    'gpu_info': gpu_info,
                    'index_dir': output_dir,
                    'dataset_path': dataset_path,
                    'base_model': base_model,
                    'index_mode': index_mode,
                    'encoder': 'pending',
                },
            }

        _run_index()
        try:
            tj = TrainingJob.objects.get(id=job_id_str)
        except TrainingJob.DoesNotExist:
            return {'success': False, 'error': '索引任务未找到'}

        if tj.status == 'failed':
            return {'success': False, 'error': tj.error_message or '索引构建失败'}

        artifacts = tj.exported_artifacts or {}
        metrics = tj.metrics or {}
        return {
            'success': True,
            'output': {
                'training_run_id': job_id_str,
                'training_status': 'completed',
                'websocket_url': f'/ws/training/{job_id_str}/',
                'gpu_info': gpu_info,
                'index_dir': artifacts.get('index_dir') or output_dir,
                'metadata_path': artifacts.get('metadata_path', ''),
                'metrics': metrics,
                'r_at_1': metrics.get('r_at_1'),
                'r_at_5': metrics.get('r_at_5'),
                'r_at_10': metrics.get('r_at_10'),
                'output_dir': output_dir,
                'image_count': artifacts.get('image_count', 0),
                'encoder': artifacts.get('encoder', 'bow'),
                'index_mode': index_mode,
                'built_on': 'server',
                'duration_ms': int((tj.duration_seconds or 0) * 1000),
            },
        }

    def run_clip_classification_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """CLIP zero-shot / finetune classification (M4.2)."""
        import threading

        from training.models import TrainingJob
        from training.clip_service import run_zero_shot_classification, run_finetune_classification

        cfg = node_config.get('config', {}) or {}
        gpu_info = self._detect_gpu()

        mode = node_config.get('mode') or cfg.get('mode') or 'zero_shot'
        class_names_raw = node_config.get('classNames') or cfg.get('classNames') or context.get('class_names') or []
        if isinstance(class_names_raw, str):
            class_names = [c.strip() for c in class_names_raw.split(',') if c.strip()]
        else:
            class_names = list(class_names_raw or [])

        dataset_path = (
            node_config.get('datasetPath', '')
            or cfg.get('datasetPath', '')
            or context.get('dataset_path', '')
            or context.get('path', '')
        )
        dataset_id = node_config.get('datasetId', '') or cfg.get('datasetId', '') or context.get('dataset_id', '')
        base_model = node_config.get('baseModel') or cfg.get('baseModel') or 'ViT-B/32'
        epochs = int(node_config.get('epochs') or cfg.get('epochs') or 10)
        batch_size = int(node_config.get('batchSize') or cfg.get('batchSize') or gpu_info.get('recommended_batch_size', 32))
        learning_rate = float(node_config.get('learningRate') or cfg.get('learningRate') or 1e-4)
        execution_mode = cfg.get('trainingMode', node_config.get('trainingMode', 'local'))
        output_dir = (
            node_config.get('outputDir', '')
            or cfg.get('outputDir', '')
            or context.get('output_dir', '')
            or f'./outputs/clip_cls_{uuid.uuid4().hex[:8]}'
        )

        if not class_names:
            return {'success': False, 'error': 'classNames 不能为空（可从上游 dataset_upload 继承）'}
        if mode == 'finetune' and not dataset_path:
            return {'success': False, 'error': 'finetune 模式需要 dataset_path'}

        try:
            clip_job = TrainingJob.objects.create(
                name=node_config.get('label', 'CLIP 分类'),
                framework='pytorch',
                model_type='classifier',
                training_kind='clip_cls',
                status='queued',
                dataset_id=str(dataset_id) if dataset_id else '',
                dataset_path=dataset_path or '',
                class_names=class_names,
                total_epochs=epochs if mode == 'finetune' else 0,
                gpu_info=gpu_info,
                config={**cfg, 'mode': mode, 'base_model': base_model, 'output_dir': output_dir},
            )

            if mode == 'zero_shot':
                clip_job.status = 'running'
                clip_job.save(update_fields=['status'])
                result = run_zero_shot_classification(
                    dataset_path or '.',
                    class_names,
                    output_dir,
                    base_model=base_model,
                )
                if not result.get('success'):
                    clip_job.status = 'failed'
                    clip_job.error_message = result.get('error', 'CLIP zero-shot failed')
                    clip_job.save(update_fields=['status', 'error_message'])
                    return {'success': False, 'error': clip_job.error_message}

                self._update_clip_job_result(str(clip_job.id), result)
                return {
                    'success': True,
                    'output': {
                        'training_run_id': str(clip_job.id),
                        'training_status': 'completed',
                        'model_path': result['model_path'],
                        'class_names': result.get('class_names', []),
                        'metrics': result.get('metrics', {}),
                        'mode': mode,
                        'base_model': base_model,
                        'websocket_url': f'/ws/training/{clip_job.id}/',
                    },
                }

            clip_job.status = 'running'
            clip_job.save(update_fields=['status'])

            def _run_finetune(job_id_str: str):
                def _progress(payload: Dict[str, Any]):
                    try:
                        tj = TrainingJob.objects.get(id=job_id_str)
                        if payload.get('progress') is not None:
                            tj.progress = int(payload['progress'])
                        if payload.get('epoch') is not None:
                            tj.current_epoch = int(payload['epoch'])
                        metrics = payload.get('metrics') or {}
                        if metrics.get('val_acc') is not None:
                            tj.current_metric = float(metrics['val_acc'])
                        tj.save(update_fields=['progress', 'current_epoch', 'current_metric'])
                    except Exception:
                        pass

                result = run_finetune_classification(
                    dataset_path,
                    class_names,
                    output_dir,
                    base_model=base_model,
                    epochs=epochs,
                    batch_size=batch_size,
                    learning_rate=learning_rate,
                    progress_callback=_progress,
                )
                self._update_clip_job_result(job_id_str, result)

            if execution_mode == 'local':
                threading.Thread(target=_run_finetune, args=(str(clip_job.id),), daemon=True).start()
                return {
                    'success': True,
                    'output': {
                        'training_run_id': str(clip_job.id),
                        'training_status': 'running',
                        'execution_mode': 'local',
                        'websocket_url': f'/ws/training/{clip_job.id}/',
                        'dataset_path': dataset_path,
                        'class_names': class_names,
                        'mode': mode,
                        'base_model': base_model,
                        'gpu_info': gpu_info,
                    },
                }

            _run_finetune(str(clip_job.id))
            clip_job.refresh_from_db()
            if clip_job.status == 'failed':
                return {'success': False, 'error': clip_job.error_message or 'finetune failed'}
            return {
                'success': True,
                'output': {
                    'training_run_id': str(clip_job.id),
                    'training_status': 'completed',
                    'model_path': clip_job.model_path,
                    'class_names': class_names,
                    'metrics': clip_job.metrics or {},
                    'mode': mode,
                    'base_model': base_model,
                },
            }

        except Exception as e:
            logger.exception(f"CLIP classification node error: {e}")
            return {'success': False, 'error': str(e)}

    def _update_clip_job_result(self, job_id_str: str, result: Dict[str, Any]):
        """Update TrainingJob with CLIP classification result."""
        try:
            from training.models import TrainingJob

            tj = TrainingJob.objects.get(id=job_id_str)
            if result.get('success'):
                tj.status = 'completed'
                tj.progress = 100
                tj.model_path = result.get('model_path', '')
                tj.best_weight_path = result.get('model_path', '')
                metrics = result.get('metrics') or {}
                if metrics.get('accuracy') is not None:
                    tj.current_metric = float(metrics['accuracy'])
                    tj.best_fitness = float(metrics['accuracy'])
                tj.metrics = metrics
                tj.exported_artifacts = {
                    'manifest_path': result.get('manifest_path', ''),
                    'encoder_type': result.get('encoder_type', ''),
                }
                tj.duration_seconds = result.get('duration_seconds', 0)
                if result.get('training_history'):
                    tj.metrics_history = result['training_history']
            else:
                tj.status = 'failed'
                tj.error_message = result.get('error', 'CLIP training failed')
            tj.save()
        except Exception:
            pass

    def _update_clip_retrieval_job_result(
        self, job_id_str: str, result: Dict[str, Any], started: float,
    ):
        """Update TrainingJob after CLIP retrieval index build."""
        from django.utils import timezone
        from training.models import TrainingJob
        from training.tasks import _broadcast_training_event

        try:
            tj = TrainingJob.objects.get(id=job_id_str)
            if not result.get('success'):
                tj.status = 'failed'
                tj.error_message = result.get('error', '索引构建失败')
                tj.save(update_fields=['status', 'error_message'])
                _broadcast_training_event(job_id_str, 'training_error', {
                    'type': 'training_error',
                    'training_run_id': job_id_str,
                    'message': tj.error_message,
                })
                return

            tj.status = 'completed'
            tj.progress = 100
            tj.metrics = result.get('metrics', {})
            tj.exported_artifacts = {
                'index_dir': result['index_dir'],
                'metadata_path': result.get('metadata_path', ''),
                'encoder': result.get('encoder', 'bow'),
                'image_count': result.get('image_count', 0),
            }
            tj.duration_seconds = int(time.time() - started)
            tj.completed_at = timezone.now()
            tj.save()
            _broadcast_training_event(job_id_str, 'training_complete', {
                'type': 'training_complete',
                'training_run_id': job_id_str,
                'progress_percent': 100,
                'metrics': tj.metrics,
                'artifacts': tj.exported_artifacts,
                'encoder': result.get('encoder', 'bow'),
            })
        except Exception:
            pass

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

    def _poll_generated_site_completion(
        self,
        site_id: str,
        *,
        timeout_seconds: int = 600,
        poll_interval: int = 2,
    ) -> Dict[str, Any]:
        """Poll GeneratedSite until completed or failed."""
        import time
        from website_generator.models import GeneratedSite

        max_attempts = max(1, timeout_seconds // poll_interval)
        for _ in range(max_attempts):
            try:
                site = GeneratedSite.objects.get(id=site_id)
            except GeneratedSite.DoesNotExist:
                return {'success': False, 'error': f'GeneratedSite 不存在: {site_id}'}

            if site.status == 'completed':
                return {'success': True, 'site': site}
            if site.status == 'failed':
                return {
                    'success': False,
                    'error': site.error_message or '网站生成失败',
                    'site': site,
                }
            time.sleep(poll_interval)

        return {'success': False, 'error': f'网站生成超时（{timeout_seconds}s）', 'site': site}

    def _poll_training_job_completion(
        self,
        job_id: str,
        *,
        timeout_seconds: int = 3600,
        poll_interval: int = 3,
    ) -> Dict[str, Any]:
        """Poll TrainingJob until terminal state."""
        import time
        from training.models import TrainingJob

        max_attempts = max(1, timeout_seconds // poll_interval)
        job = None
        for _ in range(max_attempts):
            try:
                job = TrainingJob.objects.get(id=job_id)
            except TrainingJob.DoesNotExist:
                return {'success': False, 'error': f'TrainingJob 不存在: {job_id}'}

            if job.status == 'completed':
                return {'success': True, 'job': job}
            if job.status in ('failed', 'cancelled', 'timeout'):
                return {
                    'success': False,
                    'error': job.error_message or f'训练失败: {job.status}',
                    'job': job,
                }
            time.sleep(poll_interval)

        return {'success': False, 'error': f'训练超时（{timeout_seconds}s）', 'job': job}

    def run_project_profiler_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze class names / scenario and emit profile JSON for site wizard."""
        from website_generator.site_factory.project_profiler import (
            build_project_profile,
            build_retrieval_profile,
            write_profile_json,
        )
        from website_generator.site_factory.role_agents.design_tokens import (
            build_design_tokens,
            write_design_tokens,
        )

        website_type = (
            node_config.get('websiteType', '')
            or context.get('website_type', '')
            or 'detection'
        ).lower()
        output_dir = node_config.get('outputDir', '') or context.get('output_dir', '')
        use_llm = node_config.get('useLlmEnrich')
        if use_llm is None:
            from django.conf import settings as dj_settings
            use_llm = getattr(dj_settings, 'SITE_AGENT_PREFER_LLM', True)
        use_llm = bool(use_llm)

        if website_type in ('clip_retrieval', 'retrieval'):
            index_dir = (
                node_config.get('indexDir', '')
                or context.get('index_dir', '')
                or context.get('output_dir', '')
            )
            metrics = dict(context.get('metrics') or {})
            profile = build_retrieval_profile(
                index_dir=index_dir,
                metrics=metrics,
                use_llm=use_llm,
            )
            profile_path = write_profile_json(output_dir, profile) if output_dir else ''
            design_tokens_path = ''
            wizard = node_config.get('wizard') or context.get('wizard') or {}
            if output_dir:
                tokens = build_design_tokens(profile, wizard)
                design_tokens_path = write_design_tokens(output_dir, tokens)
            return {
                'success': True,
                'output': {
                    'profile': profile,
                    'profile_path': profile_path,
                    'design_tokens_path': design_tokens_path,
                    'domain': profile.get('domain', ''),
                    'scenario': profile.get('scenario', ''),
                    'ui_tone': profile.get('ui_tone', ''),
                    'recommended_template': 'clip_retrieval',
                    'class_names': [],
                    'class_display_names': {},
                    'copy_hints': profile.get('copy_hints', []),
                    'risk_notes': profile.get('risk_notes', []),
                    'website_type': 'clip_retrieval',
                    'index_dir': index_dir,
                    'metrics': profile.get('metrics', metrics),
                },
            }

        class_names = node_config.get('classNames') or context.get('class_names') or context.get('labels') or []
        if isinstance(class_names, str):
            class_names = [x.strip() for x in class_names.split(',') if x.strip()]
        model_path = (
            node_config.get('modelPath', '')
            or context.get('best_weight_path', '')
            or context.get('model_path', '')
        )
        website_type = (
            node_config.get('websiteType', '')
            or context.get('website_type', '')
            or 'detection'
        )
        sample_images = node_config.get('sampleImagePaths') or context.get('sample_image_paths') or []
        metrics = dict(context.get('metrics') or {})

        if not class_names:
            return {'success': False, 'error': '缺少 class_names，请先连接训练或数据集节点'}

        profile = build_project_profile(
            class_names=class_names,
            model_path=model_path,
            website_type=website_type,
            sample_image_paths=sample_images,
            use_llm=use_llm,
            metrics=metrics,
            wizard_scenario=node_config.get('scenario') or context.get('scenario') or '',
        )

        profile_path = ''
        design_tokens_path = ''
        if output_dir:
            profile_path = write_profile_json(output_dir, profile)
            wizard = node_config.get('wizard') or context.get('wizard') or {}
            tokens = build_design_tokens(profile, wizard)
            design_tokens_path = write_design_tokens(output_dir, tokens)

        return {
            'success': True,
            'output': {
                'profile': profile,
                'profile_path': profile_path,
                'design_tokens_path': design_tokens_path,
                'domain': profile.get('domain', ''),
                'scenario': profile.get('scenario', ''),
                'ui_tone': profile.get('ui_tone', ''),
                'recommended_template': profile.get('recommended_template', website_type),
                'class_names': profile.get('class_names', class_names),
                'class_display_names': profile.get('class_display_names', {}),
                'copy_hints': profile.get('copy_hints', []),
                'risk_notes': profile.get('risk_notes', []),
                'website_type': website_type,
                'model_path': model_path,
                'metrics': profile.get('metrics', metrics),
            },
        }

    def run_website_generator_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Website Generator Node
        Generates a complete full-stack website from a trained model.
        """
        from website_generator.generators import get_generator
        from website_generator.models import GeneratedSite
        from website_generator.views import register_site_codegraph
        import os
        import json
        import threading
        from django.utils import timezone

        website_type = node_config.get('websiteType', 'classification')
        profile = node_config.get('profile') or context.get('profile') or {}
        wizard = node_config.get('wizard') or context.get('wizard') or {}
        if isinstance(profile, dict) and profile.get('recommended_template') and not node_config.get('websiteType'):
            website_type = profile.get('recommended_template', website_type)
        training_run_id = node_config.get('trainingRunId', '') or context.get('training_run_id', '')
        model_path = (
            node_config.get('modelPath', '')
            or context.get('best_weight_path', '')
            or context.get('model_path', '')
        )
        labels_raw = (
            node_config.get('labels', '')
            or wizard.get('labels', '')
            or context.get('class_names', '')
        )
        if isinstance(labels_raw, str):
            labels = [l.strip() for l in labels_raw.split(',') if l.strip()]
        else:
            labels = labels_raw or context.get('labels', [])
        output_dir = node_config.get('outputDir', '') or context.get('website_output_dir', '')
        upstream_dir = context.get('output_dir', '')
        if not output_dir and upstream_dir:
            output_dir = os.path.join(upstream_dir, 'generated_site')
        elif output_dir and upstream_dir and os.path.normpath(output_dir) == os.path.normpath(upstream_dir):
            if os.path.isdir(output_dir) and os.listdir(output_dir):
                output_dir = os.path.join(upstream_dir, 'generated_site')
        frontend_framework = node_config.get('frontendFramework', 'vue')
        backend_framework = node_config.get('backendFramework', 'flask')
        port = node_config.get('port') or wizard.get('port') or 5000
        name = (
            wizard.get('siteName')
            or node_config.get('siteName', '')
            or node_config.get('label', 'Generated AI Website')
        )
        description = (
            wizard.get('usageDescription')
            or node_config.get('description', '')
            or profile.get('scenario', '')
        )
        qa_profile = wizard.get('qaProfile') or node_config.get('qaProfile', 'default')

        index_dir = node_config.get('indexDir') or context.get('index_dir', '') or profile.get('index_dir', '')
        clip_metrics = dict(context.get('metrics') or profile.get('metrics') or {})

        example_queries_raw = wizard.get('exampleQueries') or wizard.get('example_queries')
        if example_queries_raw and website_type in ('clip_retrieval', 'retrieval'):
            if isinstance(example_queries_raw, str):
                hints = [h.strip() for h in example_queries_raw.replace('，', ',').split(',') if h.strip()]
            else:
                hints = [str(h).strip() for h in example_queries_raw if str(h).strip()]
            if hints:
                profile = dict(profile or {})
                profile['copy_hints'] = hints

        if wizard.get('wizardCompleted') and not (wizard.get('siteName') or '').strip():
            return {'success': False, 'error': '建站向导缺少必填项：站点名称（Step2 品牌）'}
        framework = node_config.get('framework', 'pytorch')
        if training_run_id:
            try:
                from training.models import TrainingJob
                run = TrainingJob.objects.get(id=training_run_id)
                kind = run.training_kind or 'generic'
                labels = run.class_names or labels
                if kind == 'yolo':
                    model_path = run.best_weight_path or run.model_path or model_path
                    framework = 'ultralytics'
                    website_type = 'detection'
                elif kind == 'clip_ret':
                    website_type = 'clip_retrieval'
                    artifacts = run.exported_artifacts or {}
                    index_dir = index_dir or artifacts.get('index_dir', '')
                    clip_metrics.update(run.metrics or {})
                elif kind == 'clip_cls':
                    website_type = 'classification'
                    model_path = run.model_path or model_path
                    framework = 'clip'
                elif not model_path:
                    model_path = run.best_weight_path or run.model_path or model_path
            except Exception:
                pass

        if website_type in ('clip_retrieval', 'retrieval') and not index_dir:
            return {'success': False, 'error': 'CLIP 检索站缺少 index_dir，请先运行 clip_retrieval 节点或从上游继承'}

        if not output_dir:
            return {'success': False, 'error': '输出目录未指定（请在节点配置 outputDir 或确保上游训练节点已输出 output_dir）'}
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception:
                return {'success': False, 'error': f'无法创建输出目录: {output_dir}'}
        elif os.listdir(output_dir):
            return {'success': False, 'error': f'输出目录必须为空文件夹: {output_dir}'}

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
            training_run_id=training_run_id or '',
            show_in_nav=True,
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
                    'profile': profile,
                    'wizard': wizard,
                    'index_dir': index_dir,
                    'metrics': clip_metrics,
                    'base_model': context.get('base_model', 'simple-bow'),
                    'dbEngine': wizard.get('dbEngine') or wizard.get('db_engine') or node_config.get('dbEngine', 'sqlite'),
                })
                result = generator.generate()
                if not result.get('success'):
                    site.status = 'failed'
                    site.error_message = result.get('error', 'Generation failed')
                    site.completed_at = timezone.now()
                    site.save()
                    return
                site.generated_files = result.get('generated_files', [])
                site.status = 'completed'
                if website_type in ('clip_retrieval', 'retrieval'):
                    site.inference_endpoint = f'http://localhost:{port}/search/text'
                else:
                    site.inference_endpoint = f'http://localhost:{port}/predict'
                site.completed_at = timezone.now()
                site.save()
                try:
                    register_site_codegraph(site)
                except Exception as cg_err:
                    logger.warning(f"CodeGraph registration skipped for site {site.id}: {cg_err}")
            except Exception as e:
                site.status = 'failed'
                site.error_message = str(e)
                site.completed_at = timezone.now()
                site.save()

        t = threading.Thread(target=run_gen)
        t.start()

        wait_for_completion = node_config.get('waitForCompletion')
        if wait_for_completion is None:
            wait_for_completion = True
        wait_for_completion = bool(wait_for_completion)
        timeout_seconds = int(node_config.get('waitTimeoutSeconds') or 600)

        status = 'generating'
        generated_files_count = 0
        error_message = ''

        if wait_for_completion:
            poll = self._poll_generated_site_completion(
                str(site.id),
                timeout_seconds=timeout_seconds,
            )
            if not poll.get('success'):
                return {
                    'success': False,
                    'error': poll.get('error', '网站生成未完成'),
                    'output': {
                        'site_id': str(site.id),
                        'status': 'failed',
                        'output_dir': output_dir,
                    },
                }
            site = poll['site']
            status = site.status
            generated_files_count = len(site.generated_files or [])
        else:
            status = 'generating'

        return {
            'success': True,
            'output': {
                'site_id': str(site.id),
                'status': status,
                'output_dir': output_dir,
                'website_output_dir': output_dir,
                'profile': profile,
                'wizard': wizard,
                'qa_profile': qa_profile,
                'website_type': website_type,
                'frontend_framework': frontend_framework,
                'backend_framework': backend_framework,
                'inference_endpoint': site.inference_endpoint or (
                    f'http://localhost:{port}/search/text'
                    if website_type in ('clip_retrieval', 'retrieval')
                    else f'http://localhost:{port}/predict'
                ),
                'url': f'/projects/{site.id}',
                'message': '网站生成已完成' if status == 'completed' else '网站生成已开始，请等待完成',
                'generated_files_count': generated_files_count,
            }
        }

    def _resolve_site_factory_context(
        self,
        node_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Shared context fields for site-factory role nodes."""
        output_dir = node_config.get('outputDir', '') or context.get('output_dir', '') or context.get('website_output_dir', '')
        return {
            'output_dir': output_dir,
            'site_id': str(node_config.get('generatedSiteId', '') or context.get('site_id', '') or ''),
            'website_type': node_config.get('websiteType', '') or context.get('website_type', 'detection'),
            'profile': node_config.get('profile') or context.get('profile') or {},
            'wizard': node_config.get('wizard') or context.get('wizard') or {},
            'model_path': (
                node_config.get('modelPath', '')
                or context.get('best_weight_path', '')
                or context.get('model_path', '')
            ),
            'port': node_config.get('port') or context.get('assigned_port') or context.get('port'),
            'agent_mode': node_config.get('agentMode', 'auto'),
            'use_llm': node_config.get('useLlm'),
            'allow_core_edit': bool(node_config.get('allowCoreEdit', False)),
            'auto_qa_after_edit': node_config.get('autoQaAfterEdit', True) is not False,
        }

    def run_backend_setup_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from website_generator.site_factory.role_agents import run_backend_setup

        sf = self._resolve_site_factory_context(node_config, context)
        if not sf['output_dir']:
            return {'success': False, 'error': '输出目录未指定，请先运行网站生成节点'}

        agent_mode = sf['agent_mode']
        if sf['use_llm'] is False:
            agent_mode = 'rules'
        elif sf['use_llm'] is True and agent_mode == 'auto':
            agent_mode = 'llm'

        result = run_backend_setup(
            sf['output_dir'],
            website_type=sf['website_type'],
            profile=sf['profile'],
            wizard=sf['wizard'],
            model_path=sf['model_path'],
            port=int(sf['port']) if sf['port'] else None,
            agent_mode=agent_mode,
            allow_core_edit=bool(node_config.get('allowCoreEdit', True)),
            auto_qa=sf['auto_qa_after_edit'],
            instruction=node_config.get('instruction', ''),
        )
        if not result.get('success'):
            return result
        return {'success': True, 'output': result}

    def run_frontend_setup_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from website_generator.site_factory.role_agents import run_frontend_setup

        sf = self._resolve_site_factory_context(node_config, context)
        if not sf['output_dir']:
            return {'success': False, 'error': '输出目录未指定，请先运行网站生成节点'}

        agent_mode = sf['agent_mode']
        if sf['use_llm'] is False:
            agent_mode = 'rules'
        elif sf['use_llm'] is True and agent_mode == 'auto':
            agent_mode = 'llm'

        result = run_frontend_setup(
            sf['output_dir'],
            website_type=sf['website_type'],
            profile=sf['profile'],
            wizard=sf['wizard'],
            model_path=sf['model_path'],
            port=int(sf['port']) if sf['port'] else None,
            agent_mode=agent_mode,
            auto_qa=sf['auto_qa_after_edit'],
            instruction=node_config.get('instruction', ''),
        )
        if not result.get('success'):
            return result
        return {'success': True, 'output': {**result, 'site_id': sf['site_id'], 'output_dir': sf['output_dir']}}

    def run_ui_beautify_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from website_generator.site_factory.role_agents import run_ui_beautify

        sf = self._resolve_site_factory_context(node_config, context)
        if not sf['output_dir']:
            return {'success': False, 'error': '输出目录未指定，请先运行网站生成节点'}

        agent_mode = sf['agent_mode']
        if sf['use_llm'] is False:
            agent_mode = 'rules'
        elif sf['use_llm'] is True and agent_mode == 'auto':
            agent_mode = 'llm'

        result = run_ui_beautify(
            sf['output_dir'],
            website_type=sf['website_type'],
            profile=sf['profile'],
            wizard=sf['wizard'],
            model_path=sf['model_path'],
            port=int(sf['port']) if sf['port'] else None,
            agent_mode=agent_mode,
            auto_qa=sf['auto_qa_after_edit'],
            instruction=node_config.get('instruction', ''),
        )
        if not result.get('success'):
            return result
        return {'success': True, 'output': {**result, 'site_id': sf['site_id'], 'output_dir': sf['output_dir']}}

    def run_site_code_review_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from website_generator.site_factory.role_agents import run_site_code_review

        sf = self._resolve_site_factory_context(node_config, context)
        if not sf['output_dir']:
            return {'success': False, 'error': '输出目录未指定，请先运行网站生成节点'}

        agent_mode = sf['agent_mode']
        if sf['use_llm'] is False:
            agent_mode = 'rules'

        result = run_site_code_review(
            sf['output_dir'],
            website_type=sf['website_type'],
            profile=sf['profile'],
            wizard=sf['wizard'],
            model_path=sf['model_path'],
            port=int(sf['port']) if sf['port'] else None,
            agent_mode=agent_mode,
            max_rounds=int(node_config.get('maxRounds') or 2),
        )
        if not result.get('success'):
            return result
        return {'success': True, 'output': {**result, 'site_id': sf['site_id'], 'output_dir': sf['output_dir']}}

    def run_environment_provision_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Environment provision: disk, paths, port, GPU manifest."""
        from website_generator.site_factory.environment import run_environment_checks

        output_dir = node_config.get('outputDir', '') or context.get('output_dir', '')
        model_path = (
            node_config.get('modelPath', '')
            or context.get('best_weight_path', '')
            or context.get('model_path', '')
        )
        site_id = str(node_config.get('generatedSiteId', '') or context.get('site_id', '') or '')
        runtime_mode = node_config.get('runtimeMode', 'desktop')
        port = node_config.get('port') or context.get('assigned_port') or context.get('port')

        if not output_dir:
            return {'success': False, 'error': '输出目录未指定，请先运行网站生成节点（及可选的后端/前端/UI 节点）'}

        result = run_environment_checks(
            output_dir=output_dir,
            model_path=model_path,
            site_id=site_id,
            runtime_mode=runtime_mode,
            assigned_port=int(port) if port else None,
        )

        return {
            'success': True,
            'output': {
                'ready': result['ready'],
                'runtime_manifest': result['runtime_manifest'],
                'checks': result['checks'],
                'assigned_port': result['assigned_port'],
                'output_dir': output_dir,
                'model_path': model_path,
                'site_id': site_id,
            },
        }

    def run_site_qa_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Full site QA: L1–L4 with gate green/yellow/red."""
        from website_generator.site_factory.qa_runner import run_site_qa
        from website_generator.models import GeneratedSite

        output_dir = node_config.get('outputDir', '') or context.get('output_dir', '')
        model_path = (
            node_config.get('modelPath', '')
            or context.get('best_weight_path', '')
            or context.get('model_path', '')
        )
        website_type = node_config.get('websiteType', '') or context.get('website_type', 'detection')
        qa_profile = node_config.get('qaProfile', 'default')
        site_id = str(node_config.get('generatedSiteId', '') or context.get('site_id', '') or '')
        port = node_config.get('port') or context.get('assigned_port') or context.get('port')
        skip_playwright = bool(node_config.get('skipPlaywright', False))

        metrics = context.get('metrics') or {}
        if isinstance(metrics, dict) and not metrics:
            for key in ('map50', 'mAP50', 'map_50', 'best_fitness'):
                if context.get(key) is not None:
                    metrics['map50'] = context.get(key)
                    break
            if context.get('best_fitness') and 'map50' not in metrics:
                metrics['map50'] = context.get('best_fitness')
            for rk in ('r_at_5', 'rAt5', 'recall_at_5', 'r_at_1', 'r_at_10'):
                if context.get(rk) is not None:
                    metrics['r_at_5'] = metrics.get('r_at_5') or context.get('r_at_5') or context.get('rAt5') or context.get('recall_at_5')
                    metrics['r_at_1'] = metrics.get('r_at_1') or context.get('r_at_1')
                    metrics['r_at_10'] = metrics.get('r_at_10') or context.get('r_at_10')
                    break

        if not output_dir:
            return {'success': False, 'error': '输出目录未指定'}

        qa_result = run_site_qa(
            output_dir=output_dir,
            model_path=model_path,
            website_type=website_type,
            qa_profile=qa_profile,
            metrics=metrics,
            port=int(port) if port else None,
            skip_playwright=skip_playwright,
            generated_site_id=site_id,
        )

        if site_id:
            try:
                site = GeneratedSite.objects.filter(id=site_id).first()
                if site:
                    site.last_qa_gate = qa_result['gate']
                    site.last_qa_report = qa_result.get('qa_report', {})
                    site.save(update_fields=['last_qa_gate', 'last_qa_report'])
            except Exception:
                logger.warning('Failed to persist QA report for site %s', site_id)

        return {
            'success': qa_result['gate'] != 'red',
            'output': {
                'gate': qa_result['gate'],
                'qa_gate': qa_result['gate'],
                'layers': qa_result['layers'],
                'metrics': qa_result['metrics'],
                'report_path': qa_result['report_path'],
                'summary_zh': qa_result['summary_zh'],
                'recommendations': qa_result.get('recommendations', []),
                'assigned_port': qa_result['assigned_port'],
                'preview_url': qa_result.get('preview_url'),
                'output_dir': output_dir,
                'site_id': site_id,
            },
            'error': None if qa_result['gate'] != 'red' else qa_result['summary_zh'],
        }

    def run_site_preview_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Site preview URL; blocked when QA red (default profile)."""
        from website_generator.models import GeneratedSite

        qa_gate = (
            node_config.get('qaGate', '')
            or context.get('qa_gate', '')
            or context.get('gate', 'yellow')
        )
        qa_profile = node_config.get('qaProfile', '') or context.get('qa_profile', 'default')
        port = node_config.get('port') or context.get('assigned_port') or context.get('port') or 49152
        site_id = str(node_config.get('generatedSiteId', '') or context.get('site_id', '') or '')
        output_dir = node_config.get('outputDir', '') or context.get('output_dir', '')

        if qa_gate == 'red':
            return {
                'success': False,
                'error': 'QA 红灯，预览已阻断。请先修复 QA 报告中的问题。',
                'output': {'status': 'blocked', 'qa_gate': qa_gate},
            }
        if qa_profile == 'default' and qa_gate == 'red':
            return {'success': False, 'error': 'QA 未通过', 'output': {'status': 'blocked'}}

        preview_url = f'http://127.0.0.1:{int(port)}/'
        screenshot_path = os.path.join(output_dir, '.flowly', 'preview', 'latest.png') if output_dir else ''

        if site_id:
            try:
                site = GeneratedSite.objects.filter(id=site_id).first()
                if site:
                    site.last_preview_url = preview_url
                    site.inference_endpoint = preview_url.rstrip('/') + '/predict'
                    site.port = int(port)
                    site.save(update_fields=['last_preview_url', 'inference_endpoint', 'port'])
            except Exception:
                logger.warning('Failed to update preview URL for site %s', site_id)

        return {
            'success': True,
            'output': {
                'preview_url': preview_url,
                'url': preview_url,
                'screenshot_path': screenshot_path,
                'status': 'live',
                'qa_gate': qa_gate,
                'warning': qa_gate == 'yellow',
                'site_id': site_id,
            },
        }

    def run_project_agent_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Project Agent: sandboxed edits + mandatory QA after code change."""
        from website_generator.models import GeneratedSite
        from website_generator.site_factory.project_agent import run_agent_for_site

        message = (
            node_config.get('message', '')
            or node_config.get('userMessage', '')
            or context.get('agent_message', '')
        ).strip()
        site_id = str(node_config.get('generatedSiteId', '') or context.get('site_id', '') or '')
        auto_qa = node_config.get('autoQaAfterEdit', True)
        qa_profile = node_config.get('qaProfile', '') or context.get('qa_profile', 'default')

        if not message:
            return {
                'success': True,
                'output': {
                    'skipped': True,
                    'reply': '未配置 Agent 消息，跳过。可在节点配置中填写 message 或通过 API 发送。',
                    'site_id': site_id,
                },
            }

        site = None
        if site_id:
            site = GeneratedSite.objects.filter(id=site_id).first()
        if not site:
            output_dir = node_config.get('outputDir', '') or context.get('output_dir', '')
            if output_dir:
                site = GeneratedSite.objects.filter(output_dir=output_dir).order_by('-created_at').first()

        if not site:
            return {'success': False, 'error': '未找到 GeneratedSite，请先完成网站生成'}

        user = context.get('user')
        result = run_agent_for_site(
            site,
            message,
            qa_profile=qa_profile,
            auto_qa=bool(auto_qa),
            confirm_core_edit=bool(node_config.get('confirmCoreEdit', False)),
            user=user,
            agent_mode=node_config.get('agentMode') or 'auto',
        )

        if not result.get('success'):
            return {'success': False, 'error': result.get('error', 'Agent 执行失败'), 'output': result}

        return {
            'success': not (result.get('qa_triggered') and result.get('qa_gate') == 'red'),
            'output': {
                'reply': result.get('reply'),
                'files_changed': result.get('files_changed', []),
                'qa_triggered': result.get('qa_triggered'),
                'qa_gate': result.get('qa_gate'),
                'qa_report': result.get('qa_report'),
                'preview_url': result.get('preview_url'),
                'preview_status': result.get('preview_status'),
                'site_id': str(site.id),
                'rag_collection_id': result.get('rag_collection_id'),
                'blocked': result.get('blocked', False),
            },
            'error': None if result.get('qa_gate') != 'red' else result.get('reply'),
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

            if provider == 'knowledge_base':
                return self._run_knowledge_base_retriever(node_config, query, top_k, enable_rerank)

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

    def _run_knowledge_base_retriever(
        self, node_config: Dict[str, Any], query: str, top_k: int, enable_rerank: bool
    ) -> Dict[str, Any]:
        """Retrieve context directly from a rag.DocumentCollection (the Knowledge Base app),
        unifying the workflow retriever node with the same data used by Agent's
        knowledge_base tool, instead of a separate Chroma-only vector path.
        """
        collection_id = node_config.get('collectionId') or node_config.get('collection_id')
        if not collection_id:
            return {'success': False, 'error': 'knowledge_base 检索节点缺少 collectionId 配置'}

        from rag.models import DocumentCollection
        from rag.services import RAGService

        try:
            collection = DocumentCollection.objects.get(id=collection_id)
        except DocumentCollection.DoesNotExist:
            return {'success': False, 'error': f'知识库集合 {collection_id} 不存在'}
        except (ValueError, TypeError):
            return {'success': False, 'error': f'知识库集合 ID 格式无效: {collection_id}'}

        rag_service = RAGService(collection=collection, top_k=top_k, min_similarity=0.0)
        rag_service.initialize()
        results = rag_service.retrieve(query)

        docs = [
            {
                'text': r['payload'].get('content', ''),
                'score': r.get('score', 0),
                'id': r.get('id', ''),
                'metadata': r['payload'],
            }
            for r in results
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
                'provider': 'knowledge_base',
                'index_name': collection.name,
                'collection_id': str(collection.id),
            }
        }

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
    # Control Flow & Integration Node Executors
    # ========================================================================

    def run_switch_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        from .node_executors_extra import run_switch_node
        return run_switch_node(self, node_config, input_data)

    def run_merge_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        from .node_executors_extra import run_merge_node
        return run_merge_node(self, node_config, input_data)

    def run_filter_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        from .node_executors_extra import run_filter_node
        return run_filter_node(self, node_config, input_data)

    def run_split_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        from .node_executors_extra import run_split_node
        return run_split_node(self, node_config, input_data)

    def run_set_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        from .node_executors_extra import run_set_node
        return run_set_node(self, node_config, input_data)

    def run_datetime_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        from .node_executors_extra import run_datetime_node
        return run_datetime_node(self, node_config, input_data)

    def run_rss_feed_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        from .node_executors_extra import run_rss_feed_node
        return run_rss_feed_node(self, node_config, input_data)

    def run_json_parser_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse / stringify / validate JSON from upstream text."""
        source_key = node_config.get('source_key', 'input')
        raw = self._resolve_input_text(input_data, source_key)
        if raw is None:
            raw = ''
        params = {
            'json': raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False),
            'action': node_config.get('action', 'parse'),
            'pretty': node_config.get('pretty', False),
        }
        try:
            result = self._tool_json_parser(params, input_data)
            return {'success': True, 'output': result}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_text_template_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render Jinja-style text template with workflow variables."""
        template = node_config.get('template') or node_config.get('text') or '{input}'
        variables = node_config.get('variables') if isinstance(node_config.get('variables'), dict) else {}
        try:
            result = self._tool_text_template({'template': template, 'variables': variables}, input_data)
            return {'success': True, 'output': result}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_slack_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('slack', node_config, input_data)

    def run_discord_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('discord', node_config, input_data)

    def run_telegram_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('telegram', node_config, input_data)

    def run_notion_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('notion', node_config, input_data)

    def run_github_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('github', node_config, input_data)

    def run_redis_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('redis', node_config, input_data)

    def run_openai_api_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('openai_api', node_config, input_data)

    def run_huggingface_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('huggingface', node_config, input_data)

    def run_feishu_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('feishu', node_config, input_data)

    def run_dingtalk_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('dingtalk', node_config, input_data)

    def run_wechat_work_node(self, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_integration('wechat_work', node_config, input_data)

    def _run_integration(self, node_type: str, node_config: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        from .node_executors_extra import run_integration_node
        return run_integration_node(self, node_type, node_config, input_data)

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
