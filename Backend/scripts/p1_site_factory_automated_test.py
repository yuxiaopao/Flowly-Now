#!/usr/bin/env python
"""
P1 automated checks for Desktop ML Site Factory (no Electron UI required).

Covers items marked P1 in 05-acceptance-checklist.md that can be verified statically
or via subprocess smoke tests.

Output: test-reports/P1_SITE_FACTORY_AUTOMATED.md + p1-site-factory-result.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "Backend"
FRONTEND = REPO / "Frontend"
DESKTOP = REPO / "Desktop"
REPORT_JSON = REPO / "test-reports" / "p1-site-factory-result.json"
REPORT_MD = REPO / "test-reports" / "P1_SITE_FACTORY_AUTOMATED.md"

sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


@dataclass
class Check:
    id: str
    category: str
    title: str
    passed: bool
    evidence: str = ""
    severity: str = "P1"


@dataclass
class Suite:
    checks: List[Check] = field(default_factory=list)

    def add(self, cid, cat, title, passed, evidence="", severity="P1"):
        self.checks.append(Check(cid, cat, title, passed, evidence, severity))

    @property
    def failed(self):
        return [c for c in self.checks if not c.passed]

    def passed_count(self):
        return sum(1 for c in self.checks if c.passed)

    def total(self):
        return len(self.checks)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def desktop_ipc(suite: Suite) -> None:
    cat = "Desktop IPC"
    main_js = read_text(DESKTOP / "main.js")
    preload = read_text(DESKTOP / "preload.js")
    suite.add("P1-D01", cat, "runtime:startSite IPC", "runtime:startSite" in main_js or "'runtime:startSite'" in main_js)
    suite.add("P1-D02", cat, "clipIndex:start IPC", "clipIndex:start" in main_js)
    suite.add("P1-D03", cat, "preload startClipIndex", "startClipIndex" in preload)
    suite.add("P1-D04", cat, "build_clip_index.py", (BACKEND / "scripts/build_clip_index.py").is_file())


def frontend_p1(suite: Suite) -> None:
    cat = "前端 P1"
    preview = read_text(FRONTEND / "src/components/workflow/nodes/SitePreviewNode.vue")
    shell = read_text(FRONTEND / "src/components/workflow/nodes/SiteFactoryNodeShell.vue")
    wizard = read_text(FRONTEND / "src/components/workflow/configs/TrainingSiteWizard.vue")
    clip_node = read_text(FRONTEND / "src/components/workflow/nodes/ClipRetrievalNode.vue")
    clip_cfg = read_text(FRONTEND / "src/components/workflow/configs/ClipRetrievalConfig.vue")
    editor = read_text(FRONTEND / "src/views/workflow/Editor.vue")
    clip_desktop = read_text(FRONTEND / "src/composables/useClipIndexDesktop.js")

    suite.add("P1-F01", cat, "SitePreview enableDesktopPreview", "enable-desktop-preview" in preview)
    suite.add("P1-F02", cat, "SiteFactoryNodeShell startSite", "startSite" in shell and "effectivePreviewUrl" in shell)
    suite.add("P1-F03", cat, "Wizard CLIP indexDir", "indexDir" in wizard and "exampleQueries" in wizard)
    suite.add("P1-F04", cat, "Wizard CLIP topK", "topK" in wizard)
    suite.add("P1-F05", cat, "ClipRetrieval indexMode desktop", "indexMode" in clip_cfg and "desktop" in clip_cfg)
    suite.add("P1-F06", cat, "ClipRetrievalNode 本地 GPU", "buildLocalIndex" in clip_node)
    suite.add("P1-F07", cat, "Editor prepareDesktopClipIndexes", "prepareDesktopClipIndexes" in editor)
    suite.add("P1-F08", cat, "useClipIndexDesktop composable", "startIndex" in clip_desktop and "waitForCompletion" in clip_desktop)
    suite.add("P1-F09", cat, "ProjectAgentNode 存在", (FRONTEND / "src/components/workflow/nodes/ProjectAgentNode.vue").is_file())


def backend_p1(suite: Suite) -> None:
    cat = "后端 P1"
    qa = read_text(BACKEND / "website_generator/site_factory/qa_runner.py")
    lcs = read_text(BACKEND / "workflows/services/langchain_service.py")
    cls_gen = read_text(BACKEND / "website_generator/generators/classification.py")
    thresholds = read_text(BACKEND / "website_generator/site_factory/qa_thresholds.py")

    suite.add("P1-B01", cat, "Playwright L3 检索站 Tab", "_run_l3_clip_retrieval_playwright" in qa)
    suite.add("P1-B02", cat, "prebuiltIndexDir 跳过重建", "prebuiltIndexDir" in lcs and "built_on" in lcs)
    suite.add("P1-B03", cat, "CLIP 分类站 generator", "_generate_clip_classification_backend" in cls_gen)
    suite.add("P1-B04", cat, "QA L4 clip R@5 阈值", "r_at_5" in thresholds and "clip_retrieval" in thresholds)

    urls = read_text(BACKEND / "config/urls.py")
    wg_views = read_text(BACKEND / "website_generator/views.py")
    suite.add("P1-B05", cat, "website-generator API 路由", "website-generator" in urls)
    suite.add("P1-B06", cat, "agent/message API", "agent/message" in wg_views and "def agent_message" in wg_views)


def build_clip_index_smoke(suite: Suite) -> None:
    cat = "冒烟"
    script = BACKEND / "scripts/build_clip_index.py"
    if not script.is_file():
        suite.add("P1-G01", cat, "build_clip_index 冒烟", False, "脚本缺失")
        return

    tmp = Path(tempfile.mkdtemp(prefix="flowly_p1_clip_"))
    ds = tmp / "dataset"
    img_dir = ds / "images"
    img_dir.mkdir(parents=True)
    try:
        from PIL import Image

        for i, (name, text) in enumerate([("a.jpg", "猫"), ("b.jpg", "狗")]):
            Image.new("RGB", (32, 32), color=(100 + i * 50, 80, 60)).save(img_dir / name)
            with open(ds / "pairs.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"image": f"images/{name}", "text": text}, ensure_ascii=False) + "\n")

        cfg_path = tmp / "job.json"
        out_dir = tmp / "index"
        cfg_path.write_text(json.dumps({
            "dataset_path": str(ds),
            "output_dir": str(out_dir),
            "base_model": "simple-bow",
        }), encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(script), "--config", str(cfg_path), "--output-dir", str(out_dir), "--streaming"],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=120,
        )
        ok = proc.returncode == 0 and (out_dir / "metadata.json").is_file()
        suite.add("P1-G01", cat, "build_clip_index 冒烟", ok, (proc.stderr or "")[-200:])
    except Exception as exc:
        suite.add("P1-G01", cat, "build_clip_index 冒烟", False, str(exc))


def qa_l4_clip_smoke(suite: Suite) -> None:
    cat = "QA L4"
    try:
        import django

        django.setup()
        from website_generator.site_factory.qa_thresholds import evaluate_metrics_gate

        green, _, _ = evaluate_metrics_gate("clip_retrieval", {"r_at_5": 0.85}, "default")
        yellow, _, _ = evaluate_metrics_gate("clip_retrieval", {"r_at_5": 0.65}, "default")
        red, _, _ = evaluate_metrics_gate("clip_retrieval", {"r_at_5": 0.2}, "default")
        suite.add("P1-Q01", cat, "clip_retrieval L4 绿/黄/红", green == "green" and yellow == "yellow" and red == "red")
    except Exception as exc:
        suite.add("P1-Q01", cat, "clip_retrieval L4 绿/黄/红", False, str(exc))


def clip_zero_shot_site_smoke(suite: Suite) -> None:
    """Generate CLIP classification site files in temp dir (M4.7)."""
    cat = "CLIP 建站"
    try:
        import django

        django.setup()
        from website_generator.generators.classification import ClassificationGenerator

        tmp = Path(tempfile.mkdtemp(prefix="flowly_p1_clip_cls_"))
        gen = ClassificationGenerator({
            "output_dir": str(tmp),
            "model_path": str(tmp / "manifest.json"),
            "labels": ["cat", "dog"],
            "framework": "clip",
            "website_type": "classification",
            "name": "P1 CLIP Test",
            "wizard": {"siteName": "CLIP 零样本测试", "primaryColor": "#06b6d4"},
            "profile": {"scenario": "宠物分类演示", "class_display_names": {"cat": "猫", "dog": "狗"}},
        })
        gen.generate()
        app_py = read_text(tmp / "backend" / "app.py")
        ok = "predict_clip_image" in app_py and (tmp / "backend" / "manifest.json").is_file()
        suite.add("P1-G02", cat, "CLIP 零样本分类站生成", ok)
    except Exception as exc:
        suite.add("P1-G02", cat, "CLIP 零样本分类站生成", False, str(exc))


def write_reports(suite: Suite) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    failed = suite.failed
    verdict = "通过" if not failed else "不通过"
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps({
        "timestamp": now,
        "verdict": verdict,
        "passed": suite.passed_count(),
        "total": suite.total(),
        "checks": [{"id": c.id, "title": c.title, "passed": c.passed, "severity": c.severity} for c in suite.checks],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# P1 自动化验收报告\n",
        f"> {now} **{verdict}** ({suite.passed_count()}/{suite.total()})\n",
        "",
        "## 说明",
        "",
        "本报告覆盖可在 CI/无 Desktop UI 环境下自动验证的 P1 项。",
        "以下仍需 **Flowly Desktop 人工走查**：",
        "",
        "- M1-M01：Preview 节点 iframe 首次权限弹窗",
        "- M1-M02：Playwright 在真实生成站上的全路径（需 playwright + 运行中 Flask）",
        "- M2-M02：PropertyPanel Wizard 四步 UI 交互",
        "- M3：ProjectAgent 对话 UI 与 RAG 检索 E2E",
        "",
        "## 检查项",
        "",
        "| ID | 类别 | 项 | 结果 |",
        "|----|------|-----|------|",
    ]
    for c in suite.checks:
        mark = "✅" if c.passed else "❌"
        lines.append(f"| {c.id} | {c.category} | {c.title} | {mark} |")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Verdict: {verdict} ({suite.passed_count()}/{suite.total()})")
    print(f"Report: {REPORT_MD}")
    return 0 if not failed else 1


def main() -> int:
    suite = Suite()
    desktop_ipc(suite)
    frontend_p1(suite)
    backend_p1(suite)
    build_clip_index_smoke(suite)
    qa_l4_clip_smoke(suite)
    clip_zero_shot_site_smoke(suite)
    return write_reports(suite)


if __name__ == "__main__":
    sys.exit(main())
