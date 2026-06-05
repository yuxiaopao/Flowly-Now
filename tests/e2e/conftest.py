"""
Pytest configuration and fixtures for E2E tests.
"""
import os
import pytest
import requests
from typing import Generator, Optional

# Environment configuration
DJANGO_BASE_URL = os.getenv("DJANGO_BASE_URL", "http://localhost:8000")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_AVAILABLE = os.getenv("OLLAMA_AVAILABLE", "false").lower() == "true"


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "ollama: tests that require Ollama to be running")
    config.addinivalue_line("markers", "streaming: tests that involve streaming responses")
    config.addinivalue_line("markers", "slow: slow-running tests")


def is_django_running() -> bool:
    """Check if Django dev server is running."""
    try:
        response = requests.get(f"{DJANGO_BASE_URL}/api/health/", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def is_ollama_running() -> bool:
    """Check if Ollama server is running and reachable."""
    if not OLLAMA_AVAILABLE:
        return False
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


@pytest.fixture(scope="session")
def django_base_url() -> str:
    """Return the Django base URL."""
    return DJANGO_BASE_URL


@pytest.fixture(scope="session")
def ollama_base_url() -> str:
    """Return the Ollama base URL."""
    return OLLAMA_BASE_URL


@pytest.fixture(scope="session")
def ollama_model() -> str:
    """Return the Ollama model to use."""
    return OLLAMA_MODEL


@pytest.fixture(scope="session")
def django_available() -> bool:
    """Check if Django server is available."""
    return is_django_running()


@pytest.fixture(scope="session")
def ollama_available() -> bool:
    """Check if Ollama server is available."""
    return is_ollama_running()


@pytest.fixture
def api_client(django_available: bool, django_base_url: str) -> Generator[Optional[requests.Session], None, None]:
    """
    Authenticated API client fixture.
    Returns a requests session with auth headers if Django is running.
    """
    if not django_available:
        pytest.skip("Django server is not running at " + django_base_url)
    
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    
    # Try to get auth token if available
    token = os.getenv("TEST_AUTH_TOKEN")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    
    yield session
    session.close()


@pytest.fixture
def auth_token(api_client: requests.Session, django_base_url: str) -> Optional[str]:
    """
    Get an authentication token.
    This creates a test user and returns a token for API calls.
    """
    # Try to get existing token from env
    token = os.getenv("TEST_AUTH_TOKEN")
    if token:
        return token
    
    # Try to login with test credentials
    test_username = os.getenv("TEST_USERNAME", "testuser")
    test_password = os.getenv("TEST_PASSWORD", "testpass123")
    
    try:
        response = api_client.post(
            f"{django_base_url}/api/v1/auth/login/",
            json={"username": test_username, "password": test_password}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access") or data.get("token")
    except requests.exceptions.RequestException:
        pass
    
    return None


@pytest.fixture
def authenticated_client(api_client: requests.Session, auth_token: Optional[str]) -> requests.Session:
    """
    Returns an authenticated API client.
    """
    if auth_token:
        api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


@pytest.fixture
def test_workflow_data() -> dict:
    """Return sample workflow data for testing."""
    return {
        "name": "Test Workflow E2E",
        "description": "Workflow created by E2E tests",
        "status": "draft",
        "settings": {
            "timeout": 300,
            "retry_on_failure": False
        },
        "nodes": [
            {
                "id": "node_start",
                "type": "start",
                "position": {"x": 100, "y": 100},
                "data": {"label": "Start"}
            },
            {
                "id": "node_input",
                "type": "input",
                "position": {"x": 100, "y": 200},
                "data": {"label": "User Input", "input_type": "text"}
            },
            {
                "id": "node_end",
                "type": "end",
                "position": {"x": 100, "y": 300},
                "data": {"label": "End"}
            }
        ],
        "edges": [
            {"id": "e1", "source": "node_start", "target": "node_input"},
            {"id": "e2", "source": "node_input", "target": "node_end"}
        ]
    }


@pytest.fixture
def test_llm_workflow_data() -> dict:
    """Return a workflow with LLM node for testing."""
    return {
        "name": "Test LLM Workflow E2E",
        "description": "Workflow with LLM node for Ollama testing",
        "status": "draft",
        "nodes": [
            {
                "id": "node_start",
                "type": "start",
                "position": {"x": 100, "y": 100},
                "data": {"label": "Start"}
            },
            {
                "id": "node_input",
                "type": "input",
                "position": {"x": 100, "y": 200},
                "data": {"label": "User Input", "input_type": "text"}
            },
            {
                "id": "node_llm",
                "type": "llm",
                "position": {"x": 100, "y": 300},
                "data": {
                    "label": "Ollama LLM",
                    "model_provider": "ollama",
                    "model_name": OLLAMA_MODEL,
                    "temperature": 0.7,
                    "system_prompt": "You are a helpful assistant."
                }
            },
            {
                "id": "node_end",
                "type": "end",
                "position": {"x": 100, "y": 400},
                "data": {"label": "End"}
            }
        ],
        "edges": [
            {"id": "e1", "source": "node_start", "target": "node_input"},
            {"id": "e2", "source": "node_input", "target": "node_llm"},
            {"id": "e3", "source": "node_llm", "target": "node_end"}
        ]
    }


@pytest.fixture
def skip_if_django_not_available(django_available: bool):
    """Skip test if Django is not available."""
    if not django_available:
        pytest.skip("Django server is not running")


@pytest.fixture
def skip_if_ollama_not_available(ollama_available: bool):
    """Skip test if Ollama is not available."""
    if not ollama_available:
        pytest.skip("Ollama server is not running or not available")


@pytest.fixture
def cleanup_workflow(authenticated_client: requests.Session, django_base_url: str):
    """
    Fixture to clean up created workflows after test.
    Yields the created workflow ID.
    """
    created_workflows = []
    
    def register_workflow(workflow_id: int):
        created_workflows.append(workflow_id)
    
    yield register_workflow
    
    # Cleanup
    for workflow_id in created_workflows:
        try:
            authenticated_client.delete(f"{django_base_url}/api/v1/workflows/{workflow_id}/")
        except requests.exceptions.RequestException:
            pass
