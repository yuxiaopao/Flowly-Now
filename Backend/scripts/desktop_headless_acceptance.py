#!/usr/bin/env python
"""
Desktop headless acceptance — no manual UI required.

Runs:
  1. Desktop/scripts/smoke-test.mjs (Electron launch + script sync)
  2. Desktop/scripts/integration-test.mjs (optional, if backend online)

Output: tests/artifacts/acceptance/DESKTOP_HEADLESS_ACCEPTANCE.md
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

REPO = Path(__file__).resolve().parents[2]
DESKTOP = REPO / "Desktop"
REPORT = REPO / "tests/artifacts/acceptance" / "DESKTOP_HEADLESS_ACCEPTANCE.md"
REPORT_JSON = REPO / "tests/artifacts/acceptance" / "desktop-headless-result.json"

CLOUD_URL = "http://127.0.0.1:8000"
VERDICT_PASS = "通过"
VERDICT_FAIL = "不通过"


def backend_online() -> bool:
    try:
        with urllib.request.urlopen(f"{CLOUD_URL}/admin/login/", timeout=3) as resp:
            return resp.status < 500
    except Exception:
        return False


def run_node_script(script_name: str, timeout: int = 180) -> Tuple[bool, str]:
    script = DESKTOP / "scripts" / script_name
    if not script.is_file():
        return False, f"missing {script}"
    try:
        proc = subprocess.run(
            ["node", str(script)],
            cwd=str(DESKTOP),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "FLOWLY_CLOUD_URL": CLOUD_URL},
        )
        tail = (proc.stdout or proc.stderr or "")[-400:]
        return proc.returncode == 0, tail
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    checks = []

    smoke_ok, smoke_ev = run_node_script("smoke-test.mjs", timeout=120)
    checks.append({
        "id": "DH-01",
        "title": "Desktop smoke-test.mjs",
        "passed": smoke_ok,
        "evidence": smoke_ev,
    })

    if backend_online():
        integration_ok, integration_ev = run_node_script("integration-test.mjs", timeout=30)
        checks.append({
            "id": "DH-02",
            "title": "Desktop integration-test.mjs (agent WS)",
            "passed": integration_ok,
            "evidence": integration_ev,
        })
    else:
        checks.append({
            "id": "DH-02",
            "title": "Desktop integration-test.mjs (agent WS)",
            "passed": True,
            "evidence": "skipped — backend not at 127.0.0.1:8000",
            "skipped": True,
        })

    required = [c for c in checks if not c.get("skipped")]
    passed = sum(1 for c in required if c["passed"])
    total = len(required)
    verdict = VERDICT_PASS if all(c["passed"] for c in required) else VERDICT_FAIL

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps({
        "timestamp": now,
        "verdict": verdict,
        "passed": passed,
        "total": total,
        "checks": checks,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Desktop 无头验收",
        f"> {now} **{verdict}** ({passed}/{total})",
        "",
        "| ID | 项 | 结果 |",
        "|----|-----|------|",
    ]
    for c in checks:
        if c.get("skipped"):
            mark = "⏭ skip"
        elif c["passed"]:
            mark = "✅"
        else:
            mark = "❌"
        lines.append(f"| {c['id']} | {c['title']} | {mark} |")

    lines.extend([
        "",
        "## 复验",
        "",
        "```bash",
        "cd Backend && python scripts/desktop_headless_acceptance.py",
        "cd Desktop && npm run test:smoke",
        "```",
        "",
        "> UI 走查（iframe / Wizard / Agent）仍需 Flowly Desktop 人工执行，见 PROGRESS.md。",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Verdict: {verdict} ({passed}/{total})")
    print(f"Report: {REPORT}")
    return 0 if verdict == VERDICT_PASS else 1


if __name__ == "__main__":
    sys.exit(main())
