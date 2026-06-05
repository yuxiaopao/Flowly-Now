"""
Pytest configuration and fixtures for workflow tests.
"""

import os
import sys
from pathlib import Path

import django
import pytest

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()


def pytest_configure():
    """Configure pytest."""
    import pytest
    from django.conf import settings
    
    # Override settings for testing
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'workflows',
            ],
            USE_TZ=True,
        )


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        'name': 'Test Workflow',
        'description': 'A test workflow',
        'status': 'draft',
        'version': 1
    }


@pytest.fixture
def sample_node_data():
    """Sample node data for testing."""
    return {
        'node_type': 'llm',
        'name': 'Test LLM Node',
        'config': {
            'model': 'gpt-3.5-turbo',
            'temperature': 0.7,
            'system_prompt': 'You are a helpful assistant.'
        },
        'error_handling': 'stop',
        'max_retries': 3,
        'retry_delay': 1.0
    }


@pytest.fixture
def sample_execution_data():
    """Sample execution data for testing."""
    return {
        'trigger_type': 'manual',
        'input_data': {'test': 'value'}
    }
