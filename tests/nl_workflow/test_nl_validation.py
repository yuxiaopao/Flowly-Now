# -*- coding: utf-8 -*-
"""
Tests for Workflow Validation and Auto-layout.

Tests the _validate_workflow method including:
- Missing start/end nodes
- Disconnected nodes
- Auto-positioning of nodes
- Auto-generation of workflow names
"""

import pytest
from nl_to_workflow.services import NLToWorkflowService, calculate_node_positions


class TestNLValidation:
    """Test workflow validation."""

    def test_validate_valid_workflow(self):
        """Valid workflow should pass validation."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Valid Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 150}, 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI', 'position': {'x': 280, 'y': 150}, 'config': {'model': 'llama3'}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'position': {'x': 460, 'y': 150}, 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        validated = service._validate_workflow(workflow)
        assert validated['validation']['valid'] is True
        assert len(validated['validation']['errors']) == 0

    def test_validate_missing_start(self):
        """Workflow without start node should generate warning."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'No Start Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'llm', 'name': 'AI', 'position': {'x': 280, 'y': 150}, 'config': {}},
                {'id': 'node_2', 'type': 'end', 'name': 'End', 'position': {'x': 460, 'y': 150}, 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'}
            ]
        }

        validated = service._validate_workflow(workflow)
        assert validated['validation']['valid'] is True  # Still valid but with warning
        assert len(validated['validation']['warnings']) > 0
        assert any('开始节点' in str(w) for w in validated['validation']['warnings'])

    def test_validate_missing_end(self):
        """Workflow without end node should generate warning."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'No End Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 150}, 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI', 'position': {'x': 280, 'y': 150}, 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'}
            ]
        }

        validated = service._validate_workflow(workflow)
        assert validated['validation']['valid'] is True  # Still valid but with warning
        assert len(validated['validation']['warnings']) > 0
        assert any('结束节点' in str(w) for w in validated['validation']['warnings'])

    def test_validate_multiple_starts(self):
        """Workflow with multiple start nodes should fail validation."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Multi Start Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start 1', 'position': {'x': 100, 'y': 150}, 'config': {}},
                {'id': 'node_2', 'type': 'start', 'name': 'Start 2', 'position': {'x': 100, 'y': 300}, 'config': {}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'position': {'x': 460, 'y': 150}, 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_3'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        validated = service._validate_workflow(workflow)
        assert validated['validation']['valid'] is False
        assert len(validated['validation']['errors']) > 0
        assert any('开始节点' in str(e) for e in validated['validation']['errors'])

    def test_validate_disconnected_nodes(self):
        """Workflow with disconnected nodes should generate warning."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Disconnected Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 150}, 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI', 'position': {'x': 280, 'y': 150}, 'config': {}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'position': {'x': 460, 'y': 150}, 'config': {}},
                {'id': 'node_4', 'type': 'llm', 'name': 'Orphan', 'position': {'x': 280, 'y': 300}, 'config': {}}  # Disconnected
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        validated = service._validate_workflow(workflow)
        assert len(validated['validation']['warnings']) > 0
        assert any('node_4' in str(w) or '未连接' in str(w) for w in validated['validation']['warnings'])

    def test_validate_missing_nodes(self):
        """Workflow with no nodes should fail validation."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Empty Nodes Workflow',
            'nodes': [],
            'edges': []
        }

        validated = service._validate_workflow(workflow)
        assert validated['validation']['valid'] is False
        assert any('没有节点' in str(e) for e in validated['validation']['errors'])

    def test_validate_with_auto_layout(self):
        """Nodes without positions should get auto-positioned."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'No Positions Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI', 'config': {}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        validated = service._validate_workflow(workflow)
        
        # Check that positions were added
        for node in validated['nodes']:
            assert 'position' in node
            assert 'x' in node['position']
            assert 'y' in node['position']

    def test_validate_partial_positions(self):
        """Some nodes with positions, some without should auto-layout missing ones."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Partial Positions Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 150}, 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI', 'config': {}},  # No position
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}}   # No position
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        validated = service._validate_workflow(workflow)
        
        # node_1 should keep its position
        assert validated['nodes'][0]['position'] == {'x': 100, 'y': 150}
        # node_2 and node_3 should get auto-positioned
        assert validated['nodes'][1]['position']['x'] is not None
        assert validated['nodes'][1]['position']['y'] is not None
        assert validated['nodes'][2]['position']['x'] is not None
        assert validated['nodes'][2]['position']['y'] is not None

    def test_validate_with_null_position(self):
        """Nodes with null position should get auto-positioned."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Null Position Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': None, 'config': {}},
                {'id': 'node_2', 'type': 'end', 'name': 'End', 'position': None, 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'}
            ]
        }

        validated = service._validate_workflow(workflow)
        
        for node in validated['nodes']:
            assert node['position'] is not None
            assert 'x' in node['position']
            assert 'y' in node['position']


class TestNLWorkflowNameGeneration:
    """Test auto-generated workflow names."""

    def test_generate_name_from_description_qa_bot(self):
        """Description about QA bot should generate relevant name."""
        service = NLToWorkflowService()
        workflow = {
            'name': '',  # Missing name
            'description': '创建一个问答机器人',
            'nodes': [],
            'edges': []
        }

        validated = service._validate_workflow(workflow)
        # Name should be auto-generated
        assert validated['name'] != ''
        assert '问答' in validated['name'] or '智能' in validated['name'] or '工作流' in validated['name']

    def test_generate_name_from_description_translation(self):
        """Description about translation should generate relevant name."""
        service = NLToWorkflowService()
        workflow = {
            'name': '',
            'description': '翻译文章内容',
            'nodes': [],
            'edges': []
        }

        validated = service._validate_workflow(workflow)
        assert validated['name'] != ''
        assert '翻' in validated['name'] or '智能' in validated['name']

    def test_generate_name_from_description_data_processing(self):
        """Description about data processing should generate relevant name."""
        service = NLToWorkflowService()
        workflow = {
            'name': '',
            'description': '处理数据并生成报告',
            'nodes': [],
            'edges': []
        }

        validated = service._validate_workflow(workflow)
        assert validated['name'] != ''

    def test_generate_name_no_input(self):
        """Empty description should still generate a name."""
        service = NLToWorkflowService()
        workflow = {
            'name': '',
            'description': '',
            'nodes': [],
            'edges': []
        }

        validated = service._validate_workflow(workflow)
        # Since description is empty and name is empty, should have error
        assert len(validated['validation']['errors']) > 0

    def test_generate_name_existing_name_preserved(self):
        """Existing name should be preserved."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'My Custom Workflow',
            'description': 'Some workflow',
            'nodes': [],
            'edges': []
        }

        validated = service._validate_workflow(workflow)
        assert validated['name'] == 'My Custom Workflow'
        assert len(validated['validation']['errors']) == 0

    def test_generate_workflow_name_direct(self):
        """Test _generate_workflow_name method directly."""
        service = NLToWorkflowService()
        
        name = service._generate_workflow_name('创建一个问答机器人')
        assert name != ''
        
        name = service._generate_workflow_name('翻译英文文章')
        assert name != ''
        
        name = service._generate_workflow_name('处理数据')
        assert name != ''


class TestCalculateNodePositions:
    """Test calculate_node_positions helper function."""

    def test_single_node(self):
        """Single node should be positioned at start."""
        positions = calculate_node_positions(1)
        assert len(positions) == 1
        assert positions[0]['x'] == 100
        assert positions[0]['y'] == 150

    def test_multiple_nodes(self):
        """Multiple nodes should be positioned in a grid."""
        positions = calculate_node_positions(5)
        assert len(positions) == 5
        
        # First row: positions 0-3
        assert positions[0]['x'] == 100
        assert positions[0]['y'] == 150
        assert positions[1]['x'] == 280
        assert positions[1]['y'] == 150
        assert positions[2]['x'] == 460
        assert positions[2]['y'] == 150
        assert positions[3]['x'] == 640
        assert positions[3]['y'] == 150
        
        # Second row: position 4
        assert positions[4]['x'] == 100
        assert positions[4]['y'] == 270

    def test_custom_start_position(self):
        """Custom start position should work."""
        positions = calculate_node_positions(2, start_x=200, start_y=300)
        assert positions[0]['x'] == 200
        assert positions[0]['y'] == 300
        assert positions[1]['x'] == 380
        assert positions[1]['y'] == 300

    def test_custom_spacing(self):
        """Custom spacing should work."""
        positions = calculate_node_positions(2, spacing_x=300, spacing_y=200)
        assert positions[0]['x'] == 100
        assert positions[0]['y'] == 150
        assert positions[1]['x'] == 400  # 100 + 300
        assert positions[1]['y'] == 150

    def test_empty_nodes(self):
        """Zero nodes should return empty list."""
        positions = calculate_node_positions(0)
        assert positions == []


class TestValidationIncludesCost:
    """Test that validation includes cost estimation."""

    def test_validation_includes_cost(self, sample_workflow):
        """_validate_workflow should include estimated_cost in result."""
        service = NLToWorkflowService()
        validated = service._validate_workflow(sample_workflow)
        assert 'estimated_cost' in validated
        assert validated['estimated_cost'] >= 0

    def test_validation_cost_matches_estimate(self):
        """Validation cost should match direct cost estimation."""
        service = NLToWorkflowService()
        workflow = {
            'name': 'Cost Test',
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

        estimated = service._estimate_workflow_cost(workflow)
        validated = service._validate_workflow(workflow)
        
        assert validated['estimated_cost'] == estimated
