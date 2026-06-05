# -*- coding: utf-8 -*-
"""
pytest configuration for NL Workflow tests.
Extends the backend conftest.py fixtures.
"""

import os
import sys
import uuid
from pathlib import Path

# Add the Backend directory to the path
_backend = Path(__file__).resolve().parents[2] / 'Backend'
sys.path.insert(0, str(_backend))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
import django
django.setup()

import pytest
from django.conf import settings
from rest_framework.test import APIClient


# Re-use existing fixtures from backend conftest
pytest_plugins = ['tests.backend.conftest']


@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(db, user):
    """Return an authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def nl_session(db, user):
    """Create a test NL session."""
    from nl_to_workflow.models import NLSession
    session = NLSession.objects.create(
        user=user,
        name='Test NL Session',
        description='Test workflow generation'
    )
    return session


@pytest.fixture
def nl_session_with_workflow(db, user):
    """Create an NL session with a generated workflow."""
    from nl_to_workflow.models import NLSession
    session = NLSession.objects.create(
        user=user,
        name='Test Session with Workflow',
        description='A session with a complete workflow',
        workflow_json={
            'name': 'Test Workflow',
            'description': 'A test workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 150}, 'config': {}},
                {'id': 'node_2', 'type': 'input', 'name': 'Input', 'position': {'x': 280, 'y': 150}, 'config': {'input_name': 'user_input'}},
                {'id': 'node_3', 'type': 'llm', 'name': 'AI', 'position': {'x': 460, 'y': 150}, 'config': {'model': 'llama3', 'prompt': 'Process: {{input.user_input}}'}},
                {'id': 'node_4', 'type': 'output', 'name': 'Output', 'position': {'x': 640, 'y': 150}, 'config': {}},
                {'id': 'node_5', 'type': 'end', 'name': 'End', 'position': {'x': 820, 'y': 150}, 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
                {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4', 'label': ''},
                {'id': 'edge_4', 'source': 'node_4', 'target': 'node_5', 'label': ''}
            ]
        },
        workflow_name='Test Workflow',
        status='active'
    )
    return session


@pytest.fixture
def sample_workflow():
    """Return a sample workflow dict for testing."""
    return {
        'name': 'Sample Workflow',
        'description': 'A sample workflow for testing',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 150}, 'config': {}},
            {'id': 'node_2', 'type': 'llm', 'name': 'AI', 'position': {'x': 280, 'y': 150}, 'config': {'model': 'llama3', 'prompt': 'Hello'}},
            {'id': 'node_3', 'type': 'end', 'name': 'End', 'position': {'x': 460, 'y': 150}, 'config': {}}
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''}
        ]
    }


@pytest.fixture
def workflow_with_cycle():
    """Return a workflow with a cycle (for cycle detection testing)."""
    return {
        'name': 'Workflow with Cycle',
        'description': 'A workflow that has a cycle',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 150}, 'config': {}},
            {'id': 'node_2', 'type': 'llm', 'name': 'AI 1', 'position': {'x': 280, 'y': 150}, 'config': {}},
            {'id': 'node_3', 'type': 'llm', 'name': 'AI 2', 'position': {'x': 460, 'y': 150}, 'config': {}},
            {'id': 'node_4', 'type': 'end', 'name': 'End', 'position': {'x': 640, 'y': 150}, 'config': {}}
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
            {'id': 'edge_3', 'source': 'node_3', 'target': 'node_2', 'label': ''},  # Creates cycle: node_2 -> node_3 -> node_2
            {'id': 'edge_4', 'source': 'node_2', 'target': 'node_4', 'label': ''}
        ]
    }


@pytest.fixture
def workflow_with_self_loop():
    """Return a workflow with a self-loop node (for cycle detection testing)."""
    return {
        'name': 'Workflow with Self Loop',
        'description': 'A workflow where a node points to itself',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 150}, 'config': {}},
            {'id': 'node_2', 'type': 'llm', 'name': 'AI', 'position': {'x': 280, 'y': 150}, 'config': {}},
            {'id': 'node_3', 'type': 'end', 'name': 'End', 'position': {'x': 460, 'y': 150}, 'config': {}}
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_2', 'label': ''},  # Self loop
            {'id': 'edge_3', 'source': 'node_2', 'target': 'node_3', 'label': ''}
        ]
    }


@pytest.fixture
def complex_workflow():
    """Return a complex workflow for cost estimation testing."""
    return {
        'name': 'Complex Workflow',
        'description': 'A complex workflow with many nodes',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 150}, 'config': {}},
            {'id': 'node_2', 'type': 'input', 'name': 'Input', 'position': {'x': 200, 'y': 150}, 'config': {}},
            {'id': 'node_3', 'type': 'llm', 'name': 'GPT-4 Analysis', 'position': {'x': 300, 'y': 150}, 'config': {'model': 'gpt-4', 'prompt': 'Analyze'}},
            {'id': 'node_4', 'type': 'llm', 'name': 'Claude Processing', 'position': {'x': 400, 'y': 150}, 'config': {'model': 'claude-3', 'prompt': 'Process'}},
            {'id': 'node_5', 'type': 'condition', 'name': 'Check', 'position': {'x': 500, 'y': 150}, 'config': {'conditions': []}},
            {'id': 'node_6', 'type': 'tool', 'name': 'API Call', 'position': {'x': 600, 'y': 100}, 'config': {'tool_name': 'http', 'parameters': {}}},
            {'id': 'node_7', 'type': 'code', 'name': 'Transform', 'position': {'x': 600, 'y': 200}, 'config': {'code': 'x = 1'}},
            {'id': 'node_8', 'type': 'output', 'name': 'Output', 'position': {'x': 700, 'y': 150}, 'config': {}},
            {'id': 'node_9', 'type': 'end', 'name': 'End', 'position': {'x': 800, 'y': 150}, 'config': {}}
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
            {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4', 'label': ''},
            {'id': 'edge_4', 'source': 'node_4', 'target': 'node_5', 'label': ''},
            {'id': 'edge_5', 'source': 'node_5', 'target': 'node_6', 'label': 'Yes'},
            {'id': 'edge_6', 'source': 'node_5', 'target': 'node_7', 'label': 'No'},
            {'id': 'edge_7', 'source': 'node_6', 'target': 'node_8', 'label': ''},
            {'id': 'edge_8', 'source': 'node_7', 'target': 'node_8', 'label': ''},
            {'id': 'edge_9', 'source': 'node_8', 'target': 'node_9', 'label': ''}
        ]
    }
