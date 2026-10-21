"""
Conversation compression helpers (no hard dependency on LangChain SummaryMemory APIs).
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = """请将以下工作流设计对话压缩为简洁中文摘要（不超过 400 字），保留：
- 用户最终需求与约束
- 已确认的关键参数（语言、模型、数据源、收件人等）
- 尚未确认的问题
不要输出 JSON，只输出摘要正文。

对话：
{transcript}
"""


def _normalize_role(role: str) -> str:
    r = (role or '').lower()
    if r in ('user', 'human'):
        return '用户'
    if r in ('assistant', 'ai'):
        return '助手'
    return role or '未知'


def format_messages_transcript(messages: List[Dict[str, Any]], max_chars: int = 6000) -> str:
    lines: List[str] = []
    for msg in messages or []:
        content = (msg.get('content') or '').strip()
        if not content:
            continue
        lines.append(f"{_normalize_role(msg.get('role'))}：{content}")
    text = '\n'.join(lines)
    if len(text) > max_chars:
        return text[-max_chars:]
    return text


def should_summarize(messages: List[Dict[str, Any]]) -> bool:
    threshold = int(getattr(settings, 'NL_CHAT_SUMMARY_THRESHOLD', 12))
    return len(messages or []) >= threshold


def summarize_messages(
    messages: List[Dict[str, Any]],
    call_llm: Optional[Callable[[List[Dict[str, str]]], Dict[str, Any]]] = None,
    existing_summary: str = '',
) -> str:
    """
    Compress long chat history. Falls back to heuristic truncation if LLM unavailable.
    """
    if not messages:
        return existing_summary or ''

    transcript = format_messages_transcript(messages)
    if not transcript:
        return existing_summary or ''

    if call_llm and getattr(settings, 'NL_CHAT_USE_SUMMARY', True):
        prompt = _SUMMARY_PROMPT.format(transcript=transcript)
        if existing_summary:
            prompt += f"\n\n已有摘要（请融合更新）：\n{existing_summary[:800]}"
        try:
            result = call_llm([{'role': 'user', 'content': prompt}])
            if not result.get('error'):
                content = (result.get('content') or '').strip()
                if content:
                    return content[:2000]
        except Exception as exc:
            logger.warning('conversation summarize LLM failed: %s', exc)

    # Heuristic fallback: keep first user ask + last N turns
    keep_tail = messages[-6:]
    head = next((m for m in messages if (m.get('role') in ('user', 'human'))), None)
    parts = []
    if existing_summary:
        parts.append(f'既往摘要：{existing_summary[:300]}')
    if head:
        parts.append(f"初始需求：{(head.get('content') or '')[:300]}")
    parts.append('近期对话：')
    parts.append(format_messages_transcript(keep_tail, max_chars=1500))
    return '\n'.join(parts)[:2000]


def compress_messages_for_generation(
    messages: List[Dict[str, Any]],
    user_message: str,
    *,
    call_llm: Optional[Callable] = None,
    existing_summary: str = '',
) -> Tuple[str, str]:
    """
    Returns (description_for_generate, updated_summary).
    """
    summary = existing_summary or ''
    if should_summarize(messages):
        summary = summarize_messages(messages, call_llm=call_llm, existing_summary=summary)

    parts: List[str] = []
    if summary:
        parts.append(f'【对话摘要】\n{summary}')
    # Always include last few raw turns for precision
    recent = (messages or [])[-4:]
    if recent:
        parts.append('【最近对话】\n' + format_messages_transcript(recent, max_chars=2000))
    parts.append(f'【当前用户】\n{(user_message or "").strip()}')
    parts.append('请综合以上信息，生成完整可执行的工作流 JSON。')
    return '\n\n'.join(parts), summary
