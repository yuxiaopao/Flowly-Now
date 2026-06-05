#!/usr/bin/env python3
"""
Comprehensive Workflow API Test Suite
Tests: CRUD, nodes, edges, execution, validation, templates, variables
"""

import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

def login():
    url = f"{BASE_URL}/auth/login/"
    data = json.dumps({"username": "testuser123", "password": "test123456"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
        return result["data"]["access"]

def api_request(method, path, token, data=None, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # urllib always uses GET when data is None, POST when data is provided.
    # For PATCH/DELETE/other methods with data, we need special handling.
    if method in ("PATCH", "DELETE") and data is not None:
        # Use lambda to override method after construction
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
        req.get_method = lambda: method
    elif method in ("GET", "HEAD", "OPTIONS") or data is None:
        req = urllib.request.Request(url, headers=headers)
        if method != "GET":
            req.get_method = lambda: method
    else:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            if body:
                return resp.status, json.loads(body)
            return resp.status, {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, {"error": body[:500]}

def test(name, fn):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)
    try:
        result = fn()
        if result:
            print(f"  PASS")
        else:
            print(f"  FAIL")
    except Exception as e:
        print(f"  ERROR: {e}")
    time.sleep(0.5)

def main():
    print("Starting Comprehensive Workflow API Tests")
    token = login()
    print(f"Logged in as testuser123")

    # Clean up existing test workflows
    status, data = api_request("GET", "/workflows/", token, params={"page_size": 100})
    if status == 200:
        for wf in data.get("data", {}).get("results", []):
            if "Test Workflow" in wf.get("name", "") or "测试工作流" in wf.get("name", ""):
                api_request("DELETE", f"/workflows/{wf['id']}/", token)
                print(f"  Cleaned up: {wf['name']}")

    # ============================================================
    # TEST 1: Create Simple Workflow
    # ============================================================
    def test_create_simple():
        status, data = api_request("POST", "/workflows/", token, {
            "name": "Test Simple Workflow",
            "description": "A simple test workflow"
        })
        print(f"  Status: {status}")
        if status == 201:
            print(f"  Created: {data['data']['id']} - {data['data']['name']}")
            return True
        print(f"  Error: {data}")
        return False
    test("Create Simple Workflow", test_create_simple)

    # ============================================================
    # TEST 2: Create Workflow with Nodes
    # ============================================================
    wf_id = None
    def test_create_with_nodes():
        nonlocal wf_id
        status, data = api_request("POST", "/workflows/", token, {
            "name": "Test Workflow with Nodes",
            "nodes": [
                {"node_type": "start", "name": "Start", "position_x": 100, "position_y": 100, "config": {}},
                {"node_type": "input", "name": "User Input", "position_x": 100, "position_y": 200, "config": {"input_type": "text"}},
                {"node_type": "llm", "name": "LLM Response", "position_x": 100, "position_y": 300, "config": {"model": "ollama/llama3", "prompt": "Answer: {{input}}"}},
                {"node_type": "end", "name": "End", "position_x": 100, "position_y": 400, "config": {}}
            ]
        })
        print(f"  Status: {status}")
        if status == 201:
            wf_id = data["data"]["id"]
            print(f"  Created: {wf_id}")
            print(f"  Nodes: {len(data['data'].get('nodes', []))}")
            return True
        print(f"  Error: {data}")
        return False
    test("Create Workflow with Nodes", test_create_with_nodes)

    # ============================================================
    # TEST 4: Get Workflow Detail
    # ============================================================
    detail_id = None
    def test_get_detail():
        nonlocal detail_id
        if not wf_id:
            print("  Skipped - no workflow created")
            return False
        status, data = api_request("GET", f"/workflows/{wf_id}/", token)
        print(f"  Status: {status}")
        if status == 200:
            detail_id = wf_id
            nodes = data["data"].get("nodes", [])
            edges = data["data"].get("edges", [])
            print(f"  Name: {data['data']['name']}")
            print(f"  Nodes: {len(nodes)}, Edges: {len(edges)}")
            for n in nodes:
                print(f"    - {n['node_type']}: {n['name']} (ID: {n['id']})")
            return True
        print(f"  Error: {data}")
        return False
    test("Get Workflow Detail", test_get_detail)

    # ============================================================
    # TEST 4: List Workflows with Pagination
    # ============================================================
    def test_list_workflows():
        status, data = api_request("GET", "/workflows/", token, params={"page_size": 5})
        print(f"  Status: {status}")
        if status == 200:
            results = data["data"].get("results", [])
            print(f"  Total count: {data['data'].get('count', 0)}")
            print(f"  Page 1 items: {len(results)}")
            return True
        print(f"  Error: {data}")
        return False
    test("List Workflows with Pagination", test_list_workflows)

    # ============================================================
    # TEST 5: Update Workflow
    # ============================================================
    def test_update_workflow():
        if not wf_id:
            print("  Skipped - no workflow created")
            return False
        status, data = api_request("PATCH", f"/workflows/{wf_id}/", token, {
            "name": "Test Workflow - Updated",
            "description": "Updated description"
        })
        print(f"  Status: {status}")
        if status == 200:
            print(f"  New name: {data['data']['name']}")
            return True
        print(f"  Error: {data}")
        return False
    test("Update Workflow", test_update_workflow)

    # ============================================================
    # TEST 6: Validate Workflow
    # ============================================================
    def test_validate_workflow():
        if not wf_id:
            print("  Skipped - no workflow created")
            return False
        status, data = api_request("POST", f"/workflows/{wf_id}/validate/", token, {})
        print(f"  Status: {status}")
        print(f"  Response: {json.dumps(data, ensure_ascii=False)[:300]}")
        return status in [200, 201]
    test("Validate Workflow", test_validate_workflow)

    # ============================================================
    # TEST 7: Execute Workflow
    # ============================================================
    exec_id = None
    def test_execute_workflow():
        nonlocal exec_id
        if not wf_id:
            print("  Skipped - no workflow created")
            return False
        status, data = api_request("POST", f"/workflows/{wf_id}/execute/", token, {
            "input_data": {"input": "Hello, world!"},
            "is_async": False
        })
        print(f"  Status: {status}")
        print(f"  Response: {json.dumps(data, ensure_ascii=False)[:500]}")
        if status in [200, 202]:
            exec_id = data.get("data", {}).get("execution_id")
            print(f"  Execution ID: {exec_id}")
            return True
        return False
    test("Execute Workflow (sync)", test_execute_workflow)

    # ============================================================
    # TEST 8: Get Execution Status
    # ============================================================
    def test_get_execution():
        if not exec_id:
            print("  Skipped - no execution created")
            return False
        status, data = api_request("GET", f"/workflows/executions/{exec_id}/", token)
        print(f"  Status: {status}")
        if status == 200:
            print(f"  Execution status: {data.get('data', {}).get('status')}")
            return True
        return False
    test("Get Execution Status", test_get_execution)

    # ============================================================
    # TEST 9: List Executions
    # ============================================================
    def test_list_executions():
        status, data = api_request("GET", "/workflows/executions/", token)
        print(f"  Status: {status}")
        if status == 200:
            print(f"  Count: {data['data'].get('count', 0)}")
            return True
        return False
    test("List Executions", test_list_executions)

    # ============================================================
    # TEST 10: List Templates
    # ============================================================
    def test_list_templates():
        status, data = api_request("GET", "/templates/", token)
        print(f"  Status: {status}")
        if status == 200:
            count = data["data"].get("count", 0)
            print(f"  Template count: {count}")
            return True
        return False
    test("List Templates", test_list_templates)

    # ============================================================
    # TEST 11: List Variables
    # ============================================================
    def test_list_variables():
        status, data = api_request("GET", "/variables/", token)
        print(f"  Status: {status}")
        return status == 200
    test("List Variables", test_list_variables)

    # ============================================================
    # TEST 12: Create Variable
    # ============================================================
    var_id = None
    def test_create_variable():
        nonlocal var_id
        status, data = api_request("POST", "/variables/", token, {
            "name": "test_var",
            "value": "test_value",
            "type": "string"
        })
        print(f"  Status: {status}")
        if status == 201:
            var_id = data["data"]["id"]
            print(f"  Created: {var_id}")
            return True
        print(f"  Error: {data}")
        return False
    test("Create Variable", test_create_variable)

    # ============================================================
    # TEST 13: List Tools
    # ============================================================
    def test_list_tools():
        status, data = api_request("GET", "/tools/", token)
        print(f"  Status: {status}")
        if status == 200:
            print(f"  Tool count: {data['data'].get('count', 0)}")
            return True
        return False
    test("List Tools", test_list_tools)

    # ============================================================
    # TEST 14: List Node Types
    # ============================================================
    def test_list_node_types():
        status, data = api_request("GET", "/workflows/nodes/available_types/", token)
        print(f"  Status: {status}")
        if status == 200:
            types = data.get("data", [])
            print(f"  Node types: {len(types)}")
            print(f"  Types: {[t.get('type') or t.get('node_type', '?') for t in types[:10]]}")
            return True
        return False
    test("List Available Node Types", test_list_node_types)

    # ============================================================
    # TEST 15: Duplicate Workflow
    # ============================================================
    dup_id = None
    def test_duplicate():
        nonlocal dup_id
        if not wf_id:
            print("  Skipped - no workflow created")
            return False
        status, data = api_request("POST", f"/workflows/{wf_id}/duplicate/", token, {})
        print(f"  Status: {status}")
        if status in [200, 201]:
            dup_id = data.get("data", {}).get("id") or data.get("data", {}).get("workflow_id")
            print(f"  Duplicated ID: {dup_id}")
            return True
        print(f"  Error: {data}")
        return False
    test("Duplicate Workflow", test_duplicate)

    # ============================================================
    # TEST 16: Export Workflow
    # ============================================================
    def test_export():
        if not wf_id:
            print("  Skipped - no workflow created")
            return False
        status, data = api_request("GET", f"/workflows/{wf_id}/export/", token)
        print(f"  Status: {status}")
        if status == 200:
            print(f"  Has data: {'data' in data}")
            return True
        return False
    test("Export Workflow", test_export)

    # ============================================================
    # TEST 17: Search Workflows
    # ============================================================
    def test_search():
        status, data = api_request("GET", "/workflows/", token, params={"search": "Test"})
        print(f"  Status: {status}")
        if status == 200:
            print(f"  Found: {data['data'].get('count', 0)} workflows")
            return True
        return False
    test("Search Workflows", test_search)

    # ============================================================
    # TEST 18: Delete Duplicated Workflow
    # ============================================================
    def test_delete_dup():
        if not dup_id:
            print("  Skipped - no duplicated workflow")
            return False
        status, data = api_request("DELETE", f"/workflows/{dup_id}/", token)
        print(f"  Status: {status}")
        return status in [200, 204]
    test("Delete Duplicated Workflow", test_delete_dup)

    # ============================================================
    # TEST 19: Delete Main Workflow
    # ============================================================
    def test_delete_main():
        if not wf_id:
            print("  Skipped - no workflow created")
            return False
        status, data = api_request("DELETE", f"/workflows/{wf_id}/", token)
        print(f"  Status: {status}")
        return status in [200, 204]
    test("Delete Main Workflow", test_delete_main)

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"  Base URL: {BASE_URL}")
    print(f"  User: testuser123")
    print(f"  Tests completed: Comprehensive workflow API tests")
    print("="*60)

if __name__ == "__main__":
    main()
