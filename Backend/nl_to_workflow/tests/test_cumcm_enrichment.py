# -*- coding: utf-8 -*-
"""Tests for CUMCM workflow enrichment."""

from django.test import SimpleTestCase

from nl_to_workflow.cumcm_enrichment import (
    build_cumcm_workflow,
    enrich_cumcm_workflow,
    expand_cumcm_pipeline,
    is_cumcm_intent,
)


class CumcmEnrichmentTests(SimpleTestCase):
    def test_intent_detection(self):
        self.assertTrue(is_cumcm_intent('帮我搭建 CUMCM 数学建模工作流'))
        self.assertTrue(is_cumcm_intent('全国大学生数学建模竞赛论文'))
        self.assertFalse(is_cumcm_intent('做一个客服机器人'))

    def test_build_workflow_structure(self):
        wf = build_cumcm_workflow('测试赛题', subproblem_count=3)
        self.assertIn('CUMCM', wf.get('name', ''))
        nodes = wf.get('nodes') or []
        edges = wf.get('edges') or []
        self.assertGreaterEqual(len(nodes), 34)
        self.assertGreaterEqual(len(edges), 40)
        types = {n.get('type') for n in nodes}
        self.assertIn('llm', types)
        self.assertIn('code', types)
        self.assertIn('input', types)
        self.assertIn('output', types)
        names = [n.get('name') or '' for n in nodes]
        self.assertTrue(any('数值灵敏度' in n for n in names))
        self.assertTrue(any('数值求解' in n for n in names))
        self.assertTrue(any('图表' in n for n in names))
        self.assertTrue(any('三线表' in n for n in names))
        self.assertTrue(any('格式自检' in n for n in names))
        fw = [n for n in nodes if n.get('type') == 'file_writer']
        paths = [n.get('config', {}).get('path', '') for n in fw]
        self.assertIn('paper/main.md', paths)
        self.assertIn('figures/TABLE_summary.md', paths)
        self.assertIn('paper/main.docx', paths)
        # 2025 A题 default input
        inp = next(n for n in nodes if n.get('type') == 'input')
        dv = (inp.get('config') or {}).get('default_value') or ''
        self.assertIn('烟幕干扰弹', dv)
        self.assertIn('2025', dv)
        self.assertIn('FY1', dv)

    def test_build_a_problem_five_subproblems(self):
        wf = build_cumcm_workflow('2025 A题', subproblem_count=5)
        solve_nodes = [n for n in wf['nodes'] if '数值求解' in (n.get('name') or '')]
        self.assertEqual(len(solve_nodes), 5)
        self.assertGreaterEqual(len(wf['nodes']), 44)

    def test_expand_subproblem_count(self):
        wf, changes = expand_cumcm_pipeline(None, subproblem_count=4)
        solve_nodes = [n for n in wf['nodes'] if '数值求解' in (n.get('name') or '')]
        self.assertEqual(len(solve_nodes), 4)
        self.assertTrue(any('4' in c for c in changes))

    def test_enrich_from_empty(self):
        empty = {'name': '', 'nodes': [], 'edges': []}
        wf, changes = enrich_cumcm_workflow(empty, subproblem_count=2)
        self.assertGreater(len(wf['nodes']), 15)
        self.assertTrue(changes)
