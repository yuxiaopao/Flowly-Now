# -*- coding: utf-8 -*-
"""Live API smoke for NL P2 paths."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
RESULTS = []


def record(name: str, ok: bool, detail: str = ""):
    RESULTS.append({"name": name, "ok": ok, "detail": detail})
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}: {detail}")


def unwrap(payload):
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        # Prefer inner data when API envelope is present
        inner = payload["data"]
        # Keep top-level code/message for debugging
        return inner
    return payload


def req(method: str, path: str, token: str | None = None, body=None, timeout=180):
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return resp.status, unwrap(payload), payload, None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:800]}
        return e.code, unwrap(payload), payload, str(e)
    except Exception as e:
        return 0, {}, {}, str(e)


def main():
    status, login, _, err = req(
        "POST",
        "/auth/login/",
        body={"username": "nlwftest", "password": "Test123456!"},
        timeout=30,
    )
    token = (login.get("access") if isinstance(login, dict) else None)
    if not token and isinstance(login, dict):
        token = (login.get("data") or {}).get("access")
    record("login", status == 200 and bool(token), f"http={status} err={err}")
    if not token:
        return 1

    status, intent, _, err = req(
        "POST",
        "/nl-workflow/analyze-intent/",
        token=token,
        body={"message": "创建一个视频翻译工作流"},
        timeout=60,
    )
    data = intent if isinstance(intent, dict) else {}
    source = data.get("source") or (data.get("resolved") or {}).get("source")
    record(
        "analyze-intent",
        status == 200 and bool(data),
        f"http={status} source={source} intent={data.get('intent')} err={err}",
    )

    status, sync, _, err = req(
        "POST",
        "/nl-workflow/sessions/",
        token=token,
        body={
            "description": "创建一个简单问答机器人，节点：开始、LLM问答、结束",
            "name": "P2-smoke-sync",
            "mode": "generate",
        },
        timeout=180,
    )
    wf = sync.get("workflow_json") or sync.get("workflow") or {}
    nodes = wf.get("nodes") or []
    sync_ok = status in (200, 201) and len(nodes) > 0 and not sync.get("error")
    record(
        "sync-generate",
        sync_ok,
        f"http={status} nodes={len(nodes)} intelligent={wf.get('_is_intelligent')} "
        f"mode={wf.get('_generation_mode')} agent_val={bool(wf.get('_agent_validation'))} "
        f"err={sync.get('error') or err}",
    )
    sync_sid = sync.get("session_id")

    status, async_resp, _, err = req(
        "POST",
        "/nl-workflow/sessions/",
        token=token,
        body={
            "description": "创建一个CSV数据清洗与邮件通知工作流",
            "name": "P2-smoke-async",
            "mode": "generate",
            "async": True,
        },
        timeout=60,
    )
    async_ok = status == 202 and async_resp.get("status") == "processing" and async_resp.get("task_id")
    record(
        "async-enqueue",
        bool(async_ok),
        f"http={status} status={async_resp.get('status')} task={async_resp.get('task_id')} err={err}",
    )
    async_sid = async_resp.get("session_id")

    final_status = None
    node_count = 0
    if async_sid:
        for i in range(40):
            time.sleep(3)
            st, task, _, terr = req("GET", f"/nl-workflow/sessions/{async_sid}/task/", token=token, timeout=30)
            final_status = task.get("status")
            node_count = len((task.get("workflow_json") or {}).get("nodes") or [])
            print(f"  poll[{i}] http={st} status={final_status} celery={task.get('celery_state')} nodes={node_count}")
            if final_status in ("completed", "failed"):
                break
        record(
            "async-poll-complete",
            final_status == "completed" and node_count > 0,
            f"status={final_status} nodes={node_count}",
        )
    else:
        record("async-poll-complete", False, "no session id")

    if sync_sid:
        st, detail, _, derr = req("GET", f"/nl-workflow/sessions/{sync_sid}/", token=token, timeout=30)
        record(
            "session-detail-p2-fields",
            st == 200 and ("conversation_summary" in detail) and ("celery_task_id" in detail),
            f"http={st} keys_ok={('conversation_summary' in detail) and ('celery_task_id' in detail)} err={derr}",
        )

        st, msg, _, merr = req(
            "POST",
            f"/nl-workflow/sessions/{sync_sid}/message/",
            token=token,
            body={"message": "把LLM节点改成使用agnes模型", "mode": "editor"},
            timeout=120,
        )
        record(
            "editor-message",
            st == 200 and bool(msg.get("message") is not None),
            f"http={st} intent={msg.get('intent')} has_wf={bool(msg.get('workflow') or msg.get('workflow_json'))} err={merr}",
        )
    else:
        record("session-detail-p2-fields", False, "no sync session")
        record("editor-message", False, "no sync session")

    # task endpoint 404 sanity for bad id
    st, _, _, _ = req("GET", "/nl-workflow/sessions/00000000-0000-0000-0000-000000000099/task/", token=token, timeout=20)
    record("task-404", st == 404, f"http={st}")

    passed = sum(1 for r in RESULTS if r["ok"])
    failed = sum(1 for r in RESULTS if not r["ok"])
    print("\n=== SUMMARY ===")
    print(f"passed={passed} failed={failed} total={len(RESULTS)}")
    out = {
        "passed": passed,
        "failed": failed,
        "results": RESULTS,
    }
    with open(r"E:\Flowly-now\test-reports\nl_p2_api_smoke.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
