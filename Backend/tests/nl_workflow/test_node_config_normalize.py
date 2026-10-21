"""Unit tests for domain-agnostic NL node config normalization."""
from nl_to_workflow.node_config_normalize import (
    normalize_code_node_config,
    normalize_image_generation_node_config,
    normalize_loop_node_config,
    normalize_node_config,
    normalize_subtitle_generation_node_config,
    normalize_video_generation_node_config,
)


def test_code_script_alias_and_js_replaced_with_python():
    cfg = normalize_code_node_config({
        'language': 'javascript',
        'script': "const shots = JSON.parse('{input}'); return shots;",
    })
    assert cfg['language'] == 'python'
    assert 'enriched_shots' in cfg['code']
    assert cfg['code'] == cfg['script']


def test_loop_aliases_and_mustache_items_use_input_source():
    cfg = normalize_loop_node_config({
        'items': '{{plot_chapters}}',
        'item_var': 'current_chapter',
        'max': 8,
        'mode': 'For 循环',
    })
    assert cfg['item_variable'] == 'current_chapter'
    assert 'item_var' not in cfg
    assert cfg['items_source'] == 'input'
    assert 'items' not in cfg
    assert cfg['max_iterations'] == 8
    assert cfg['loop_type'] == 'for_each'


def test_image_and_video_provider_models_normalized():
    image = normalize_image_generation_node_config({
        'provider': 'agnes',
        'model': 'stable-diffusion-xl',
        'prompt': '{theme}',
        'batch_input': '{{enriched_shots}}',
    })
    assert image['model'] == 'agnes-image-2.1-flash'
    assert image['prompt'] == '{prompt}'
    assert 'batch_input' not in image

    video = normalize_video_generation_node_config({
        'provider': 'agnes',
        'model': 'runway-gen3',
        'keyframes_input': '{{generated_images}}',
    })
    assert video['model'] == 'agnes-video-v2.0'
    assert video['inputImage'] == '{images.0.url}'
    assert 'keyframes_input' not in video


def test_subtitle_input_aliases():
    cfg = normalize_subtitle_generation_node_config({
        'input_video': '{{video_clips}}',
        'reference_audio': '{{vo_script}}',
    })
    assert cfg['inputPath'] == '{video_url}'
    assert 'reference_audio' not in cfg


def test_dispatch_normalize_node_config():
    out = normalize_node_config('code', {'script': 'output = {"ok": True}'})
    assert 'output = {"ok": True}' in out['code']
