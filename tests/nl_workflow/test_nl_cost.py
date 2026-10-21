# -*- coding: utf-8 -*-
"""
Tests for Workflow Cost Estimation.

Tests the _estimate_workflow_cost method in NLToWorkflowService.
"""

import pytest
from nl_to_workflow.services import NLToWorkflowService


class TestNLCostEstimation:
    """Test workflow cost estimation."""

    def test_estimate_empty_workflow(self):
        """Empty workflow should return minimal cost."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Empty Workflow',
            'nodes': [],
            'edges': []
        }

        cost = service._estimate_workflow_cost(workflow)
        assert cost == 0.0

    def test_estimate_only_start_end_nodes(self):
        """Workflow with only start and end nodes should have low cost."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Minimal Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # start (0.1) + end (0.1) + edge (0.1) = 0.3
        assert cost == 0.3

    def test_estimate_llm_nodes(self):
        """LLM nodes should increase cost significantly."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'LLM Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI', 'config': {'model': 'llama3'}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # start (0.1) + llm (10.0) + end (0.1) + edges (2 * 0.1) = 10.3
        assert cost == 10.4

    def test_estimate_multiple_llm_nodes(self):
        """Multiple LLM nodes should scale cost."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Multi LLM Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI 1', 'config': {'model': 'llama3'}},
                {'id': 'node_3', 'type': 'llm', 'name': 'AI 2', 'config': {'model': 'llama3'}},
                {'id': 'node_4', 'type': 'llm', 'name': 'AI 3', 'config': {'model': 'llama3'}},
                {'id': 'node_5', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'},
                {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4'},
                {'id': 'edge_4', 'source': 'node_4', 'target': 'node_5'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # start (0.1) + 3*llm (3 * 10.0) + end (0.1) + edges (4 * 0.1) = 30.5
        assert cost == 30.6

    def test_estimate_premium_model_gpt4(self):
        """Premium models like GPT-4 should cost more."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'GPT-4 Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'GPT-4', 'config': {'model': 'gpt-4'}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # start (0.1) + llm with gpt-4 (10.0 * 2.0) + end (0.1) + edges (2 * 0.1) = 20.3
        assert cost == 20.4

    def test_estimate_premium_model_claude(self):
        """Claude models should cost more."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Claude Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'Claude', 'config': {'model': 'claude-3'}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # start (0.1) + llm with claude (10.0 * 2.0) + end (0.1) + edges (2 * 0.1) = 20.3
        assert cost == 20.4

    def test_estimate_budget_model(self):
        """Budget models like GPT-3.5 should cost less."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'GPT-3.5 Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'GPT-3.5', 'config': {'model': 'gpt-3.5-turbo'}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # start (0.1) + llm with gpt-3.5 (10.0 * 0.5) + end (0.1) + edges (2 * 0.1) = 5.3
        assert cost == 5.4

    def test_estimate_tool_nodes(self):
        """Tool nodes should have medium cost."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Tool Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'tool', 'name': 'API', 'config': {'tool_name': 'http', 'parameters': {}}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # start (0.1) + tool (3.0) + end (0.1) + edges (2 * 0.1) = 3.3
        assert cost == 3.4

    def test_estimate_code_nodes(self):
        """Code nodes should have medium cost."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Code Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'code', 'name': 'Transform', 'config': {'code': 'x = 1'}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # start (0.1) + code (2.0) + end (0.1) + edges (2 * 0.1) = 2.3
        assert cost == 2.4

    def test_estimate_condition_nodes(self):
        """Condition nodes should have low cost."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Condition Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'condition', 'name': 'Check', 'config': {}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # start (0.1) + condition (0.5) + end (0.1) + edges (2 * 0.1) = 0.8
        assert cost == 0.9

    def test_estimate_complex_workflow(self, complex_workflow):
        """Complex workflow should have higher cost due to node count multiplier."""
        service = NLToWorkflowService()
        cost = service._estimate_workflow_cost(complex_workflow)
        # Should be higher than simple workflows
        assert cost > 10.0

    def test_estimate_validation_includes_cost(self, sample_workflow):
        """_validate_workflow should include estimated_cost in result."""
        service = NLToWorkflowService()
        validated = service._validate_workflow(sample_workflow)
        assert 'estimated_cost' in validated
        assert validated['estimated_cost'] >= 0

    def test_cost_rounding(self):
        """Cost should be rounded to 2 decimal places."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Cost Test',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI', 'config': {'model': 'gpt-4'}},
                {'id': 'node_3', 'type': 'tool', 'name': 'API', 'config': {'tool_name': 'http', 'parameters': {'a': 1, 'b': 2}}},
                {'id': 'node_4', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'},
                {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # Check that cost is rounded to 2 decimal places
        assert cost == round(cost, 2)

    def test_cost_with_http_parameters(self):
        """HTTP nodes with parameters should have slightly higher cost."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'HTTP Params Test',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'http', 'name': 'API', 'config': {'tool_name': 'http', 'parameters': {'a': 1, 'b': 2, 'c': 3}}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        cost = service._estimate_workflow_cost(workflow)
        # tool/http base (3.0) + 3 params * 0.1 = 3.3
        # + start (0.1) + end (0.1) + edges (2 * 0.1) = 0.4
        # Total = 3.7
        assert cost == 3.7
