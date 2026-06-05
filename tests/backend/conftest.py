# -*- coding: utf-8 -*-
"""
pytest configuration for Flowly backend tests.
"""

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

# Add the Backend directory to the path
_backend = Path(__file__).resolve().parents[1] / 'Backend'
sys.path.insert(0, str(_backend))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
import django
django.setup()

import pytest
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework.settings import api_settings


@pytest.fixture(scope='session')
def django_db_setup():
    """Configure test database."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': False,
    }


@pytest.fixture(autouse=True)
def disable_throttling():
    """Disable throttling for all tests to avoid rate limit issues."""
    original_throttle_classes = api_settings.DEFAULT_THROTTLE_CLASSES
    api_settings.DEFAULT_THROTTLE_CLASSES = []
    yield
    api_settings.DEFAULT_THROTTLE_CLASSES = original_throttle_classes


@pytest.fixture(autouse=True)
def mock_audit_logging():
    """Mock _log_audit to avoid audit log database issues in tests."""
    with patch('users.views._log_audit'):
        yield


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
def user(db):
    """Create a test user (function-scoped to avoid duplicates)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username=f'testuser_{uuid.uuid4().hex[:8]}',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_superuser(
        username=f'admin_{uuid.uuid4().hex[:8]}',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def workflow(db, user):
    """Create a test workflow."""
    from workflows.models import Workflow
    return Workflow.objects.create(
        name='Test Workflow',
        description='A test workflow',
        owner=user,
        status='draft'
    )


@pytest.fixture
def workflow_with_nodes(db, workflow):
    """Create a workflow with nodes."""
    from workflows.models import Node, Edge

    # Create nodes
    start_node = Node.objects.create(
        workflow=workflow,
        node_type='start',
        name='Start',
        position_x=100,
        position_y=100
    )

    llm_node = Node.objects.create(
        workflow=workflow,
        node_type='llm',
        name='AI Assistant',
        position_x=300,
        position_y=100,
        config={'model': 'gpt-3.5-turbo', 'prompt': 'You are a helpful assistant.'}
    )

    end_node = Node.objects.create(
        workflow=workflow,
        node_type='end',
        name='End',
        position_x=500,
        position_y=100
    )

    # Create edges
    Edge.objects.create(
        workflow=workflow,
        source_node=start_node,
        target_node=llm_node
    )

    Edge.objects.create(
        workflow=workflow,
        source_node=llm_node,
        target_node=end_node
    )

    return workflow


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
