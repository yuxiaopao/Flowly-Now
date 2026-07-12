#!/usr/bin/env python
"""Desktop E2E walkthrough helper — EP → QA → HTTP health (D-01/D-05 checklist JSON)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
REPORT = REPO / "test-reports" / "desktop-e2e-walkthrough.json"

sys.path.insert(0, str(BACKEND))


def generate_sample_site(tmp_base: str) -> tuple[str, str]:
    from website_generator.generators.detection import DetectionGenerator

    yolo_dir = os.path.join(tmp_base, "yolo_run")
    site_dir = os.path.join(yolo_dir, "generated_site")
    os.makedirs(yolo_dir, exist_ok=True)
    weight = os.path.join(yolo_dir, "best.pt")
    with open(weight, "w", encoding="utf-8") as f:
        f.write("fake")

    gen = DetectionGenerator({
        "output_dir": site_dir,
        "model_path": weight,
        "model_type": "detection",
        "labels": ["helmet", "no_helmet"],
        "framework": "pytorch",
        "website_type": "detection",
        "frontend_framework": "vue",
        "backend_framework": "flask",
        "port": 49152,
        "name": "E2E Walkthrough Site",
        "description": "Desktop E2E helper",
    })
    result = gen.generate()
    if not result.get("success", True):
        raise RuntimeError(result.get("error") or "generation failed")
    return site_dir, weight


def try_start_flask(site_dir: str, port: int) -> dict:
    backend_dir = os.path.join(site_dir, "backend")
    app_py = os.path.join(backend_dir, "app.py")
    if not os.path.isfile(app_py):
        return {"started": False, "error": "missing app.py"}

    env = {**os.environ, "FLASK_RUN_PORT": str(port)}
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=backend_dir,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    health_url = f"http://127.0.0.1:{port}/health"
    ok = False
    for _ in range(24):
        try:
            with urllib.request.urlopen(health_url, timeout=2) as resp:
                ok = 200 <= resp.status < 300
                break
        except Exception:
            time.sleep(0.5)
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return {"started": ok, "health_url": health_url, "port": port}


def main() -> int:
    from website_generator.site_factory.environment import run_environment_checks
    from website_generator.site_factory.qa_runner import run_site_qa
    from website_generator.site_factory.project_agent import process_agent_message

    tmp_base = tempfile.mkdtemp(prefix="flowly_desktop_e2e_")
    checks = []
    try:
        site_dir, weight = generate_sample_site(tmp_base)

        ep = run_environment_checks(
            output_dir=site_dir,
            model_path=weight,
            site_id="e2e-walkthrough",
            runtime_mode="desktop",
        )
        checks.append({
            "id": "D-01-EP",
            "label": "environment_provision",
            "ok": ep.get("ready") is True,
            "detail": f"port={ep.get('assigned_port')}",
        })

        qa = run_site_qa(
            output_dir=site_dir,
            model_path=weight,
            website_type="detection",
            qa_profile="default",
            metrics={"map50": 0.82},
            port=ep["assigned_port"],
            skip_playwright=True,
            generated_site_id="e2e-walkthrough",
        )
        checks.append({
            "id": "D-01-QA",
            "label": "site_qa L1-L4",
            "ok": qa.get("gate") in ("green", "yellow"),
            "detail": qa.get("summary_zh", ""),
        })

        flask = try_start_flask(site_dir, ep["assigned_port"])
        checks.append({
            "id": "D-01-HTTP",
            "label": "Flask /health",
            "ok": flask.get("started") is True,
            "detail": flask.get("health_url", flask.get("error", "")),
        })

        agent = process_agent_message(
            output_dir=site_dir,
            message="把主色改成 #3b82f6",
            site_name="E2E Site",
            model_path=weight,
            qa_profile="default",
            auto_qa=True,
            website_type="detection",
            metrics={"map50": 0.82},
            port=ep["assigned_port"],
        )
        checks.append({
            "id": "D-03-Agent",
            "label": "project_agent 改色 + QA",
            "ok": agent.get("success") and bool(agent.get("files_changed")),
            "detail": agent.get("reply", agent.get("error", "")),
        })

        checks.append({
            "id": "D-05-T2-partial",
            "label": "建站→QA→预览→Agent 脚本链",
            "ok": all(c["ok"] for c in checks),
            "detail": "自动化子集；Desktop iframe 权限弹窗需 Flowly Desktop 人工确认",
        })
    finally:
        shutil.rmtree(tmp_base, ignore_errors=True)

    passed = all(c["ok"] for c in checks)
    out = {"passed": passed, "checks": checks}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\nReport: {REPORT}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
