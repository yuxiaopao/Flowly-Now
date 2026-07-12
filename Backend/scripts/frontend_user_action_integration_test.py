#!/usr/bin/env python
"""Action-level integration tests for user-facing write operations."""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")
REQUIRE_LLM = os.environ.get("FLOWLY_REQUIRE_LLM", "1") == "1"


def has_llm_env():
    return bool(
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("OLLAMA_HOST")
        or os.environ.get("OLLAMA_BASE_URL")
    )


def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and "code" in payload:
        return payload["data"]
    return payload


def call(method, path, token=None, payload=None, expect=(200, 201, 204), timeout=120):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
            parsed = json.loads(body) if body else None
            return status, unwrap(parsed), status in expect
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = unwrap(json.loads(body) if body else None)
        except json.JSONDecodeError:
            parsed = body[:300]
        return status, parsed, status in expect


def login():
    status, data, ok = call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
    if not ok or not isinstance(data, dict) or not data.get("access"):
        raise RuntimeError(f"login failed: {status} {data}")
    return data["access"]


def record(name, ok, **extra):
    item = {"name": name, "ok": ok}
    item.update(extra)
    return item


def test_workflow_crud(token):
    name = f"action-test-{uuid.uuid4().hex[:8]}"
    status, created, ok = call(
        "POST",
        "/workflows/",
        token=token,
        payload={"name": name, "description": "action integration test", "nodes": [], "edges": []},
    )
    if not ok or not isinstance(created, dict):
        return record("workflow-create", False, status=status, error=created)

    workflow_id = created.get("id")
    status, detail, ok = call("GET", f"/workflows/{workflow_id}/", token=token)
    if not ok:
        return record("workflow-detail", False, status=status, error=detail)

    status, _, ok = call("DELETE", f"/workflows/{workflow_id}/", token=token, expect=(204, 200))
    return record("workflow-crud", ok, workflow_id=workflow_id, delete_status=status)


def test_data_export(token):
    status, created, ok = call(
        "POST",
        "/data-export/request_export/",
        token=token,
        payload={"export_type": "workflows", "format": "json"},
    )
    if not ok or not isinstance(created, dict):
        return record("data-export-create", False, status=status, error=created)

    export_id = created.get("id")
    url = f"{BASE}/data-export/{export_id}/download/"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            ok_download = (
                resp.status == 200
                and len(content) > 0
                and b'"download_url"' not in content
                and content[:1] in (b"{", b"[")
            )
            return record(
                "data-export",
                ok_download,
                export_id=export_id,
                download_status=resp.status,
                bytes=len(content),
            )
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:300]
        return record("data-export", False, export_id=export_id, download_status=exc.code, error=err)


def test_rag_collection(token):
    suffix = uuid.uuid4().hex[:8]
    status, collection, ok = call(
        "POST",
        "/rag/collections/",
        token=token,
        payload={"name": f"action-test-{suffix}", "description": "integration test"},
    )
    if not ok or not isinstance(collection, dict):
        return record("rag-collection-create", False, status=status, error=collection)

    collection_id = collection.get("id")
    status, doc, ok = call(
        "POST",
        f"/rag/collections/{collection_id}/add_document/",
        token=token,
        payload={"title": "Action Test Doc", "content": "Flowly action integration test document about reviews."},
    )
    if not ok:
        call("DELETE", f"/rag/collections/{collection_id}/", token=token, expect=(204, 200))
        return record("rag-add-document", False, status=status, error=doc, collection_id=collection_id)

    status, docs, ok = call("GET", f"/rag/documents/?collection={collection_id}", token=token)
    doc_count = docs.get("count") if isinstance(docs, dict) else None

    call("DELETE", f"/rag/collections/{collection_id}/", token=token, expect=(204, 200))
    return record("rag-collection-document", ok, collection_id=collection_id, document_count=doc_count)


def test_nl_stream(token):
    """Verify NL workflow streaming endpoint creates session (SSE)."""
    status, models, ok = call("GET", "/gateway/models/", token=token)
    model_list = models if isinstance(models, list) else (models.get("results") if isinstance(models, dict) else [])
    if not ok or not model_list:
        return record("nl-stream", False, error="no gateway models available")

    model_id = model_list[0].get("model_id") or model_list[0].get("modelId") or model_list[0].get("id") or model_list[0].get("name")
    url = f"{BASE}/nl-workflow/stream/"
    payload = json.dumps({
        "description": "Action test: simple translate workflow",
        "model": model_id,
        "mode": "generate",
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            preview = resp.read(800).decode("utf-8", errors="replace")
            ok_stream = resp.status == 200 and '"type": "session"' in preview
            return record("nl-stream", ok_stream, status=resp.status, preview=preview[:200])
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:300]
        return record("nl-stream", False, status=exc.code, error=err)


def test_nl_session_llm(token):
    status, models, ok = call("GET", "/gateway/models/", token=token)
    model_list = models if isinstance(models, list) else (models.get("results") if isinstance(models, dict) else [])
    if not ok or not model_list:
        if REQUIRE_LLM:
            return record("nl-session-llm", False, error="no gateway models available")
        return record("nl-session-llm", True, skipped=True, reason="no models; LLM not required")

    model_id = model_list[0].get("model_id") or model_list[0].get("modelId") or model_list[0].get("id") or model_list[0].get("name")
    status, session, ok = call(
        "POST",
        "/nl-workflow/sessions/",
        token=token,
        payload={
            "description": "Create a simple workflow that translates text from English to Chinese.",
            "model": model_id,
            "mode": "chat",
        },
        timeout=180,
    )
    if not ok:
        return record("nl-session-llm", False, status=status, error=session)

    session_id = session.get("session_id") or session.get("id")
    return record("nl-session-llm", bool(session_id), session_id=session_id, status=session.get("status"))


def test_credentials(token):
    suffix = uuid.uuid4().hex[:8]
    status, created, ok = call(
        "POST",
        "/credentials/",
        token=token,
        payload={
            "name": f"action-test-{suffix}",
            "credential_type": "api_key",
            "credential_data": "test-key-action-integration",
            "service_type": "openai",
        },
        expect=(200, 201),
    )
    if not ok or not isinstance(created, dict):
        return record("credentials-create", False, status=status, error=created)

    cred_id = created.get("id")
    status, verify, ok = call("POST", f"/credentials/{cred_id}/verify/", token=token, expect=(200, 400))
    call("DELETE", f"/credentials/{cred_id}/", token=token, expect=(204, 200))
    return record("credentials-crud", True, credential_id=cred_id, verify_status=status, verify=verify)


def test_dataset_download(token):
    status, dataset_list, ok = call("GET", "/training/datasets/?page_size=20", token=token)
    if not ok or not isinstance(dataset_list, dict):
        return record("dataset-download", False, status=status, error=dataset_list)

    for item in dataset_list.get("results") or []:
        dataset_id = item.get("id") if isinstance(item, dict) else None
        if not dataset_id:
            continue
        url = f"{BASE}/training/datasets/{dataset_id}/download/"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                content = resp.read()
                if resp.status == 200 and len(content) > 0:
                    return record("dataset-download", True, dataset_id=dataset_id, bytes=len(content))
        except urllib.error.HTTPError:
            continue

    return record("dataset-download", False, error="no downloadable dataset with existing file")


def test_agent_stream_chat(token):
    """Verify agent stream_chat uses Ollama for local models (SSE, not 404)."""
    status, models, ok = call("GET", "/gateway/models/", token=token)
    model_list = models if isinstance(models, list) else (models.get("results") if isinstance(models, dict) else [])
    if not ok or not model_list:
        if REQUIRE_LLM:
            return record("agent-stream", False, error="no gateway models available")
        return record("agent-stream", True, skipped=True, reason="no models; LLM not required")

    model_id = model_list[0].get("model_id") or model_list[0].get("modelId") or model_list[0].get("id") or model_list[0].get("name")
    agent_name = f"action-agent-{uuid.uuid4().hex[:8]}"
    status, created, ok = call(
        "POST",
        "/agents/",
        token=token,
        payload={
            "name": agent_name,
            "description": "action integration test agent",
            "model": model_id,
            "system_prompt": "Reply concisely.",
            "temperature": 0.7,
            "max_tokens": 64,
        },
    )
    if not ok or not isinstance(created, dict):
        return record("agent-stream", False, step="create", status=status, error=created)

    agent_id = created.get("id")
    url = f"{BASE}/agents/{agent_id}/stream_chat/"
    payload = json.dumps({"message": "Reply with exactly: pong"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            ok_stream = (
                resp.status == 200
                and '"type": "done"' in body
                and "404 page not found" not in body
                and '"type": "error"' not in body
            )
            call("DELETE", f"/agents/{agent_id}/", token=token, expect=(204, 200))
            return record(
                "agent-stream",
                ok_stream,
                agent_id=agent_id,
                status=resp.status,
                preview=body[:200],
            )
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:300]
        call("DELETE", f"/agents/{agent_id}/", token=token, expect=(204, 200))
        return record("agent-stream", False, agent_id=agent_id, status=exc.code, error=err)


def test_alert_rule_crud(token):
    suffix = uuid.uuid4().hex[:8]
    status, created, ok = call(
        "POST",
        "/monitoring/rules/",
        token=token,
        payload={
            "name": f"action-test-{suffix}",
            "description": "integration test alert rule",
            "condition": "execution_failed",
            "severity": "medium",
            "threshold": 1,
            "enabled": True,
        },
    )
    if not ok or not isinstance(created, dict):
        return record("alert-rule-crud", False, status=status, error=created)

    rule_id = created.get("id")
    status, _, ok = call(
        "PATCH",
        f"/monitoring/rules/{rule_id}/",
        token=token,
        payload={"threshold": 2},
    )
    if not ok:
        call("DELETE", f"/monitoring/rules/{rule_id}/", token=token, expect=(204, 200))
        return record("alert-rule-update", False, status=status)

    status, _, ok = call("DELETE", f"/monitoring/rules/{rule_id}/", token=token, expect=(204, 200))
    return record("alert-rule-crud", ok, rule_id=rule_id, delete_status=status)


def test_tenant_invite(token):
    status, tenant_list, ok = call("GET", "/tenants/tenants/", token=token)
    tenant_items = tenant_list if isinstance(tenant_list, list) else (
        tenant_list.get("results") if isinstance(tenant_list, dict) else []
    )
    first_tenant = (tenant_items or [None])[0]
    if not ok or not isinstance(first_tenant, dict):
        return record("tenant-invite", False, status=status, error=tenant_list)

    tenant_id = first_tenant.get("id")
    email = f"action-invite-{uuid.uuid4().hex[:8]}@flowly.test"
    status, data, ok = call(
        "POST",
        f"/tenants/tenants/{tenant_id}/invite/",
        token=token,
        payload={"email": email, "role": "member"},
    )
    if not ok:
        return record("tenant-invite", False, status=status, error=data)

    invitation = data.get("invitation") if isinstance(data, dict) else None
    inv_id = invitation.get("id") if isinstance(invitation, dict) else None
    return record("tenant-invite", bool(inv_id), tenant_id=tenant_id, invitation_id=inv_id, email=email)


def _first_tenant_id(token):
    status, tenant_list, ok = call("GET", "/tenants/tenants/", token=token)
    if not ok:
        return None, status, tenant_list
    tenant_items = tenant_list if isinstance(tenant_list, list) else (
        tenant_list.get("results") if isinstance(tenant_list, dict) else []
    )
    first_tenant = (tenant_items or [None])[0]
    if not isinstance(first_tenant, dict):
        return None, status, tenant_list
    return first_tenant.get("id"), status, tenant_list


def test_yolo_run_create(token):
    suffix = uuid.uuid4().hex[:8]
    status, created, ok = call(
        "POST",
        "/training/yolo-runs/",
        token=token,
        payload={
            "name": f"action-yolo-{suffix}",
            "yolo_version": "v8",
            "model_variant": "n",
            "total_epochs": 5,
            "dataset_yaml_path": "demo/datasets/traffic_signs/data.yaml",
            "class_names": [],
        },
        expect=(200, 201),
    )
    if not ok or not isinstance(created, dict):
        return record("yolo-run-create", False, status=status, error=created)

    run_id = created.get("id")
    return record("yolo-run-create", bool(run_id), run_id=run_id, status=status)


def test_tenant_skill_task(token):
    tenant_id, status, err = _first_tenant_id(token)
    if not tenant_id:
        return record("tenant-skill-task", False, status=status, error=err)

    suffix = uuid.uuid4().hex[:8]
    status, skill, ok = call(
        "POST",
        "/tenants/skills/",
        token=token,
        payload={
            "tenant": tenant_id,
            "name": f"action-skill-{suffix}",
            "description": "integration test skill",
            "category": "workflow",
            "mastery_level": 2,
        },
        expect=(200, 201),
    )
    if not ok or not isinstance(skill, dict):
        return record("tenant-skill-task", False, step="skill", status=status, error=skill)

    skill_id = skill.get("id")
    status, task, ok = call(
        "POST",
        "/tenants/tasks/",
        token=token,
        payload={
            "tenant": tenant_id,
            "title": f"action-task-{suffix}",
            "description": "integration test task",
            "priority": "medium",
            "linked_skill": skill_id,
        },
        expect=(200, 201),
    )
    if not ok or not isinstance(task, dict):
        call("DELETE", f"/tenants/skills/{skill_id}/", token=token, expect=(204, 200))
        return record("tenant-skill-task", False, step="task", status=status, error=task)

    task_id = task.get("id")

    status, user_data, user_ok = call("GET", "/auth/user/", token=token)
    user_id = user_data.get("id") if isinstance(user_data, dict) else None
    assign_ok = False
    if user_id and skill_id:
        status, assign_data, assign_ok = call(
            "POST",
            f"/tenants/skills/{skill_id}/assign/",
            token=token,
            payload={"user_id": user_id, "role": "contributor", "proficiency_level": 3},
            expect=(200, 201),
        )
        if assign_ok:
            call(
                "POST",
                f"/tenants/skills/{skill_id}/unassign/",
                token=token,
                payload={"user_id": user_id},
                expect=(200,),
            )

    status, task_assign_data, task_assign_ok = call(
        "POST",
        f"/tenants/tasks/{task_id}/assign_user/",
        token=token,
        payload={"user_id": user_id, "role": "contributor"},
        expect=(200, 201),
    ) if user_id and task_id else (0, None, False)

    call("DELETE", f"/tenants/tasks/{task_id}/", token=token, expect=(204, 200))
    call("DELETE", f"/tenants/skills/{skill_id}/", token=token, expect=(204, 200))
    return record(
        "tenant-skill-task",
        bool(skill_id and task_id and assign_ok and task_assign_ok),
        skill_id=skill_id,
        task_id=task_id,
        skill_assign=assign_ok,
        task_assign=task_assign_ok,
    )


def main():
    token = login()
    results = [
        test_workflow_crud(token),
        test_data_export(token),
        test_rag_collection(token),
        test_credentials(token),
        test_dataset_download(token),
        test_nl_stream(token),
        test_nl_session_llm(token),
        test_agent_stream_chat(token),
        test_alert_rule_crud(token),
        test_tenant_invite(token),
        test_yolo_run_create(token),
        test_tenant_skill_task(token),
    ]

    passed = sum(1 for r in results if r["ok"])
    failed = [r for r in results if not r["ok"]]
    summary = {"passed": passed, "total": len(results), "failed": failed, "results": results}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
