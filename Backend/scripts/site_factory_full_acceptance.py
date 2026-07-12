#!/usr/bin/env python
"""Site Factory M1–M4 full acceptance aggregator."""
from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "Backend"
REPORT = REPO / "test-reports" / "SITE_FACTORY_FULL_ACCEPTANCE.md"
CLOUD_URL = "http://127.0.0.1:8000"

SUITES = [
    ("M1", BACKEND / "scripts/m1_acceptance_test.py", False),
    ("M2", BACKEND / "scripts/m2_acceptance_test.py", False),
    ("M3", BACKEND / "scripts/m3_acceptance_test.py", False),
    ("M4", BACKEND / "scripts/m4_acceptance_test.py", False),
    ("P1", BACKEND / "scripts/p1_site_factory_automated_test.py", False),
    ("Preflight", BACKEND / "scripts/desktop_manual_preflight_test.py", True),
    ("Desktop", BACKEND / "scripts/desktop_headless_acceptance.py", False),
    ("T-5", BACKEND / "scripts/frontend_user_api_smoke_test.py", True),
]

OPTIONAL_SUITES = [
    ("T-2", BACKEND / "scripts/t2_full_chain_test.py", False),
    ("D-E2E", BACKEND / "scripts/desktop_e2e_walkthrough.py", False),
]


def backend_online() -> bool:
    try:
        with urllib.request.urlopen(f"{CLOUD_URL}/admin/login/", timeout=3) as resp:
            return resp.status < 500
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Site Factory full acceptance")
    parser.add_argument(
        "--with-t2-dataset",
        action="store_true",
        help="Include T-2 full chain and Desktop E2E walkthrough scripts",
    )
    args = parser.parse_args()

    suites = list(SUITES)
    if args.with_t2_dataset:
        suites.extend(OPTIONAL_SUITES)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    online = backend_online()
    lines = [f"# Site Factory 全链路验收\n", f"> {now}\n", "| Phase | 结果 |", "|-------|------|"]
    failed = []
    skipped = []

    for name, script, needs_backend in suites:
        if not script.is_file():
            lines.append(f"| {name} | ❌ 脚本缺失 |")
            failed.append(name)
            continue
        if needs_backend and not online:
            lines.append(f"| {name} | ⏭️ 跳过（后端未启动） |")
            skipped.append(name)
            continue
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=600,
        )
        ok = proc.returncode == 0
        lines.append(f"| {name} | {'✅ 通过' if ok else '❌ 失败'} |")
        if not ok:
            failed.append(name)

    verdict = "通过" if not failed else f"失败（{', '.join(failed)}）"
    if skipped:
        lines.insert(3, f"> 后端：{'在线' if online else '离线'}；跳过 {', '.join(skipped)}\n")
    lines.insert(2, f"> **结论：{verdict}**\n")
    lines.extend([
        "",
        "## 复验",
        "",
        "```bash",
        "# 启动后端后跑全量（含 T-5 / Preflight）",
        "cd Backend && python scripts/site_factory_full_acceptance.py",
        "cd Backend && python scripts/site_factory_full_acceptance.py --with-t2-dataset",
        "```",
    ])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {REPORT}")
    print(f"Verdict: {verdict}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
