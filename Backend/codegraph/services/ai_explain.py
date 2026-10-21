"""
AI explanation for CodeGraph file nodes.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Simple process-local cache: key -> {mtime, result}
_EXPLAIN_CACHE: Dict[str, Dict[str, Any]] = {}
_MAX_CODE_CHARS = 14000


def _resolve_model() -> str:
    try:
        from django.conf import settings
        return (
            getattr(settings, 'CODEGRAPH_AI_MODEL', '')
            or getattr(settings, 'NL_WORKFLOW_MODEL', '')
            or getattr(settings, 'SITE_AGENT_MODEL', '')
            or 'gpt-4o-mini'
        )
    except Exception:
        return 'gpt-4o-mini'


def _invoke_llm(
    system: str,
    user: str,
    *,
    temperature: float = 0.25,
    max_tokens: int = 1200,
) -> Optional[str]:
    """Call configured LLM via gateway registry; fallback to ChatOpenAI."""
    model = _resolve_model()
    try:
        from gateway.providers.registry import get_registry, register_default_providers

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
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = ''
            if isinstance(result, dict):
                text = result.get('content') or ''
            elif hasattr(result, 'content'):
                text = getattr(result, 'content', '') or ''
            else:
                text = str(result or '')
            # Guard against accidental ProviderResponse repr leakage
            if text.startswith('ProviderResponse('):
                m = re.search(r"content=(['\"])(.*?)\1", text, flags=re.S)
                text = m.group(2) if m else ''
            return str(text).strip()
    except Exception as exc:
        logger.warning('CodeGraph AI registry call failed: %s', exc)

    try:
        from django.conf import settings
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        if not (getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')):
            return None
        llm = ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens)
        resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return (resp.content or '').strip()
    except Exception as exc:
        logger.warning('CodeGraph AI ChatOpenAI fallback failed: %s', exc)
        return None


def _heuristic_explain(path: str, name: str, content: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Offline fallback when LLM is unavailable."""
    ext = os.path.splitext(path)[1].lower()
    lines = content.splitlines()
    exports = []
    for line in lines[:200]:
        m = re.search(
            r'^\s*(?:export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+(\w+)'
            r'|def\s+(\w+)|class\s+(\w+)|function\s+(\w+))',
            line,
        )
        if m:
            exports.append(next(g for g in m.groups() if g))
        if len(exports) >= 8:
            break

    role_hints = []
    lower = (path + ' ' + content[:2000]).lower()
    if 'store' in lower or 'pinia' in lower or 'vuex' in lower:
        role_hints.append('状态管理')
    if 'router' in lower or 'route' in lower:
        role_hints.append('路由')
    if 'api' in lower or 'axios' in lower or 'fetch(' in lower:
        role_hints.append('接口请求')
    if 'component' in lower or ext == '.vue':
        role_hints.append('UI 组件')
    if 'util' in lower or 'helper' in lower:
        role_hints.append('工具函数')
    if 'model' in lower or 'schema' in lower:
        role_hints.append('数据模型')
    if not role_hints:
        role_hints.append('通用模块')

    summary = (
        f'「{name}」是项目中的{"/".join(role_hints)}文件'
        f'（{ext or "无扩展名"}，约 {len(lines)} 行）。'
        f'当前未配置可用 LLM，已基于路径与代码结构给出启发式说明。'
    )
    return {
        'summary': summary,
        'purpose': f"主要承担{'、'.join(role_hints)}相关职责。",
        'key_points': [
            f"路径：{path}",
            f"模块：{meta.get('module') or '未知'}",
            f"依赖出度：{meta.get('outdegree', 0)}，入度：{meta.get('indegree', 0)}",
            *( [f"可见符号：{', '.join(exports[:6])}"] if exports else [] ),
        ],
        'source': 'heuristic',
    }


def _parse_llm_sections(text: str) -> Dict[str, Any]:
    text = (text or '').strip()
    # Normalize escaped newlines from some providers
    text = text.replace('\\n', '\n')
    summary = text
    purpose = ''
    key_points = []

    numbered = re.findall(r'(?:^|\n)\s*\d+\)\s*(.+?)(?=(?:\n\s*\d+\)|\Z))', text, flags=re.S)
    if numbered:
        summary = numbered[0].strip()
        if len(numbered) > 1:
            purpose_line = numbered[1].strip()
            purpose_m = re.search(r'(?:用途|职责|作用)[:：]\s*(.+)', purpose_line, flags=re.S)
            purpose = (purpose_m.group(1) if purpose_m else purpose_line).strip()
        if len(numbered) > 2:
            key_points = re.findall(r'^\s*[-*•]\s+(.+)$', numbered[2], flags=re.M)

    if not purpose:
        purpose_m = re.search(r'(?:用途|职责|作用)[:：]\s*(.+)', text)
        if purpose_m:
            purpose = purpose_m.group(1).strip().split('\n')[0]

    if not key_points:
        key_points = re.findall(r'^\s*[-*•]\s+(.+)$', text, flags=re.M)

    key_points = [b.strip() for b in key_points[:12] if b.strip()]
    purpose = (purpose or '').split('\n')[0].strip()
    # Drop leading list markers accidentally captured into purpose
    purpose = re.sub(r'^\s*[-*•]\s*', '', purpose)
    # Keep summary readable but do not hard-cut mid-sentence for the UI scrollbar
    if len(summary) > 1200:
        cut = summary[:1200]
        # prefer breaking at sentence end
        for sep in ('。', '！', '？', '.', '\n'):
            idx = cut.rfind(sep)
            if idx > 400:
                cut = cut[: idx + 1]
                break
        summary = cut.rstrip() + ('…' if len(summary) > len(cut) else '')

    return {
        'summary': summary,
        'purpose': purpose or summary,
        'key_points': key_points,
        'source': 'llm',
    }


def explain_file_code(
    *,
    path: str,
    name: str,
    content: str,
    meta: Optional[Dict[str, Any]] = None,
    mtime: Optional[float] = None,
) -> Dict[str, Any]:
    """Explain what a source file does. Uses LLM when available."""
    meta = meta or {}
    cache_key = hashlib.sha1(f'{path}|{mtime or 0}|{len(content)}'.encode('utf-8')).hexdigest()
    cached = _EXPLAIN_CACHE.get(cache_key)
    if cached:
        return {**cached, 'cached': True}

    clipped = content if len(content) <= _MAX_CODE_CHARS else (
        content[:_MAX_CODE_CHARS] + '\n\n/* … truncated for analysis … */\n'
    )

    system = (
        '你是资深前端/全栈代码审阅助手。请用简洁中文解释源码文件「做什么」。'
        '不要复述整段代码，不要编造不存在的依赖。'
        '输出结构：\n'
        '1) 先用 2-4 句总结该文件职责\n'
        '2) 一行「用途：…」\n'
        '3) 用 3-6 条「- 」要点列出关键能力/导出/与周边关系'
    )
    user = (
        f'文件名：{name}\n'
        f'路径：{path}\n'
        f'模块：{meta.get("module") or "-"}\n'
        f'类型：{meta.get("type") or "-"}\n'
        f'入度/出度：{meta.get("indegree", 0)}/{meta.get("outdegree", 0)}\n'
        f'中心性：{meta.get("centrality", 0)}\n\n'
        f'代码：\n```\n{clipped}\n```'
    )

    raw = _invoke_llm(system, user)
    if raw:
        result = _parse_llm_sections(raw)
        result['raw'] = raw
    else:
        result = _heuristic_explain(path, name, content, meta)

    result['path'] = path
    result['name'] = name
    result['cached'] = False
    _EXPLAIN_CACHE[cache_key] = {k: v for k, v in result.items() if k != 'cached'}
    # Bound cache size
    if len(_EXPLAIN_CACHE) > 256:
        for key in list(_EXPLAIN_CACHE.keys())[:64]:
            _EXPLAIN_CACHE.pop(key, None)
    return result
