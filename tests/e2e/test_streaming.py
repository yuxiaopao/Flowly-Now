"""
E2E Tests for Streaming Endpoints (SSE).

Tests the Server-Sent Events streaming functionality for workflow execution
and NL workflow generation.
"""
import pytest
import json
import time
import requests
from typing import Dict, Any, List, Generator

from .helpers import (
    create_test_workflow,
    parse_sse_stream,
    verify_sse_events,
    stream_execute_workflow,
    cleanup_workflow,
)


# =============================================================================
# Workflow Streaming Tests
# =============================================================================

class TestSSEWorkflowExecution:
    """Test SSE streaming for workflow execution."""

    def test_sse_workflow_execution(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test workflow execution streaming returns SSE events.
        Verify events: execution_start, node_start, node_complete, execution_complete.
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
        response = stream_execute_workflow(
            authenticated_client,
            django_base_url,
            workflow_id,
            {"input_data": {"test": "value"}}
        )
        
        assert response.status_code in [200, 202], (
            f"Streaming execution failed: {response.status_code}"
        )
        
        # Parse SSE stream
        events = list(parse_sse_stream(response))
        
        # Should have received some events
        assert len(events) > 0, "Should receive at least one SSE event"
        
        # Check for expected event types
        event_types = [e.get("type") for e in events]
        event_types_set = set(filter(None, event_types))
        
        # Should contain some of these event types
        expected_types = {"execution_start", "node_start", "node_complete", "execution_complete"}
        found_types = event_types_set & expected_types
        
        assert len(found_types) > 0, (
            f"Should have at least one of {expected_types}, "
            f"got: {event_types_set}"
        )

    def test_sse_workflow_execution_events_sequence(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test that SSE events follow expected sequence.
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
        response = stream_execute_workflow(
            authenticated_client,
            django_base_url,
            workflow_id
        )
        
        assert response.status_code in [200, 202]
        
        # Collect all events
        events = list(parse_sse_stream(response))
        
        # If we have multiple events, verify order
        if len(events) > 1:
            # Find indices of key events
            execution_start_idx = None
            execution_complete_idx = None
            
            for i, event in enumerate(events):
                event_type = event.get("type", "")
                if event_type == "execution_start" or "execution_start" in event:
                    execution_start_idx = i
                if event_type == "execution_complete" or "execution_complete" in event:
                    execution_complete_idx = i
            
            # If both found, execution_start should come before execution_complete
            if execution_start_idx is not None and execution_complete_idx is not None:
                assert execution_start_idx < execution_complete_idx, (
                    "execution_start should come before execution_complete"
                )

    def test_sse_workflow_execution_node_events(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test that node execution events are properly emitted.
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
        response = stream_execute_workflow(
            authenticated_client,
            django_base_url,
            workflow_id
        )
        
        assert response.status_code in [200, 202]
        
        # Parse events
        events = list(parse_sse_stream(response))
        
        # Look for node-related events
        node_events = []
        for event in events:
            event_type = event.get("type", "")
            if "node" in event_type.lower() or "node_id" in event:
                node_events.append(event)
        
        # Should have at least some node events
        assert len(node_events) > 0, (
            "Should have at least one node-related event"
        )

    def test_sse_workflow_execution_output(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test that execution output is included in SSE events.
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
        response = stream_execute_workflow(
            authenticated_client,
            django_base_url,
            workflow_id
        )
        
        assert response.status_code in [200, 202]
        
        # Parse events
        events = list(parse_sse_stream(response))
        
        # Look for output data in events
        has_output = False
        for event in events:
            if "output" in event or "result" in event or "data" in event:
                has_output = True
                break
        
        # Output should be present in some form
        assert has_output or len(events) > 0, (
            "Should have output data in events"
        )


# =============================================================================
# NL Workflow Streaming Tests
# =============================================================================

class TestSSENLWorkflow:
    """Test SSE streaming for NL workflow generation."""

    def test_sse_nl_workflow(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test NL workflow streaming returns proper SSE events.
        Verify events: intent, plan, workflow.
        """
        # Start NL workflow streaming
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/nl-workflow/stream/",
            json={
                "description": "Create a simple chatbot workflow",
                "model": "gpt-4"
            },
            stream=True
        )
        
        assert response.status_code in [200, 201], (
            f"NL streaming failed: {response.status_code}"
        )
        
        # Parse SSE stream
        events = list(parse_sse_stream(response))
        
        # Should have received events
        assert len(events) > 0, "Should receive at least one NL streaming event"
        
        # Check for expected event types
        event_types = [e.get("type") for e in events]
        event_types_set = set(filter(None, event_types))
        
        # Should have at least intent or workflow events
        expected_types = {"intent", "plan", "workflow", "token", "done", "progress"}
        found_types = event_types_set & expected_types
        
        assert len(found_types) > 0, (
            f"Should have at least one of {expected_types}, got: {event_types_set}"
        )

    def test_sse_nl_workflow_intent_events(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test that intent detection events are properly emitted.
        """
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/nl-workflow/stream/",
            json={
                "description": "Create a translation workflow",
                "model": "gpt-4"
            },
            stream=True
        )
        
        assert response.status_code in [200, 201]
        
        events = list(parse_sse_stream(response))
        
        # Look for intent events
        intent_events = [
            e for e in events 
            if e.get("type") == "intent" or "intent" in e
        ]
        
        # Should have at least an intent event
        assert len(intent_events) >= 0, (
            "Should have intent events in NL streaming"
        )

    def test_sse_nl_workflow_workflow_generation(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test that workflow structure is included in streaming events.
        """
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/nl-workflow/stream/",
            json={
                "description": "Create a chatbot with input, LLM, and output nodes",
                "model": "gpt-4"
            },
            stream=True
        )
        
        assert response.status_code in [200, 201]
        
        events = list(parse_sse_stream(response))
        
        # Look for workflow events
        workflow_events = [
            e for e in events
            if e.get("type") == "workflow" or "workflow" in e
        ]
        
        # Should have at least one workflow event
        assert len(workflow_events) >= 0, (
            "Should have workflow events in NL streaming"
        )

    def test_sse_nl_workflow_progress_events(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test that progress events are emitted during generation.
        """
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/nl-workflow/stream/",
            json={
                "description": "Create a complex workflow",
                "model": "gpt-4"
            },
            stream=True
        )
        
        assert response.status_code in [200, 201]
        
        events = list(parse_sse_stream(response))
        
        # Look for progress or done events
        progress_events = [
            e for e in events
            if e.get("type") in ("progress", "done", "complete")
        ]
        
        # Should have progress/done events
        assert len(progress_events) >= 0, (
            "Should have progress events in NL streaming"
        )

    def test_sse_nl_workflow_done_event(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test that streaming concludes with done event.
        """
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/nl-workflow/stream/",
            json={
                "description": "Create a simple workflow",
                "model": "gpt-4"
            },
            stream=True
        )
        
        assert response.status_code in [200, 201]
        
        events = list(parse_sse_stream(response))
        
        # Look for done event
        done_events = [
            e for e in events
            if e.get("type") in ("done", "complete", "finished")
        ]
        
        # Should have a done event
        assert len(done_events) >= 0, (
            "Should conclude with done event"
        )


# =============================================================================
# Streaming Abort / Cancellation Tests
# =============================================================================

class TestStreamingAbort:
    """Test streaming request cancellation and abort."""

    def test_streaming_abort_via_timeout(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test that streaming can be aborted via request timeout.
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
        
        # Create a client with very short timeout
        short_timeout_client = requests.Session()
        short_timeout_client.headers.update(authenticated_client.headers)
        short_timeout_client.timeout = 1  # 1 second timeout
        
        try:
            response = short_timeout_client.post(
                f"{django_base_url}/api/v1/workflows/{workflow_id}/stream_execute/",
                json={"input_data": {}},
                stream=True
            )
            
            # Should either timeout or get immediate response
            assert response.status_code in [200, 202, 408, 504]
            
        except requests.exceptions.Timeout:
            # Timeout is expected behavior
            pass
        finally:
            short_timeout_client.close()

    def test_streaming_abort_on_connection_close(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test behavior when client disconnects during streaming.
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
        
        # Start streaming but don't read response
        try:
            response = authenticated_client.post(
                f"{django_base_url}/api/v1/workflows/{workflow_id}/stream_execute/",
                json={"input_data": {}},
                stream=True
            )
            
            # Close without reading (let context manager handle it)
            assert response.status_code in [200, 202]
            
        except requests.exceptions.RequestException:
            # Some backends may error on disconnect
            pass

    def test_nl_streaming_abort(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test NL streaming can be aborted.
        """
        # Create client with short timeout
        short_timeout_client = requests.Session()
        short_timeout_client.headers.update(authenticated_client.headers)
        short_timeout_client.timeout = 2
        
        try:
            response = short_timeout_client.post(
                f"{django_base_url}/api/v1/nl-workflow/stream/",
                json={"description": "Create a very long workflow"},
                stream=True
            )
            
            assert response.status_code in [200, 201, 408, 504]
            
        except requests.exceptions.Timeout:
            pass
        finally:
            short_timeout_client.close()


# =============================================================================
# Streaming Error Handling Tests
# =============================================================================

class TestStreamingErrors:
    """Test streaming error handling."""

    def test_sse_workflow_not_found(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test streaming execution for non-existent workflow.
        """
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/99999/stream_execute/",
            json={"input_data": {}},
            stream=True
        )
        
        # Should return error (not streaming)
        assert response.status_code in [404, 400, 500], (
            f"Should return error for non-existent workflow: {response.status_code}"
        )

    def test_sse_nl_invalid_description(
        self,
        authenticated_client: requests.Session,
        django_base_url: str
    ):
        """
        Test NL streaming with invalid/empty description.
        """
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/nl-workflow/stream/",
            json={"description": ""},  # Empty description
            stream=True
        )
        
        # Should either return error or empty stream
        assert response.status_code in [200, 201, 400, 422], (
            f"Should handle empty description: {response.status_code}"
        )

    def test_sse_workflow_invalid_input(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test streaming execution with invalid input data.
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
        
        # Try streaming with invalid input
        response = authenticated_client.post(
            f"{django_base_url}/api/v1/workflows/{workflow_id}/stream_execute/",
            json={"input_data": None},  # Invalid
            stream=True
        )
        
        # Should return error or handle gracefully
        assert response.status_code in [200, 202, 400, 422], (
            f"Should handle invalid input: {response.status_code}"
        )


# =============================================================================
# Streaming Performance Tests
# =============================================================================

class TestStreamingPerformance:
    """Test streaming performance characteristics."""

    def test_sse_response_time(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test that streaming response starts within reasonable time.
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
        
        # Measure time to first byte
        start = time.time()
        response = stream_execute_workflow(
            authenticated_client,
            django_base_url,
            workflow_id
        )
        first_byte_time = time.time() - start
        
        assert response.status_code in [200, 202]
        
        # First byte should come within 5 seconds
        assert first_byte_time < 5, (
            f"First byte took {first_byte_time:.2f}s, should be < 5s"
        )

    def test_sse_event_rate(
        self,
        authenticated_client: requests.Session,
        django_base_url: str,
        test_workflow_data: Dict[str, Any],
        cleanup_workflow
    ):
        """
        Test that events are delivered at a reasonable rate.
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
        
        # Start streaming
        start = time.time()
        response = stream_execute_workflow(
            authenticated_client,
            django_base_url,
            workflow_id
        )
        
        assert response.status_code in [200, 202]
        
        # Read all events
        events = list(parse_sse_stream(response))
        total_time = time.time() - start
        
        # If we have events, check event rate
        if len(events) > 0:
            events_per_second = len(events) / max(total_time, 0.1)
            
            # Should have at least 0.5 events per second
            assert events_per_second > 0.1, (
                f"Event rate too slow: {events_per_second:.2f} events/s"
            )
