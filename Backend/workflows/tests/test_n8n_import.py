"""Tests for n8n -> Flowly workflow import converter."""

from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase

from workflows.services.n8n_import import (
    N8N_NODE_MAP,
    SKIP_N8N_TYPES,
    _map_node_type,
    _n8n_suffix,
    convert_n8n_workflow,
    is_n8n_workflow,
)


class N8nImportMappingTests(SimpleTestCase):
    def test_common_nodes_preserve_type_without_claiming_compatibility(self):
        cases = {
            'n8n-nodes-base.httpRequest': 'http_request',
            'n8n-nodes-base.splitOut': 'split',
            'n8n-nodes-base.executeWorkflow': 'subworkflow',
            'n8n-nodes-base.hubspot': 'http_request',
            'n8n-nodes-base.googleCalendarTool': 'http_request',
            'n8n-nodes-base.markdown': 'text_template',
            'n8n-nodes-base.mcpClientTool': 'tool',
        }
        for n8n_type, expected in cases.items():
            flowly, exact = _map_node_type(n8n_type)
            self.assertEqual(exact, n8n_type == 'n8n-nodes-base.httpRequest', msg=n8n_type)
            self.assertEqual(flowly, expected)

    def test_tool_suffix_resolves_parent(self):
        flowly, exact = _map_node_type('n8n-nodes-base.postgresTool')
        self.assertFalse(exact)
        self.assertEqual(flowly, 'postgres')

    def test_unknown_trigger_maps_webhook(self):
        flowly, exact = _map_node_type('n8n-nodes-base.customSaasTrigger')
        self.assertFalse(exact)
        self.assertEqual(flowly, 'webhook')

    def test_convert_minimal_workflow(self):
        payload = {
            'name': 'Demo',
            'nodes': [
                {
                    'id': '1',
                    'name': 'When clicking',
                    'type': 'n8n-nodes-base.manualTrigger',
                    'position': [0, 0],
                    'parameters': {},
                },
                {
                    'id': '2',
                    'name': 'HTTP',
                    'type': 'n8n-nodes-base.httpRequest',
                    'position': [200, 0],
                    'parameters': {'url': 'https://example.com', 'method': 'GET'},
                },
            ],
            'connections': {
                'When clicking': {
                    'main': [[{'node': 'HTTP', 'type': 'main', 'index': 0}]],
                },
            },
        }
        self.assertTrue(is_n8n_workflow(payload))
        result = convert_n8n_workflow(payload, source_path='demo.json')
        self.assertTrue(result['name'].startswith('[n8n]'))
        self.assertGreaterEqual(len(result['nodes']), 2)
        self.assertEqual(result['meta']['unmapped_nodes'], 0)

    def test_repo_coverage_when_available(self):
        root = Path('/external/n8n-workflows/workflows')
        if not root.exists():
            root = Path(__file__).resolve().parents[3] / '_external' / 'n8n-workflows' / 'workflows'
        if not root.exists():
            self.skipTest('n8n-workflows repo not mounted')

        suffixes: set[str] = set()
        inexact: set[str] = set()
        for path in root.rglob('*.json'):
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            for node in data.get('nodes', []):
                suffix = _n8n_suffix(node.get('type', ''))
                if suffix in SKIP_N8N_TYPES:
                    continue
                suffixes.add(suffix)
                _, exact = _map_node_type(node.get('type', ''))
                if not exact:
                    inexact.add(suffix)

        self.assertGreater(len(suffixes), 100)
        self.assertTrue(inexact, msg='类型映射不能被误报为已完成业务兼容')
        self.assertGreater(len(N8N_NODE_MAP), 200)
