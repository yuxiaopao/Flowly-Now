#!/usr/bin/env python
"""
Desktop manual walkthrough preflight — verify environment before D-01–D05.

Does NOT require Flowly Desktop UI; checks files, ports, and optional services.

Output: test-reports/DESKTOP_MANUAL_PREFLIGHT.md + desktop-manual-preflight.json
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "Backend"
FRONTEND = REPO / "Frontend"
DESKTOP = REPO / "Desktop"
REPORT_JSON = REPO / "test-reports" / "desktop-manual-preflight.json"
REPORT_MD = REPO / "test-reports" / "DESKTOP_MANUAL_PREFLIGHT.md"

API_BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
FRONTEND_URL = os.environ.get("FLOWLY_FRONTEND_URL", "http://127.0.0.1:5200")


@dataclass
class Check:
    id: str
    title: str
    passed: bool
    detail: str = ""
    required: bool = True


@dataclass
class Suite:
    checks: List[Check] = field(default_factory=list)

    def add(self, cid: str, title: str, passed: bool, detail: str = "", required: bool = True):
        self.checks.append(Check(cid, title, passed, detail, required))

    @property
    def blocking_failed(self):
        return [c for c in self.checks if c.required and not c.passed]

    def passed_count(self):
        return sum(1 for c in self.checks if c.passed)

    def total(self):
        return len(self.checks)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_ok(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 500, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return exc.code < 500, f"HTTP {exc.code}"
    except Exception as exc:
        return False, str(exc)


def check_static(suite: Suite) -> None:
    main_js = read_text(DESKTOP / "main.js")
    preload = read_text(DESKTOP / "preload.js")
    suite.add("PF-S01", "Desktop main.js 存在", DESKTOP.joinpath("main.js").is_file())
    suite.add("PF-S02", "runtime:startSite IPC", "runtime:startSite" in main_js or "'runtime:startSite'" in main_js)
    suite.add("PF-S03", "clipIndex:start IPC", "clipIndex:start" in main_js)
    suite.add("PF-S04", "preload startClipIndex", "startClipIndex" in preload)
    suite.add("PF-S05", "build_clip_index.py", (BACKEND / "scripts/build_clip_index.py").is_file())
    suite.add("PF-S06", "SitePreviewNode Desktop 预览", "enable-desktop-preview" in read_text(
        FRONTEND / "src/components/workflow/nodes/SitePreviewNode.vue"
    ))
    suite.add("PF-S07", "useClipIndexDesktop", (FRONTEND / "src/composables/useClipIndexDesktop.js").is_file())
    suite.add("PF-S08", "YOLO 模板九节点链", "project_agent" in read_text(FRONTEND / "src/config/yoloWorkflowTemplate.js"))
    suite.add("PF-S09", "CLIP 模板", (FRONTEND / "src/config/clipRetrievalWorkflowTemplate.js").is_file())


def check_services(suite: Suite) -> None:
    api_ok, api_detail = http_ok(f"{API_BASE.rstrip('/')}/monitoring/health/")
    suite.add("PF-N01", "后端 API 可达", api_ok, api_detail, required=False)

    fe_ok, fe_detail = http_ok(FRONTEND_URL)
    suite.add("PF-N02", "前端 dev 可达", fe_ok, fe_detail, required=False)

    suite.add("PF-N03", "端口 8000 监听", port_open("127.0.0.1", 8000), required=False)
    suite.add("PF-N04", "端口 5200 监听", port_open("127.0.0.1", 5200), required=False)


def check_playwright(suite: Suite) -> None:
    try:
        import playwright  # noqa: F401
        suite.add("PF-P01", "playwright Python 包", True)
    except ImportError:
        suite.add("PF-P01", "playwright Python 包", False, "pip install playwright && playwright install chromium", required=False)

    try:
        proc = subprocess.run(
            [sys.executable, "-c", "from playwright.sync_api import sync_playwright; sync_playwright().start().chromium.launch(headless=True).close()"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        suite.add("PF-P02", "Playwright Chromium 可启动", proc.returncode == 0, (proc.stderr or "")[-120:], required=False)
    except Exception as exc:
        suite.add("PF-P02", "Playwright Chromium 可启动", False, str(exc), required=False)


def check_gpu_hint(suite: Suite) -> None:
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            suite.add("PF-G01", "NVIDIA GPU", True, proc.stdout.strip().split("\n")[0], required=False)
        else:
            suite.add("PF-G01", "NVIDIA GPU", False, "未检测到（CLIP 将用 CPU/BOW）", required=False)
    except FileNotFoundError:
        suite.add("PF-G01", "NVIDIA GPU", False, "nvidia-smi 不可用", required=False)
    except Exception as exc:
        suite.add("PF-G01", "NVIDIA GPU", False, str(exc), required=False)


def write_reports(suite: Suite) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    blocking = suite.blocking_failed
    ready = not blocking
    verdict = "可开始人工走查" if ready else "静态检查未通过"

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps({
        "timestamp": now,
        "verdict": verdict,
        "ready_for_manual": ready,
        "passed": suite.passed_count(),
        "total": suite.total(),
        "checks": [{"id": c.id, "title": c.title, "passed": c.passed, "required": c.required, "detail": c.detail} for c in suite.checks],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Desktop 人工走查预检\n",
        f"> {now} · **{verdict}** ({suite.passed_count()}/{suite.total()})\n",
        "",
        "## 人工走查步骤（D-01–D05）",
        "",
        "见 [`Docs/desktop-ml-site-factory/05-acceptance-checklist.md`](../Docs/desktop-ml-site-factory/05-acceptance-checklist.md)",
        "",
        "1. 启动后端 Daphne + 前端（或 Flowly Desktop）",
        "2. 登录 `nlwftest@flowly.test`",
        "3. 打开 `yolo-detection-project` 或 `clip-retrieval-project` 模板",
        "4. 按 D-01–D05 逐项勾选",
        "",
        "## 预检结果",
        "",
        "| ID | 项 | 必需 | 结果 | 说明 |",
        "|----|-----|------|------|------|",
    ]
    for c in suite.checks:
        mark = "✅" if c.passed else ("⚠️" if not c.required else "❌")
        req = "是" if c.required else "否"
        detail = (c.detail or "").replace("|", "\\|")[:80]
        lines.append(f"| {c.id} | {c.title} | {req} | {mark} | {detail} |")

    if not suite.checks[0 if suite.checks else None:]:
        pass

    optional_failed = [c for c in suite.checks if not c.required and not c.passed]
    if optional_failed:
        lines.extend(["", "## 可选项未满足（不阻断走查）", ""])
        for c in optional_failed:
            lines.append(f"- **{c.id}** {c.title}: {c.detail}")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Verdict: {verdict} ({suite.passed_count()}/{suite.total()})")
    print(f"Report: {REPORT_MD}")
    return 0 if ready else 1


def main() -> int:
    suite = Suite()
    check_static(suite)
    check_services(suite)
    check_playwright(suite)
    check_gpu_hint(suite)
    return write_reports(suite)


if __name__ == "__main__":
    sys.exit(main())
