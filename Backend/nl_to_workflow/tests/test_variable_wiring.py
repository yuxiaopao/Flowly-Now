"""Regression tests for edge-based variable wiring (no chaotic / duplicate params)."""
from nl_to_workflow.variable_wiring import (
    wire_target_config_on_connect,
    wire_workflow_variable_refs,
)


def test_image_to_video_only_wires_image_slot():
    cfg, changed = wire_target_config_on_connect('image_generation', 'video_generation', {})
    assert changed
    assert cfg.get('inputImage') == '{images.0.url}'
    assert 'prompt' not in cfg
    assert 'text' not in cfg
    assert 'input_image' not in cfg  # no duplicate aliases


def test_llm_to_video_only_wires_prompt_slot():
    cfg, changed = wire_target_config_on_connect('llm', 'video_generation', {})
    assert changed
    assert cfg.get('prompt') == '{text}'
    assert 'inputImage' not in cfg
    assert 'text' not in cfg  # single primary field only


def test_multi_edge_image_then_llm_no_overwrite():
    wf = {
        'nodes': [
            {'id': 'img', 'type': 'image_generation', 'config': {}},
            {'id': 'llm', 'type': 'llm', 'config': {}},
            {'id': 'vid', 'type': 'video_generation', 'config': {}},
        ],
        'edges': [
            {'source': 'img', 'target': 'vid'},
            {'source': 'llm', 'target': 'vid'},
        ],
    }
    out = wire_workflow_variable_refs(wf)
    vid = next(n for n in out['nodes'] if n['id'] == 'vid')
    assert vid['config']['inputImage'] == '{images.0.url}'
    assert vid['config']['prompt'] == '{text}'
    assert 'text' not in vid['config']
    assert 'input_image' not in vid['config']


def test_does_not_overwrite_user_values():
    cfg, changed = wire_target_config_on_connect(
        'llm', 'image_generation', {'prompt': '手写提示词'},
    )
    assert not changed
    assert cfg['prompt'] == '手写提示词'


def test_alias_already_filled_skips_duplicate():
    cfg, changed = wire_target_config_on_connect(
        'llm', 'image_generation', {'text': '{text}'},
    )
    assert not changed
    assert 'prompt' not in cfg


def test_unrelated_pair_no_wire():
    cfg, changed = wire_target_config_on_connect('video_generation', 'image_generation', {})
    assert not changed
    assert cfg == {}


def test_rag_to_image_no_wire():
    cfg, changed = wire_target_config_on_connect('rag', 'image_generation', {})
    assert not changed


def test_start_to_llm_no_wire():
    cfg, changed = wire_target_config_on_connect('start', 'llm', {})
    assert not changed


def test_input_uses_variable_name():
    source = {'id': 'in', 'type': 'input', 'config': {'input_name': 'prompt'}}
    cfg, changed = wire_target_config_on_connect(
        'input', 'image_generation', {}, source_node=source,
    )
    assert changed
    assert cfg['prompt'] == '{prompt}'


def test_image_editing_slots_split():
    img_cfg, _ = wire_target_config_on_connect('image_generation', 'image_editing', {})
    assert img_cfg.get('inputImage') == '{images.0.url}'
    assert 'instruction' not in img_cfg
    assert 'prompt' not in img_cfg

    llm_cfg, _ = wire_target_config_on_connect('llm', 'image_editing', {})
    assert llm_cfg.get('instruction') == '{text}'
    assert 'inputImage' not in llm_cfg
