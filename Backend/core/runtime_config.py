"""
Runtime configuration exposed to the frontend and internal services.

Centralizes values that were previously duplicated across settings,
constants, and hardcoded frontend defaults.
"""
from __future__ import annotations

from typing import Any, Dict

from django.conf import settings

from config.constants import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_OLLAMA_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_TEMPERATURE,
    VECTOR_STORE_DEFAULT_HOST,
    VECTOR_STORE_DEFAULT_PORT,
    VECTOR_STORE_DEFAULT_PROTOCOL,
)


def resolve_default_chat_model() -> str:
    """Pick the default chat model based on configured providers."""
    api_key = (getattr(settings, 'OPENAI_API_KEY', None) or '').strip()
    ollama_model = getattr(settings, 'OLLAMA_MODEL', DEFAULT_OLLAMA_MODEL)
    if api_key:
        return getattr(settings, 'DEFAULT_LLM_MODEL', DEFAULT_LLM_MODEL) or ollama_model
    return ollama_model or DEFAULT_OLLAMA_MODEL


def resolve_default_embedding_model() -> str:
    """Pick the default embedding model based on configured providers."""
    api_key = (getattr(settings, 'OPENAI_API_KEY', None) or '').strip()
    if api_key:
        return getattr(settings, 'DEFAULT_EMBEDDING_MODEL', DEFAULT_EMBEDDING_MODEL)
    return getattr(settings, 'OLLAMA_EMBEDDING_MODEL', DEFAULT_OLLAMA_EMBEDDING_MODEL)


def get_public_api_base_url() -> str:
    """Backend origin used for webhooks, SSE, and API links in the UI."""
    explicit = (getattr(settings, 'PUBLIC_API_BASE_URL', None) or '').strip()
    if explicit:
        return explicit.rstrip('/')
    return 'http://127.0.0.1:8000'


def get_runtime_config() -> Dict[str, Any]:
    """Build the runtime section for public site config."""
    api_base = get_public_api_base_url()
    ws_url = (getattr(settings, 'PUBLIC_WS_URL', None) or '').strip()
    if not ws_url:
        ws_url = api_base.replace('https://', 'wss://').replace('http://', 'ws://')

    return {
        'api_base_url': api_base,
        'api_prefix': '/api/v1',
        'frontend_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:5200').rstrip('/'),
        'ws_url': ws_url,
        'llm': {
            'default_model': resolve_default_chat_model(),
            'nl_workflow_model': getattr(settings, 'NL_WORKFLOW_MODEL', DEFAULT_OLLAMA_MODEL),
            'default_temperature': float(getattr(settings, 'DEFAULT_TEMPERATURE', DEFAULT_TEMPERATURE)),
            'default_max_tokens': int(getattr(settings, 'DEFAULT_MAX_TOKENS', DEFAULT_MAX_TOKENS)),
        },
        'embedding': {
            'default_model': resolve_default_embedding_model(),
            'ollama_model': getattr(settings, 'OLLAMA_EMBEDDING_MODEL', DEFAULT_OLLAMA_EMBEDDING_MODEL),
        },
        'ollama': {
            'base_url': getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
            'chat_model': getattr(settings, 'OLLAMA_MODEL', DEFAULT_OLLAMA_MODEL),
        },
        'vector_store': {
            'default_host': VECTOR_STORE_DEFAULT_HOST,
            'default_port': VECTOR_STORE_DEFAULT_PORT,
            'default_protocol': VECTOR_STORE_DEFAULT_PROTOCOL,
        },
        'providers': {
            'openai_configured': bool((getattr(settings, 'OPENAI_API_KEY', None) or '').strip()),
            'ollama_configured': bool(getattr(settings, 'OLLAMA_BASE_URL', '')),
            'dashscope_configured': bool((getattr(settings, 'DASHSCOPE_API_KEY', None) or '').strip()),
        },
    }
