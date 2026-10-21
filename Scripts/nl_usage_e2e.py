# -*- coding: utf-8 -*-
"""End-to-end usage: generate -> confirm save -> verify workflow."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
OUT = r"E:\Flowly-now\test-reports\nl_usage_e2e.json"
results = []


def record(name, ok, detail=""):
    results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def req(method, path, token=None, body=None, timeout=180):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode() or "{}")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:500]}
        status = e.code
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return status, payload["data"], payload
    return status, payload, payload


def main():
    st, login, _ = req("POST", "/auth/login/", body={"username": "nlwftest", "password": "Test123456!"})
    token = login.get("access")
    record("login", st == 200 and token, f"http={st}")
    if not token:
        return 1

    # Sync generate (daily path fallback)
    st, sync, _ = req(
        "POST",
        "/nl-workflow/sessions/",
        token=token,
        body={
            "description": "创建一个简单问答机器人，包含开始、LLM问答、结束节点",
            "name": "usage-sync-qa",
            "mode": "generate",
        },
        timeout=180,
    )
    wf = sync.get("workflow_json") or sync.get("workflow") or {}
    sync_sid = sync.get("session_id")
    record(
        "sync-generate",
        st in (200, 201) and len(wf.get("nodes") or []) >= 3 and wf.get("_is_intelligent") is True,
        f"http={st} nodes={len(wf.get('nodes') or [])} intelligent={wf.get('_is_intelligent')} agent={bool(wf.get('_agent_validation'))}",
    )

    # Confirm save
    st, confirmed, _ = req("POST", f"/nl-workflow/sessions/{sync_sid}/confirm/", token=token, timeout=60)
    wid = confirmed.get("workflow_id") or confirmed.get("id") or (confirmed.get("workflow") or {}).get("id")
    record("confirm-save", st in (200, 201) and bool(wid), f"http={st} workflow_id={wid}")

    # Fetch saved workflow
    if wid:
        st, detail, _ = req("GET", f"/workflows/{wid}/", token=token, timeout=30)
        nodes = (detail.get("nodes") or []) if isinstance(detail, dict) else []
        # nodes may be nested
        if not nodes and isinstance(detail, dict):
            nodes = (detail.get("workflow") or {}).get("nodes") or detail.get("node_list") or []
        record("workflow-detail", st == 200, f"http={st} keys={list(detail.keys())[:8] if isinstance(detail, dict) else type(detail)}")
    else:
        record("workflow-detail", False, "no workflow id")

    # Async enqueue + poll (+ auto reconcile)
    st, async_resp, _ = req(
        "POST",
        "/nl-workflow/sessions/",
        token=token,
        body={
            "description": "创建一个文本摘要工作流",
            "name": "usage-async-summary",
            "mode": "generate",
            "async": True,
        },
        timeout=60,
    )
    async_sid = async_resp.get("session_id")
    task_id = async_resp.get("task_id")
    record("async-enqueue", st == 202 and async_resp.get("status") == "processing" and task_id, f"http={st} task={task_id}")

    final = None
    if async_sid:
        for i in range(50):
            time.sleep(3)
            st, task, _ = req("GET", f"/nl-workflow/sessions/{async_sid}/task/", token=token, timeout=30)
            final = task
            print(f"  poll[{i}] status={task.get('status')} celery={task.get('celery_state')} recovered={task.get('recovered')} nodes={len((task.get('workflow_json') or {}).get('nodes') or [])}")
            if task.get("status") in ("completed", "failed"):
                break
            # mid-way retry once if still pending
            if i == 12 and task.get("celery_state") == "PENDING":
                rst, retry, _ = req("POST", f"/nl-workflow/sessions/{async_sid}/task/", token=token, body={"action": "retry"}, timeout=30)
                print(f"  retry http={rst} task={retry.get('task_id')}")
        nodes = len(((final or {}).get("workflow_json") or {}).get("nodes") or [])
        record(
            "async-complete",
            (final or {}).get("status") == "completed" and nodes > 0,
            f"status={(final or {}).get('status')} nodes={nodes} recovered={(final or {}).get('recovered')}",
        )
    else:
        record("async-complete", False, "no async session")

    # Editor refine on sync session
    if sync_sid:
        st, msg, _ = req(
            "POST",
            f"/nl-workflow/sessions/{sync_sid}/message/",
            token=token,
            body={"message": "优化一下节点布局", "mode": "editor"},
            timeout=120,
        )
        record(
            "editor-layout",
            st == 200 and bool(msg.get("workflow") or msg.get("workflow_json")),
            f"http={st} intent={msg.get('intent')} msg={(msg.get('message') or '')[:60]}",
        )

    passed = sum(1 for r in results if r["ok"])
    failed = sum(1 for r in results if not r["ok"])
    report = {"passed": passed, "failed": failed, "results": results, "workflow_id": wid, "sync_session": sync_sid, "async_session": async_sid}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nSUMMARY passed={passed} failed={failed} -> {OUT}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
