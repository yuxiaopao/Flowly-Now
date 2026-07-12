"""Tests for rule-based workflow optimizer."""
from django.test import SimpleTestCase

from workflows.services.workflow_optimizer import analyze_workflow


class WorkflowOptimizerTests(SimpleTestCase):
    def test_empty_workflow_returns_warning(self):
        suggestions = analyze_workflow([], [], ['maintainability'])
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]['type'], 'maintainability')

    def test_llm_without_timeout_flagged(self):
        nodes = [{
            'id': 'llm-1',
            'type': 'llm',
            'label': 'AI 处理',
            'config': {},
        }]
        suggestions = analyze_workflow(nodes, [], ['performance'])
        self.assertTrue(any(s['type'] == 'performance' for s in suggestions))
        self.assertIn('llm-1', suggestions[0]['affectedNodes'])

    def test_http_without_retry_flagged(self):
        nodes = [{
            'id': 'http-1',
            'type': 'http',
            'label': '获取数据',
            'config': {'url': 'https://example.com'},
        }]
        suggestions = analyze_workflow(nodes, [], ['error_handling'])
        self.assertTrue(any(s['severity'] == 'critical' for s in suggestions))
