"""各测试套件共用的真实数据库/API 客户端夹具。"""
import uuid
import pytest
from rest_framework.test import APIClient
from rest_framework.settings import api_settings


@pytest.fixture(autouse=True)
def disable_throttling():
    """Disable throttling for all tests to avoid rate limit issues."""
    original_throttle_classes = api_settings.DEFAULT_THROTTLE_CLASSES
    api_settings.DEFAULT_THROTTLE_CLASSES = []
    yield
    api_settings.DEFAULT_THROTTLE_CLASSES = original_throttle_classes


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
