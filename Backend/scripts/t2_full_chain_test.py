#!/usr/bin/env python
"""T-2 full chain: generate site → QA → Agent recolor → re-QA (no real YOLO training)."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
REPORT = REPO / "test-reports" / "t2-full-chain-result.json"
FIXTURE = BACKEND / "scripts" / "fixtures" / "t2_mini_yolo"

sys.path.insert(0, str(BACKEND))


def ensure_mini_dataset() -> Path:
    """Create minimal YOLO dataset fixture if missing."""
    root = FIXTURE
    images = root / "images" / "train"
    labels = root / "labels" / "train"
    images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image
    except ImportError:
        Image = None

    for i in range(3):
        img_path = images / f"sample_{i}.jpg"
        lbl_path = labels / f"sample_{i}.txt"
        if not lbl_path.exists():
            lbl_path.write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        if not img_path.exists():
            if Image:
                img = Image.new("RGB", (64, 64), color=(128, 128, 128))
                img.save(img_path)
            else:
                img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    yaml_path = root / "dataset.yaml"
    if not yaml_path.exists():
        yaml_path.write_text(
            f"path: {root.as_posix()}\n"
            "train: images/train\n"
            "val: images/train\n"
            "names:\n  0: helmet\n  1: vest\n",
            encoding="utf-8",
        )
    return root


def main() -> int:
    from website_generator.generators.detection import DetectionGenerator
    from website_generator.site_factory.environment import run_environment_checks
    from website_generator.site_factory.project_profiler import build_project_profile
    from website_generator.site_factory.project_agent import process_agent_message
    from website_generator.site_factory.qa_runner import run_site_qa
    from training.options import analyze_dataset_payload

    dataset_root = ensure_mini_dataset()
    yaml_path = dataset_root / "dataset.yaml"
    analysis = analyze_dataset_payload({
        "training_kind": "yolo",
        "dataset_yaml_path": str(yaml_path),
    })

    tmp_base = tempfile.mkdtemp(prefix="flowly_t2_")
    try:
        run_dir = os.path.join(tmp_base, "training_run")
        site_dir = os.path.join(run_dir, "generated_site")
        os.makedirs(run_dir, exist_ok=True)
        weight = os.path.join(run_dir, "best.pt")
        with open(weight, "w", encoding="utf-8") as f:
            f.write("fake-yolo-weight")

        class_names = [c["name"] for c in analysis.get("classes", [])] or ["helmet", "vest"]
        profile = build_project_profile(
            class_names=class_names,
            model_path=weight,
            website_type="detection",
        )

        gen = DetectionGenerator({
            "output_dir": site_dir,
            "model_path": weight,
            "model_type": "detection",
            "labels": class_names,
            "framework": "pytorch",
            "website_type": "detection",
            "frontend_framework": "vue",
            "backend_framework": "flask",
            "port": 49153,
            "name": profile.get("scenario", "T2 识别系统"),
            "profile": profile,
            "wizard": {
                "siteName": profile.get("scenario", "T2 识别系统"),
                "usageDescription": "T2 全链路验收",
                "primaryColor": "#f59e0b",
                "wizardCompleted": True,
            },
        })
        gen_result = gen.generate()
        if not gen_result.get("success", True):
            raise RuntimeError(gen_result.get("error") or "website generation failed")

        ep = run_environment_checks(output_dir=site_dir, model_path=weight, runtime_mode="desktop")
        qa1 = run_site_qa(
            output_dir=site_dir,
            model_path=weight,
            website_type="detection",
            qa_profile="default",
            metrics={"map50": 0.75},
            port=ep["assigned_port"],
            skip_playwright=True,
        )
        agent = process_agent_message(
            output_dir=site_dir,
            message="把主色改成 #3b82f6",
            model_path=weight,
            qa_profile="default",
            auto_qa=True,
            website_type="detection",
            metrics={"map50": 0.75},
            port=ep["assigned_port"],
        )
        qa2_gate = agent.get("qa_gate")

        result = {
            "passed": qa1.get("gate") != "red" and agent.get("success") and qa2_gate != "red",
            "dataset_analysis": {
                "class_count": analysis.get("class_count"),
                "classes": class_names,
            },
            "profiler": {"scenario": profile.get("scenario"), "domain": profile.get("domain")},
            "qa_initial": qa1.get("gate"),
            "agent": {
                "files_changed": agent.get("files_changed"),
                "qa_gate": qa2_gate,
            },
            "output_dir": site_dir,
        }
    finally:
        shutil.rmtree(tmp_base, ignore_errors=True)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
