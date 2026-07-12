#!/usr/bin/env python
"""Full-chain Emotion Detection E2E via NL2WF: preview → save → train → site."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
REPORT = REPO / "test-reports" / "EMOTION_DETECTION_FULLCHAIN_20260707.md"
DATASET_ROOT = BACKEND / "scripts" / "fixtures" / "t2_mini_emotion"

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")

NL_PROMPT = (
    "帮我做一个情绪检测系统，上传人脸图片训练 YOLO 模型，"
    "实时显示训练曲线，并生成情绪识别网站。现在就生成工作流"
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
            parsed = unwrap(json.loads(body) if body else None)
        except json.JSONDecodeError:
            parsed = body[:500]
        return exc.code, parsed, exc.code in expect


def login():
    status, data, ok = call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
    if not ok or not isinstance(data, dict) or not data.get("access"):
        raise RuntimeError(f"login failed: {status} {data}")
    return data["access"]


def nl2wf_preview(token: str) -> dict:
    status, data, ok = call(
        "POST",
        "/nl-workflow/preview/",
        token=token,
        payload={"description": NL_PROMPT},
        timeout=120,
    )
    if not ok:
        raise RuntimeError(f"NL2WF preview failed: {status} {data}")
    workflow = data.get("workflow_json") or data.get("workflow") or {}
    if not workflow.get("nodes"):
        raise RuntimeError(f"NL2WF returned empty workflow: {data}")
    return workflow


def patch_workflow_for_execution(workflow: dict) -> dict:
    """Inject fixture dataset path and fast CPU training params."""
    ds_path = DATASET_ROOT.as_posix()
    for node in workflow.get("nodes", []):
        ntype = node.get("type")
        config = node.setdefault("config", {})
        if ntype == "dataset_upload":
            config["format"] = "yolo"
            config["sourceType"] = "upload"
            config["source"] = "upload"
            config["path"] = ds_path
            config["classNames"] = ["happy", "sad", "angry", "neutral", "surprise"]
        elif ntype == "yolo_training":
            config.update({
                "trainingMode": "local",
                "yoloVersion": "v8",
                "modelVariant": "n",
                "epochs": 1,
                "batchSize": 2,
                "imageSize": 320,
                "dataSourceType": "upstream",
                "device": "cpu",
            })
        elif ntype == "site_qa":
            config["skipPlaywright"] = True
        elif ntype == "website_generator":
            wizard = config.setdefault("wizard", {})
            wizard.setdefault("siteName", "情绪检测系统")
            wizard.setdefault("primaryColor", "#8b5cf6")
            wizard["wizardCompleted"] = True
    workflow["name"] = workflow.get("name") or f"情绪检测全链路-{uuid.uuid4().hex[:6]}"
    workflow["status"] = "draft"
    return workflow


def workflow_to_create_payload(workflow: dict) -> dict:
    """Convert NL workflow nodes to API create format."""
    nodes = []
    for node in workflow.get("nodes", []):
        nodes.append({
            "id": node.get("id"),
            "type": node.get("type"),
            "position": node.get("position") or {"x": 0, "y": 0},
            "data": {
                "label": node.get("name") or node.get("type", "Node"),
                "config": node.get("config") or {},
            },
        })
    return {
        "name": workflow.get("name"),
        "description": workflow.get("description", NL_PROMPT),
        "status": "draft",
        "nodes": nodes,
        "edges": workflow.get("edges") or [],
    }


def poll_execution(token, execution_id, max_wait=2400):
    deadline = time.time() + max_wait
    last = None
    while time.time() < deadline:
        status, data, ok = call("GET", f"/workflows/executions/{execution_id}/", token=token, timeout=60)
        if ok and isinstance(data, dict):
            last = data
            st = data.get("status")
            print(f"  execution status: {st}")
            if st in ("completed", "failed", "cancelled"):
                return data
        time.sleep(15)
    return last or {"status": "timeout"}


def verify_nl2wf_structure(workflow: dict) -> dict:
    types = [n.get("type") for n in workflow.get("nodes", [])]
    expected = [
        "dataset_upload",
        "yolo_training",
        "project_profiler",
        "website_generator",
        "environment_provision",
        "site_qa",
        "site_preview",
        "project_agent",
    ]
    missing = [t for t in expected if t not in types]
    generation_mode = workflow.get("_generation_mode") or workflow.get("generation_mode") or "unknown"
    profiler_llm = False
    wizard_site = ""
    for node in workflow.get("nodes", []):
        if node.get("type") == "project_profiler":
            profiler_llm = bool((node.get("config") or {}).get("useLlmEnrich"))
        if node.get("type") == "website_generator":
            wizard = (node.get("config") or {}).get("wizard") or {}
            wizard_site = wizard.get("siteName") or node.get("name") or ""
    return {
        "node_count": len(types),
        "node_types": types,
        "missing_types": missing,
        "ok": not missing and len(types) >= 8,
        "workflow_name": workflow.get("name"),
        "generation_mode": generation_mode,
        "llm_generated": generation_mode == "llm",
        "profiler_use_llm_enrich": profiler_llm,
        "wizard_site_name": wizard_site,
    }


def main():
    sys.path.insert(0, str(BACKEND / "scripts"))
    from ensure_mini_emotion_dataset import ensure_mini_emotion_dataset

    ensure_mini_emotion_dataset()
    results = {
        "nl_prompt": NL_PROMPT,
        "steps": [],
        "ok": False,
    }

    token = login()
    results["steps"].append({"name": "login", "ok": True})

    nl_workflow = nl2wf_preview(token)
    structure = verify_nl2wf_structure(nl_workflow)
    results["nl2wf_structure"] = structure
    results["generation_mode"] = structure.get("generation_mode")
    llm_ok = structure.get("llm_generated", False)
    results["steps"].append({"name": "nl2wf_preview", "ok": structure["ok"]})
    results["steps"].append({"name": "nl2wf_llm_mode", "ok": llm_ok, "mode": structure.get("generation_mode")})
    print(f"NL2WF generated: {structure['workflow_name']} ({structure['node_count']} nodes) mode={structure.get('generation_mode')}")
    if not llm_ok:
        print("WARNING: _generation_mode is not 'llm' — template/mock path was used")
    if not structure["ok"]:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    patched = patch_workflow_for_execution(nl_workflow)
    payload = workflow_to_create_payload(patched)
    status, created, ok = call("POST", "/workflows/", token=token, payload=payload, timeout=120)
    results["steps"].append({"name": "create_workflow", "ok": ok, "status": status})
    if not ok or not isinstance(created, dict):
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    workflow_id = created.get("id")
    results["workflow_id"] = workflow_id
    print(f"Created workflow {workflow_id}")

    status, exec_data, ok = call(
        "POST",
        f"/workflows/{workflow_id}/execute/",
        token=token,
        payload={"input_data": {}, "trigger_type": "manual", "is_async": True},
        timeout=120,
        expect=(200, 201, 202),
    )
    results["steps"].append({"name": "execute_async", "ok": ok, "status": status})

    execution_id = None
    if isinstance(exec_data, dict):
        execution_id = exec_data.get("execution_id") or exec_data.get("id")
        results["execution_id"] = execution_id
        if execution_id:
            exec_data = poll_execution(token, execution_id)
        results["execution_status"] = exec_data.get("status") if isinstance(exec_data, dict) else None
        results["execution_error"] = exec_data.get("error_message") if isinstance(exec_data, dict) else None

    training_run_id = None
    metrics_series_len = {}
    plot_count = 0

    if execution_id:
        status, exec_detail, _ = call("GET", f"/workflows/executions/{execution_id}/", token=token, timeout=60)
        if isinstance(exec_detail, dict):
            node_outputs = (exec_detail.get("output_data") or {}).get("node_outputs") or {}
            artifacts = {}
            for _nid, out in node_outputs.items():
                if not isinstance(out, dict):
                    continue
                if out.get("best_weight_path") or out.get("final_metrics"):
                    artifacts["training"] = {
                        "output_dir": out.get("output_dir"),
                        "best_weight_path": out.get("best_weight_path") or out.get("model_path"),
                        "training_run_id": out.get("training_run_id") or out.get("job_id"),
                        "final_metrics": out.get("final_metrics"),
                    }
                    training_run_id = artifacts["training"].get("training_run_id")
                if out.get("output_dir") and "generated_site" in str(out.get("output_dir", "")):
                    artifacts["website"] = {
                        "output_dir": out.get("output_dir"),
                        "url": out.get("url") or out.get("preview_url"),
                    }
                if out.get("preview_url") or out.get("url"):
                    artifacts.setdefault("preview", {})
                    artifacts["preview"]["url"] = out.get("preview_url") or out.get("url")
            results["artifacts"] = artifacts

            deliverables = {}
            train = artifacts.get("training") or {}
            best_pt = train.get("best_weight_path") or ""
            if best_pt and os.path.isfile(best_pt):
                deliverables["best_pt"] = {"path": best_pt, "bytes": os.path.getsize(best_pt)}
            site_dir = (artifacts.get("website") or {}).get("output_dir") or ""
            site_weights = os.path.join(site_dir, "backend", "best.pt") if site_dir else ""
            if site_weights and os.path.isfile(site_weights):
                deliverables["site_best_pt"] = {"path": site_weights, "bytes": os.path.getsize(site_weights)}
            results["deliverables"] = deliverables

    if training_run_id:
        status, metrics, _ = call(
            "GET",
            f"/training/yolo-runs/{training_run_id}/metrics_history/",
            token=token,
            timeout=60,
        )
        if isinstance(metrics, dict):
            series = metrics.get("series") or {}
            metrics_series_len = {k: len(v) for k, v in series.items() if isinstance(v, list)}
            results["metrics_series_len"] = metrics_series_len
        status, plots, _ = call(
            "GET",
            f"/training/yolo-runs/{training_run_id}/plots/",
            token=token,
            timeout=60,
        )
        if isinstance(plots, dict):
            plot_count = len(plots.get("plots") or [])
            results["native_plots"] = plots.get("plots") or []

    results["training_run_id"] = training_run_id
    results["ok"] = (
        results.get("execution_status") == "completed"
        and structure["ok"]
        and llm_ok
        and bool((results.get("deliverables") or {}).get("best_pt"))
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 情绪检测系统 — NL2WF 全链路验收报告",
        "",
        f"> 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> NL 提示词: {NL_PROMPT}",
        f"> 工作流: `{results.get('workflow_id', '')}`",
        "",
        "## 链路说明",
        "",
        "1. **NL2WF** — `/nl-workflow/preview/` 从自然语言生成 8 节点 MLOps 工作流",
        "2. **训练** — YOLO 本地训练，节点内 WebSocket + metrics_history 原生曲线",
        "3. **建站** — 自动生成「情绪检测系统」主题识别网站并复制权重",
        "",
        "## 结果",
        "",
        f"- **AI 生成模式**: `{structure.get('generation_mode', 'unknown')}` — **{'PASS (LLM 自主)' if structure.get('llm_generated') else 'FAIL (非 LLM)'}**",
        f"- NL2WF 结构: **{'PASS' if structure['ok'] else 'FAIL'}** ({structure.get('node_count')} nodes)",
        f"- AI 站点名: {structure.get('wizard_site_name') or '—'}",
        f"- project_profiler.useLlmEnrich: **{structure.get('profiler_use_llm_enrich')}**",
        f"- 执行状态: **{results.get('execution_status', 'unknown')}**",
        f"- 总体: **{'PASS' if results.get('ok') else 'FAIL/PARTIAL'}**",
        "",
        "## NL2WF 生成节点",
        "",
    ]
    for t in structure.get("node_types") or []:
        lines.append(f"- `{t}`")
    if results.get("deliverables"):
        lines.extend(["", "## 交付物", ""])
        d = results["deliverables"]
        if d.get("best_pt"):
            lines.append(f"- **best.pt**: `{d['best_pt']['path']}` ({d['best_pt']['bytes']:,} bytes)")
        if d.get("site_best_pt"):
            lines.append(f"- **站点权重**: `{d['site_best_pt']['path']}`")
    if metrics_series_len:
        lines.extend(["", "## 训练指标曲线（原生）", ""])
        for k, v in metrics_series_len.items():
            lines.append(f"- `{k}`: {v} points")
    if plot_count:
        lines.append(f"- Ultralytics 原生图表: **{plot_count}** 张")
    if results.get("artifacts", {}).get("preview", {}).get("url"):
        lines.append(f"- 预览 URL: {results['artifacts']['preview']['url']}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report: {REPORT}")
    return 0 if results.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
