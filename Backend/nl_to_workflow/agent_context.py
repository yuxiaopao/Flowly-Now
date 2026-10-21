"""
Local agent context gathering for NL workflow generation.

Avoids LangChain Hub network pulls. Tools are invoked directly to enrich
the LLM generation prompt — reference only, never pasted as final graphs.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _safe_tool_call(fn, **kwargs) -> Optional[Any]:
    try:
        if hasattr(fn, 'invoke'):
            return fn.invoke(kwargs)
        return fn(**kwargs)
    except Exception as exc:
        logger.debug('agent tool %s failed: %s', getattr(fn, 'name', fn), exc)
        return None


def _parse_tool_json(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def gather_generation_context(
    description: str,
    *,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    limit: int = 3,
) -> Dict[str, Any]:
    """
    Run retrieval tools and return structured + textual context for generation.
    """
    if not getattr(settings, 'NL_WORKFLOW_USE_AGENT_CONTEXT', True):
        return {'text': '', 'templates': [], 'user_workflows': [], 'source': 'disabled'}

    try:
        from .agent import (
            get_nl_session_history,
            get_user_workflows,
            search_workflow_templates,
        )
    except Exception as exc:
        logger.warning('agent tools unavailable, skip context: %s', exc)
        return {'text': '', 'templates': [], 'user_workflows': [], 'source': 'import_error'}

    templates_raw = _safe_tool_call(
        search_workflow_templates,
        query=(description or '')[:500],
        category='',
        limit=limit,
    )
    templates = _parse_tool_json(templates_raw) or []
    if not isinstance(templates, list):
        templates = []

    user_workflows: List[Dict[str, Any]] = []
    if user_id:
        uw_raw = _safe_tool_call(
            get_user_workflows,
            user_id=str(user_id),
            limit=limit,
        )
        parsed = _parse_tool_json(uw_raw)
        if isinstance(parsed, list):
            user_workflows = parsed

    history_snippet = ''
    if session_id:
        hist_raw = _safe_tool_call(
            get_nl_session_history,
            session_id=str(session_id),
            limit=8,
        )
        hist = _parse_tool_json(hist_raw)
        if isinstance(hist, dict) and hist.get('messages'):
            lines = []
            for msg in hist['messages'][-6:]:
                role = msg.get('role') or 'user'
                content = (msg.get('content') or '')[:200]
                if content:
                    lines.append(f'{role}: {content}')
            history_snippet = '\n'.join(lines)

    # Soft RAG recommender (already best-effort)
    recommender_lines: List[str] = []
    try:
        from .recommender import TemplateRecommender

        recs = TemplateRecommender(user_id=user_id).recommend(description or '', limit=limit)
        for r in recs:
            recommender_lines.append(
                f'- {r.name} [{r.source}] score={r.relevance_score:.2f}: {(r.description or "")[:140]}'
            )
    except Exception as exc:
        logger.debug('recommender skip: %s', exc)

    text_parts: List[str] = [
        '【Agent 工具检索上下文 — 仅供启发，禁止整图复制】',
    ]
    if templates:
        text_parts.append('相似工作流模板：')
        for t in templates[:limit]:
            if isinstance(t, dict):
                text_parts.append(
                    f"- {t.get('name')} ({t.get('category') or 'general'}): "
                    f"{(t.get('description') or '')[:140]}"
                )
    if user_workflows:
        text_parts.append('用户历史工作流：')
        for w in user_workflows[:limit]:
            if isinstance(w, dict):
                text_parts.append(
                    f"- {w.get('name')}: {(w.get('description') or '')[:120]} "
                    f"(nodes={w.get('node_count')})"
                )
    if recommender_lines:
        text_parts.append('语义推荐：')
        text_parts.extend(recommender_lines)

    n8n_hits: List[Dict[str, Any]] = []
    try:
        from .n8n_corpus import format_corpus_reference, search_n8n_corpus

        n8n_block = format_corpus_reference(description or '', limit=limit)
        if n8n_block:
            text_parts.append(n8n_block)
        for entry, score in search_n8n_corpus(description or '', limit=limit):
            n8n_hits.append({
                'id': entry.id,
                'name': entry.clean_name,
                'category': entry.category,
                'score': round(score, 4),
                'node_type_sequence': entry.node_type_sequence,
                'quality_score': entry.quality_score,
            })
    except Exception as exc:
        logger.debug('n8n corpus skip: %s', exc)

    if history_snippet:
        text_parts.append('近期会话片段：')
        text_parts.append(history_snippet)

    text = '\n'.join(text_parts) if len(text_parts) > 1 else ''
    return {
        'text': text,
        'templates': templates,
        'user_workflows': user_workflows,
        'n8n_examples': n8n_hits,
        'history_snippet': history_snippet,
        'source': 'agent_tools',
    }


def validate_generated_workflow_payload(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Run agent validate tool on a workflow dict."""
    from .agent import validate_workflow_nodes

    raw = _safe_tool_call(
        validate_workflow_nodes,
        workflow_json=json.dumps(workflow, ensure_ascii=False),
    )
    parsed = _parse_tool_json(raw)
    if isinstance(parsed, dict):
        return parsed
    return {'valid': True, 'errors': [], 'warnings': []}
