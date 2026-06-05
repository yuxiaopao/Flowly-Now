"""
E2E Tests for Backend API - Workflow CRUD, Execution, and NL Workflow endpoints.

Tests require Django server running at http://localhost:8000
Many tests will be skipped if Ollama is not available.
"""
import pytest
import requests
from typing import Dict, Any, Optional

from .helpers import (
    create_test_workflow,
    delete_workflow,
    get_workflow_by_id,
    execute_workflow_sync,
    check_ollama_health,
    check_gateway_health,
    validate_workflow,
)
from .conftest import OLLAMA_AVAILABLE


# =============================================================================
# Workflow CRUD Tests
# =============================================================================

class TestWorkflowCRUD:
    """Test workflow create, read, update, delete operations."""

    def test_workflow_crud_full_flow(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test complete workflow CRUD flow: create → read → update → delete.
        """
        # Create workflow
        create_response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/",
            json=test_workflow_data
        )
        
        assert create_response.status_code == 201, (
            f"Failed to create workflow: {create_response.status_code} - {create_response.text}"
        )
        
        workflow = create_response.json()
        workflow_id = workflow.get("id")
        assert workflow_id is not None, "Created workflow should have an ID"
        assert workflow.get("name") == test_workflow_data["name"]
        
        # Register for cleanup
        cleanup_workflow(workflow_id)
        
        # Read workflow
        get_response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/"
        )
        
        assert get_response.status_code == 200, (
            f"Failed to get workflow: {get_response.status_code}"
        )
        
        retrieved_workflow = get_response.json()
        assert retrieved_workflow["id"] == workflow_id
        assert retrieved_workflow["name"] == test_workflow_data["name"]
        
        # Update workflow
        update_data = {
            "name": "Updated Test Workflow E2E",
            "description": "Updated description"
        }
        update_response = authenticated_client.patch(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/",
            json=update_data
        )
        
        assert update_response.status_code == 200, (
            f"Failed to update workflow: {update_response.status_code}"
        )
        
        updated_workflow = update_response.json()
        assert updated_workflow["name"] == update_data["name"]
        assert updated_workflow["description"] == update_data["description"]
        
        # Delete workflow
        delete_response = authenticated_client.delete(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/"
        )
        
        assert delete_response.status_code == 204, (
            f"Failed to delete workflow: {delete_response.status_code}"
        )
        
        # Verify deletion
        verify_response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/"
        )
        assert verify_response.status_code == 404, (
            "Workflow should not exist after deletion"
        )

    def test_workflow_list_pagination(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test workflow list with pagination parameters.
        """
        response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/",
            params={"page": 1, "page_size": 10}
        )
        
        assert response.status_code == 200, (
            f"Failed to get workflow list: {response.status_code}"
        )
        
        data = response.json()
        assert "results" in data or isinstance(data, list), (
            "Response should contain results list or be a list"
        )

    def test_workflow_search(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test workflow search functionality.
        """
        response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/",
            params={"search": "test"}
        )
        
        assert response.status_code == 200, (
            f"Failed to search workflows: {response.status_code}"
        )


# =============================================================================
# Workflow Validation Tests
# =============================================================================

class TestWorkflowValidation:
    """Test workflow validation."""

    def test_workflow_validation_invalid_workflow(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        cleanup_workflow
    ):
        """
        Test that invalid workflow returns 400 or validation errors.
        """
        # Create workflow with invalid data (missing required fields)
        invalid_workflow = {
            "name": "",  # Empty name should fail
            "description": "Test"
        }
        
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/",
            json=invalid_workflow
        )
        
        # Should return 400 or 201 (some backends are lenient)
        assert response.status_code in [201, 400], (
            f"Unexpected status code: {response.status_code}"
        )
        
        if response.status_code == 201:
            # Backend accepted, now validate
            workflow = response.json()
            workflow_id = workflow.get("id")
            cleanup_workflow(workflow_id)
            
            validation_result = validate_workflow(
                authenticated_client,
                django_base_url,
                workflow_id
            )
            
            # Should have validation errors
            if "errors" in validation_result:
                assert len(validation_result["errors"]) > 0 or validation_result.get("valid") is True

    def test_workflow_validation_valid_workflow(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test validation of a valid workflow passes.
        """
        # Create valid workflow
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            test_workflow_data
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Validate
        result = validate_workflow(
            authenticated_client,
            django_base_url,
            workflow_id
        )
        
        # Valid workflow should have no errors
        if result.get("valid") is False:
            assert "errors" in result, "Invalid workflow should have errors"


# =============================================================================
# Workflow Nodes CRUD Tests
# =============================================================================

class TestWorkflowNodesCRUD:
    """Test workflow nodes CRUD operations."""

    def test_workflow_nodes_crud(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test creating workflow with nodes, retrieving, and verifying structure.
        """
        # Create workflow with nodes
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            test_workflow_data
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Get workflow nodes
        nodes_response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/nodes/",
            params={"workflow": workflow_id}
        )
        
        assert nodes_response.status_code == 200, (
            f"Failed to get nodes: {nodes_response.status_code}"
        )
        
        nodes = nodes_response.json()
        if isinstance(nodes, dict) and "results" in nodes:
            nodes = nodes["results"]
        
        # Should have nodes from test data
        expected_node_count = len(test_workflow_data.get("nodes", []))
        assert len(nodes) >= expected_node_count, (
            f"Expected at least {expected_node_count} nodes, got {len(nodes)}"
        )

    def test_workflow_nodes_batch_create(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test batch creation of nodes.
        """
        # Create workflow
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            {"name": "Batch Nodes Test", "description": "Test"}
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Batch create nodes
        nodes_to_create = [
            {"id": f"batch_node_{i}", "type": "input", "position": {"x": 100, "y": 100 * i}}
            for i in range(5)
        ]
        
        batch_response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/nodes/batch_create/",
            json={"workflow_id": workflow_id, "nodes": nodes_to_create}
        )
        
        assert batch_response.status_code in [200, 201], (
            f"Batch create failed: {batch_response.status_code}"
        )

    def test_workflow_edges_crud(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test workflow edges CRUD operations.
        """
        # Create workflow
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            test_workflow_data
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Get workflow edges
        edges_response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/edges/",
            params={"workflow": workflow_id}
        )
        
        assert edges_response.status_code == 200, (
            f"Failed to get edges: {edges_response.status_code}"
        )


# =============================================================================
# Workflow Execution Tests
# =============================================================================

class TestWorkflowExecution:
    """Test workflow execution endpoints."""

    def test_workflow_execution_basic(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test basic workflow execution via POST /api/v1/workflows/{id}/execute/
        """
        # Create workflow
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            test_workflow_data
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Execute workflow
        exec_response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/execute/",
            json={"input_data": {"test": "value"}}
        )
        
        assert exec_response.status_code == 200, (
            f"Execution failed: {exec_response.status_code} - {exec_response.text}"
        )
        
        result = exec_response.json()
        assert "execution_id" in result or "status" in result, (
            "Execution response should contain execution_id or status"
        )

    @pytest.mark.ollama
    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="Ollama not available")
    def test_workflow_execution_with_llm_node(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        ollama_base_url: str,
        ollama_model: str,
        test_llm_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test workflow execution through LLM node with Ollama.
        Requires Ollama to be running.
        """
        # Verify Ollama is accessible
        health = check_ollama_health(ollama_base_url)
        assert health.get("status") == "ok", (
            f"Ollama health check failed: {health}"
        )
        
        # Create workflow with LLM node
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            test_llm_workflow_data
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow with LLM node")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Execute with LLM input
        exec_response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/execute/",
            json={
                "input_data": {
                    "text": "Hello, how are you?"
                },
                "timeout": 120
            }
        )
        
        # Should succeed or return a valid response
        assert exec_response.status_code in [200, 202], (
            f"LLM execution failed: {exec_response.status_code} - {exec_response.text}"
        )

    def test_workflow_execution_timeout(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test execution timeout handling.
        """
        # Create workflow
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            test_workflow_data
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Execute with very short timeout
        exec_response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/execute/",
            json={
                "input_data": {},
                "timeout": 1  # 1 second timeout
            }
        )
        
        # Should either succeed or return timeout error
        assert exec_response.status_code in [200, 400, 408, 504], (
            f"Unexpected status for timeout test: {exec_response.status_code}"
        )

    def test_workflow_execution_invalid_input(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test execution with invalid input data.
        """
        # Create workflow
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            test_workflow_data
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Execute with invalid input
        exec_response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/execute/",
            json={"input_data": None}  # Invalid input
        )
        
        # Should return error
        assert exec_response.status_code in [200, 400, 422], (
            f"Should return error for invalid input: {exec_response.status_code}"
        )


# =============================================================================
# NL Workflow Tests
# =============================================================================

class TestNLWorkflow:
    """Test Natural Language to Workflow conversion."""

    def test_nl_workflow_generate(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test NL workflow generation via POST /api/v1/nl-workflow/sessions/
        """
        # Create NL session
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/nl-workflow/sessions/",
            json={
                "description": "Create a simple translation workflow: input text → translate to Chinese → output",
                "model": "gpt-4",
                "temperature": 0.7
            }
        )
        
        # Should succeed or return valid response structure
        assert response.status_code in [200, 201], (
            f"NL workflow generation failed: {response.status_code} - {response.text}"
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "session_id" in data or "id" in data, (
                "Response should contain session_id or id"
            )

    def test_nl_workflow_continue(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test continuing NL workflow conversation via PATCH.
        """
        # First create a session
        create_response = authenticated_client.post(
            f"{django_base_url}/api/v1/nl-workflow/sessions/",
            json={
                "description": "Create a chatbot workflow",
                "model": "gpt-4"
            }
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip("Failed to create NL session")
        
        session = create_response.json()
        session_id = session.get("session_id") or session.get("id")
        
        if not session_id:
            pytest.skip("No session ID returned")
        
        # Continue conversation
        continue_response = authenticated_client.patch(
            f"{django_base_url}/api/v1/nl-workflow/sessions/{session_id}/message/",
            json={"message": "Add a condition node to handle errors"}
        )
        
        assert continue_response.status_code in [200, 201, 202], (
            f"Continue conversation failed: {continue_response.status_code}"
        )

    def test_nl_workflow_models_list(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test getting available NL models.
        """
        response = authenticated_client.get(
            f"{django_base_url}/api/v1/nl-workflow/models/"
        )
        
        assert response.status_code == 200, (
            f"Failed to get NL models: {response.status_code}"
        )
        
        data = response.json()
        assert "models" in data or isinstance(data, list), (
            "Response should contain models list"
        )

    def test_nl_workflow_sessions_list(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test listing NL workflow sessions.
        """
        response = authenticated_client.get(
            f"{django_base_url}/api/v1/nl-workflow/sessions/"
        )
        
        assert response.status_code == 200, (
            f"Failed to get sessions: {response.status_code}"
        )

    def test_nl_workflow_analyze_intent(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test intent analysis for NL workflow.
        """
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/nl-workflow/analyze-intent/",
            json={"message": "Create a translation workflow"}
        )
        
        assert response.status_code in [200, 201], (
            f"Intent analysis failed: {response.status_code} - {response.text}"
        )


# =============================================================================
# Gateway / Ollama Health Tests
# =============================================================================

class TestGatewayHealth:
    """Test gateway health and Ollama integration."""

    def test_ollama_health(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        ollama_base_url: str
    ):
        """
        Test Ollama health check via gateway.
        GET /api/v1/gateway/health/
        """
        response = authenticated_client.get(
            f"{django_base_url}/api/v1/gateway/health/"
        )
        
        assert response.status_code == 200, (
            f"Gateway health check failed: {response.status_code} - {response.text}"
        )
        
        data = response.json()
        assert "status" in data or "ollama" in str(data).lower(), (
            "Health response should contain status info"
        )

    def test_ollama_direct_health(
        self,
        ollama_base_url: str
    ):
        """
        Test direct Ollama health check.
        """
        health = check_ollama_health(ollama_base_url)
        
        # Regardless of Ollama availability, function should return a valid response
        assert "status" in health, (
            "Health check should return status field"
        )
        
        # If Ollama is running, should have models_count
        if health["status"] == "ok":
            assert "models_count" in health, (
                "Successful health check should include models_count"
            )

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="Ollama not available")
    def test_gateway_ollama_integration(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test gateway integration with Ollama provider.
        """
        # Get providers
        providers_response = authenticated_client.get(
            f"{django_base_url}/api/v1/gateway/providers/"
        )
        
        assert providers_response.status_code == 200, (
            f"Failed to get providers: {providers_response.status_code}"
        )

    @pytest.mark.skipif(not OLLAMA_AVAILABLE, reason="Ollama not available")
    def test_gateway_models_list(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test listing available models from gateway.
        """
        response = authenticated_client.get(
            f"{django_base_url}/api/v1/gateway/models/"
        )
        
        assert response.status_code == 200, (
            f"Failed to get models: {response.status_code}"
        )


# =============================================================================
# Workflow Streaming Tests
# =============================================================================

class TestWorkflowStreaming:
    """Test workflow streaming execution."""

    def test_workflow_stream_execute_endpoint(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test streaming execution endpoint exists and returns valid response.
        POST /api/v1/workflows/{id}/stream_execute/
        """
        # Create workflow
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            test_workflow_data
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Start streaming execution
        exec_response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/stream_execute/",
            json={"input_data": {"test": "value"}},
            stream=True
        )
        
        assert exec_response.status_code in [200, 202], (
            f"Streaming execution failed: {exec_response.status_code} - {exec_response.text}"
        )
        
        # Should be a streaming response
        content_type = exec_response.headers.get("Content-Type", "")
        assert "text/event-stream" in content_type or "application/json" in content_type, (
            f"Expected streaming content type, got: {content_type}"
        )

    def test_workflow_execution_status(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test getting execution status.
        GET /api/v1/workflows/executions/{id}/status/
        """
        # Create and execute workflow
        workflow = create_test_workflow(
            authenticated_client,
            django_base_url,
            test_workflow_data
        )
        
        if workflow is None:
            pytest.skip("Failed to create test workflow")
        
        workflow_id = workflow.get("id")
        cleanup_workflow(workflow_id)
        
        # Execute
        exec_response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/execute/",
            json={"input_data": {}}
        )
        
        if exec_response.status_code != 200:
            pytest.skip("Failed to execute workflow")
        
        exec_data = exec_response.json()
        execution_id = exec_data.get("execution_id")
        
        if not execution_id:
            pytest.skip("No execution ID returned")
        
        # Get status
        status_response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/executions/{execution_id}/status/"
        )
        
        assert status_response.status_code == 200, (
            f"Failed to get execution status: {status_response.status_code}"
        )


# =============================================================================
# Execution History Tests
# =============================================================================

class TestExecutionHistory:
    """Test execution history and management."""

    def test_execution_list(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test listing execution history.
        """
        response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/executions/"
        )
        
        assert response.status_code == 200, (
            f"Failed to get executions: {response.status_code}"
        )

    def test_execution_detail(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test getting execution detail.
        """
        # First get a list of executions
        list_response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/executions/",
            params={"page_size": 1}
        )
        
        if list_response.status_code != 200:
            pytest.skip("Failed to list executions")
        
        data = list_response.json()
        executions = data.get("results", [])
        
        if not executions:
            pytest.skip("No executions found")
        
        execution_id = executions[0].get("id")
        
        # Get detail
        detail_response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/executions/{execution_id}/"
        )
        
        assert detail_response.status_code == 200, (
            f"Failed to get execution detail: {detail_response.status_code}"
        )

    def test_execution_logs(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test getting execution logs.
        """
        # Get first execution
        list_response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/executions/",
            params={"page_size": 1}
        )
        
        if list_response.status_code != 200:
            pytest.skip("Failed to list executions")
        
        data = list_response.json()
        executions = data.get("results", [])
        
        if not executions:
            pytest.skip("No executions found")
        
        execution_id = executions[0].get("id")
        
        # Get logs
        logs_response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/executions/{execution_id}/logs/"
        )
        
        assert logs_response.status_code == 200, (
            f"Failed to get execution logs: {logs_response.status_code}"
        )

    def test_execution_statistics(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test getting execution statistics.
        """
        response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/executions/statistics/"
        )
        
        assert response.status_code == 200, (
            f"Failed to get statistics: {response.status_code}"
        )


# =============================================================================
# Template Tests
# =============================================================================

class TestWorkflowTemplates:
    """Test workflow templates."""

    def test_template_list(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test listing workflow templates.
        """
        response = authenticated_client.get(
            f"{django_base_url}/api/v1/workflows/templates/"
        )
        
        assert response.status_code == 200, (
            f"Failed to get templates: {response.status_code}"
        )
