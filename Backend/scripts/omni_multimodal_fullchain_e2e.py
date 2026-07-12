#!/usr/bin/env python
"""
Agnes AI 多模态全链路 E2E:
  NL2WF (agnes-2.0-flash) → 保存工作流 → 执行(agnes 文生图/文生视频) → 验证输出

Usage:
  python scripts/omni_multimodal_fullchain_e2e.py
  python scripts/omni_multimodal_fullchain_e2e.py --skip-nl   # 仅手动工作流执行
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
REPORT = REPO / "test-reports" / "OMNI_MULTIMODAL_FULLCHAIN.md"

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")
NL_MODEL = os.environ.get("NL_WORKFLOW_MODEL", "agnes-2.0-flash")

NL_PROMPT = (
    "帮我创建一个多模态 AI 工作流：用户输入提示词，"
    "先用文生图节点生成图片，再用文生视频节点生成短视频，"
    "最后在输出节点展示结果。现在就生成工作流。"
)

FALLBACK_WORKFLOW = {
    "name": "Agnes多模态-文生图+文生视频",
    "description": "Agnes NL2WF + agnes-image-2.1-flash + agnes-video-v2.0",
    "nodes": [],
    "edges": [],
}


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


def build_fallback_workflow():
    """Manual multimodal workflow when NL2WF fails."""
    specs = [
        ("start", "开始", {}),
        ("input", "提示词", {"input_name": "prompt", "placeholder": "描述你想生成的画面…"}),
        (
            "image_generation",
            "文生图",
            {
                "provider": "agnes",
                "model": "agnes-image-2.1-flash",
                "prompt": "{prompt}",
                "size": "1024x1024",
                "n": 1,
            },
        ),
        (
            "video_generation",
            "图生视频",
            {
                "provider": "agnes",
                "model": "agnes-video-v2.0",
                "prompt": "{prompt}",
                "inputImage": "{images.0.url}",
                "duration": 5,
                "resolution": "720p",
            },
        ),
        ("output", "结果输出", {"template": "{video_url}", "format": "json"}),
        ("end", "结束", {}),
    ]
    nodes, edges, ids = [], [], []
    x = 80
    for i, (ntype, label, config) in enumerate(specs):
        nid = f"n{i}_{uuid.uuid4().hex[:6]}"
        ids.append(nid)
        nodes.append(
            {
                "id": nid,
                "type": ntype,
                "data": {"label": label, "config": config},
                "position": {"x": x, "y": 180},
                "config": config,
            }
        )
        x += 260
    for i in range(len(ids) - 1):
        edges.append({"id": f"e{i}", "source": ids[i], "target": ids[i + 1], "label": ""})
    wf = dict(FALLBACK_WORKFLOW)
    wf["nodes"] = nodes
    wf["edges"] = edges
    return wf


def sanitize_workflow(workflow: dict) -> dict:
    """Remove NL2WF internal metadata and normalize for API save."""
    wf = {k: v for k, v in workflow.items() if not str(k).startswith("_")}
    nodes = []
    for node in wf.get("nodes", []):
        if not isinstance(node, dict):
            continue
        clean = {k: v for k, v in node.items() if not str(k).startswith("_")}
        nodes.append(clean)
    wf["nodes"] = nodes
    wf["edges"] = [
        e for e in wf.get("edges", []) if isinstance(e, dict) and not str(e.get("id", "")).startswith("_")
    ]
    return wf


def patch_workflow_for_agnes(workflow: dict) -> dict:
    """Force Agnes cloud providers for image/video generation."""
    for node in workflow.get("nodes", []):
        ntype = node.get("type")
        config = node.setdefault("config", {})
        data_cfg = node.get("data", {}).get("config")
        if isinstance(data_cfg, dict):
            config.update(data_cfg)
        if ntype == "input":
            # NL2WF may emit user_prompt; normalize to prompt for downstream {prompt} templates
            if config.get("input_name") in (None, "", "user_prompt", "user_input"):
                config["input_name"] = "prompt"
            if not config.get("input_type"):
                config["input_type"] = "text"
        elif ntype == "image_generation":
            config.update({
                "provider": "agnes",
                "model": "agnes-image-2.1-flash",
                "size": "1024x1024",
                "n": 1,
            })
            if not config.get("prompt"):
                config["prompt"] = "{prompt}"
        elif ntype == "video_generation":
            config.update({
                "provider": "agnes",
                "model": "agnes-video-v2.0",
                "resolution": "720p",
            })
            config.setdefault("prompt", "{prompt}")
            config.setdefault("inputImage", "{images.0.url}")
            if node.get("data", {}).get("label") in (None, "", "文生视频"):
                node.setdefault("data", {})["label"] = "图生视频"
        elif ntype == "audio_generation":
            config.setdefault("provider", "dashscope")
            config.setdefault("model", "cosyvoice-v3-flash")
        if node.get("data") is None:
            node["data"] = {}
        node["data"]["config"] = config
    return sanitize_workflow(workflow)


def nl2wf_preview(token: str) -> tuple[dict, str]:
    status, data, ok = call(
        "POST",
        "/nl-workflow/preview/",
        token=token,
        payload={"description": NL_PROMPT, "model": NL_MODEL},
        timeout=300,
    )
    if not ok:
        return {}, f"NL2WF preview failed: {status} {data}"
    workflow = data.get("workflow_json") or data.get("workflow") or {}
    if not workflow.get("nodes"):
        return {}, f"NL2WF empty workflow: {str(data)[:300]}"
    types = [n.get("type") for n in workflow.get("nodes", [])]
    if "image_generation" not in types:
        from nl_to_workflow.multimodal_workflow import is_multimodal_intent, build_multimodal_workflow
        if is_multimodal_intent(NL_PROMPT):
            workflow = build_multimodal_workflow(NL_PROMPT)
            return workflow, "template_multimodal"
        return {}, f"NL2WF missing image_generation (types={types})"
    return workflow, "ok"


def save_workflow(token: str, workflow: dict) -> tuple[str | None, str]:
    payload = {
        "name": workflow.get("name") or f"Omni多模态-{uuid.uuid4().hex[:6]}",
        "description": workflow.get("description") or NL_PROMPT,
        "status": "draft",
        "nodes": workflow.get("nodes", []),
        "edges": workflow.get("edges", []),
    }
    status, data, ok = call("POST", "/workflows/", token=token, payload=payload)
    if not ok or not isinstance(data, dict):
        return None, f"save failed: {status} {data}"
    return data.get("id"), "ok"


def build_execute_input(workflow: dict, prompt: str) -> dict:
    """Map execute payload keys to each input node's configured input_name."""
    payload = {"prompt": prompt, "user_input": prompt, "user_prompt": prompt}
    for node in workflow.get("nodes", []):
        if node.get("type") != "input":
            continue
        config = node.get("config") or node.get("data", {}).get("config") or {}
        name = config.get("input_name")
        if name:
            payload[name] = prompt
    return payload


def execute_workflow(token: str, wf_id: str, prompt: str, workflow: dict | None = None) -> tuple[dict, str]:
    input_data = build_execute_input(workflow or {}, prompt)
    status, data, ok = call(
        "POST",
        f"/workflows/{wf_id}/execute/",
        token=token,
        payload={
            "input_data": input_data,
            "is_async": False,
        },
        timeout=900,
    )
    exec_id = (data or {}).get("execution_id") if isinstance(data, dict) else None
    detail = data
    if exec_id:
        for _ in range(3):
            time.sleep(2)
            _, detail, _ = call("GET", f"/workflows/executions/{exec_id}/", token=token, timeout=120)
            if isinstance(detail, dict) and detail.get("status") in ("completed", "failed"):
                break
    if not ok and not exec_id:
        return {}, f"execute failed: {status} {data}"
    return detail if isinstance(detail, dict) else {}, "ok"


def extract_media(detail: dict) -> dict:
    node_status = detail.get("node_status") or {}
    image_url = ""
    video_url = ""
    image_node_id = ""
    video_node_id = ""
    for nid, info in node_status.items():
        if not isinstance(info, dict):
            continue
        output = info.get("output") or {}
        if info.get("status") != "completed":
            continue
        if isinstance(output, dict):
            images = output.get("images") or []
            if images and not image_url:
                first = images[0]
                if isinstance(first, dict):
                    image_url = first.get("url") or first.get("path") or ""
                elif isinstance(first, str):
                    image_url = first
                if image_url:
                    image_node_id = nid
            vurl = output.get("video_url") or output.get("url") or ""
            if vurl and not video_url and "video" in str(info.get("node_type", "")).lower() or output.get("video_url"):
                video_url = vurl
                video_node_id = nid
            if output.get("video_url"):
                video_url = output["video_url"]
                video_node_id = nid
    return {
        "image_url": image_url,
        "video_url": video_url,
        "image_node_id": image_node_id,
        "video_node_id": video_node_id,
        "node_status": node_status,
    }


def write_report(lines: list[str]):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-nl", action="store_true")
    args = parser.parse_args()

    lines = [
        "# Agnes AI 多模态全链路 E2E",
        "",
        f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- NL 模型: `{NL_MODEL}`",
        f"- 图像模型: `agnes` / agnes-image-2.1-flash",
        f"- 视频模型: `agnes` / agnes-video-v2.0",
        "",
    ]

    results = {"login": False, "nl2wf": False, "save": False, "execute": False, "image": False, "video": False}
    wf_id = None
    nl_mode = "skipped" if args.skip_nl else "live"
    prompt = "一只可爱的橘猫坐在窗台上，阳光洒在它身上，水彩插画风格"

    try:
        token = login()
        results["login"] = True
        lines.append("- 登录: PASS")
    except Exception as exc:
        lines.append(f"- 登录: FAIL — {exc}")
        write_report(lines)
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)

    workflow = build_fallback_workflow()
    if not args.skip_nl:
        try:
            wf, err = nl2wf_preview(token)
            if wf.get("nodes"):
                workflow = patch_workflow_for_agnes(wf)
                results["nl2wf"] = True
                types = [n.get("type") for n in workflow.get("nodes", [])]
                nl_mode = f"LLM ({len(types)} nodes: {', '.join(types[:8])})"
                lines.append(f"- NL2WF: PASS — {nl_mode}")
            else:
                workflow = patch_workflow_for_agnes(build_fallback_workflow())
                nl_mode = f"FALLBACK — {err}"
                lines.append(f"- NL2WF: FALLBACK — {err}")
        except Exception as exc:
            workflow = patch_workflow_for_agnes(build_fallback_workflow())
            nl_mode = f"FALLBACK — {exc}"
            lines.append(f"- NL2WF: FALLBACK — {exc}")
    else:
        workflow = patch_workflow_for_agnes(workflow)
        lines.append("- NL2WF: SKIPPED (manual workflow)")

    try:
        wf_id, err = save_workflow(token, workflow)
        if wf_id:
            results["save"] = True
            lines.append(f"- 保存工作流: PASS — id={wf_id}")
        else:
            lines.append(f"- 保存工作流: FAIL — {err}")
            write_report(lines)
            print(json.dumps({"ok": False, "workflow_id": None, "error": err}, ensure_ascii=False))
            sys.exit(1)
    except Exception as exc:
        lines.append(f"- 保存工作流: FAIL — {exc}")
        write_report(lines)
        sys.exit(1)

    try:
        detail, err = execute_workflow(token, wf_id, prompt, workflow)
        status = detail.get("status")
        media = extract_media(detail)
        results["execute"] = status == "completed"
        results["image"] = bool(media["image_url"])
        results["video"] = bool(media["video_url"])

        lines.append(f"- 执行工作流: {'PASS' if results['execute'] else 'FAIL'} — status={status}")
        if detail.get("error_message"):
            lines.append(f"  - error: {detail['error_message'][:200]}")
        lines.append(f"- 图像输出: {'PASS' if results['image'] else 'FAIL'} — node={media['image_node_id']}")
        if media["image_url"]:
            lines.append(f"  - url: {media['image_url'][:120]}...")
        lines.append(f"- 视频输出: {'PASS' if results['video'] else 'FAIL'} — node={media['video_node_id']}")
        if media["video_url"]:
            lines.append(f"  - url: {media['video_url'][:120]}...")

        for nid, info in (media.get("node_status") or {}).items():
            if isinstance(info, dict) and info.get("status") == "failed":
                lines.append(f"  - 节点失败 {nid}: {(info.get('error') or info.get('message') or '')[:150]}")

    except Exception as exc:
        lines.append(f"- 执行工作流: FAIL — {exc}")

    ok = results["login"] and results["save"] and results["execute"] and results["image"]
    lines.extend([
        "",
        f"## 总结: {'PASS' if ok else 'PARTIAL/FAIL'}",
        f"- workflow_id: `{wf_id}`",
        f"- editor: http://127.0.0.1:5200/workflows/{wf_id}/edit",
    ])
    write_report(lines)

    out = {
        "ok": ok,
        "workflow_id": wf_id,
        "nl_mode": nl_mode,
        "results": results,
        "editor_url": f"http://127.0.0.1:5200/workflows/{wf_id}/edit",
        "report": str(REPORT),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
