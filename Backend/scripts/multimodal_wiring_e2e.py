#!/usr/bin/env python
"""E2E: multimodal NL2WF template wiring + execute with user prompt."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
REPORT = REPO / "test-reports" / "MULTIMODAL_WIRING_E2E.md"

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")
NL_MODEL = os.environ.get("NL_WORKFLOW_MODEL", "agnes-2.0-flash")
TEST_PROMPT = os.environ.get("MULTIMODAL_TEST_PROMPT", "生成一只猫")

NL_DESCRIPTION = (
    "文生图再生视频工作流：用户输入描述，先生成图像，再用该图像和相同描述生成视频。"
    "现在就生成工作流。"
)


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


def verify_wiring(workflow: dict) -> list[str]:
    errors = []
    nodes = workflow.get("nodes") or []
    types = [n.get("type") for n in nodes]
    for required in ("input", "image_generation", "video_generation"):
        if required not in types:
            errors.append(f"missing node type: {required}")
    inp = next((n for n in nodes if n.get("type") == "input"), None)
    img = next((n for n in nodes if n.get("type") == "image_generation"), None)
    vid = next((n for n in nodes if n.get("type") == "video_generation"), None)
    if inp:
        name = (inp.get("config") or {}).get("input_name") or (inp.get("config") or {}).get("variable_name")
        if name != "prompt":
            errors.append(f"input_name expected prompt, got {name!r}")
    if img:
        prompt = (img.get("config") or {}).get("prompt", "")
        if prompt != "{prompt}":
            errors.append(f"image prompt expected {{prompt}}, got {prompt!r}")
    if vid:
        vp = (vid.get("config") or {}).get("prompt", "")
        vi = (vid.get("config") or {}).get("inputImage") or (vid.get("config") or {}).get("input_image")
        if vp != "{prompt}":
            errors.append(f"video prompt expected {{prompt}}, got {vp!r}")
        if vi != "{images.0.url}":
            errors.append(f"video inputImage expected {{images.0.url}}, got {vi!r}")
    return errors


def build_execute_input(workflow: dict, prompt: str) -> dict:
    payload = {"prompt": prompt, "text": prompt, "user_input": prompt, "input": prompt}
    for node in workflow.get("nodes", []):
        if node.get("type") != "input":
            continue
        cfg = node.get("config") or {}
        name = cfg.get("input_name") or cfg.get("variable_name") or "prompt"
        payload[name] = prompt
    return payload


def extract_node_outputs(detail: dict) -> dict:
    out = {}
    node_status = detail.get("node_status") or {}
    for nid, info in node_status.items():
        if not isinstance(info, dict):
            continue
        out[nid] = {
            "type": info.get("node_type"),
            "name": info.get("node_name"),
            "status": info.get("status"),
            "output": info.get("output") or {},
            "error": info.get("error") or info.get("message"),
        }
    return out


def main():
    lines = [
        "# Multimodal Wiring E2E",
        "",
        f"- Time: {datetime.now().isoformat()}",
        f"- Test prompt: `{TEST_PROMPT}`",
        "",
    ]
    token = login()
    lines.append("- Login: OK")

    status, preview, ok = call(
        "POST",
        "/nl-workflow/preview/",
        token=token,
        payload={"description": NL_DESCRIPTION, "model": NL_MODEL},
        timeout=300,
    )
    workflow = (preview or {}).get("workflow_json") or (preview or {}).get("workflow") or preview or {}
    mode = workflow.get("_generation_mode", "unknown")
    wiring_errors = verify_wiring(workflow) if workflow.get("nodes") else ["empty workflow"]
    lines.append(f"- NL Preview: status={status}, mode={mode}, nodes={len(workflow.get('nodes') or [])}")
    if wiring_errors:
        lines.append(f"- Wiring: FAIL — {wiring_errors}")
    else:
        lines.append("- Wiring: OK — input=prompt, image={prompt}, video={prompt}+{images.0.url}")

    if wiring_errors:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        sys.exit(1)

    save_payload = {
        "name": workflow.get("name") or "文生图再生视频工作流",
        "description": workflow.get("description") or NL_DESCRIPTION,
        "nodes": workflow.get("nodes", []),
        "edges": workflow.get("edges", []),
        "status": "draft",
    }
    status, saved, ok = call("POST", "/workflows/", token=token, payload=save_payload)
    wf_id = (saved or {}).get("id") if isinstance(saved, dict) else None
    if not wf_id:
        lines.append(f"- Save: FAIL — {status} {saved}")
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        sys.exit(1)
    lines.append(f"- Save: OK — `{wf_id}`")

    input_data = build_execute_input(workflow, TEST_PROMPT)
    status, exec_resp, ok = call(
        "POST",
        f"/workflows/{wf_id}/execute/",
        token=token,
        payload={"input_data": input_data, "is_async": False},
        timeout=900,
    )
    exec_id = (exec_resp or {}).get("id") or (exec_resp or {}).get("execution_id")
    detail = exec_resp if isinstance(exec_resp, dict) else {}
    if exec_id:
        for _ in range(120):
            if detail.get("status") in ("completed", "failed"):
                break
            time.sleep(2)
            _, detail, _ = call("GET", f"/workflows/executions/{exec_id}/", token=token, timeout=120)

    exec_status = detail.get("status")
    lines.append(f"- Execute: status={exec_status}, id={exec_id}")

    node_out = extract_node_outputs(detail)
    image_ok = video_ok = prompt_ok = False
    used_prompt = ""
    image_url = ""
    video_url = ""

    for info in node_out.values():
        ntype = info.get("type")
        output = info.get("output") or {}
        if ntype == "input" and info.get("status") == "completed":
            if output.get("prompt") == TEST_PROMPT:
                prompt_ok = True
        if ntype == "image_generation" and info.get("status") == "completed":
            images = output.get("images") or []
            if images:
                image_ok = True
                first = images[0]
                image_url = first.get("url") if isinstance(first, dict) else str(first)
            used_prompt = output.get("prompt") or used_prompt
        if ntype == "video_generation" and info.get("status") == "completed":
            video_url = output.get("video_url") or output.get("url") or ""
            video_ok = bool(video_url)
            if output.get("prompt"):
                used_prompt = output.get("prompt")

    lines.append(f"- Input node prompt: {'OK' if prompt_ok else 'CHECK'} (expected `{TEST_PROMPT}`)")
    lines.append(f"- Image generation: {'OK' if image_ok else 'FAIL'} url={image_url[:100] if image_url else 'none'}")
    lines.append(f"- Video generation: {'OK' if video_ok else 'PENDING/FAIL'} url={video_url[:100] if video_url else 'none'}")
    if used_prompt:
        lines.append(f"- Resolved generation prompt: `{used_prompt[:80]}`")

    for nid, info in node_out.items():
        if info.get("status") == "failed":
            lines.append(f"  - FAILED {info.get('name')} ({info.get('type')}): {(info.get('error') or '')[:200]}")

    lines.extend([
        "",
        "## Result",
        f"- Workflow: http://127.0.0.1:5200/workflows/{wf_id}/edit",
        f"- Pass wiring: {not wiring_errors}",
        f"- Pass execute: {exec_status == 'completed'}",
        f"- Pass image: {image_ok}",
        f"- Pass video: {video_ok}",
    ])

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReport: {REPORT}")

    ok_all = not wiring_errors and exec_status == "completed" and image_ok
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    main()
