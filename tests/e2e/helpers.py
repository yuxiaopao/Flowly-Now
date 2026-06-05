"""
Test utilities and helper functions for E2E tests.
"""
import json
import time
import requests
from typing import Any, Callable, Dict, List, Optional, Generator
from urllib.parse import urlparse


def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 30,
    poll_interval: float = 0.5,
    error_message: str = "Condition not met within timeout"
) -> bool:
    """
    Wait for a condition to become true.
    
    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        poll_interval: Time between checks in seconds
        error_message: Error message if timeout occurs
    
    Returns:
        True if condition met, raises TimeoutError otherwise
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(poll_interval)
    
    raise TimeoutError(error_message)


def wait_for_response(
    request_func: Callable[[], requests.Response],
    timeout: float = 30,
    poll_interval: float = 0.5,
    expected_status: int = 200
) -> requests.Response:
    """
    Wait for a request to succeed.
    
    Args:
        request_func: Function that makes a request
        timeout: Maximum time to wait in seconds
        poll_interval: Time between checks in seconds
        expected_status: Expected HTTP status code
    
    Returns:
        The successful response
    
    Raises:
        TimeoutError: If request doesn't succeed within timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = request_func()
            if response.status_code == expected_status:
                return response
            if 400 <= response.status_code < 600:
                raise requests.exceptions.HTTPError(
                    f"Request failed with status {response.status_code}: {response.text}"
                )
        except requests.exceptions.RequestException:
            pass
        time.sleep(poll_interval)
    
    raise TimeoutError(f"Request did not succeed within {timeout} seconds")


def verify_sse_events(
    response: requests.Response,
    expected_events: List[str],
    timeout: float = 60
) -> List[Dict[str, Any]]:
    """
    Verify SSE stream contains expected event types.
    
    Args:
        response: The streaming response from the server
        expected_events: List of expected event types (e.g., ['execution_start', 'node_start'])
        timeout: Maximum time to wait for all events
    
    Returns:
        List of parsed event dictionaries
    
    Raises:
        AssertionError: If expected events are not found
    """
    events = []
    found_events = set()
    
    start_time = time.time()
    
    for line in response.iter_lines(decode_unicode=True):
        if time.time() - start_time > timeout:
            raise TimeoutError(f"SSE stream timeout after {timeout} seconds")
        
        if line.startswith("data:"):
            data = line[5:].strip()
            try:
                event = json.loads(data)
                events.append(event)
                
                # Check for event type
                event_type = event.get("type") or event.get("event")
                if event_type:
                    found_events.add(event_type)
                
                # Check for special markers
                if "execution_start" in event:
                    found_events.add("execution_start")
                if "node_start" in event:
                    found_events.add("node_start")
                if "node_complete" in event:
                    found_events.add("node_complete")
                if "execution_complete" in event or event.get("status") == "completed":
                    found_events.add("execution_complete")
                
            except json.JSONDecodeError:
                pass
        
        # Check if we've received all expected events
        if all(e in found_events for e in expected_events):
            break
    
    # Verify all expected events were found
    missing_events = set(expected_events) - found_events
    if missing_events:
        raise AssertionError(
            f"Missing expected events in SSE stream: {missing_events}. "
            f"Found events: {found_events}"
        )
    
    return events


def parse_sse_stream(response: requests.Response) -> Generator[Dict[str, Any], None, None]:
    """
    Parse Server-Sent Events from a streaming response.
    
    Args:
        response: The streaming response
    
    Yields:
        Parsed event dictionaries
    """
    for line in response.iter_lines(decode_unicode=True):
        if line.startswith("data:"):
            data = line[5:].strip()
            if data:
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    yield {"raw": data}


def create_test_workflow(
    client: requests.Session,
    base_url: str,
    workflow_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Create a test workflow via API.
    
    Args:
        client: Authenticated requests session
        base_url: Django base URL
        workflow_data: Workflow data to create
    
    Returns:
        Created workflow data or None if failed
    """
    try:
        response = client.post(f"{base_url}/api/v1/workflows/", json=workflow_data)
        if response.status_code == 201:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None


def create_test_nodes(
    client: requests.Session,
    base_url: str,
    workflow_id: int,
    nodes_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Create test nodes for a workflow.
    
    Args:
        client: Authenticated requests session
        base_url: Django base URL
        workflow_id: ID of the parent workflow
        nodes_data: List of node data to create
    
    Returns:
        List of created node data
    """
    created_nodes = []
    
    for node_data in nodes_data:
        try:
            node_with_workflow = {**node_data, "workflow": workflow_id}
            response = client.post(
                f"{base_url}/api/v1/workflows/nodes/",
                json=node_with_workflow
            )
            if response.status_code == 201:
                created_nodes.append(response.json())
        except requests.exceptions.RequestException:
            pass
    
    return created_nodes


def create_test_edges(
    client: requests.Session,
    base_url: str,
    workflow_id: int,
    edges_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Create test edges for a workflow.
    
    Args:
        client: Authenticated requests session
        base_url: Django base URL
        workflow_id: ID of the parent workflow
        edges_data: List of edge data to create
    
    Returns:
        List of created edge data
    """
    created_edges = []
    
    for edge_data in edges_data:
        try:
            edge_with_workflow = {**edge_data, "workflow": workflow_id}
            response = client.post(
                f"{base_url}/api/v1/workflows/edges/",
                json=edge_with_workflow
            )
            if response.status_code == 201:
                created_edges.append(response.json())
        except requests.exceptions.RequestException:
            pass
    
    return created_edges


def execute_workflow_sync(
    client: requests.Session,
    base_url: str,
    workflow_id: int,
    input_data: Dict[str, Any] = None,
    timeout: float = 120
) -> Dict[str, Any]:
    """
    Execute a workflow synchronously and wait for completion.
    
    Args:
        client: Authenticated requests session
        base_url: Django base URL
        workflow_id: ID of workflow to execute
        input_data: Input data for execution
        timeout: Maximum time to wait for execution
    
    Returns:
        Execution result dictionary
    """
    input_data = input_data or {}
    
    # Start execution
    response = client.post(
        f"{base_url}/api/v1/workflows/{workflow_id}/execute/",
        json={"input_data": input_data}
    )
    
    if response.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"Failed to start execution: {response.status_code} - {response.text}"
        )
    
    result = response.json()
    execution_id = result.get("execution_id")
    
    if not execution_id:
        return result
    
    # Poll for completion
    start_time = time.time()
    while time.time() - start_time < timeout:
        status_response = client.get(
            f"{base_url}/api/v1/workflows/executions/{execution_id}/status/"
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status in ("completed", "success"):
                # Get final result
                output_response = client.get(
                    f"{base_url}/api/v1/workflows/executions/{execution_id}/output/"
                )
                if output_response.status_code == 200:
                    return output_response.json()
                return status_data
            
            if status in ("failed", "error"):
                return {"status": status, "error": status_data.get("error")}
        
        time.sleep(2)
    
    return {"status": "timeout", "execution_id": execution_id}


def stream_execute_workflow(
    client: requests.Session,
    base_url: str,
    workflow_id: int,
    input_data: Dict[str, Any] = None
) -> requests.Response:
    """
    Start streaming execution of a workflow.
    
    Args:
        client: Authenticated requests session
        base_url: Django base URL
        workflow_id: ID of workflow to execute
        input_data: Input data for execution
    
    Returns:
        Streaming response
    """
    input_data = input_data or {}
    
    response = client.post(
        f"{base_url}/api/v1/workflows/{workflow_id}/stream_execute/",
        json={"input_data": input_data},
        stream=True
    )
    
    return response


def get_workflow_by_id(
    client: requests.Session,
    base_url: str,
    workflow_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get a workflow by ID.
    
    Args:
        client: Authenticated requests session
        base_url: Django base URL
        workflow_id: ID of workflow to retrieve
    
    Returns:
        Workflow data or None if not found
    """
    try:
        response = client.get(f"{base_url}/api/v1/workflows/{workflow_id}/")
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None


def delete_workflow(
    client: requests.Session,
    base_url: str,
    workflow_id: int
) -> bool:
    """
    Delete a workflow.
    
    Args:
        client: Authenticated requests session
        base_url: Django base URL
        workflow_id: ID of workflow to delete
    
    Returns:
        True if deleted successfully
    """
    try:
        response = client.delete(f"{base_url}/api/v1/workflows/{workflow_id}/")
        return response.status_code in (204, 200)
    except requests.exceptions.RequestException:
        return False


def check_ollama_health(base_url: str = "http://localhost:11434") -> Dict[str, Any]:
    """
    Check Ollama server health.
    
    Args:
        base_url: Ollama base URL
    
    Returns:
        Health status dictionary with keys: status, latency_ms, models_count
    """
    start = time.time()
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=10)
        latency_ms = int((time.time() - start) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "ok",
                "latency_ms": latency_ms,
                "models_count": len(data.get("models", [])),
                "models": [m.get("name") for m in data.get("models", [])]
            }
        else:
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "error": f"HTTP {response.status_code}"
            }
    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "latency_ms": int((time.time() - start) * 1000),
            "error": "Connection timeout"
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "latency_ms": int((time.time() - start) * 1000),
            "error": str(e)
        }


def check_gateway_health(client: requests.Session, base_url: str) -> Dict[str, Any]:
    """
    Check gateway health via Django API.
    
    Args:
        client: Authenticated requests session
        base_url: Django base URL
    
    Returns:
        Health status dictionary
    """
    try:
        response = client.get(f"{base_url}/api/v1/gateway/health/")
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "status_code": response.status_code}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": str(e)}


def validate_workflow(
    client: requests.Session,
    base_url: str,
    workflow_id: int
) -> Dict[str, Any]:
    """
    Validate a workflow.
    
    Args:
        client: Authenticated requests session
        base_url: Django base URL
        workflow_id: ID of workflow to validate
    
    Returns:
        Validation result dictionary with valid, errors, warnings
    """
    try:
        response = client.post(f"{base_url}/api/v1/workflows/{workflow_id}/validate/")
        if response.status_code == 200:
            return response.json()
        return {"valid": False, "errors": [f"Validation failed: {response.status_code}"]}
    except requests.exceptions.RequestException as e:
        return {"valid": False, "errors": [str(e)]}
