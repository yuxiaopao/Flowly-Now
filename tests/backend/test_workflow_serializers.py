# -*- coding: utf-8 -*-
"""
Tests for Workflow serializers.
Covers WorkflowCreateSerializer, WorkflowExecuteSerializer, and all validation rules.
"""

import pytest
import json
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.django_db


class TestWorkflowCreateSerializerValidation:
    """Test WorkflowCreateSerializer validation rules."""

    def _get_serializer(self, data=None):
        from workflows.serializers import WorkflowCreateSerializer
        return WorkflowCreateSerializer(data=data or {})

    # ---- name validation ----

    def test_validate_name_success(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test Workflow',
            'nodes': [],
            'edges': []
        })
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['name'] == 'Test Workflow'

    def test_validate_name_strips_whitespace(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': '  Trimmed Name  ',
            'nodes': [],
            'edges': []
        })
        assert serializer.is_valid()
        assert serializer.validated_data['name'] == 'Trimmed Name'

    def test_validate_name_too_long(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'A' * 300,
            'nodes': [],
            'edges': []
        })
        assert not serializer.is_valid()
        assert 'name' in serializer.errors

    # ---- description validation ----

    def test_validate_description_too_long(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'description': 'X' * 6000,
            'nodes': [],
            'edges': []
        })
        assert not serializer.is_valid()
        assert 'description' in serializer.errors

    def test_validate_description_success(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'description': 'A reasonable description.',
            'nodes': [],
            'edges': []
        })
        assert serializer.is_valid()

    # ---- tags validation ----

    def test_validate_tags_too_many(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'tags': ['tag'] * 60,
            'nodes': [],
            'edges': []
        })
        assert not serializer.is_valid()
        assert 'tags' in serializer.errors

    def test_validate_tags_single_too_long(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'tags': ['a' * 150],
            'nodes': [],
            'edges': []
        })
        assert not serializer.is_valid()
        assert 'tags' in serializer.errors

    def test_validate_tags_success(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'tags': ['ai', 'workflow', 'automation'],
            'nodes': [],
            'edges': []
        })
        assert serializer.is_valid()

    # ---- nodes validation ----

    def test_validate_nodes_none_returns_empty_list(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'nodes': None,
            'edges': []
        })
        assert serializer.is_valid()
        assert serializer.validated_data['nodes'] == []

    def test_validate_nodes_too_many(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'nodes': [{'id': f'n{i}', 'type': 'start'} for i in range(600)],
            'edges': []
        })
        assert not serializer.is_valid()
        assert 'nodes' in serializer.errors

    def test_validate_nodes_valid(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'nodes': [
                {'id': 'n1', 'type': 'start'},
                {'id': 'n2', 'type': 'llm'},
            ],
            'edges': []
        })
        assert serializer.is_valid()


class TestWorkflowExecuteSerializerValidation:
    """Test WorkflowExecuteSerializer validation rules."""

    def test_validate_input_data_within_limit(self):
        from workflows.serializers import WorkflowExecuteSerializer
        serializer = WorkflowExecuteSerializer(data={
            'input_data': {'key': 'value'},
            'trigger_type': 'manual'
        })
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['input_data'] == {'key': 'value'}

    def test_validate_input_data_exceeds_limit(self):
        from workflows.serializers import WorkflowExecuteSerializer
        # Create data > 100KB
        large_data = {'key': 'X' * 150 * 1024}
        serializer = WorkflowExecuteSerializer(data={
            'input_data': large_data,
            'trigger_type': 'manual'
        })
        assert not serializer.is_valid()
        assert 'input_data' in serializer.errors

    def test_validate_trigger_type_defaults_to_manual(self):
        from workflows.serializers import WorkflowExecuteSerializer
        serializer = WorkflowExecuteSerializer(data={
            'input_data': {}
        })
        assert serializer.is_valid()
        assert serializer.validated_data['trigger_type'] == 'manual'
        assert serializer.validated_data['is_async'] is False


class TestWorkflowCreateSerializerTransform:
    """Test WorkflowCreateSerializer node/edge transformation."""

    def test_transform_nodes_flat_format(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'nodes': [
                {
                    'id': 'node-1',
                    'type': 'llm',
                    'data': {
                        'label': 'AI Node',
                        'description': 'Test node',
                        'config': {'model': 'gpt-4'},
                        'style': {}
                    },
                    'position': {'x': 100, 'y': 200}
                }
            ],
            'edges': []
        })
        assert serializer.is_valid()

    def test_validate_rejects_non_dict_node(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'nodes': ['not a dict'],
            'edges': []
        })
        assert not serializer.is_valid()
        assert 'nodes' in serializer.errors

    def test_validate_rejects_non_dict_edge(self):
        from workflows.serializers import WorkflowCreateSerializer
        serializer = WorkflowCreateSerializer(data={
            'name': 'Test',
            'nodes': [],
            'edges': ['not a dict']
        })
        assert not serializer.is_valid()
        assert 'edges' in serializer.errors
