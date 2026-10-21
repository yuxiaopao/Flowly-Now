"""
AI-first intelligence helpers for NL workflow create / refine.

Templates and keyword rules are offline/weak fallbacks only — never the
primary path when an LLM is available.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from django.conf import settings

from .workflow_layout import auto_layout_workflow

logger = logging.getLogger(__name__)

VALID_INTENTS = frozenset({'create', 'modify', 'delete', 'chat', 'optimize', 'layout'})

EDITOR_ACTIONS = frozenset({
    'optimize',
    'layout',
    'add_language',
    'set_video_url',
    'config_check',
    'modify',
    'chat',
    'generate',
    'enrich_short_drama',
    'enrich_miao_embroidery',
    'enrich_cumcm',
})

_INTENT_CLASSIFY_PROMPT = """你是工作流助手的意图分类器。根据用户消息判断意图，只输出 JSON：
{{"intent":"create|modify|delete|chat|optimize|layout","subtype":"generic|video_translation|yolo_detection|emotion_detection|multimodal|web_scrape_email|mobile_page_email|qa_bot|translation|email_sending|data_processing|moderation|article_generation|customer_service|miao_embroidery|cumcm","confidence":0.0,"ready_to_generate":false,"rationale":"一句话"}}

规则：
- create：要新建工作流
- modify：改现有节点/配置/连线（含添加语言链、换模型）
- delete：删除节点或边
- optimize：优化/整理/完善工作流结构
- layout：只排布节点位置
- chat：讨论、提问、澄清需求
- ready_to_generate：信息是否已够生成完整工作流

用户消息：
{message}
"""

_EDITOR_PLAN_PROMPT = """你是工作流编辑规划器。根据用户请求和当前工作流摘要，决定要执行的动作。
只输出 JSON（不要 markdown）：
{{"action":"optimize|layout|add_language|set_video_url|config_check|modify|chat|generate|enrich_short_drama|enrich_miao_embroidery|enrich_cumcm","params":{{}},"message":"给用户的简短说明"}}

params 说明：
- add_language: {{"languages":["ja","ko"]}}
- set_video_url: {{"url":"https://..."}}
- enrich_short_drama: {{"shot_count":12}}  # 用户要1分钟/短剧/大制作/12镜时优先选这个
- enrich_miao_embroidery: {{"pattern_count":4,"series_count":6,"product_count":8}}  # 苗绣纹样识别/融合/产品矩阵
- enrich_cumcm: {{"subproblem_count":3}}  # CUMCM/数学建模竞赛完整流水线
- modify/optimize/layout/config_check/chat/generate: params 可为空对象

规则：
- 用户提到「1分钟」「短剧」「大制作」「12镜」「60秒」等，且当前已有剧情/图像/视频链路时，必须选 enrich_short_drama
- 用户提到「苗绣」「纹样识别」「纹样融合」「产品矩阵」「文创产品」时，必须选 enrich_miao_embroidery
- 用户提到「CUMCM」「数学建模」「建模竞赛」「国赛」「建模论文」「灵敏度分析」时，必须选 enrich_cumcm
- 不要用 modify 去改深层 prompt（容易空操作）

当前工作流摘要：
{workflow_summary}

用户请求：
{message}
"""

OPTIMIZE_LLM_INSTRUCTION = (
    "请优化以下工作流：去掉冗余节点、补全缺失连线、统一变量引用、"
    "补齐合理默认配置（不要改用户已明确填写的 provider/model），"
    "保持业务语义，返回完整工作流 JSON。"
)


def mark_offline_template(workflow: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Stamp a workflow as non-intelligent offline fallback."""
    if not isinstance(workflow, dict):
        return workflow
    workflow = copy.deepcopy(workflow)
    workflow['_generation_mode'] = 'offline_template'
    workflow['_intelligence_note'] = reason
    workflow['_is_intelligent'] = False
    return workflow


def mark_llm_workflow(workflow: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    if not isinstance(workflow, dict):
        return workflow
    workflow.setdefault('_generation_mode', 'llm')
    workflow['_is_intelligent'] = True
    workflow.pop('_intelligence_note', None)
    if model:
        workflow['_llm_model'] = model
    return workflow


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def classify_intent_with_llm(
    message: str,
    call_llm: Callable[[List[Dict[str, str]]], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Return structured intent from LLM, or None on failure."""
    prompt = _INTENT_CLASSIFY_PROMPT.format(message=(message or '').strip()[:2000])
    result = call_llm([{'role': 'user', 'content': prompt}])
    if result.get('error'):
        logger.info('LLM intent classify failed: %s', result.get('error'))
        return None
    parsed = extract_json_object(result.get('content') or '')
    if not parsed:
        return None
    intent = str(parsed.get('intent') or 'chat').lower().strip()
    if intent not in VALID_INTENTS:
        intent = 'chat'
    return {
        'intent': intent,
        'subtype': str(parsed.get('subtype') or 'generic'),
        'is_retry': False,
        'confidence': float(parsed.get('confidence') or 0.0),
        'ready_to_generate': bool(parsed.get('ready_to_generate')),
        'rationale': str(parsed.get('rationale') or ''),
        'source': 'llm',
    }


def plan_editor_action_with_llm(
    message: str,
    workflow: Dict[str, Any],
    call_llm: Callable[[List[Dict[str, str]]], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    summary = summarize_workflow(workflow)
    prompt = _EDITOR_PLAN_PROMPT.format(
        workflow_summary=summary[:3000],
        message=(message or '').strip()[:1500],
    )
    result = call_llm([{'role': 'user', 'content': prompt}])
    if result.get('error'):
        return None
    parsed = extract_json_object(result.get('content') or '')
    if not parsed:
        return None
    action = str(parsed.get('action') or 'chat').lower().strip()
    if action not in EDITOR_ACTIONS:
        action = 'chat'
    params = parsed.get('params') if isinstance(parsed.get('params'), dict) else {}
    return {
        'action': action,
        'params': params,
        'message': str(parsed.get('message') or ''),
        'source': 'llm',
    }


def summarize_workflow(workflow: Optional[Dict[str, Any]]) -> str:
    if not workflow:
        return '(空工作流)'
    nodes = workflow.get('nodes') or []
    edges = workflow.get('edges') or []
    lines = [
        f"名称: {workflow.get('name') or '未命名'}",
        f"节点数: {len(nodes)}, 连线数: {len(edges)}",
        f"生成模式: {workflow.get('_generation_mode') or 'unknown'}",
    ]
    for node in nodes[:40]:
        data = node.get('data') if isinstance(node.get('data'), dict) else {}
        ntype = node.get('type') or data.get('type') or '?'
        name = node.get('name') or data.get('label') or node.get('id')
        cfg = node.get('config') if isinstance(node.get('config'), dict) and node.get('config') else {}
        if not cfg:
            cfg = data.get('config') if isinstance(data.get('config'), dict) else {}
        hint = ''
        if ntype in ('subtitle_translate', 'segment_dubbing', 'lip_sync', 'subtitle_burn'):
            hint = f" lang={cfg.get('target_language') or cfg.get('language') or ''}"
        if ntype == 'video_upload':
            hint = f" url={(cfg.get('video_url') or cfg.get('url') or '')[:80]}"
        if ntype == 'loop':
            hint = f" max_iterations={cfg.get('max_iterations')}"
        if ntype == 'llm' and cfg.get('system_prompt'):
            hint = f" prompt={(cfg.get('system_prompt') or '')[:40]}"
        lines.append(f"- [{ntype}] {name}{hint}")
    return '\n'.join(lines)


def build_reference_context(description: str, user_id: Optional[int] = None) -> str:
    """
    Soft RAG: similar templates as reference text for the LLM — never paste as final graph.
    Failures are swallowed; empty string means no enrichment.
    """
    parts: List[str] = []
    try:
        from .recommender import TemplateRecommender

        recommender = TemplateRecommender(user_id=user_id)
        recs = recommender.recommend(description or '', limit=3)
        if recs:
            lines = ['以下是相似历史模板摘要，仅供参考结构与节点类型，禁止原样复制成图：']
            for r in recs:
                lines.append(
                    f"- {r.name} ({r.category or 'general'}, score={r.relevance_score:.2f}): "
                    f"{(r.description or '')[:160]}"
                )
            parts.append('\n'.join(lines))
    except Exception as exc:
        logger.debug('reference context unavailable: %s', exc)

    try:
        from .n8n_corpus import format_corpus_reference

        n8n_block = format_corpus_reference(description or '')
        if n8n_block:
            parts.append(n8n_block)
    except Exception as exc:
        logger.debug('n8n corpus reference unavailable: %s', exc)

    try:
        from .node_catalog import NL_PRIMARY_NODE_TYPES, SUPPORTED_NODE_TYPES

        sample_types = list(NL_PRIMARY_NODE_TYPES)[:24] if NL_PRIMARY_NODE_TYPES else list(SUPPORTED_NODE_TYPES)[:24]
        parts.append(
            '可用核心节点类型（请按需组合，不要输出未列出的 type）: '
            + ', '.join(sample_types)
        )
    except Exception:
        pass

    return '\n\n'.join(parts)


def optimize_workflow_structure(workflow: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Deterministic structural optimize pass (safe tool used by AI planner)."""
    if not workflow or not workflow.get('nodes'):
        return workflow or {}, []

    wf = copy.deepcopy(workflow)
    changes: List[str] = []
    nodes = wf.get('nodes') or []
    edges = wf.get('edges') or []
    node_ids = {n.get('id') for n in nodes if n.get('id')}

    cleaned_edges = []
    removed_edges = 0
    for edge in edges:
        src, tgt = edge.get('source'), edge.get('target')
        if src in node_ids and tgt in node_ids and src != tgt:
            cleaned_edges.append(edge)
        else:
            removed_edges += 1
    if removed_edges:
        changes.append(f'移除 {removed_edges} 条无效连线')
    wf['edges'] = cleaned_edges

    # Ensure unique edge ids
    seen_edge_ids = set()
    for i, edge in enumerate(wf['edges']):
        eid = edge.get('id') or f'edge_{i + 1}'
        if eid in seen_edge_ids:
            eid = f'edge_{i + 1}_{eid}'
        edge['id'] = eid
        seen_edge_ids.add(eid)

    # Fill missing wiring for video pipeline nodes without overriding providers
    for node in nodes:
        ntype = node.get('type')
        cfg = node.setdefault('config', {})
        if ntype == 'subtitle_generation':
            raw = str(cfg.get('inputPath') or cfg.get('input') or '').strip()
            if not raw:
                cfg['inputPath'] = '{video_url}'
                changes.append(f"补齐字幕生成输入引用 ({node.get('name') or node.get('id')})")
            if not cfg.get('provider'):
                cfg['provider'] = getattr(
                    settings, 'VIDEO_TRANSLATION_ASR_PROVIDER', 'local_whisper'
                )
        elif ntype == 'lip_sync':
            if not str(cfg.get('video_input') or '').strip():
                cfg['video_input'] = '{source_video_url}'
            if not str(cfg.get('audio_input') or '').strip():
                cfg['audio_input'] = '{dubbed_audio_url}'
            if 'lip_sync' not in cfg:
                cfg['lip_sync'] = False
        elif ntype == 'subtitle_burn':
            if not str(cfg.get('video_input') or '').strip():
                cfg['video_input'] = '{video_url}'
        elif ntype == 'segment_dubbing':
            if not cfg.get('provider'):
                cfg['provider'] = getattr(
                    settings, 'VIDEO_TRANSLATION_TTS_PROVIDER', 'pyttsx3'
                )

    before_pos = [(n.get('id'), (n.get('position') or {}).get('x'), (n.get('position') or {}).get('y')) for n in nodes]
    laid = auto_layout_workflow(wf)
    after_pos = [
        (n.get('id'), (n.get('position') or {}).get('x'), (n.get('position') or {}).get('y'))
        for n in (laid.get('nodes') or [])
    ]
    if before_pos != after_pos:
        changes.append('按数据流自动排布节点')
    laid['_optimized'] = True
    if not changes:
        changes.append('结构检查完成，无需大幅调整')
    return laid, changes


def validation_error_text(workflow: Dict[str, Any]) -> str:
    validation = workflow.get('validation') or {}
    errors = validation.get('errors') or []
    if isinstance(errors, list) and errors:
        return '; '.join(str(e) for e in errors)
    if workflow.get('error'):
        return str(workflow['error'])
    return ''
