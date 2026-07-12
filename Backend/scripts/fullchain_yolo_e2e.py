#!/usr/bin/env python
"""Full-chain YOLO E2E: create workflow -> train -> site generation."""
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
REPORT = REPO / "test-reports" / "FULLCHAIN_YOLO_E2E_20260701.md"
DATASET_ROOT = BACKEND / "scripts" / "fixtures" / "t2_mini_yolo"

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")


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


def build_workflow_payload():
    ds_path = DATASET_ROOT.as_posix()
    nodes = [
        {
            "id": "dataset_upload_1",
            "type": "dataset_upload",
            "position": {"x": 80, "y": 200},
            "data": {
                "label": "上传标注数据集",
                "config": {
                    "format": "yolo",
                    "source": "upload",
                    "path": ds_path,
                },
            },
        },
        {
            "id": "yolo_training_1",
            "type": "yolo_training",
            "position": {"x": 280, "y": 200},
            "data": {
                "label": "YOLO 训练",
                "config": {
                    "trainingMode": "local",
                    "yoloVersion": "v8",
                    "modelVariant": "n",
                    "epochs": 1,
                    "batchSize": 2,
                    "imageSize": 320,
                    "dataSourceType": "upstream",
                    "device": "cpu",
                },
            },
        },
        {
            "id": "project_profiler_1",
            "type": "project_profiler",
            "position": {"x": 480, "y": 200},
            "data": {
                "label": "场景分析",
                "config": {"websiteType": "detection", "useLlmEnrich": False},
            },
        },
        {
            "id": "website_generator_1",
            "type": "website_generator",
            "position": {"x": 680, "y": 200},
            "data": {
                "label": "生成识别网站",
                "config": {
                    "websiteType": "detection",
                    "projectType": "detection",
                    "framework": "ultralytics",
                    "frontendFramework": "vue",
                    "backendFramework": "flask",
                    "qaProfile": "default",
                    "wizard": {
                        "siteName": "全链路验收识别站",
                        "usageDescription": "上传图片进行目标检测",
                        "primaryColor": "#f59e0b",
                        "wizardCompleted": True,
                    },
                },
            },
        },
        {
            "id": "environment_provision_1",
            "type": "environment_provision",
            "position": {"x": 880, "y": 200},
            "data": {"label": "环境配置", "config": {"runtimeMode": "desktop"}},
        },
        {
            "id": "site_qa_1",
            "type": "site_qa",
            "position": {"x": 1080, "y": 200},
            "data": {
                "label": "站点自查",
                "config": {
                    "websiteType": "detection",
                    "qaProfile": "default",
                    "skipPlaywright": True,
                },
            },
        },
        {
            "id": "site_preview_1",
            "type": "site_preview",
            "position": {"x": 1280, "y": 200},
            "data": {"label": "站点预览", "config": {"qaProfile": "default"}},
        },
        {
            "id": "project_agent_1",
            "type": "project_agent",
            "position": {"x": 1480, "y": 200},
            "data": {
                "label": "项目 Agent",
                "config": {"qaProfile": "default", "autoQaAfterEdit": False, "message": ""},
            },
        },
    ]
    edges = [
        {"id": "e1", "source": "dataset_upload_1", "target": "yolo_training_1"},
        {"id": "e2", "source": "yolo_training_1", "target": "project_profiler_1"},
        {"id": "e3", "source": "project_profiler_1", "target": "website_generator_1"},
        {"id": "e4", "source": "website_generator_1", "target": "environment_provision_1"},
        {"id": "e5", "source": "environment_provision_1", "target": "site_qa_1"},
        {"id": "e6", "source": "site_qa_1", "target": "site_preview_1"},
        {"id": "e7", "source": "site_preview_1", "target": "project_agent_1"},
    ]
    return {
        "name": f"全链路验收YOLO-{uuid.uuid4().hex[:6]}",
        "description": "NL2WF 替代模板：数据集→训练→建站全链路验收",
        "status": "draft",
        "nodes": nodes,
        "edges": edges,
    }


def poll_execution(token, execution_id, max_wait=1800):
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


def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "t2_full_chain_test",
        BACKEND / "scripts" / "t2_full_chain_test.py",
    )
    t2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t2)
    t2.ensure_mini_dataset()
    results = {"steps": [], "ok": False}

    token = login()
    results["steps"].append({"name": "login", "ok": True})

    payload = build_workflow_payload()
    status, created, ok = call("POST", "/workflows/", token=token, payload=payload, timeout=120)
    results["steps"].append({"name": "create_workflow", "ok": ok, "status": status, "detail": created if not ok else None})
    if not ok or not isinstance(created, dict):
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    workflow_id = created.get("id")
    results["workflow_id"] = workflow_id
    results["workflow_name"] = created.get("name")
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
            exec_data = poll_execution(token, execution_id, max_wait=2400)
        results["execution_status"] = exec_data.get("status") if isinstance(exec_data, dict) else None
        results["execution_error"] = exec_data.get("error_message") if isinstance(exec_data, dict) else None
        results["output_preview"] = str(exec_data.get("output_data", ""))[:500] if isinstance(exec_data, dict) else None

    if execution_id:
        status, timeline, _ = call("GET", f"/workflows/executions/{execution_id}/timeline/", token=token, timeout=60)
        if isinstance(timeline, dict):
            node_execs = timeline.get("node_executions") or []
            results["timeline"] = [
                {
                    "node": item.get("node_name") or item.get("node_type"),
                    "status": item.get("status"),
                    "error": (item.get("error") or item.get("error_message") or "")[:200],
                }
                for item in node_execs[:20]
            ]
        elif isinstance(timeline, list):
            results["timeline"] = [
                {
                    "node": item.get("node_name") or item.get("node_type"),
                    "status": item.get("status"),
                    "error": (item.get("error") or item.get("error_message") or "")[:200],
                }
                for item in timeline[:20]
            ]

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
                        "epochs": out.get("epochs"),
                        "final_metrics": out.get("final_metrics"),
                        "duration_seconds": out.get("duration_seconds"),
                    }
                if out.get("output_dir") and str(out.get("output_dir", "")).endswith("generated_site"):
                    artifacts["website"] = {
                        "output_dir": out.get("output_dir"),
                        "site_id": out.get("site_id"),
                        "url": out.get("url") or out.get("preview_url"),
                        "status": out.get("status"),
                    }
                if out.get("preview_url") or (out.get("url") and str(out.get("url", "")).startswith("http")):
                    artifacts["preview"] = {
                        "url": out.get("preview_url") or out.get("url"),
                        "qa_gate": out.get("qa_gate") or out.get("gate"),
                        "status": out.get("status"),
                    }
            results["artifacts"] = artifacts

            # Verify deliverable files on disk
            deliverables = {}
            train = artifacts.get("training") or {}
            best_pt = train.get("best_weight_path") or ""
            if best_pt and os.path.isfile(best_pt):
                deliverables["best_pt"] = {"path": best_pt, "bytes": os.path.getsize(best_pt)}
            out_dir = train.get("output_dir") or ""
            tr_json = os.path.join(out_dir, "training_result.json") if out_dir else ""
            if tr_json and os.path.isfile(tr_json):
                with open(tr_json, encoding="utf-8") as f:
                    deliverables["training_result"] = json.load(f)
            site_dir = (artifacts.get("website") or {}).get("output_dir") or ""
            site_weights = os.path.join(site_dir, "backend", "best.pt") if site_dir else ""
            if site_weights and os.path.isfile(site_weights):
                deliverables["site_best_pt"] = {"path": site_weights, "bytes": os.path.getsize(site_weights)}
            results["deliverables"] = deliverables

    status, sites, _ = call("GET", "/website-generator/?page_size=5", token=token, timeout=60)
    if isinstance(sites, dict):
        site_list = sites.get("results") or []
        results["generated_sites"] = [
            {"id": s.get("id"), "name": s.get("name"), "status": s.get("status"), "port": s.get("port")}
            for s in site_list[:3]
        ]

    results["ok"] = results.get("execution_status") == "completed"
    print(json.dumps(results, ensure_ascii=False, indent=2))

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 全链路 YOLO E2E 测试报告",
        "",
        f"> 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 工作流: `{results.get('workflow_id', '')}`",
        "",
        "## 结果",
        "",
        f"- 执行状态: **{results.get('execution_status', 'unknown')}**",
        f"- 总体: **{'PASS' if results.get('ok') else 'FAIL/PARTIAL'}**",
        "",
        "## 步骤",
        "",
    ]
    for step in results.get("steps", []):
        lines.append(f"- {step['name']}: {'✅' if step.get('ok') else '❌'}")
    if results.get("timeline"):
        lines.extend(["", "## 节点时间线", ""])
        for item in results["timeline"]:
            lines.append(f"- {item.get('node')}: {item.get('status')} {item.get('error') or ''}")
    if results.get("deliverables"):
        lines.extend(["", "## 交付物（训练权重 / 指标 / 建站）", ""])
        d = results["deliverables"]
        if d.get("best_pt"):
            lines.append(f"- **best.pt**: `{d['best_pt']['path']}` ({d['best_pt']['bytes']:,} bytes)")
        if d.get("site_best_pt"):
            lines.append(f"- **站点内 best.pt**: `{d['site_best_pt']['path']}` ({d['site_best_pt']['bytes']:,} bytes)")
        if d.get("training_result"):
            tr = d["training_result"]
            lines.append(f"- **训练耗时**: {tr.get('duration_seconds')}s | best_epoch: {tr.get('best_epoch')}")
            fm = tr.get("final_metrics") or {}
            lines.append(f"- **指标**: mAP50={fm.get('mAP50')} precision={fm.get('precision')} recall={fm.get('recall')}")
    if results.get("artifacts"):
        lines.extend(["", "## 节点产出摘要", ""])
        for key, val in results["artifacts"].items():
            lines.append(f"- **{key}**: {json.dumps(val, ensure_ascii=False)}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report: {REPORT}")
    return 0 if results.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
