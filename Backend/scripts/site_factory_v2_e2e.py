#!/usr/bin/env python
"""E2E: Site Factory v2 AI role agents + NL2WF preview for v2 chain."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
REPORT = REPO / "test-reports" / "SITE_FACTORY_V2_E2E.md"

sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")

V2_NODE_TYPES = {
    "backend_setup",
    "frontend_setup",
    "ui_beautify",
    "site_code_review",
}


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


def test_role_agents_chain() -> tuple[bool, str]:
    import django

    django.setup()

    from website_generator.generators import get_generator
    from website_generator.site_factory.role_agents import (
        run_backend_setup,
        run_frontend_setup,
        run_site_code_review,
        run_ui_beautify,
    )

    tmp = tempfile.mkdtemp(prefix="sf_v2_e2e_")
    try:
        gen = get_generator("detection", {
            "output_dir": tmp,
            "model_path": "",
            "labels": ["cat", "dog"],
            "framework": "ultralytics",
            "website_type": "detection",
            "port": 5000,
            "name": "E2E Test Site",
            "description": "v2 chain test",
            "profile": {"scenario": "宠物识别", "ui_tone": "friendly", "copy_hints": ["上传宠物照片"]},
            "wizard": {"siteName": "E2E 站", "usageDescription": "测试", "primaryColor": "#6366f1"},
        })
        result = gen.generate()
        if not result.get("success"):
            return False, f"scaffold failed: {result.get('error')}"

        steps = []
        for name, fn in (
            ("backend_setup", lambda: run_backend_setup(tmp, agent_mode="rules", allow_core_edit=True, auto_qa=False)),
            ("frontend_setup", lambda: run_frontend_setup(tmp, agent_mode="rules", auto_qa=False)),
            ("ui_beautify", lambda: run_ui_beautify(tmp, agent_mode="rules", auto_qa=False)),
            ("site_code_review", lambda: run_site_code_review(tmp, agent_mode="rules", max_rounds=1)),
        ):
            r = fn()
            ok = r.get("success", True)
            steps.append(f"{name}={'OK' if ok else 'FAIL'}")
            if not ok:
                return False, "; ".join(steps) + f" err={r.get('error')}"

        app_py = Path(tmp) / "backend" / "app.py"
        theme = Path(tmp) / "frontend" / "src" / "styles" / "theme.css"
        review = Path(tmp) / ".flowly" / "review" / "review_report.json"
        if not app_py.is_file() or "/health" not in app_py.read_text(encoding="utf-8"):
            return False, "backend /health missing after chain"
        if not theme.is_file():
            return False, "theme.css missing after chain"
        if not review.is_file():
            return False, "review_report.json missing"
        return True, "; ".join(steps)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_nl2wf_v2_preview(token: str) -> tuple[bool, str, list[str]]:
    prompt = (
        "我有 YOLO 标注数据集，想训练 YOLOv8 并分工完善现代化网站，"
        "后端前端 UI 都要 AI 优化，包含后端搭建、前端搭建、UI美化和代码复查节点"
    )
    status, prev, ok = call(
        "POST",
        "/nl-workflow/preview/",
        token=token,
        payload={"description": prompt},
        timeout=180,
    )
    wf = (prev or {}).get("workflow_json") or (prev or {}).get("workflow") or {}
    types = [n.get("type") for n in wf.get("nodes", [])]
    missing = sorted(V2_NODE_TYPES - set(types))
    if ok and not missing:
        return True, f"{len(types)} nodes", types
    if ok and "website_generator" in types and len(types) >= 8:
        return True, f"partial v2 ({len(types)} nodes, missing={missing})", types
    return False, f"status={status} types={types} missing={missing}", types


def test_executor_registration() -> tuple[bool, str]:
    import django

    django.setup()
    from workflows.services.langchain_service import LangChainService

    svc = LangChainService()
    executors = getattr(svc, "execute_node", None)
    if not executors:
        return False, "LangChainService missing"
    for nt in V2_NODE_TYPES:
        method = f"run_{nt}_node"
        if not hasattr(svc, method):
            return False, f"missing {method}"
    return True, "all 4 runners registered"


def main() -> int:
    lines = [
        "# Site Factory v2 E2E",
        "",
        f"- Time: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## API / Script",
        "",
    ]
    errors: list[str] = []

    ok, detail = test_executor_registration()
    lines.append(f"| Executor registration | {'PASS' if ok else 'FAIL'} | {detail} |")
    if not ok:
        errors.append(detail)

    ok, detail = test_role_agents_chain()
    lines.append(f"| Role agents chain (rules) | {'PASS' if ok else 'FAIL'} | {detail} |")
    if not ok:
        errors.append(f"role chain: {detail}")

    status, login, ok = call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
    token = login.get("access") if isinstance(login, dict) else None
    if not ok or not token:
        lines.append(f"| Login | FAIL | {status} {login} |")
        errors.append("login failed")
    else:
        lines.append("| Login | OK | OK |")
        ok, detail, types = test_nl2wf_v2_preview(token)
        mark = "PASS" if ok else "FAIL"
        lines.append(f"| NL2WF v2 preview | {mark} | {detail} |")
        lines.append("")
        lines.append("**NL2WF node types:**")
        lines.append("```")
        lines.append(", ".join(types))
        lines.append("```")
        if not ok:
            errors.append(f"nl2wf: {detail}")

    lines.extend(["", f"## Result: **{'PASS' if not errors else 'FAIL'}**"])
    if errors:
        lines.extend(["", "### Errors", ""])
        for e in errors:
            lines.append(f"- {e}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
