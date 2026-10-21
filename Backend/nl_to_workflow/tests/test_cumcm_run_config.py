# -*- coding: utf-8 -*-
"""Tests for CUMCM run-config presets and wiring."""

from django.test import SimpleTestCase

from nl_to_workflow.cumcm_prompts import (
    build_paper_section_specs,
    get_decompose_system,
    get_format_check_prompt,
    get_logic_adversarial_prompt,
)
from nl_to_workflow.cumcm_run_config import (
    assert_strict_for_testing,
    build_run_config_prompt_block,
    default_cumcm_config,
    fast_review_config,
    get_preset,
    get_testing_config,
    strictest_test_config,
)
from nl_to_workflow.cumcm_solvers import build_chart_code
from nl_to_workflow.cumcm_enrichment import expand_cumcm_pipeline


class CumcmRunConfigTests(SimpleTestCase):
    def test_default_is_strictest_testing_mode(self):
        cfg = default_cumcm_config()
        self.assertEqual(cfg, get_testing_config())
        self.assertEqual(cfg.contest, 'cumcm')
        self.assertEqual(cfg.review_mode, 'strict')
        self.assertTrue(cfg.logic_adversarial_review)
        self.assertEqual(cfg.chart_palette, 'bw')
        self.assertGreaterEqual(cfg.min_models_per_subproblem, 3)
        self.assertGreaterEqual(cfg.paper_improve_loops, 2)
        self.assertTrue(cfg.chart_vision_qa)
        self.assertTrue(cfg.flowchart_vision_qa)
        self.assertLessEqual(cfg.page_limit_body, 25)
        assert_strict_for_testing(cfg)

    def test_strictest_preset_aliases(self):
        for name in ('strictest', 'test', 'testing', 'cumcm_default'):
            cfg = get_preset(name)
            assert_strict_for_testing(cfg)

    def test_huawei_rich_is_explicit_preset(self):
        cfg = get_preset('huawei_rich')
        self.assertEqual(cfg.contest, 'huawei')
        self.assertGreaterEqual(cfg.page_limit_body, 40)
        self.assertGreaterEqual(cfg.min_figures, 30)

    def test_fast_disables_logic_review_and_fails_assert(self):
        cfg = fast_review_config()
        self.assertEqual(cfg.review_mode, 'fast')
        self.assertFalse(cfg.logic_adversarial_review)
        with self.assertRaises(ValueError):
            assert_strict_for_testing(cfg)

    def test_paper_sections_include_extras(self):
        specs = build_paper_section_specs(strictest_test_config())
        keys = [k for k, _, _ in specs]
        self.assertIn('tech_route', keys)
        self.assertIn('method_compare', keys)
        self.assertIn('ai_declaration', keys)
        self.assertIn('modeling', keys)

    def test_prompt_block_mentions_page_limit(self):
        block = build_run_config_prompt_block(get_testing_config())
        self.assertIn('页', block)
        self.assertIn('bw', block)
        self.assertIn('视觉质检', block)

    def test_format_check_fast_vs_strict(self):
        strict = get_format_check_prompt(get_testing_config())
        fast = get_format_check_prompt(fast_review_config())
        self.assertIn('完整审查', strict + '严格')
        self.assertTrue(len(strict) > len(fast) - 500)
        self.assertIn('快速', fast)

    def test_logic_prompt(self):
        p = get_logic_adversarial_prompt()
        self.assertIn('方向反', p)
        self.assertIn('ok_to_write_paper', p)

    def test_decompose_includes_candidate_floor(self):
        p = get_decompose_system(5, get_testing_config())
        self.assertIn('3', p)
        self.assertIn('model_candidates', p)

    def test_chart_bw_replaces_blue(self):
        code = build_chart_code(palette='bw')
        self.assertNotIn('#2563eb', code)
        self.assertIn('#000000', code)

    def test_expand_adds_logic_and_config(self):
        wf, changes = expand_cumcm_pipeline(None, subproblem_count=5)
        labels = [n.get('name') or n.get('data', {}).get('label') for n in wf['nodes']]
        self.assertIn('逻辑对抗复核', labels)
        self.assertIn('技术路线', labels)
        self.assertIn('候选方法对比', labels)
        self.assertIn('AI工具使用声明', labels)
        self.assertIn('_cumcm_run_config', wf)
        cfg = wf['_cumcm_run_config']
        self.assertEqual(cfg['chart_palette'], 'bw')
        self.assertEqual(cfg['review_mode'], 'strict')
        self.assertTrue(cfg['logic_adversarial_review'])
        self.assertGreaterEqual(cfg['min_models_per_subproblem'], 3)
        assert_strict_for_testing(
            __import__(
                'nl_to_workflow.cumcm_run_config', fromlist=['CumcmRunConfig']
            ).CumcmRunConfig.from_dict(cfg)
        )
        self.assertTrue(any('逻辑对抗' in c or '章节' in c for c in changes))

    def test_expand_fast_skips_logic(self):
        wf, _ = expand_cumcm_pipeline(
            None, subproblem_count=3, run_config=get_preset('fast')
        )
        labels = [n.get('name') for n in wf['nodes']]
        self.assertNotIn('逻辑对抗复核', labels)
