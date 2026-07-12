#!/usr/bin/env python
"""Smoke test user-facing API endpoints used by the frontend."""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")


def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and "code" in payload:
        return payload["data"]
    return payload


def call(method, path, token=None, payload=None, expect=(200, 201, 204)):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
            parsed = json.loads(body) if body else None
            parsed = unwrap(parsed)
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = unwrap(json.loads(body) if body else None)
        except json.JSONDecodeError:
            parsed = body[:200]
        if status not in expect:
            return status, parsed, False
        return status, parsed, True
    ok = status in expect
    return status, parsed, ok


def login():
    status, data, ok = call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
    if not ok or not isinstance(data, dict) or not data.get("access"):
        raise RuntimeError(f"login failed: {status} {data}")
    return data["access"]


def check(name, method, path, token, expect=(200, 201), payload=None):
    status, data, ok = call(method, path, token=token, payload=payload, expect=expect)
    result = {
        "name": name,
        "method": method,
        "path": path,
        "status": status,
        "ok": ok,
    }
    if not ok:
        result["error"] = data
    elif isinstance(data, dict) and "count" in data:
        result["count"] = data.get("count")
    elif isinstance(data, list):
        result["count"] = len(data)
    return result


def probe_websocket(name, path, expected_type="connected", token=None):
    """Generic WebSocket connectivity probe (requires Daphne/ASGI)."""
    import urllib.parse

    ws_base = os.environ.get("FLOWLY_WS_BASE", "ws://127.0.0.1:8000")
    result = {
        "name": name,
        "method": "WS",
        "path": path,
        "ok": False,
    }
    try:
        import asyncio
        import websockets
    except ImportError:
        result["error"] = "websockets package not installed — skip WS check"
        result["ok"] = True
        result["skipped"] = True
        return result

    uri = f"{ws_base.rstrip('/')}{path}"
    if token:
        uri += ("&" if "?" in uri else "?") + f"token={urllib.parse.quote(token)}"

    async def probe():
        async with websockets.connect(uri, open_timeout=5) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            payload = json.loads(msg)
            if payload.get("type") != expected_type:
                raise RuntimeError(f"unexpected ws payload: {payload}")
            return payload

    try:
        payload = asyncio.run(probe())
        result["ok"] = True
        result["message_type"] = payload.get("type")
    except Exception as exc:
        result["error"] = str(exc)
    return result


def check_training_websocket(token):
    """Verify training WebSocket accepts connections (requires Daphne/ASGI)."""
    result = {
        "name": "training-websocket",
        "method": "WS",
        "path": "/ws/training/<job_id>/",
        "ok": False,
    }

    status, data, ok = call("GET", "/training/yolo-runs/?page_size=1", token=token)
    if not ok or not isinstance(data, dict):
        result["error"] = f"cannot list yolo runs: {status} {data}"
        return result

    first_run = (data.get("results") or [None])[0]
    job_id = first_run.get("id") if isinstance(first_run, dict) else None
    if not job_id:
        result["error"] = "no yolo runs available for websocket probe"
        return result

    path = f"/ws/training/{job_id}/"
    probe = probe_websocket("training-websocket", path)
    probe["job_id"] = job_id
    return probe


def check_execution_websocket(token):
    """Verify execution WebSocket accepts UUID execution ids."""
    result = {
        "name": "execution-websocket",
        "method": "WS",
        "path": "/ws/execution/<execution_id>/",
        "ok": False,
    }

    status, data, ok = call("GET", "/workflows/executions/?page_size=1", token=token)
    if not ok or not isinstance(data, dict):
        result["error"] = f"cannot list executions: {status} {data}"
        return result

    first_exec = (data.get("results") or [None])[0]
    execution_id = first_exec.get("id") if isinstance(first_exec, dict) else None
    if not execution_id:
        result["error"] = "no executions available for websocket probe"
        return result

    path = f"/ws/execution/{execution_id}/"
    probe = probe_websocket("execution-websocket", path)
    probe["execution_id"] = execution_id
    return probe


def check_monitoring_websocket():
    return probe_websocket("monitoring-websocket", "/ws/monitoring/")


def check_workflow_websocket(token):
    """Verify workflow collaboration WebSocket accepts UUID workflow ids."""
    result = {
        "name": "workflow-websocket",
        "method": "WS",
        "path": "/ws/workflow/<workflow_id>/",
        "ok": False,
    }

    status, data, ok = call("GET", "/workflows/?page_size=1", token=token)
    if not ok or not isinstance(data, dict):
        result["error"] = f"cannot list workflows: {status} {data}"
        return result

    first_workflow = (data.get("results") or [None])[0]
    workflow_id = first_workflow.get("id") if isinstance(first_workflow, dict) else None
    if not workflow_id:
        result["error"] = "no workflows available for websocket probe"
        return result

    path = f"/ws/workflow/{workflow_id}/"
    probe = probe_websocket("workflow-websocket", path, token=token)
    probe["workflow_id"] = workflow_id
    return probe


def check_codegraph_websocket(token):
    """Verify codegraph WebSocket accepts authenticated connections."""
    result = {
        "name": "codegraph-websocket",
        "method": "WS",
        "path": "/ws/<project_id>/",
        "ok": False,
    }

    status, data, ok = call("GET", "/codegraph/projects/", token=token)
    if not ok:
        result["error"] = f"cannot list codegraph projects: {status} {data}"
        return result

    projects = data if isinstance(data, list) else (data.get("results") if isinstance(data, dict) else [])
    if not projects:
        result["ok"] = True
        result["skipped"] = True
        result["error"] = "no codegraph projects — skipped"
        return result

    project_id = projects[0].get("id") if isinstance(projects[0], dict) else None
    if project_id is None:
        result["error"] = "invalid codegraph project payload"
        return result

    path = f"/ws/{project_id}/"
    probe = probe_websocket("codegraph-websocket", path, token=token)
    probe["project_id"] = project_id
    return probe


def check_desktop_agent_websocket():
    """Verify desktop agent WebSocket endpoint accepts connections."""
    return probe_websocket("desktop-agent-websocket", "/ws/agent/smoke-test-agent/")


def main():
    token = login()
    results = []

    endpoints = [
        ("auth-me", "GET", "/auth/user/"),
        ("workflows-list", "GET", "/workflows/"),
        ("agents-list", "GET", "/agents/"),
        ("agents-desktop-available", "GET", "/agents/desktop/available/"),
        ("templates-list", "GET", "/templates/"),
        ("templates-mine", "GET", "/templates/mine/"),
        ("templates-installed", "GET", "/templates/installed/"),
        ("templates-featured", "GET", "/templates/featured/"),
        ("templates-by-category", "GET", "/templates/by_category/"),
        ("executions-list", "GET", "/workflows/executions/"),
        ("executions-statistics", "GET", "/workflows/executions/statistics/"),
        ("prompts-list", "GET", "/prompts/templates/"),
        ("gateway-models", "GET", "/gateway/models/"),
        ("gateway-providers", "GET", "/gateway/providers/"),
        ("rag-vector-stores", "GET", "/rag/vector-stores/"),
        ("rag-collections", "GET", "/rag/collections/"),
        ("rag-documents", "GET", "/rag/documents/"),
        ("rag-pipelines", "GET", "/rag/pipelines/"),
        ("datasets-list", "GET", "/training/datasets/"),
        ("tenants-memberships", "GET", "/tenants/memberships/"),
        ("notifications-list", "GET", "/notifications/"),
        ("analytics-overview", "GET", "/monitoring/analytics/overview/"),
        ("monitoring-health", "GET", "/monitoring/health/"),
        ("nl-sessions", "GET", "/nl-workflow/sessions/"),
        ("nl-models", "GET", "/nl-workflow/models/"),
        ("triggers-list", "GET", "/workflows/triggers/"),
        ("nodes-available-types", "GET", "/workflows/nodes/available_types/"),
        ("credentials-list", "GET", "/credentials/"),
        ("integrations-list", "GET", "/integrations/integrations/"),
        ("training-runs", "GET", "/training/training-jobs/"),
        ("yolo-runs-list", "GET", "/training/yolo-runs/"),
        ("codegraph-projects", "GET", "/codegraph/projects/"),
        ("augmentations-list", "GET", "/augmentations/"),
        ("augmentations-statistics", "GET", "/augmentations/statistics/"),
        ("execution-cache-list", "GET", "/execution-cache/"),
        ("execution-cache-stats", "GET", "/execution-cache/stats/"),
        ("cache-config-list", "GET", "/cache-config/"),
        ("billing-plans", "GET", "/billing/prices/plans/"),
        ("billing-subscription", "GET", "/billing/subscriptions/my/"),
        ("billing-usage", "GET", "/billing/subscriptions/usage/"),
        ("integrations-available", "GET", "/integrations/integrations/available/"),
        ("integrations-templates", "GET", "/integrations/templates/"),
        ("integrations-templates-featured", "GET", "/integrations/templates/featured/"),
        ("templates-categories", "GET", "/templates/categories/"),
        ("branding-current", "GET", "/branding/branding/current/"),
        ("dataset-recommend-list", "GET", "/dataset-recommend/datasets/"),
        ("website-generator-list", "GET", "/website-generator/"),
    ]

    for name, method, path in endpoints:
        results.append(check(name, method, path, token))

    status, tenant_list, ok = call("GET", "/tenants/tenants/", token=token)
    if ok:
        tenant_items = tenant_list if isinstance(tenant_list, list) else (
            tenant_list.get("results") if isinstance(tenant_list, dict) else []
        )
        first_tenant = (tenant_items or [None])[0]
        tenant_id = first_tenant.get("id") if isinstance(first_tenant, dict) else None
        if tenant_id:
            results.append(check("tenants-members", "GET", f"/tenants/tenants/{tenant_id}/members/", token))
            results.append(check("tenants-usage", "GET", f"/tenants/tenants/{tenant_id}/usage/", token))
            results.append(
                check(
                    "tenants-invite",
                    "POST",
                    f"/tenants/tenants/{tenant_id}/invite/",
                    token,
                    payload={"email": f"smoke-invite-{uuid.uuid4().hex[:8]}@flowly.test", "role": "member"},
                    expect=(200, 201),
                )
            )
            results.append(
                check(
                    "tenants-skills-create",
                    "POST",
                    "/tenants/skills/",
                    token,
                    payload={
                        "tenant": tenant_id,
                        "name": f"smoke-skill-{uuid.uuid4().hex[:8]}",
                        "category": "workflow",
                        "mastery_level": 1,
                    },
                    expect=(200, 201),
                )
            )
            results.append(
                check(
                    "yolo-runs-create",
                    "POST",
                    "/training/yolo-runs/",
                    token,
                    payload={
                        "name": f"smoke-yolo-{uuid.uuid4().hex[:8]}",
                        "yolo_version": "v8",
                        "model_variant": "n",
                        "total_epochs": 3,
                        "dataset_yaml_path": "demo/datasets/traffic_signs/data.yaml",
                    },
                    expect=(200, 201),
                )
            )

    status, exec_list, ok = call("GET", "/workflows/executions/?page_size=1", token=token)
    if ok and isinstance(exec_list, dict):
        first_exec = (exec_list.get("results") or [None])[0]
        exec_id = first_exec.get("id") if isinstance(first_exec, dict) else None
        if exec_id:
            results.append(check(
                "executions-timeline",
                "GET",
                f"/workflows/executions/{exec_id}/timeline/",
                token,
            ))

    results.append(check(
        "agents-desktop-dispatch-validation",
        "POST",
        "/agents/desktop/dispatch_training/",
        token,
        expect=(400,),
        payload={"agent_id": "", "job_config": {}},
    ))

    results.append(check(
        "workflows-optimize",
        "POST",
        "/workflows/optimize/",
        token,
        expect=(200,),
        payload={"nodes": [], "edges": [], "dimensions": ["maintainability"]},
    ))

    results.append(check(
        "training-gpu-info",
        "GET",
        "/training/training-jobs/gpu-info/",
        token,
    ))

    results.append(check(
        "website-generator-agent-validation",
        "POST",
        "/website-generator/00000000-0000-0000-0000-000000000000/agent/message/",
        token,
        expect=(400, 404),
        payload={"content": "smoke test"},
    ))

    status, site_list, ok = call("GET", "/website-generator/?page_size=1", token=token)
    if ok and isinstance(site_list, dict):
        first_site = (site_list.get("results") or [None])[0]
        site_id = first_site.get("id") if isinstance(first_site, dict) else None
        if site_id:
            results.append(check(
                "website-generator-detail",
                "GET",
                f"/website-generator/{site_id}/",
                token,
            ))

    status, dataset_list, ok = call("GET", "/training/datasets/?page_size=20", token=token)
    if ok and isinstance(dataset_list, dict):
        seen_formats = set()
        for dataset_item in dataset_list.get("results") or []:
            if not isinstance(dataset_item, dict):
                continue
            dataset_id = dataset_item.get("id")
            fmt = dataset_item.get("format")
            if not dataset_id or fmt not in ("csv", "json") or fmt in seen_formats:
                continue
            seen_formats.add(fmt)
            results.append(check(
                f"datasets-preview-{fmt}",
                "GET",
                f"/training/datasets/{dataset_id}/preview/",
                token,
            ))
            results.append(check(
                f"datasets-stats-{fmt}",
                "GET",
                f"/training/datasets/{dataset_id}/stats/",
                token,
            ))
        first_dataset = (dataset_list.get("results") or [None])[0]
        dataset_id = first_dataset.get("id") if isinstance(first_dataset, dict) else None
        if dataset_id:
            results.append(check(
                "datasets-detail",
                "GET",
                f"/training/datasets/{dataset_id}/",
                token,
            ))

    results.append(check_training_websocket(token))
    results.append(check_execution_websocket(token))
    results.append(check_monitoring_websocket())
    results.append(check_workflow_websocket(token))
    results.append(check_codegraph_websocket(token))
    results.append(check_desktop_agent_websocket())

    passed = sum(1 for r in results if r["ok"])
    failed = [r for r in results if not r["ok"]]

    seeded_expectations = {
        "templates-list": lambda r: (r.get("count") or 0) >= 4,
        "templates-mine": lambda r: (r.get("count") or 0) >= 2,
        "prompts-list": lambda r: (r.get("count") or 0) >= 3,
        "integrations-templates": lambda r: (r.get("count") or 0) >= 4 if isinstance(r.get("count"), int) else True,
        "yolo-runs-list": lambda r: (r.get("count") or 0) >= 2,
        "datasets-list": lambda r: (r.get("count") or 0) >= 2,
        "dataset-recommend-list": lambda r: (r.get("count") or 0) >= 10,
        "augmentations-list": lambda r: (r.get("count") or 0) >= 2,
    }
    for result in results:
        checker = seeded_expectations.get(result["name"])
        if checker and result["ok"] and not checker(result):
            result["ok"] = False
            result["error"] = f"expected seeded data for {result['name']}, got count={result.get('count')}"
            failed.append(result)
            passed -= 1

    print(json.dumps({"summary": f"{passed}/{len(results)} passed", "failed": failed, "results": results}, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
