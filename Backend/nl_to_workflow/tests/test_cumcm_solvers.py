# -*- coding: utf-8 -*-
"""Tests for CUMCM solver code generation and sandbox execution."""

import importlib.util
import json
from django.test import SimpleTestCase

from nl_to_workflow.cumcm_solvers import (
    SOLVER_TYPES,
    build_chart_code,
    build_sensitivity_code,
    build_solver_code,
    solver_catalog_for_prompt,
)


def _load_sandbox_module():
    spec = importlib.util.spec_from_file_location(
        'sandbox_service', 'workflows/services/sandbox_service.py'
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CumcmSolversTests(SimpleTestCase):
    def test_solver_types_catalog(self):
        self.assertIn('linear_programming', SOLVER_TYPES)
        self.assertIn('integer_programming', SOLVER_TYPES)
        self.assertIn('monte_carlo', SOLVER_TYPES)
        self.assertIn('regression', SOLVER_TYPES)
        self.assertIn('time_series', SOLVER_TYPES)
        self.assertIn('solver_type', solver_catalog_for_prompt())
        self.assertIn('integer_programming', solver_catalog_for_prompt())

    def test_build_solver_code_index(self):
        code = build_solver_code(2)
        self.assertIn('idx = 2', code)
        self.assertIn('linear_programming', code)
        self.assertIn('time_series', code)

    def test_sandbox_numpy_linprog(self):
        mod = _load_sandbox_module()
        sb = mod.SubprocessSandbox()
        code = build_solver_code(1)
        # Simulate upstream model spec in node_outputs
        payload = {
            'node_outputs': {
                'model': {
                    'text': (
                        '{"subproblem_index": 1, "solver_type": "linear_programming", '
                        '"parameters": {"c": [1, 2], "A_ub": [[1, 1]], "b_ub": [3], '
                        '"bounds": [[0, null], [0, null]]}}'
                    ).replace('null', 'None'),
                }
            }
        }
        # Fix JSON null -> Python None won't work in JSON; use large bound instead
        payload['node_outputs']['model']['text'] = (
            '{"subproblem_index": 1, "solver_type": "linear_programming", '
            '"parameters": {"c": [1, 2], "A_ub": [[1, 1]], "b_ub": [3]}}'
        )
        r = sb.execute(code, payload)
        self.assertTrue(r.success, r.error)
        out = r.output or {}
        self.assertEqual(out.get('solver_type'), 'linear_programming')
        comp = out.get('computed') or {}
        self.assertTrue(comp.get('success'))

    def test_sandbox_regression(self):
        mod = _load_sandbox_module()
        sb = mod.SubprocessSandbox()
        code = build_solver_code(1)
        payload = {
            'node_outputs': {
                'model': {
                    'text': (
                        '{"subproblem_index": 1, "solver_type": "regression", '
                        '"parameters": {"x": [1, 2, 3, 4], "y": [2.1, 4.0, 5.9, 8.2], "degree": 1}}'
                    ),
                }
            }
        }
        r = sb.execute(code, payload)
        self.assertTrue(r.success, r.error)
        comp = (r.output or {}).get('computed') or {}
        self.assertTrue(comp.get('success'))
        self.assertIn('coefficients', comp)

    def test_sandbox_integer_programming(self):
        mod = _load_sandbox_module()
        sb = mod.SubprocessSandbox()
        code = build_solver_code(1)
        payload = {
            'node_outputs': {
                'model': {
                    'text': (
                        '{"subproblem_index": 1, "solver_type": "integer_programming", '
                        '"parameters": {"c": [1, 1], "A_ub": [[1, 1]], "b_ub": [1.5], '
                        '"integrality": [1, 1]}}'
                    ),
                }
            }
        }
        r = sb.execute(code, payload)
        self.assertTrue(r.success, r.error)
        comp = (r.output or {}).get('computed') or {}
        self.assertEqual(comp.get('solver'), 'integer_programming')

    def test_sandbox_monte_carlo(self):
        mod = _load_sandbox_module()
        sb = mod.SubprocessSandbox()
        code = build_solver_code(1)
        payload = {
            'node_outputs': {
                'model': {
                    'text': (
                        '{"subproblem_index": 1, "solver_type": "monte_carlo", '
                        '"parameters": {"baseline": {"a": 10, "b": 20}, '
                        '"coefficients": {"a": 1, "b": 2}, "n_simulations": 500, "seed": 42}}'
                    ),
                }
            }
        }
        r = sb.execute(code, payload)
        self.assertTrue(r.success, r.error)
        comp = (r.output or {}).get('computed') or {}
        self.assertTrue(comp.get('success'))
        self.assertIn('percentiles', comp)
        self.assertIn('histogram', comp)

    def test_solver_hints_from_contest_input_when_llm_refuses(self):
        """DEFAULT_INPUT string + empty LLM model text must still solve via solver_hints."""
        mod = _load_sandbox_module()
        sb = mod.SubprocessSandbox()
        code = build_solver_code(1)
        contest = {
            'contest': 'CUMCM',
            'solver_hints': [{
                'subproblem_index': 1,
                'solver_type': 'linear_programming',
                'parameters': {
                    'c': [3.2, 2.8],
                    'A_ub': [[1, 1]],
                    'b_ub': [10],
                    'bounds': [[0, 8], [0, 8]],
                },
            }],
        }
        payload = {
            'text': '【CUMCM 赛题输入】\n' + json.dumps(contest, ensure_ascii=False),
            'input': '【CUMCM 赛题输入】\n' + json.dumps(contest, ensure_ascii=False),
            'node_outputs': {
                'model': {
                    'text': '我无法完成此任务。子问题信息为空。',
                },
                'input_node': {
                    'text': '【CUMCM 赛题输入】\n' + json.dumps(contest, ensure_ascii=False),
                },
            },
        }
        r = sb.execute(code, payload)
        self.assertTrue(r.success, r.error)
        out = r.output or {}
        self.assertEqual(out.get('solver_type'), 'linear_programming')
        comp = out.get('computed') or {}
        self.assertTrue(comp.get('success'), comp)

    def test_chart_generation_regression(self):
        mod = _load_sandbox_module()
        sb = mod.SubprocessSandbox()
        code = build_chart_code()
        payload = {
            'node_outputs': {
                'collect': {
                    'text': json.dumps({
                        'subproblem_results': [{
                            'subproblem_index': 1,
                            'computed': {
                                'solver': 'regression',
                                'x': [1, 2, 3, 4],
                                'y': [2.1, 4.0, 5.8, 8.2],
                                'fitted': [2.0, 4.1, 5.9, 8.1],
                            },
                        }],
                    }),
                }
            }
        }
        r = sb.execute(code, payload)
        self.assertTrue(r.success, r.error)
        out = r.output or {}
        if out.get('warning'):
            self.skipTest(out['warning'])
        self.assertGreaterEqual(out.get('count', 0), 1)
        self.assertTrue(any(c.get('has_image') for c in out.get('charts', [])))

    def test_sensitivity_code_runs(self):
        mod = _load_sandbox_module()
        sb = mod.SubprocessSandbox()
        code = build_sensitivity_code()
        payload = {
            'node_outputs': {
                'r1': {
                    'text': (
                        '{"subproblem_index": 1, "computed": '
                        '{"success": true, "objective_value": 100.0}}'
                    ),
                }
            }
        }
        r = sb.execute(code, payload)
        self.assertTrue(r.success, r.error)
        self.assertGreaterEqual((r.output or {}).get('count', 0), 1)

    def test_scientific_stack_detection(self):
        mod = _load_sandbox_module()
        code = build_solver_code(1)
        self.assertTrue(mod.code_uses_scientific_stack(code))
        self.assertTrue(mod.docker_image_lacks_scientific_stack('python:3.12-slim'))
        self.assertFalse(mod.docker_image_lacks_scientific_stack('flowly-code-sandbox:3.12'))
