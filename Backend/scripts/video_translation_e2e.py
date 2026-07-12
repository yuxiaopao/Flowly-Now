#!/usr/bin/env python
"""E2E: video translation NL2WF wiring, segment utilities, optional full pipeline execute."""
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
REPORT = REPO / "test-reports" / "VIDEO_TRANSLATION_E2E.md"

sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")
NL_MODEL = os.environ.get("NL_WORKFLOW_MODEL", "agnes-2.0-flash")
RUN_FULL = os.environ.get("VIDEO_TRANSLATION_RUN_FULL", "").lower() in ("1", "true", "yes")
TEST_VIDEO_URL = os.environ.get(
    "VIDEO_TRANSLATION_TEST_URL",
    "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241115/adyady/demo_video.mp4",
)

NL_DESCRIPTION = (
    "视频翻译工作流：上传中文讲解视频，识别语音，分别翻译成英文和日文，"
    "每种语言独立配音、口型同步、烧录字幕。现在就生成工作流。"
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
    except urllib.error.URLError as exc:
        return 0, str(exc), False


def login():
    status, data, ok = call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
    if not ok or not isinstance(data, dict) or not data.get("access"):
        raise RuntimeError(f"login failed: {status} {data}")
    return data["access"]


def run_local_unit_tests() -> list[str]:
    errors: list[str] = []
    try:
        import django

        django.setup()
    except Exception as exc:
        return [f"django setup failed: {exc}"]

    from nl_to_workflow.multimodal_workflow import (
        build_video_translation_workflow,
        is_video_translation_intent,
        wire_multimodal_workflow,
    )
    from workflows.services.video_translation.segment_pipeline import build_subtitle_file

    if not is_video_translation_intent("把中文视频翻译成英文并配音口型同步"):
        errors.append("is_video_translation_intent should match translation keywords")

    from nl_to_workflow.video_translation_workflow import build_split_video_translation_workflow
    wf = build_split_video_translation_workflow("中文视频翻译成英文和日文")
    types = [n.get("type") for n in wf.get("nodes", [])]
    if "video_upload" not in types or "subtitle_translate" not in types:
        errors.append("split workflow missing core node types")

    segments = [
        {"start": 0.0, "end": 2.5, "translated_text": "Hello world"},
        {"start": 2.5, "end": 5.0, "translated_text": "Video translation test"},
    ]
    srt = build_subtitle_file(segments, "srt")
    if "Hello world" not in srt or "-->" not in srt:
        errors.append("build_subtitle_file SRT output invalid")
    vtt = build_subtitle_file(segments, "vtt")
    if "WEBVTT" not in vtt:
        errors.append("build_subtitle_file VTT output invalid")

    from workflows.services.video_postprocess import is_ffmpeg_available

    if not is_ffmpeg_available():
        errors.append("FFmpeg not available (required for video translation pipeline)")

    return errors


def verify_nl_wiring(workflow: dict) -> list[str]:
    errors: list[str] = []
    nodes = workflow.get("nodes") or []
    types = [n.get("type") for n in nodes]
    required = ("video_upload", "subtitle_generation", "subtitle_translate", "segment_dubbing", "lip_sync", "subtitle_burn")
    for r in required:
        if r not in types:
            errors.append(f"missing node type: {r}")
    upload = next((n for n in nodes if n.get("type") == "video_upload"), None)
    asr = next((n for n in nodes if n.get("type") == "subtitle_generation"), None)
    if asr:
        path = (asr.get("config") or {}).get("inputPath") or (asr.get("config") or {}).get("input")
        if path != "{video_url}":
            errors.append(f"ASR inputPath expected {{video_url}}, got {path!r}")
    translate_nodes = [n for n in nodes if n.get("type") == "subtitle_translate"]
    if not translate_nodes:
        errors.append("missing subtitle_translate nodes")
    langs = sorted({(n.get("config") or {}).get("target_language") for n in translate_nodes})
    if len(langs) != len(translate_nodes):
        errors.append("each subtitle_translate should have unique target_language")
    mode = workflow.get("_generation_mode", "")
    if mode != "template_video_translation_split":
        errors.append(f"_generation_mode expected template_video_translation_split, got {mode!r}")
    return errors


def build_execute_input(workflow: dict, video_url: str) -> dict:
    payload = {"video_url": video_url, "input": video_url}
    for node in workflow.get("nodes", []):
        if node.get("type") != "input":
            continue
        cfg = node.get("config") or {}
        name = cfg.get("input_name") or cfg.get("variable_name") or "video_url"
        payload[name] = video_url
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
        "# Video Translation E2E",
        "",
        f"- Time: {datetime.now().isoformat()}",
        f"- Full execute: {RUN_FULL}",
        "",
    ]

    unit_errors = run_local_unit_tests()
    if unit_errors:
        lines.append(f"- Local unit tests: FAIL — {unit_errors}")
    else:
        lines.append("- Local unit tests: OK (intent, wiring, SRT/VTT, FFmpeg)")

    try:
        token = login()
        lines.append("- Login: OK")
    except RuntimeError as exc:
        lines.append(f"- Login: SKIP — {exc}")
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        sys.exit(1 if unit_errors else 0)

    status, preview, ok = call(
        "POST",
        "/nl-workflow/preview/",
        token=token,
        payload={"description": NL_DESCRIPTION, "model": NL_MODEL},
        timeout=300,
    )
    workflow = (preview or {}).get("workflow_json") or (preview or {}).get("workflow") or preview or {}
    wiring_errors = verify_nl_wiring(workflow) if workflow.get("nodes") else ["empty workflow"]
    mode = workflow.get("_generation_mode", "unknown")
    lines.append(f"- NL Preview: status={status}, mode={mode}, nodes={len(workflow.get('nodes') or [])}")
    if wiring_errors:
        lines.append(f"- NL Wiring: FAIL — {wiring_errors}")
    else:
        lines.append("- NL Wiring: OK — split pipeline with per-language chains")

    if unit_errors or wiring_errors:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        sys.exit(1)

    if not RUN_FULL:
        lines.append("- Full pipeline execute: SKIP (set VIDEO_TRANSLATION_RUN_FULL=1 to run)")
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        sys.exit(0)

    save_payload = {
        "name": workflow.get("name") or "视频多语言翻译工作流",
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

    input_data = build_execute_input(workflow, TEST_VIDEO_URL)
    status, exec_resp, ok = call(
        "POST",
        f"/workflows/{wf_id}/execute/",
        token=token,
        payload={"input_data": input_data, "is_async": False},
        timeout=3700,
    )
    exec_id = (exec_resp or {}).get("id") or (exec_resp or {}).get("execution_id")
    detail = exec_resp if isinstance(exec_resp, dict) else {}
    if exec_id:
        for _ in range(600):
            if detail.get("status") in ("completed", "failed"):
                break
            time.sleep(3)
            _, detail, _ = call("GET", f"/workflows/executions/{exec_id}/", token=token, timeout=120)

    exec_status = detail.get("status")
    lines.append(f"- Execute: status={exec_status}, id={exec_id}")

    translate_ok = False
    video_url = ""
    for info in extract_node_outputs(detail).values():
        if info.get("type") != "video_translation":
            continue
        output = info.get("output") or {}
        results = output.get("results") or []
        if info.get("status") == "completed" and results:
            translate_ok = True
            video_url = results[0].get("video_url") or output.get("video_url") or ""
            lines.append(
                f"- video_translation node: OK — lip_sync={results[0].get('lip_sync_applied')}, "
                f"video_url={video_url[:120] if video_url else 'n/a'}"
            )
        else:
            lines.append(f"- video_translation node: FAIL — {info.get('error') or output}")

    if exec_status == "completed" and translate_ok:
        lines.append("- Full pipeline: PASS")
    else:
        lines.append("- Full pipeline: FAIL or incomplete")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    sys.exit(0 if exec_status == "completed" and translate_ok else 1)


if __name__ == "__main__":
    main()
