"""Multimodal (image + video + audio) workflow template for NL2WF."""
from __future__ import annotations

import re
from typing import Any, Dict, List


MULTIMODAL_KEYWORDS = (
    '多模态', '文生图', '文生视频', '图生视频', '再生视频', '图像生成', '视频生成', '语音合成',
    '字幕', 'image generation', 'video generation', 'text to image', 'text to video', 'image to video',
    'multimodal', 'comfyui', '生成图片', '生成视频', '生成一张图',
)

VIDEO_TRANSLATION_KEYWORDS = (
    '视频翻译', '口型同步', '口型', '配音翻译', '多语言字幕', '视频本地化', 'videoretalk',
    'video translation', 'lip sync', 'dubbing', 'translate video',
)

_VAR_REF_RE = re.compile(r'\{\{?\s*([a-zA-Z_][\w.]*)\s*\}?\}')


def is_video_translation_intent(description: str) -> bool:
    text = (description or '').lower()
    return any(kw.lower() in text for kw in VIDEO_TRANSLATION_KEYWORDS)


def is_multimodal_intent(description: str) -> bool:
    text = (description or '').lower()
    if is_video_translation_intent(description):
        return True
    return any(kw.lower() in text for kw in MULTIMODAL_KEYWORDS)


def has_sufficient_multimodal_detail(description: str) -> bool:
    text = description or ''
    has_image = bool(re.search(r'文生图|图像|图片|image', text, re.I))
    has_video = bool(re.search(r'文生视频|视频|video', text, re.I))
    has_generate = bool(re.search(r'生成工作流|现在就生成|立即生成|开始生成', text, re.I))
    return has_generate and (has_image or has_video or '多模态' in text)


def _prompt_is_wired(value: Any) -> bool:
    text = str(value or '').strip()
    if not text:
        return False
    return bool(_VAR_REF_RE.search(text))


def wire_multimodal_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure input → image → video nodes share the same runtime variable chain.
    Fixes LLM-generated workflows that hard-code sample prompts or mismatched input_name.
    """
    nodes = workflow.get('nodes') or []
    if not any(n.get('type') in (
        'image_generation', 'video_generation', 'audio_generation', 'video_translation',
        'video_upload', 'subtitle_translate', 'segment_dubbing', 'lip_sync', 'subtitle_burn',
    ) for n in nodes):
        return workflow

    has_video_translation = any(n.get('type') == 'video_translation' for n in nodes)
    has_video_pipeline = any(n.get('type') in (
        'video_upload', 'subtitle_translate', 'segment_dubbing', 'lip_sync', 'subtitle_burn',
    ) for n in nodes)
    if has_video_pipeline:
        for node in nodes:
            ntype = node.get('type')
            cfg = node.setdefault('config', {})
            if ntype == 'subtitle_generation':
                cfg.setdefault('provider', 'dashscope')
                cfg.setdefault('inputType', 'video')
                raw = str(cfg.get('inputPath') or cfg.get('input') or '').strip()
                if not raw or not _VAR_REF_RE.search(raw):
                    cfg['inputPath'] = '{video_url}'
            elif ntype == 'lip_sync':
                cfg.setdefault('lip_sync', True)
                if not str(cfg.get('video_input') or '').strip():
                    cfg['video_input'] = '{source_video_url}'
                if not str(cfg.get('audio_input') or '').strip():
                    cfg['audio_input'] = '{dubbed_audio_url}'
            elif ntype == 'subtitle_burn':
                if not str(cfg.get('video_input') or '').strip():
                    cfg['video_input'] = '{video_url}'
        if workflow.get('name') in (None, '', '多模态 AI 工作流', 'Generated Workflow'):
            workflow['name'] = '视频多语言翻译工作流（分节点）'
        workflow['nodes'] = nodes
        return workflow

    if has_video_translation:
        input_nodes = [n for n in nodes if n.get('type') == 'input']
        var_name = 'video_url'
        for node in input_nodes:
            cfg = node.setdefault('config', {})
            cfg['input_name'] = var_name
            cfg.setdefault('input_type', 'text')
            cfg.setdefault('placeholder', '粘贴公网视频 URL，或在视频翻译节点中本地上传')
        video_ref = '{video_url}'
        for node in nodes:
            ntype = node.get('type')
            cfg = node.setdefault('config', {})
            if ntype == 'video_translation':
                cfg.setdefault('provider', 'dashscope')
                cfg.setdefault('source_language', 'zh')
                cfg.setdefault('target_languages', ['en'])
                cfg.setdefault('voice', 'longanyang')
                cfg.setdefault('subtitle_format', 'srt')
                cfg.setdefault('lip_sync', True)
                cfg.setdefault('burn_subtitles', True)
                raw_video = str(cfg.get('video_input') or cfg.get('videoInput') or '').strip()
                if not raw_video or not _VAR_REF_RE.search(raw_video):
                    cfg['video_input'] = video_ref
            elif ntype == 'output':
                template = str(cfg.get('template') or cfg.get('format') or '')
                if not template or template in ('{output}', ''):
                    cfg['template'] = '{video_url}'
                    cfg['format'] = 'json'
        if workflow.get('name') in (None, '', '多模态 AI 工作流', 'Generated Workflow'):
            workflow['name'] = '视频多语言翻译工作流'
        workflow['nodes'] = nodes
        return workflow

    input_nodes = [n for n in nodes if n.get('type') == 'input']
    var_name = 'prompt'
    if input_nodes:
        first_cfg = input_nodes[0].get('config') or {}
        raw_name = (
            first_cfg.get('input_name')
            or first_cfg.get('variable_name')
            or first_cfg.get('variableName')
            or 'prompt'
        )
        if raw_name in ('user_prompt', 'user_input', 'description', 'text', 'input', 'query'):
            var_name = 'prompt'
        else:
            var_name = str(raw_name)
        for node in input_nodes:
            cfg = node.setdefault('config', {})
            cfg['input_name'] = var_name
            cfg.setdefault('input_type', 'text')
            cfg.setdefault('placeholder', '描述你想生成的画面，如：一只在草地上的橘猫')

    prompt_ref = f'{{{var_name}}}'
    has_video = any(n.get('type') == 'video_generation' for n in nodes)

    for node in nodes:
        ntype = node.get('type')
        cfg = node.setdefault('config', {})
        if ntype == 'image_generation':
            cfg.setdefault('provider', 'agnes')
            cfg.setdefault('model', 'agnes-image-2.1-flash')
            cfg.setdefault('size', '1024x1024')
            cfg.setdefault('n', 1)
            if not _prompt_is_wired(cfg.get('prompt') or cfg.get('text')):
                cfg['prompt'] = prompt_ref
        elif ntype == 'video_generation':
            cfg.setdefault('provider', 'agnes')
            cfg.setdefault('model', 'agnes-video-v2.0')
            cfg.setdefault('resolution', '720p')
            cfg.setdefault('duration', 5)
            if not _prompt_is_wired(cfg.get('prompt') or cfg.get('text')):
                cfg['prompt'] = prompt_ref
            image_ref = '{images.0.url}'
            raw_image = str(cfg.get('inputImage') or cfg.get('input_image') or '').strip()
            if not raw_image or not _VAR_REF_RE.search(raw_image):
                cfg['inputImage'] = image_ref
        elif ntype == 'audio_generation':
            if not _prompt_is_wired(cfg.get('text') or cfg.get('prompt')):
                cfg['text'] = prompt_ref
        elif ntype == 'output' and has_video:
            template = str(cfg.get('template') or cfg.get('format') or '')
            if not template or template in ('{video_url}', '{output}'):
                cfg['template'] = '{video_url}'
                cfg['format'] = 'json'

    if has_video and workflow.get('name') in (None, '', '多模态 AI 工作流', 'Generated Workflow'):
        workflow['name'] = '文生图再生视频工作流'

    workflow['nodes'] = nodes
    return workflow


def build_multimodal_workflow(description: str) -> Dict[str, Any]:
    """Build a standard multimodal pipeline: input → image → video → output."""
    wants_video = bool(re.search(r'视频|video|再生视频|图生视频', description or '', re.I))
    wants_audio = bool(re.search(r'语音|音频|tts|audio', description or '', re.I))

    nodes: List[Dict[str, Any]] = [
        {
            'id': 'node_start',
            'type': 'start',
            'name': '开始',
            'position': {'x': 80, 'y': 200},
            'config': {},
        },
        {
            'id': 'node_input',
            'type': 'input',
            'name': '接收描述',
            'position': {'x': 280, 'y': 200},
            'config': {
                'input_name': 'prompt',
                'input_type': 'text',
                'placeholder': '描述你想生成的画面，如：一只在草地上的橘猫',
            },
        },
        {
            'id': 'node_image',
            'type': 'image_generation',
            'name': '生成图像',
            'position': {'x': 520, 'y': 200},
            'config': {
                'provider': 'agnes',
                'model': 'agnes-image-2.1-flash',
                'prompt': '{prompt}',
                'size': '1024x1024',
                'n': 1,
            },
        },
    ]
    edges = [
        {'id': 'e_start_input', 'source': 'node_start', 'target': 'node_input', 'label': ''},
        {'id': 'e_input_image', 'source': 'node_input', 'target': 'node_image', 'label': ''},
    ]

    prev_id = 'node_image'
    x = 760

    if wants_video:
        vid_id = 'node_video'
        nodes.append({
            'id': vid_id,
            'type': 'video_generation',
            'name': '生成视频',
            'position': {'x': x, 'y': 200},
            'config': {
                'provider': 'agnes',
                'model': 'agnes-video-v2.0',
                'prompt': '{prompt}',
                'inputImage': '{images.0.url}',
                'resolution': '720p',
                'duration': 5,
            },
        })
        edges.append({'id': 'e_image_video', 'source': prev_id, 'target': vid_id, 'label': ''})
        prev_id = vid_id
        x += 260

    if wants_audio:
        aud_id = 'node_audio'
        nodes.append({
            'id': aud_id,
            'type': 'audio_generation',
            'name': '语音合成',
            'position': {'x': x, 'y': 200},
            'config': {
                'provider': 'dashscope',
                'model': 'cosyvoice-v3-flash',
                'text': '{prompt}',
                'voice': 'longanyang',
                'format': 'mp3',
            },
        })
        edges.append({'id': f'e_{prev_id}_{aud_id}', 'source': prev_id, 'target': aud_id, 'label': ''})
        prev_id = aud_id
        x += 260

    out_id = 'node_output'
    output_template = '{video_url}' if wants_video else '{images.0.url}'
    nodes.extend([
        {
            'id': out_id,
            'type': 'output',
            'name': '返回视频' if wants_video else '返回图像',
            'position': {'x': x, 'y': 200},
            'config': {'template': output_template, 'format': 'json'},
        },
        {
            'id': 'node_end',
            'type': 'end',
            'name': '结束',
            'position': {'x': x + 220, 'y': 200},
            'config': {},
        },
    ])
    edges.extend([
        {'id': f'e_{prev_id}_output', 'source': prev_id, 'target': out_id, 'label': ''},
        {'id': 'e_output_end', 'source': out_id, 'target': 'node_end', 'label': ''},
    ])

    workflow = {
        'name': '文生图再生视频工作流' if wants_video else '文生图工作流',
        'description': description,
        'nodes': nodes,
        'edges': edges,
        '_generation_mode': 'template_multimodal',
    }
    return wire_multimodal_workflow(workflow)


def build_video_translation_workflow(description: str) -> Dict[str, Any]:
    """Build split-node video localization pipeline (upload → ASR → per-lang chain)."""
    from nl_to_workflow.video_translation_workflow import build_split_video_translation_workflow
    return build_split_video_translation_workflow(description)


def should_use_multimodal_template(description: str) -> bool:
    return is_multimodal_intent(description)


def should_use_video_translation_template(description: str) -> bool:
    return is_video_translation_intent(description)


def multimodal_chat_fallback_response(session_messages, user_message):
    combined = ' '.join(
        (m.get('content') or '') for m in (session_messages or []) if isinstance(m, dict)
    ) + ' ' + (user_message or '')
    if is_video_translation_intent(combined):
        if has_sufficient_multimodal_detail(combined) or re.search(
            r'现在就生成|生成工作流|开始生成', combined or '', re.I
        ):
            msg = (
                '根据您的描述，我将生成 **分节点视频多语言翻译** 工作流：\n'
                '- **上传视频**（本地上传 + 实时预览）\n'
                '- **语音识别**（Paraformer ASR）\n'
                '- 每种目标语言独立链路：**翻译 → 配音 → 口型同步 → 烧录字幕**\n\n'
                '若理解无误，请回复「现在就生成工作流」。'
            )
            return msg, True, ['现在就生成工作流', '不要口型同步', '补充更多细节']
        msg = (
            '您想搭建 **视频翻译工作流**。请确认：\n'
            '1. 视频来源是公网 URL 还是本地上传？\n'
            '2. 目标语言是什么（如英语、日语）？\n'
            '3. 是否需要口型同步与硬字幕烧录？\n\n'
            '确认后回复「现在就生成工作流」。'
        )
        return msg, False, ['中文视频翻译成英文，现在就生成工作流', '只要字幕不要配音', '需要口型同步']
    if not is_multimodal_intent(combined):
        return '', False, []
    if has_sufficient_multimodal_detail(combined):
        msg = (
            '根据您的描述，我将生成 **文生图 → 再生视频** 工作流：\n'
            '- 接收描述（变量 `{prompt}`）\n'
            '- Agnes 文生图（1024×1024）\n'
            '- Agnes 图生视频（720p，使用上游图像 `{images.0.url}`）\n\n'
            '若理解无误，请回复「现在就生成工作流」。'
        )
        return msg, True, ['现在就生成工作流', '只要文生图，不要视频', '补充更多细节']
    msg = (
        '您想搭建 **多模态生成工作流**。请确认：\n'
        '1. 是否需要文生图？\n'
        '2. 是否需要文生视频？\n'
        '3. 输入是自由文本提示词吗？\n\n'
        '确认后回复「现在就生成工作流」。'
    )
    return msg, False, ['文生图+文生视频，现在就生成工作流', '只要文生图', '需要语音合成']
