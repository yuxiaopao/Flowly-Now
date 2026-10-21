"""Ensure parallel shot branches do not share last-wins prompts."""
from workflows.services.langchain_service import resolve_execution_context


def test_resolve_context_prefers_branch_upstream_over_polluted_variables():
    ctx = {
        'input_data': {},
        'variables': {
            'image_prompt': 'LAST_WINS_WRONG_SHOT',
            'shot_12_image_prompt': 'shot12',
        },
        'node_outputs': {
            'pick1': {'image_prompt': 'shot1', 'shot_01_image_prompt': 'shot1'},
            'pick2': {'image_prompt': 'shot2', 'shot_02_image_prompt': 'shot2'},
            'pick12': {'image_prompt': 'LAST_WINS_WRONG_SHOT', 'shot_12_image_prompt': 'shot12'},
        },
        '_branch_upstream': {
            'image_prompt': 'shot3_from_predecessor',
            'shot_03_image_prompt': 'shot3_from_predecessor',
        },
        'metadata': {},
    }
    merged = resolve_execution_context(ctx)
    assert merged['image_prompt'] == 'shot3_from_predecessor'
    assert merged['shot_03_image_prompt'] == 'shot3_from_predecessor'
    # Must not flatten last node_outputs onto top-level
    assert merged['image_prompt'] != 'LAST_WINS_WRONG_SHOT'


def test_resolve_context_keeps_node_outputs_for_collect():
    ctx = {
        'input_data': {},
        'variables': {},
        'node_outputs': {'a': {'video_url': 'http://a'}, 'b': {'video_url': 'http://b'}},
        'metadata': {},
    }
    merged = resolve_execution_context(ctx)
    assert merged['node_outputs']['a']['video_url'] == 'http://a'
    assert merged['node_outputs']['b']['video_url'] == 'http://b'
    # No last-wins video_url on top-level without branch overlay
    assert 'video_url' not in merged or merged.get('video_url') in (None, '')


def test_pick_script_emits_unique_shot_keys():
    from nl_to_workflow.short_drama_enrichment import _pick_script, build_short_drama_workflow

    script = _pick_script(3)
    assert 'shot_key + \'_image_prompt\'' in script or "shot_key + '_image_prompt'" in script
    assert 'SHOT_INDEX = 3' in script
    assert 'dup_hit' in script

    wf = build_short_drama_workflow('测试短剧', shot_count=12)
    images = [n for n in wf['nodes'] if n.get('type') == 'image_generation']
    videos = [n for n in wf['nodes'] if n.get('type') == 'video_generation']
    assert len(images) == 12
    prompts = [n['config']['prompt'] for n in images]
    assert prompts[0] == '{shot_01_image_prompt}'
    assert prompts[11] == '{shot_12_image_prompt}'
    assert len(set(prompts)) == 12
    vprompts = [n['config']['prompt'] for n in videos]
    assert vprompts[4] == '{shot_05_video_motion_prompt}'
    assert len(set(vprompts)) == 12
