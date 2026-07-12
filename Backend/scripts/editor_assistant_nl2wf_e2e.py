#!/usr/bin/env python
"""E2E: NL2WF preview + editor assistant deterministic actions (layout / add language chain)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
REPORT = REPO / "test-reports" / "EDITOR_ASSISTANT_NL2WF_E2E.md"

sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")


def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and "code" in payload:
        return payload["data"]
    return payload


def call(method, path, token=None, payload=None, timeout=120):
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
            return resp.status, unwrap(parsed), True
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = unwrap(json.loads(body)) if body else None
        except json.JSONDecodeError:
            parsed = body[:500]
        return exc.code, parsed, False
    except urllib.error.URLError as exc:
        return 0, str(exc), False


def main() -> int:
    import django

    django.setup()

    from nl_to_workflow.services import NLToWorkflowService
    from nl_to_workflow.video_translation_workflow import build_split_video_translation_workflow

    lines = [
        "# Editor Assistant + NL2WF E2E",
        "",
        f"- Time: {datetime.now().isoformat(timespec='seconds')}",
        "",
    ]
    errors: list[str] = []

    status, login, ok = call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
    token = login.get("access") if isinstance(login, dict) else None
    if not ok or not token:
        lines.append(f"- Login: FAIL — {status} {login}")
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        return 1
    lines.append("- Login: OK")

    status, prev, ok = call(
        "POST",
        "/nl-workflow/preview/",
        token=token,
        payload={"description": "文生图再生视频，现在就生成工作流"},
    )
    wf = (prev or {}).get("workflow_json") or (prev or {}).get("workflow") or {}
    types = [n.get("type") for n in wf.get("nodes", [])]
    if ok and "image_generation" in types and "video_generation" in types:
        lines.append(f"- NL Preview (multimodal): OK — {len(types)} nodes")
    else:
        errors.append(f"multimodal preview: {status} types={types}")
        lines.append(f"- NL Preview (multimodal): FAIL — types={types}")

    status, prev2, ok2 = call(
        "POST",
        "/nl-workflow/preview/",
        token=token,
        payload={
            "description": "视频翻译：中文视频翻译成英文和日文，分节点，现在就生成工作流",
        },
    )
    wf2 = (prev2 or {}).get("workflow_json") or (prev2 or {}).get("workflow") or {}
    types2 = [n.get("type") for n in wf2.get("nodes", [])]
    mode2 = wf2.get("_generation_mode")
    if ok2 and "video_upload" in types2 and mode2 == "template_video_translation_split":
        lines.append(f"- NL Preview (video split): OK — {len(types2)} nodes, mode={mode2}")
    else:
        errors.append(f"video preview: mode={mode2} types={types2}")
        lines.append(f"- NL Preview (video split): FAIL — mode={mode2}, nodes={len(types2)}")

    svc = NLToWorkflowService()
    canvas = build_split_video_translation_workflow("中文视频翻译成英文")
    layout = svc.continue_conversation([], "帮我自动排布节点", current_workflow=canvas, mode="editor")
    if layout.get("workflow") and layout.get("changes"):
        lines.append(f"- Editor layout: OK — {layout.get('message', '')[:80]}")
    else:
        errors.append(f"layout: {layout}")
        lines.append("- Editor layout: FAIL")

    add_ja = svc.continue_conversation([], "添加日语翻译处理链", current_workflow=canvas, mode="editor")
    ja_nodes = [n for n in (add_ja.get("workflow") or {}).get("nodes", []) if n.get("id") == "node_translate_ja"]
    if ja_nodes:
        lines.append(f"- Editor add JA chain: OK — {add_ja.get('message', '')[:80]}")
    else:
        errors.append(f"add ja: {add_ja}")
        lines.append("- Editor add JA chain: FAIL")

    lines.extend(["", f"- **Result**: {'PASS' if not errors else 'FAIL'}"])
    if errors:
        lines.extend(["", "## Errors", ""])
        for e in errors:
            lines.append(f"- {e}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
