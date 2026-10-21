"""Edge-based variable wiring: fill empty target slots from upstream node type.

Design (mirrors Frontend/src/utils/nodeVariableWiring.js):
1. Allowlist only — unmatched source→target pairs do nothing.
2. One edge fills one semantic slot (image edge ≠ prompt edge).
3. One primary field per slot; skip if any alias already set (no duplicate params).
4. Never overwrite user/LLM-filled values.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


IMAGE_TYPES = frozenset({'image_generation', 'image_editing'})
VIDEO_TYPES = frozenset({'video_generation'})

# slot_name -> (primary, aliases)
SLOTS = {
    'llm_user': ('userTemplate', ('user_template',)),
    'prompt': ('prompt', ('text',)),
    'image': ('inputImage', ('input_image', 'image')),
    'instruction': ('instruction', ('prompt',)),
    'audio_text': ('text', ('prompt', 'input')),
    'subtitle_video': ('inputPath', ('input_path', 'input', 'inputVideo', 'input_video')),
    'burn_video': ('video_input', ('videoInput', 'inputVideo')),
    'burn_subtitle': ('subtitle_input', ('subtitleInput', 'srt')),
    'output_template': ('template', ()),
    'http_body': ('body', ()),
}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _slot_filled(cfg: Dict[str, Any], primary: str, aliases: Tuple[str, ...]) -> bool:
    for key in (primary, *aliases):
        if not _is_empty(cfg.get(key)):
            return True
    return False


def _fill_slot(cfg: Dict[str, Any], slot_name: str, value: str) -> bool:
    primary, aliases = SLOTS[slot_name]
    if _slot_filled(cfg, primary, aliases):
        return False
    cfg[primary] = value
    return True


def _node_type(node: Dict[str, Any]) -> str:
    data = node.get('data') if isinstance(node.get('data'), dict) else {}
    return str(node.get('type') or data.get('type') or '').strip()


def _node_config(node: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not node:
        return {}
    if isinstance(node.get('config'), dict) and node.get('config'):
        return node['config']
    data = node.get('data') if isinstance(node.get('data'), dict) else {}
    if isinstance(data.get('config'), dict):
        return data['config']
    return {}


def get_input_var_ref(source_node: Optional[Dict[str, Any]] = None) -> str:
    cfg = _node_config(source_node)
    name = str(
        cfg.get('input_name')
        or cfg.get('variable_name')
        or cfg.get('variableName')
        or 'input'
    ).strip() or 'input'
    return f'{{{name}}}'


def wire_target_config_on_connect(
    source_type: str,
    target_type: str,
    target_config: Optional[Dict[str, Any]] = None,
    *,
    source_node: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], bool]:
    """Fill empty target slots based on allowlisted source→target pairs."""
    source = (source_type or '').strip()
    target = (target_type or '').strip()
    cfg: Dict[str, Any] = dict(target_config or {})
    changed = False
    input_ref = get_input_var_ref(source_node) if source == 'input' else '{input}'

    def mark(ok: bool) -> None:
        nonlocal changed
        if ok:
            changed = True

    if target in ('llm', 'prompt'):
        if source == 'input':
            mark(_fill_slot(cfg, 'llm_user', input_ref))
        elif source in ('llm', 'prompt'):
            mark(_fill_slot(cfg, 'llm_user', '{text}'))

    if target == 'image_generation':
        if source == 'input':
            mark(_fill_slot(cfg, 'prompt', input_ref))
        elif source in ('llm', 'prompt'):
            mark(_fill_slot(cfg, 'prompt', '{text}'))

    if target == 'image_editing':
        if source in IMAGE_TYPES:
            mark(_fill_slot(cfg, 'image', '{images.0.url}'))
        elif source in ('llm', 'prompt'):
            mark(_fill_slot(cfg, 'instruction', '{text}'))
        elif source == 'input':
            mark(_fill_slot(cfg, 'instruction', input_ref))

    if target == 'video_generation':
        if source in IMAGE_TYPES:
            mark(_fill_slot(cfg, 'image', '{images.0.url}'))
        elif source in ('llm', 'prompt'):
            mark(_fill_slot(cfg, 'prompt', '{text}'))
        elif source == 'input':
            mark(_fill_slot(cfg, 'prompt', input_ref))

    if target == 'audio_generation':
        if source in ('llm', 'prompt'):
            mark(_fill_slot(cfg, 'audio_text', '{text}'))
        elif source == 'input':
            mark(_fill_slot(cfg, 'audio_text', input_ref))

    if target == 'subtitle_generation':
        if source in VIDEO_TYPES or source == 'video_upload':
            mark(_fill_slot(cfg, 'subtitle_video', '{video_url}'))

    if target == 'subtitle_burn':
        if source in VIDEO_TYPES or source in ('video_upload', 'lip_sync'):
            mark(_fill_slot(cfg, 'burn_video', '{video_url}'))
        elif source in ('subtitle_generation', 'subtitle_translate'):
            mark(_fill_slot(cfg, 'burn_subtitle', '{srt}'))

    if target == 'output':
        if source in IMAGE_TYPES:
            mark(_fill_slot(cfg, 'output_template', '{images.0.url}'))
        elif source in VIDEO_TYPES:
            mark(_fill_slot(cfg, 'output_template', '{video_url}'))
        elif source == 'audio_generation':
            mark(_fill_slot(cfg, 'output_template', '{audio_url}'))
        elif source in ('llm', 'prompt'):
            mark(_fill_slot(cfg, 'output_template', '{text}'))
        elif source == 'input':
            mark(_fill_slot(cfg, 'output_template', input_ref))

    if target == 'http_request' and source in ('llm', 'prompt'):
        mark(_fill_slot(cfg, 'http_body', '{text}'))

    return cfg, changed


def wire_workflow_variable_refs(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Apply edge-based auto-wiring across the whole workflow graph."""
    nodes: List[Dict[str, Any]] = list(workflow.get('nodes') or [])
    edges: List[Dict[str, Any]] = list(workflow.get('edges') or [])
    if not nodes or not edges:
        return workflow

    node_by_id: Dict[str, Dict[str, Any]] = {
        str(n.get('id')): n for n in nodes if n.get('id') is not None
    }

    for edge in edges:
        source = node_by_id.get(str(edge.get('source')))
        target = node_by_id.get(str(edge.get('target')))
        if not source or not target:
            continue
        cfg = dict(_node_config(target))
        new_cfg, changed = wire_target_config_on_connect(
            _node_type(source),
            _node_type(target),
            cfg,
            source_node=source,
        )
        if not changed:
            continue
        target['config'] = new_cfg
        if isinstance(target.get('data'), dict):
            target['data'] = {**target['data'], 'config': new_cfg, 'type': _node_type(target)}
        node_by_id[str(target.get('id'))] = target

    workflow['nodes'] = [node_by_id.get(str(n.get('id')), n) for n in nodes]
    return workflow
