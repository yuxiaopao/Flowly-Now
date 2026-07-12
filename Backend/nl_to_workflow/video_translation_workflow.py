"""Build multi-node video localization workflows for NL2WF."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from nl_to_workflow.workflow_layout import auto_layout_workflow


LANG_LABELS = {
    'en': '英语',
    'ja': '日语',
    'ko': '韩语',
    'es': '西语',
    'fr': '法语',
    'de': '德语',
    'zh': '中文',
}


def detect_target_languages(description: str) -> List[str]:
    text = description or ''
    langs: List[str] = []
    checks = [
        ('en', r'英语|英文|english|\ben\b'),
        ('ja', r'日语|日文|japanese|\bja\b'),
        ('ko', r'韩语|韩文|korean|\bko\b'),
        ('es', r'西语|西班牙语|spanish|\bes\b'),
        ('fr', r'法语|french|\bfr\b'),
        ('de', r'德语|german|\bde\b'),
    ]
    for code, pattern in checks:
        if re.search(pattern, text, re.I):
            langs.append(code)
    return langs or ['en']


def build_split_video_translation_workflow(description: str) -> Dict[str, Any]:
    """
    Multi-node pipeline:
    video_upload → subtitle_generation (ASR)
      → per language: subtitle_translate → segment_dubbing → lip_sync → subtitle_burn
    """
    target_langs = detect_target_languages(description)
    source_lang = 'zh'
    if re.search(r'英文|english|en.*video|video.*en', description or '', re.I) and '中文' not in (description or ''):
        source_lang = 'en'

    nodes: List[Dict[str, Any]] = [
        {
            'id': 'node_start',
            'type': 'start',
            'name': '开始',
            'position': {'x': 40, 'y': 240},
            'config': {},
        },
        {
            'id': 'node_upload',
            'type': 'video_upload',
            'name': '上传视频',
            'position': {'x': 200, 'y': 240},
            'config': {
                'inputMode': 'upload',
                'video_input': '',
            },
        },
        {
            'id': 'node_asr',
            'type': 'subtitle_generation',
            'name': '语音识别',
            'position': {'x': 420, 'y': 240},
            'config': {
                'provider': 'local_whisper',
                'inputPath': '{video_url}',
                'inputType': 'video',
                'language': source_lang,
                'format': 'srt',
            },
        },
    ]
    edges: List[Dict[str, Any]] = [
        {'id': 'e_start_upload', 'source': 'node_start', 'target': 'node_upload', 'label': ''},
        {'id': 'e_upload_asr', 'source': 'node_upload', 'target': 'node_asr', 'label': ''},
    ]

    x = 640
    last_node_ids: List[str] = []
    for i, lang in enumerate(target_langs):
        label = LANG_LABELS.get(lang, lang.upper())
        y = 80 + i * 180
        translate_id = f'node_translate_{lang}'
        dub_id = f'node_dub_{lang}'
        lip_id = f'node_lip_{lang}'
        burn_id = f'node_burn_{lang}'

        nodes.extend([
            {
                'id': translate_id,
                'type': 'subtitle_translate',
                'name': f'翻译·{label}',
                'position': {'x': x, 'y': y},
                'config': {
                    'source_language': source_lang,
                    'target_language': lang,
                    'subtitle_format': 'srt',
                    'translation_model': 'agnes-2.0-flash',
                },
            },
            {
                'id': dub_id,
                'type': 'segment_dubbing',
                'name': f'配音·{label}',
                'position': {'x': x + 200, 'y': y},
                'config': {
                    'target_language': lang,
                    'voice': '',
                    'provider': 'pyttsx3',
                },
            },
            {
                'id': lip_id,
                'type': 'lip_sync',
                'name': f'口型·{label}',
                'position': {'x': x + 400, 'y': y},
                'config': {
                    'target_language': lang,
                    'video_input': '{source_video_url}',
                    'audio_input': '{dubbed_audio_url}',
                    'provider': 'ffmpeg',
                    'lip_sync': False,
                },
            },
            {
                'id': burn_id,
                'type': 'subtitle_burn',
                'name': f'烧录字幕·{label}',
                'position': {'x': x + 600, 'y': y},
                'config': {
                    'target_language': lang,
                    'video_input': '{video_url}',
                    'subtitle_format': 'srt',
                },
            },
        ])
        edges.extend([
            {'id': f'e_asr_{translate_id}', 'source': 'node_asr', 'target': translate_id, 'label': ''},
            {'id': f'e_{translate_id}_{dub_id}', 'source': translate_id, 'target': dub_id, 'label': ''},
            {'id': f'e_{dub_id}_{lip_id}', 'source': dub_id, 'target': lip_id, 'label': ''},
            {'id': f'e_{lip_id}_{burn_id}', 'source': lip_id, 'target': burn_id, 'label': ''},
        ])
        last_node_ids.append(burn_id)

    output_x = x + 820
    output_template = ', '.join(f'{{video_url_{lang}}}' for lang in target_langs) or '{video_url}'
    nodes.append({
        'id': 'node_output',
        'type': 'output',
        'name': '多语言成片输出',
        'position': {'x': output_x, 'y': 240},
        'config': {'template': output_template, 'format': 'json'},
    })
    nodes.append({
        'id': 'node_end',
        'type': 'end',
        'name': '结束',
        'position': {'x': output_x + 200, 'y': 240},
        'config': {},
    })

    for burn_id in last_node_ids:
        edges.append({'id': f'e_{burn_id}_output', 'source': burn_id, 'target': 'node_output', 'label': ''})
    edges.append({'id': 'e_output_end', 'source': 'node_output', 'target': 'node_end', 'label': ''})

    return {
        'name': '视频多语言翻译工作流（分节点）',
        'description': description,
        'nodes': nodes,
        'edges': edges,
        '_generation_mode': 'template_video_translation_split',
        'target_languages': target_langs,
    }


def is_video_translation_workflow(workflow: Dict[str, Any]) -> bool:
    if not workflow or not workflow.get('nodes'):
        return False
    types = {n.get('type') for n in workflow.get('nodes', [])}
    return 'video_upload' in types and 'subtitle_generation' in types


def append_language_chain_to_workflow(
    workflow: Dict[str, Any],
    lang: str,
    description: str = '',
) -> Dict[str, Any]:
    """Append a per-language processing chain to an existing split video translation workflow."""
    import copy

    if not is_video_translation_workflow(workflow):
        return workflow

    result = copy.deepcopy(workflow)
    nodes: List[Dict[str, Any]] = result.get('nodes') or []
    edges: List[Dict[str, Any]] = result.get('edges') or []

    existing = {
        n.get('id')
        for n in nodes
        if n.get('type') == 'subtitle_translate'
        and (n.get('config') or {}).get('target_language') == lang
    }
    if existing:
        return result

    asr_node = next((n for n in nodes if n.get('type') == 'subtitle_generation'), None)
    if not asr_node:
        return result

    source_lang = (asr_node.get('config') or {}).get('language') or 'zh'
    label = LANG_LABELS.get(lang, lang.upper())

    lang_chains = [
        n for n in nodes
        if n.get('type') == 'subtitle_translate'
    ]
    row = len(lang_chains)
    x = 640
    if lang_chains:
        positions = [n.get('position') or {} for n in lang_chains]
        x = max(p.get('x', 640) for p in positions)

    y = 80 + row * 180
    translate_id = f'node_translate_{lang}'
    dub_id = f'node_dub_{lang}'
    lip_id = f'node_lip_{lang}'
    burn_id = f'node_burn_{lang}'

    nodes.extend([
        {
            'id': translate_id,
            'type': 'subtitle_translate',
            'name': f'翻译·{label}',
            'position': {'x': x, 'y': y},
            'config': {
                'source_language': source_lang,
                'target_language': lang,
                'subtitle_format': 'srt',
            },
        },
        {
            'id': dub_id,
            'type': 'segment_dubbing',
            'name': f'配音·{label}',
            'position': {'x': x + 200, 'y': y},
            'config': {
                'target_language': lang,
                'voice': '',
                'provider': 'pyttsx3',
            },
        },
        {
            'id': lip_id,
            'type': 'lip_sync',
            'name': f'口型·{label}',
            'position': {'x': x + 400, 'y': y},
            'config': {
                'target_language': lang,
                'video_input': '{source_video_url}',
                'audio_input': '{dubbed_audio_url}',
                'provider': 'ffmpeg',
                'lip_sync': False,
            },
        },
        {
            'id': burn_id,
            'type': 'subtitle_burn',
            'name': f'烧录字幕·{label}',
            'position': {'x': x + 600, 'y': y},
            'config': {
                'target_language': lang,
                'video_input': '{video_url}',
                'subtitle_format': 'srt',
            },
        },
    ])
    edges.extend([
        {'id': f'e_asr_{translate_id}', 'source': asr_node.get('id'), 'target': translate_id, 'label': ''},
        {'id': f'e_{translate_id}_{dub_id}', 'source': translate_id, 'target': dub_id, 'label': ''},
        {'id': f'e_{dub_id}_{lip_id}', 'source': dub_id, 'target': lip_id, 'label': ''},
        {'id': f'e_{lip_id}_{burn_id}', 'source': lip_id, 'target': burn_id, 'label': ''},
    ])

    output_node = next((n for n in nodes if n.get('type') == 'output'), None)
    if output_node:
        edges.append({
            'id': f'e_{burn_id}_output',
            'source': burn_id,
            'target': output_node.get('id'),
            'label': '',
        })
        langs = detect_target_languages(description)
        existing_langs = [
            (n.get('config') or {}).get('target_language')
            for n in nodes
            if n.get('type') == 'subtitle_translate'
        ]
        all_langs = list(dict.fromkeys(existing_langs + [lang]))
        output_node.setdefault('config', {})['template'] = ', '.join(
            f'{{video_url_{code}}}' for code in all_langs
        ) or '{video_url}'

    result['nodes'] = nodes
    result['edges'] = edges
    result['target_languages'] = list(dict.fromkeys(
        (result.get('target_languages') or []) + [lang]
    ))
    return auto_layout_workflow(result)


_VIDEO_SOURCE_KEYS = (
    'video_url', 'videoUrl', 'video_input', 'videoInput',
    'public_url', 'publicUrl', 'media_id', 'mediaId',
)


def _node_has_video_source(config: Dict[str, Any]) -> bool:
    cfg = config or {}
    return any(str(cfg.get(k) or '').strip() for k in _VIDEO_SOURCE_KEYS)


def is_config_check_intent(message: str) -> bool:
    text = message or ''
    keywords = (
        '还需要配置', '哪些节点还需要', '检查哪些节点', '配置检查',
        '缺少什么配置', '未配置', '待配置',
    )
    return any(k in text for k in keywords)


def extract_url_from_message(message: str) -> str:
    match = re.search(r'https?://[^\s<>"\']+', message or '', re.I)
    return match.group(0).rstrip('.,;') if match else ''


def is_video_url_intent(message: str) -> bool:
    text = message or ''
    if not extract_url_from_message(text):
        return False
    keywords = ('video_upload', '视频', 'url', 'URL', '公网', '测试视频', '设置')
    return any(k in text for k in keywords)


def apply_video_url_to_workflow(workflow: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Set public video URL on the video_upload node (editor assistant)."""
    import copy

    if not url or not is_video_translation_workflow(workflow):
        return workflow

    result = copy.deepcopy(workflow)
    for node in result.get('nodes') or []:
        if node.get('type') != 'video_upload':
            continue
        cfg = dict(node.get('config') or {})
        cfg['inputMode'] = 'url'
        cfg['video_input'] = url
        cfg['video_url'] = url
        cfg['public_url'] = url
        node['config'] = cfg
        break
    return result


def get_video_translation_config_guidance(
    workflow: Dict[str, Any],
) -> tuple[str, List[Dict[str, Any]], List[str]]:
    """
    Inspect split video translation workflow for missing runtime configuration.

    Returns (summary_message, guidance_list, missing_labels).
    """
    if not is_video_translation_workflow(workflow):
        return '当前工作流不是视频翻译分节点模板。', [], []

    from django.conf import settings

    guidance_list: List[Dict[str, Any]] = []
    missing_labels: List[str] = []

    for node in workflow.get('nodes') or []:
        node_type = node.get('type') or ''
        node_name = node.get('name') or node_type
        config = node.get('config') or {}

        if node_type == 'video_upload':
            if not _node_has_video_source(config):
                label = f'「{node_name}」- 未上传视频或填写公网 URL'
                missing_labels.append(label)
                guidance_list.append({
                    'node_name': node_name,
                    'node_type': node_type,
                    'message': '执行前请在节点内上传视频，或通过助手设置公网视频 URL。',
                    'missing_fields': [label],
                    'items': [
                        {'field': '视频来源', 'required': True, 'tip': '本地上传或公网 URL', 'example': 'https://example.com/demo.mp4'},
                    ],
                })

        elif node_type == 'subtitle_generation':
            input_path = config.get('inputPath') or config.get('input') or ''
            if input_path != '{video_url}':
                label = f'「{node_name}」- ASR 输入应引用 {{video_url}}'
                missing_labels.append(label)
                guidance_list.append({
                    'node_name': node_name,
                    'node_type': node_type,
                    'message': '语音识别节点需从视频上传节点接收 video_url。',
                    'missing_fields': [label],
                })

        elif node_type == 'segment_dubbing':
            provider = config.get('provider') or getattr(settings, 'VIDEO_TRANSLATION_TTS_PROVIDER', 'pyttsx3')
            if provider == 'dashscope':
                label = f'「{node_name}」- DashScope TTS 需配置 DASHSCOPE_API_KEY'
                missing_labels.append(label)
                guidance_list.append({
                    'node_name': node_name,
                    'node_type': node_type,
                    'message': '当前使用 DashScope 配音，请配置 DASHSCOPE_API_KEY；或改为 edge_tts / openai。',
                    'missing_fields': [label],
                })

    if missing_labels:
        summary = (
            f'共 {len(missing_labels)} 项待配置：\n'
            + '\n'.join(f'- {item}' for item in missing_labels)
            + '\n\n建议下一步：在「上传视频」节点填写公网 URL，或对我说「设置视频 URL 为 https://...」。'
        )
    else:
        summary = (
            '视频翻译流水线节点结构完整，关键字段已就绪。\n'
            '可保存工作流后点击「执行」；默认 ASR=local_whisper、TTS=pyttsx3、口型=FFmpeg 混流，需安装 FFmpeg。'
        )

    return summary, guidance_list, missing_labels
