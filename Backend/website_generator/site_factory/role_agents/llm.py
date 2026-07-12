"""Shared LLM helpers for role agents."""

from __future__ import annotations

import os
from typing import Optional


def llm_available() -> bool:
    try:
        from django.conf import settings
        if getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY'):
            return True
        if getattr(settings, 'SITE_AGENT_PREFER_LLM', True):
            from gateway.providers.registry import get_registry, register_default_providers
            registry = get_registry()
            if not registry.get_all():
                register_default_providers()
            if registry.get_all():
                return True
    except Exception:
        pass
    return bool(os.environ.get('OPENAI_API_KEY'))


def resolve_agent_model() -> str:
    try:
        from django.conf import settings
        model = getattr(settings, 'SITE_AGENT_MODEL', '') or getattr(settings, 'NL_WORKFLOW_MODEL', '')
        if model:
            return model
    except Exception:
        pass
    return 'gpt-4o-mini'


def invoke_role_llm(system: str, user: str, *, max_tokens: int = 12000) -> Optional[str]:
    try:
        from gateway.providers.registry import get_registry, register_default_providers

        model = resolve_agent_model()
        registry = get_registry()
        if not registry.get_all():
            register_default_providers()
        provider = None
        for name in registry.get_all():
            candidate = registry.get(name)
            if candidate and candidate.supports_model(model):
                provider = candidate
                break
        if not provider:
            provider = registry.get('openai') or registry.get('ollama')
        if provider:
            result = provider.chat(
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                model=model,
                temperature=0.2,
                max_tokens=max_tokens,
            )
            if isinstance(result, dict):
                return result.get('content') or result.get('text') or ''
            return str(result or '')
    except Exception:
        pass

    try:
        from langchain_openai import ChatOpenAI
        from django.conf import settings

        api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return None
        llm = ChatOpenAI(model=resolve_agent_model(), temperature=0.2, max_tokens=max_tokens)
        resp = llm.invoke([
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ])
        return getattr(resp, 'content', str(resp))
    except Exception:
        return None
