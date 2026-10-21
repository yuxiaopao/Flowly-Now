"""
Normalize LLM-generated node configs onto runtime-executable schemas.

This is intentionally domain-agnostic: alias field names, fill safe defaults,
and rewrite unsupported invented keys — never special-case a business theme.
"""
from __future__ import annotations

import re
from typing import Any, Dict

_JS_HINT_RE = re.compile(
    r'\b(const|let|var|=>|JSON\.parse|JSON\.stringify|function\s*\()\b'
)
_MUSTACHE_RE = re.compile(r'\{\{\s*([^}]+)\s*\}\}')

# Generic Python that turns upstream storyboard / list / text into prompt rows.
_DEFAULT_ENRICH_CODE = '''# Enrich upstream structured data into image prompts (schema-agnostic).
# `json` / `input` / `output` are provided by the sandbox namespace.
raw = input
if isinstance(raw, dict):
    for key in ('output', 'data', 'result', 'text', 'content', 'input'):
        if key in raw and raw[key] not in (None, ''):
            raw = raw[key]
            break
if isinstance(raw, str):
    text = raw.strip()
    try:
        raw = json.loads(text)
    except Exception:
        start = text.find('[')
        end = text.rfind(']')
        if start >= 0 and end > start:
            try:
                raw = json.loads(text[start:end + 1])
            except Exception:
                raw = [{'text': text}]
        else:
            raw = [{'text': text}]

items = raw if isinstance(raw, list) else ([raw] if raw is not None else [])
enriched = []
for i, item in enumerate(items):
    if isinstance(item, dict):
        desc = (
            item.get('prompt')
            or item.get('description')
            or item.get('画面描述')
            or item.get('scene')
            or item.get('text')
            or item.get('content')
            or str(item)
        )
        mood = item.get('mood') or item.get('情绪') or item.get('emotion') or ''
        prompt = str(desc).strip()
        if mood:
            prompt = f"{prompt}, {mood}"
        row = dict(item)
        row['prompt'] = prompt
        row['index'] = i
        enriched.append(row)
    else:
        enriched.append({'prompt': str(item), 'index': i})

output = {
    'enriched_shots': enriched,
    'result': enriched,
    'data': enriched,
}
'''


def _as_dict(config: Any) -> Dict[str, Any]:
    return dict(config) if isinstance(config, dict) else {}


def _first_nonempty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _looks_like_js(code: str) -> bool:
    return bool(_JS_HINT_RE.search(code or ''))


def normalize_code_node_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _as_dict(config)
    code = _first_nonempty(
        normalized.get('code'),
        normalized.get('script'),
        normalized.get('source'),
        normalized.get('body'),
    )
    language = str(normalized.get('language') or 'python').strip().lower()

    if code and isinstance(code, str):
        if language in {'javascript', 'js', 'node'} or _looks_like_js(code):
            # Runtime sandbox is Python-only; replace non-executable JS with
            # a generic enricher that preserves the node's intent.
            normalized['code'] = _DEFAULT_ENRICH_CODE
            normalized['language'] = 'python'
        else:
            normalized['code'] = code
            normalized['language'] = 'python' if language in {'', 'py'} else language
    else:
        normalized['code'] = _DEFAULT_ENRICH_CODE
        normalized['language'] = 'python'

    # Keep aliases for UI compatibility, but `code` is the source of truth.
    normalized['script'] = normalized['code']
    return normalized


def normalize_loop_node_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _as_dict(config)
    item_variable = _first_nonempty(
        normalized.get('item_variable'),
        normalized.get('item_var'),
        normalized.get('itemVar'),
        'item',
    )
    normalized['item_variable'] = str(item_variable)
    normalized.pop('item_var', None)

    max_iterations = _first_nonempty(
        normalized.get('max_iterations'),
        normalized.get('max'),
        normalized.get('maxIterations'),
        10,
    )
    try:
        normalized['max_iterations'] = max(1, int(max_iterations))
    except (TypeError, ValueError):
        normalized['max_iterations'] = 10

    loop_type = str(
        _first_nonempty(
            normalized.get('loop_type'),
            normalized.get('mode'),
            'for_each',
        )
    ).strip().lower()
    if (
        loop_type in {'for', 'for_each', 'foreach', 'for-each'}
        or 'for' in loop_type
        or '循环' in loop_type
        or 'each' in loop_type
    ):
        # Keep while/do_while explicit; everything else for-like → for_each
        if loop_type in {'while', 'do_while', 'range'}:
            pass
        elif 'while' in loop_type:
            loop_type = 'do_while' if 'do' in loop_type else 'while'
        elif 'range' in loop_type:
            loop_type = 'range'
        else:
            loop_type = 'for_each'
    normalized['loop_type'] = loop_type

    items = normalized.get('items')
    if isinstance(items, str) and _MUSTACHE_RE.search(items):
        # Intermediate {{vars}} are not first-class input variables; use edge input.
        normalized['items_source'] = normalized.get('items_source') or 'input'
        normalized.pop('items', None)
    elif items in (None, '', []):
        normalized['items_source'] = normalized.get('items_source') or 'input'

    return normalized


def normalize_json_transform_node_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _as_dict(config)
    operation = str(normalized.get('operation') or 'map').strip().lower()
    aliases = {
        'parse': 'parse_array',
        'parse_json': 'parse_array',
        'to_array': 'parse_array',
        'extract_array': 'parse_array',
        'array': 'parse_array',
    }
    normalized['operation'] = aliases.get(operation, operation)
    if normalized['operation'] == 'parse_array':
        normalized.setdefault('target_field', 'items')
    return normalized


def normalize_image_generation_node_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _as_dict(config)
    provider = str(normalized.get('provider') or 'agnes').strip().lower()
    normalized['provider'] = provider or 'agnes'
    model = str(normalized.get('model') or '').strip()
    if provider == 'agnes' and (not model or not model.startswith('agnes-image')):
        normalized['model'] = 'agnes-image-2.1-flash'
    prompt = _first_nonempty(normalized.get('prompt'), normalized.get('text'))
    if isinstance(prompt, str):
        # {{var}} → {var} for runtime template resolution
        prompt = _MUSTACHE_RE.sub(r'{\1}', prompt)
        normalized['prompt'] = prompt
    if not prompt:
        normalized['prompt'] = '{prompt}'
    # Prefer shot-level prompt when batch / enriched lists are referenced.
    batch = normalized.get('batch_input') or normalized.get('batchInput')
    if isinstance(batch, str) and _MUSTACHE_RE.search(batch):
        normalized['prompt'] = '{prompt}'
        normalized.pop('batch_input', None)
        normalized.pop('batchInput', None)
    normalized.setdefault('size', '1024x1024')
    normalized.setdefault('n', 1)
    return normalized


def normalize_video_generation_node_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _as_dict(config)
    provider = str(normalized.get('provider') or 'agnes').strip().lower()
    normalized['provider'] = provider or 'agnes'
    model = str(normalized.get('model') or '').strip()
    if provider == 'agnes' and (not model or not model.startswith('agnes-video')):
        normalized['model'] = 'agnes-video-v2.0'
    for key in ('inputImage', 'input_image', 'prompt', 'text'):
        value = normalized.get(key)
        if isinstance(value, str) and _MUSTACHE_RE.search(value):
            normalized[key] = _MUSTACHE_RE.sub(r'{\1}', value)
    if not _first_nonempty(normalized.get('inputImage'), normalized.get('input_image')):
        normalized['inputImage'] = '{images.0.url}'
        normalized['input_image'] = '{images.0.url}'
    else:
        image_ref = _first_nonempty(normalized.get('inputImage'), normalized.get('input_image'))
        normalized['inputImage'] = image_ref
        normalized['input_image'] = image_ref
    if not _first_nonempty(normalized.get('prompt'), normalized.get('text')):
        normalized['prompt'] = '{prompt}'
    # Drop invented list keys that the executor does not consume.
    for key in ('keyframes_input', 'keyframesInput'):
        value = normalized.get(key)
        if isinstance(value, str) and _MUSTACHE_RE.search(value):
            normalized.pop(key, None)
    normalized.setdefault('resolution', '720p')
    normalized.setdefault('duration', 5)
    return normalized


def normalize_subtitle_generation_node_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _as_dict(config)
    input_path = _first_nonempty(
        normalized.get('inputPath'),
        normalized.get('input_path'),
        normalized.get('input'),
        normalized.get('input_video'),
        normalized.get('inputVideo'),
    )
    if isinstance(input_path, str) and _MUSTACHE_RE.search(input_path):
        # Prefer standard runtime variable used by video nodes.
        input_path = '{video_url}'
    if input_path:
        normalized['inputPath'] = input_path
        normalized['input_path'] = input_path
    normalized.setdefault('format', 'srt')
    normalized.setdefault('language', 'zh')
    # Drop unused invented refs that only create false validator warnings.
    for key in ('reference_audio', 'referenceAudio', 'input_video', 'inputVideo'):
        value = normalized.get(key)
        if isinstance(value, str) and _MUSTACHE_RE.search(value):
            normalized.pop(key, None)
    return normalized


def normalize_node_config(node_type: str, config: Any) -> Dict[str, Any]:
    """Dispatch per-type normalization. Unknown types pass through as dict."""
    ntype = str(node_type or '').strip().lower()
    base = _as_dict(config)
    if ntype == 'code':
        return normalize_code_node_config(base)
    if ntype == 'loop':
        return normalize_loop_node_config(base)
    if ntype in {'json_transform', 'json'}:
        return normalize_json_transform_node_config(base)
    if ntype == 'image_generation':
        return normalize_image_generation_node_config(base)
    if ntype == 'video_generation':
        return normalize_video_generation_node_config(base)
    if ntype == 'subtitle_generation':
        return normalize_subtitle_generation_node_config(base)
    return base
