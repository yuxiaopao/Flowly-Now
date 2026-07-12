#!/usr/bin/env python
"""
NL2WF E2E: 手机网页详细 + 发邮箱 → 保存工作流 → 可选执行

Usage:
  python scripts/mobile_page_email_nl2wf_e2e.py
  python scripts/mobile_page_email_nl2wf_e2e.py --execute
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
REPORT = REPO / "test-reports" / "MOBILE_PAGE_EMAIL_NL2WF.md"

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")
NL_MODEL = os.environ.get("NL_WORKFLOW_MODEL", "agnes-2.0-flash")
RECIPIENT = os.environ.get("MOBILE_EMAIL_RECIPIENT", "3488394996@qq.com")

NL_CHAT = (
    "我想做一个工作流：根据输入主题生成详细的手机端网页（HTML），"
    f"然后把网页内容发到邮箱 {RECIPIENT}。"
)

NL_GENERATE = "主题：Flowly 产品功能介绍手机详情页。现在就生成工作流。"

FALLBACK = None


def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and "code" in payload:
        return payload["data"]
    return payload


def call(method, path, token=None, payload=None, timeout=600, expect=(200, 201, 202, 204)):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body) if body else None
            return resp.status, unwrap(parsed), resp.status in expect
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else None
            parsed = unwrap(parsed) if parsed else None
        except json.JSONDecodeError:
            parsed = body[:800]
        return exc.code, parsed, exc.code in expect


def login():
    status, data, ok = call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
    if not ok or not isinstance(data, dict) or not data.get("access"):
        raise RuntimeError(f"login failed: {status} {data}")
    return data["access"]


def parse_sse_events(raw: str):
    events = []
    for block in raw.split("\n\n"):
        for line in block.split("\n"):
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
    return events


def stream_nl_message(token, session_id, message, mode="chat"):
    url = f"{BASE}/nl-workflow/sessions/{session_id}/message/stream/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
    }
    payload = json.dumps({"message": message, "model": NL_MODEL, "mode": mode}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return parse_sse_events(raw)


def build_fallback_workflow():
    from nl_to_workflow.mobile_page_email_workflow import build_mobile_page_email_workflow

    return build_mobile_page_email_workflow(
        f"手机网页详细，发邮箱 {RECIPIENT}",
        default_recipient=RECIPIENT,
    )


def workflow_to_save_payload(workflow_json):
    nodes = []
    for n in workflow_json.get("nodes", []):
        nodes.append({
            "id": n.get("id") or str(uuid.uuid4()),
            "type": n.get("type"),
            "name": n.get("name") or n.get("label") or n.get("type"),
            "position": n.get("position") or {"x": 0, "y": 0},
            "config": n.get("config") or {},
        })
    edges = workflow_json.get("edges") or []
    return {
        "name": workflow_json.get("name") or "手机网页生成并发送邮件",
        "description": workflow_json.get("description") or "",
        "nodes": nodes,
        "edges": edges,
        "status": "draft",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Execute saved workflow after NL2WF")
    parser.add_argument("--skip-nl", action="store_true", help="Use template fallback only")
    args = parser.parse_args()

    lines = [
        f"# Mobile Page + Email NL2WF E2E",
        f"",
        f"- Time: {datetime.now().isoformat()}",
        f"- Model: {NL_MODEL}",
        f"- Recipient: {RECIPIENT}",
        f"",
    ]

    token = login()
    lines.append("- Login: OK")

    workflow_json = None
    session_id = None

    if not args.skip_nl:
        status, sess, ok = call("POST", "/nl-workflow/sessions/", token=token, payload={
            "description": NL_CHAT,
            "name": "手机网页+邮件 NL 测试",
            "model": NL_MODEL,
            "mode": "chat",
        })
        if ok and isinstance(sess, dict):
            session_id = sess.get("session_id") or sess.get("id")
            lines.append(f"- Session (chat): {session_id}, ready={sess.get('ready_to_generate')}")

        if not session_id:
            status, created, ok = call("POST", "/nl-workflow/sessions/", token=token, payload={
                "name": "手机网页+邮件 NL 测试",
                "description": NL_CHAT,
            })
            session_id = (created or {}).get("session_id") or (created or {}).get("id")

        if session_id:
            chat_events = stream_nl_message(token, session_id, NL_CHAT, mode="chat")
            done = next((e for e in reversed(chat_events) if e.get("type") == "done"), {})
            lines.append(f"- Chat stream: intent={done.get('intent')}, ready={done.get('ready_to_generate')}")

            gen_events = stream_nl_message(token, session_id, NL_GENERATE, mode="generate")
            wf_event = next((e for e in gen_events if e.get("type") == "workflow"), None)
            if wf_event:
                workflow_json = wf_event.get("workflow")
            if not workflow_json:
                done_gen = next((e for e in reversed(gen_events) if e.get("type") == "done"), {})
                workflow_json = done_gen.get("workflow")
            lines.append(f"- Generate stream: nodes={len((workflow_json or {}).get('nodes', []))}")

    if not workflow_json:
        workflow_json = build_fallback_workflow()
        lines.append("- Used template fallback workflow")

    email_nodes = [n for n in workflow_json.get("nodes", []) if n.get("type") == "email"]
    if email_nodes:
        to_addr = (email_nodes[0].get("config") or {}).get("to", "")
        lines.append(f"- Email node to: `{to_addr}`")
        if RECIPIENT not in str(to_addr):
            email_nodes[0]["config"]["to"] = RECIPIENT
            lines.append(f"- Patched email to: `{RECIPIENT}`")

    save_payload = workflow_to_save_payload(workflow_json)
    status, saved, ok = call("POST", f"/nl-workflow/sessions/{session_id}/confirm/", token=token, payload={
        "workflow_json": workflow_json,
        "name": save_payload["name"],
    }) if session_id else (0, None, False)

    workflow_id = None
    if ok and isinstance(saved, dict):
        workflow_id = saved.get("workflow_id")
        lines.append(f"- Saved workflow: `{workflow_id}`")
    else:
        status, wf_resp, ok2 = call("POST", "/workflows/", token=token, payload=save_payload)
        if ok2 and isinstance(wf_resp, dict):
            workflow_id = wf_resp.get("id")
            lines.append(f"- Saved via workflows API: `{workflow_id}`")
        else:
            lines.append(f"- Save failed: {status} {saved or wf_resp}")
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text("\n".join(lines), encoding="utf-8")
            print("\n".join(lines))
            sys.exit(1)

    if args.execute and workflow_id:
        status, exec_resp, ok = call("POST", f"/workflows/{workflow_id}/execute/", token=token, payload={
            "input_data": {"page_topic": "Flowly 智能工作流平台：自然语言创建工作流、多模态生成、邮件自动化"},
            "is_async": False,
        }, timeout=900)
        lines.append(f"- Execute: status={status}, ok={ok}")
        if isinstance(exec_resp, dict):
            lines.append(f"  - execution_id: {exec_resp.get('id') or exec_resp.get('execution_id')}")
            lines.append(f"  - execution status: {exec_resp.get('status')}")

    lines.extend([
        "",
        "## Result",
        f"- Workflow ID: `{workflow_id}`",
        f"- Editor: http://127.0.0.1:5200/workflows/{workflow_id}/edit",
    ])

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReport: {REPORT}")


if __name__ == "__main__":
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    main()
