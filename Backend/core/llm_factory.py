"""
Shared LLM construction and invocation for RAG, workflows, and utilities.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

from config.constants import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    OLLAMA_CHAT_TIMEOUT,
    OLLAMA_MODEL_PREFIXES,
    OLLAMA_NUM_CTX,
)
from core.runtime_config import resolve_default_chat_model

logger = logging.getLogger(__name__)


def _is_ollama_model(model: str) -> bool:
    model_lower = (model or '').lower()
    return any(prefix in model_lower for prefix in OLLAMA_MODEL_PREFIXES)


def _is_ollama_endpoint(base_url: Optional[str]) -> bool:
    if not base_url:
        return False
    url = base_url.rstrip('/').lower()
    if 'ollama' in url or ':11434' in url:
        return True
    default_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
    return url == default_url.rstrip('/').lower()


def _resolve_provider(model: str, api_key: Optional[str], base_url: Optional[str]) -> str:
    if _is_ollama_endpoint(base_url) or _is_ollama_model(model):
        return 'ollama'
    if base_url and 'azure' in base_url.lower():
        return 'azure'
    if any(x in model.lower() for x in ['gpt-', 'chatgpt', 'o1-', 'o3-', 'o4-']):
        return 'openai'
    if any(x in model.lower() for x in ['claude', 'sonnet', 'haiku', 'opus']):
        return 'anthropic'
    if any(x in model.lower() for x in ['gemini', 'gemma']):
        return 'google'
    return 'ollama' if not api_key else 'openai'


def build_chat_llm(
    *,
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[float] = None,
):
    """Create a LangChain chat model using the same rules as AgentEngine."""
    from langchain_openai import AzureChatOpenAI, ChatOpenAI
    from langchain_ollama import ChatOllama

    resolved_model = model or resolve_default_chat_model()
    resolved_api_key = api_key if api_key is not None else getattr(settings, 'OPENAI_API_KEY', None)
    resolved_base_url = base_url if base_url is not None else getattr(settings, 'OPENAI_BASE_URL', None)
    provider = _resolve_provider(resolved_model, resolved_api_key, resolved_base_url)
    if base_url and not _is_ollama_endpoint(base_url):
        provider = 'azure' if 'azure' in base_url.lower() else 'openai'

    if provider == 'ollama':
        ollama_url = (
            resolved_base_url if _is_ollama_endpoint(resolved_base_url)
            else getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        )
        return ChatOllama(
            model=resolved_model,
            temperature=temperature,
            timeout=timeout or OLLAMA_CHAT_TIMEOUT,
            base_url=ollama_url.rstrip('/'),
            num_ctx=getattr(settings, 'OLLAMA_NUM_CTX', OLLAMA_NUM_CTX),
            client_kwargs={'trust_env': False, 'timeout': timeout or OLLAMA_CHAT_TIMEOUT},
        )

    if provider == 'azure':
        return AzureChatOpenAI(
            model=resolved_model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=resolved_api_key,
            azure_endpoint=resolved_base_url,
            api_version='2024-02-01',
            timeout=timeout or OLLAMA_CHAT_TIMEOUT,
        )

    model_kwargs: Dict[str, Any] = {
        'model': resolved_model,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'timeout': timeout or OLLAMA_CHAT_TIMEOUT,
    }
    if resolved_api_key:
        model_kwargs['api_key'] = resolved_api_key
    if resolved_base_url and resolved_base_url != 'https://api.openai.com/v1':
        model_kwargs['base_url'] = resolved_base_url
    return ChatOpenAI(**model_kwargs)


def invoke_chat_messages(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[float] = None,
) -> str:
    """Invoke an LLM with role/content dict messages and return text content."""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = build_chat_llm(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )
    langchain_messages = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        if role == 'system':
            langchain_messages.append(SystemMessage(content=content))
        else:
            langchain_messages.append(HumanMessage(content=content))

    response = llm.invoke(langchain_messages)
    return getattr(response, 'content', str(response))
