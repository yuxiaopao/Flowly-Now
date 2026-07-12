#!/usr/bin/env python
"""Generate a v2 site and start Flask preview for visual demo."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
DEMO_DIR = REPO / "test-reports" / "demo-sites" / "yolo-v2-live"
META_FILE = DEMO_DIR / ".flowly" / "demo_meta.json"

sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def find_free_port(start: int = 49160) -> int:
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def main() -> int:
    import django

    django.setup()

    from website_generator.generators import get_generator
    from website_generator.site_factory.role_agents import (
        run_backend_setup,
        run_frontend_setup,
        run_site_code_review,
        run_ui_beautify,
    )

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    port = find_free_port()

    print(f"[demo] output_dir={DEMO_DIR}")
    print(f"[demo] port={port}")

    gen = get_generator(
        "detection",
        {
            "output_dir": str(DEMO_DIR),
            "model_path": "",
            "labels": ["猫", "狗", "鸟"],
            "framework": "ultralytics",
            "website_type": "detection",
            "port": port,
            "name": "宠物识别演示站",
            "description": "上传宠物照片进行 YOLO 目标检测",
            "profile": {
                "scenario": "宠物识别",
                "ui_tone": "friendly",
                "copy_hints": ["上传宠物照片", "查看检测框"],
            },
            "wizard": {
                "siteName": "宠物 AI 识别",
                "usageDescription": "上传图片，AI 自动标注猫狗鸟",
                "primaryColor": "#6366f1",
                "wizardCompleted": True,
            },
        },
    )
    result = gen.generate()
    if not result.get("success"):
        print(f"[demo] scaffold FAILED: {result.get('error')}")
        return 1
    print("[demo] scaffold OK")

    steps = [
        ("backend_setup", lambda: run_backend_setup(str(DEMO_DIR), agent_mode="rules", allow_core_edit=True, auto_qa=False)),
        ("frontend_setup", lambda: run_frontend_setup(str(DEMO_DIR), agent_mode="rules", auto_qa=False)),
        ("ui_beautify", lambda: run_ui_beautify(str(DEMO_DIR), agent_mode="rules", auto_qa=False)),
        ("site_code_review", lambda: run_site_code_review(str(DEMO_DIR), agent_mode="rules", max_rounds=1)),
    ]
    for name, fn in steps:
        r = fn()
        ok = r.get("success", True)
        print(f"[demo] {name}: {'OK' if ok else 'FAIL'}")
        if not ok:
            print(f"  error={r.get('error')}")
            return 1

    cfg_path = DEMO_DIR / "backend" / "config.json"
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["port"] = port
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    backend_dir = DEMO_DIR / "backend"
    env = {**os.environ, "FLASK_RUN_PORT": str(port)}
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(backend_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(4)
    if proc.poll() is not None:
        err = proc.stderr.read().decode("utf-8", errors="replace")
        print(f"[demo] Flask failed to start:\n{err[:800]}")
        return 1

    preview_url = f"http://127.0.0.1:{port}/"
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(
        json.dumps(
            {
                "preview_url": preview_url,
                "port": port,
                "pid": proc.pid,
                "output_dir": str(DEMO_DIR),
                "workflow_editor": "http://127.0.0.1:5200/workflows/ec541c9f-b580-4e73-b9f3-38b0306ea482/edit",
                "nl_create": "http://127.0.0.1:5200/nl-create",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[demo] LIVE preview: {preview_url}")
    print(f"[demo] workflow editor: http://127.0.0.1:5200/workflows/ec541c9f-b580-4e73-b9f3-38b0306ea482/edit")
    print(f"[demo] server pid={proc.pid} (leave running for browser demo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
