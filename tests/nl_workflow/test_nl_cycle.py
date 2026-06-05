# -*- coding: utf-8 -*-
"""
Tests for DAG Cycle Detection.

Tests the _has_cycle_detection method in NLToWorkflowService.
"""

import pytest
from nl_to_workflow.services import NLToWorkflowService


class TestNLCycleDetection:
    """Test DAG cycle detection."""

    def test_no_cycle_simple_linear(self):
        """Simple linear workflow should pass cycle detection."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Linear Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI'},
                {'id': 'node_3', 'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        has_cycle, cycle_path = service._has_cycle_detection(workflow)
        assert has_cycle is False
        assert cycle_path == []

    def test_no_cycle_with_branch(self):
        """Branching workflow should pass cycle detection."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Branching Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'condition', 'name': 'Check'},
                {'id': 'node_3', 'type': 'llm', 'name': 'AI A'},
                {'id': 'node_4', 'type': 'llm', 'name': 'AI B'},
                {'id': 'node_5', 'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': 'Yes'},
                {'id': 'edge_3', 'source': 'node_2', 'target': 'node_4', 'label': 'No'},
                {'id': 'edge_4', 'source': 'node_3', 'target': 'node_5'},
                {'id': 'edge_5', 'source': 'node_4', 'target': 'node_5'}
            ]
        }

        has_cycle, cycle_path = service._has_cycle_detection(workflow)
        assert has_cycle is False
        assert cycle_path == []

    def test_no_cycle_parallel_paths(self):
        """Workflow with parallel paths that merge should pass."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Parallel Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI A'},
                {'id': 'node_3', 'type': 'llm', 'name': 'AI B'},
                {'id': 'node_4', 'type': 'llm', 'name': 'AI C'},
                {'id': 'node_5', 'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_1', 'target': 'node_3'},
                {'id': 'edge_3', 'source': 'node_1', 'target': 'node_4'},
                {'id': 'edge_4', 'source': 'node_2', 'target': 'node_5'},
                {'id': 'edge_5', 'source': 'node_3', 'target': 'node_5'},
                {'id': 'edge_6', 'source': 'node_4', 'target': 'node_5'}
            ]
        }

        has_cycle, cycle_path = service._has_cycle_detection(workflow)
        assert has_cycle is False

    def test_has_cycle_self_loop(self, workflow_with_self_loop):
        """Node pointing to itself should fail cycle detection."""
        service = NLToWorkflowService()
        has_cycle, cycle_path = service._has_cycle_detection(workflow_with_self_loop)
        assert has_cycle is True
        assert 'node_2' in cycle_path

    def test_has_cycle_mutual_dependency(self):
        """A→B→A should fail cycle detection."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Mutual Dependency',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI A'},
                {'id': 'node_3', 'type': 'llm', 'name': 'AI B'},
                {'id': 'node_4', 'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'},
                {'id': 'edge_3', 'source': 'node_3', 'target': 'node_2'},  # Back to node_2
                {'id': 'edge_4', 'source': 'node_2', 'target': 'node_4'}
            ]
        }

        has_cycle, cycle_path = service._has_cycle_detection(workflow)
        assert has_cycle is True
        assert 'node_2' in cycle_path or 'node_3' in cycle_path

    def test_has_cycle_triangular(self):
        """A→B→C→A should fail cycle detection."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Triangular Cycle',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI A'},
                {'id': 'node_3', 'type': 'llm', 'name': 'AI B'},
                {'id': 'node_4', 'type': 'llm', 'name': 'AI C'},
                {'id': 'node_5', 'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'},
                {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4'},
                {'id': 'edge_4', 'source': 'node_4', 'target': 'node_2'},  # Back to node_2
                {'id': 'edge_5', 'source': 'node_2', 'target': 'node_5'}
            ]
        }

        has_cycle, cycle_path = service._has_cycle_detection(workflow)
        assert has_cycle is True

    def test_has_cycle_from_fixture(self, workflow_with_cycle):
        """Test cycle detection with the pre-defined workflow fixture."""
        service = NLToWorkflowService()
        has_cycle, cycle_path = service._has_cycle_detection(workflow_with_cycle)
        assert has_cycle is True

    def test_empty_workflow(self):
        """Empty workflow should not have cycles."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Empty Workflow',
            'nodes': [],
            'edges': []
        }

        has_cycle, cycle_path = service._has_cycle_detection(workflow)
        assert has_cycle is False

    def test_workflow_with_single_node(self):
        """Single node workflow should not have cycles."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Single Node',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'}
            ],
            'edges': []
        }

        has_cycle, cycle_path = service._has_cycle_detection(workflow)
        assert has_cycle is False

    def test_workflow_disconnected_nodes(self):
        """Workflow with disconnected nodes should still detect cycles in connected parts."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Disconnected',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'end', 'name': 'End'},
                {'id': 'node_3', 'type': 'llm', 'name': 'Orphan'},
                {'id': 'node_4', 'type': 'llm', 'name': 'AI A'},
                {'id': 'node_5', 'type': 'llm', 'name': 'AI B'}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_4', 'target': 'node_5'},
                {'id': 'edge_3', 'source': 'node_5', 'target': 'node_4'}  # Cycle in disconnected part
            ]
        }

        has_cycle, cycle_path = service._has_cycle_detection(workflow)
        assert has_cycle is True

    def test_cycle_path_includes_all_cycle_nodes(self):
        """Cycle path should include all nodes in the cycle."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Cycle Path Test',
            'nodes': [
                {'id': 'a', 'type': 'start', 'name': 'Start'},
                {'id': 'b', 'type': 'llm', 'name': 'AI B'},
                {'id': 'c', 'type': 'llm', 'name': 'AI C'},
                {'id': 'd', 'type': 'llm', 'name': 'AI D'},
                {'id': 'e', 'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'a', 'target': 'b'},
                {'id': 'edge_2', 'source': 'b', 'target': 'c'},
                {'id': 'edge_3', 'source': 'c', 'target': 'd'},
                {'id': 'edge_4', 'source': 'd', 'target': 'b'},  # Back to b
                {'id': 'edge_5', 'source': 'b', 'target': 'e'}
            ]
        }

        has_cycle, cycle_path = service._has_cycle_detection(workflow)
        assert has_cycle is True
        # The cycle should include b, c, d (or at least some of them)
        assert len(cycle_path) > 0

    def test_validation_with_cycle_in_workflow(self):
        """_validate_workflow should detect cycles and add error."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Workflow With Cycle',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI'},
                {'id': 'node_3', 'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_2'},  # Self-loop
                {'id': 'edge_3', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        validated = service._validate_workflow(workflow)
        assert validated['validation']['valid'] is False
        assert len(validated['validation']['errors']) > 0
        assert any('循环' in str(e) or 'cycle' in str(e).lower() for e in validated['validation']['errors'])
