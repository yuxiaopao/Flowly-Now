#!/usr/bin/env python
"""M4 formal acceptance — CLIP nodes + ClipRetrievalGenerator + template."""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "Backend"
FRONTEND = REPO / "Frontend"
REPORT_JSON = REPO / "test-reports" / "m4-acceptance-result.json"
REPORT_MD = REPO / "test-reports" / "M4_ACCEPTANCE_REPORT.md"
sys.path.insert(0, str(BACKEND))


@dataclass
class Check:
    id: str
    category: str
    title: str
    passed: bool
    evidence: str = ""
    severity: str = "P0"


@dataclass
class Suite:
    checks: List[Check] = field(default_factory=list)

    def add(self, cid, cat, title, passed, evidence="", severity="P0"):
        self.checks.append(Check(cid, cat, title, passed, evidence, severity))

    @property
    def p0_failed(self):
        return [c for c in self.checks if not c.passed and c.severity == "P0"]

    def passed_count(self):
        return sum(1 for c in self.checks if c.passed)

    def total(self):
        return len(self.checks)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def static_structure(suite: Suite) -> None:
    cat = "静态结构"
    files = [
        ("M4-S01", BACKEND / "training/clip_service.py"),
        ("M4-S02", BACKEND / "training/clip_trainer.py"),
        ("M4-S03", BACKEND / "website_generator/generators/clip_retrieval.py"),
        ("M4-S04", BACKEND / "datasets/ml_format_validators.py"),
        ("M4-S05", FRONTEND / "src/config/clipRetrievalWorkflowTemplate.js"),
        ("M4-S06", FRONTEND / "src/components/workflow/nodes/ClipRetrievalNode.vue"),
        ("M4-S13", FRONTEND / "src/components/workflow/configs/ClipClassificationWizard.vue"),
    ]
    for cid, path in files:
        suite.add(cid, cat, f"存在 {path.relative_to(REPO)}", path.is_file())

    lc = read_text(BACKEND / "website_generator/generators/clip_retrieval.py")
    suite.add("M4-S14", cat, "检索站 CLIP 运行时", "_query_vector_text" in lc)
    qa = read_text(BACKEND / "website_generator/site_factory/qa_runner.py")
    suite.add("M4-S15", cat, "Playwright L3 检索站 Tab", "_run_l3_clip_retrieval_playwright" in qa)
    lcs = read_text(BACKEND / "workflows/services/langchain_service.py")
    suite.add("M4-S16", cat, "clip_retrieval WS + GPU", "_broadcast_training_event" in lcs and "gpu_info" in lcs)
    suite.add("M4-S07", cat, "clip_retrieval runner", "def run_clip_retrieval_node" in lcs)
    suite.add("M4-S08", cat, "clip_classification runner", "def run_clip_classification_node" in lcs)
    suite.add("M4-S09", cat, "get_generator clip_retrieval", "'clip_retrieval'" in read_text(BACKEND / "website_generator/generators/__init__.py"))

    reg = read_text(FRONTEND / "src/config/nodeRegistry.js")
    suite.add("M4-S10", cat, "nodeRegistry clip 节点", "'clip_retrieval'" in reg and "'clip_classification'" in reg)
    suite.add("M4-S11", cat, "Editor clip-retrieval 模板", "clip-retrieval" in read_text(FRONTEND / "src/views/workflow/Editor.vue"))
    suite.add("M4-S12", cat, "seed clip-retrieval-project", 'slug="clip-retrieval-project"' in read_text(BACKEND / "workflows/management/commands/seed_domain_templates.py"))

    cls_gen = read_text(BACKEND / "website_generator/generators/classification.py")
    suite.add("M4-S17", cat, "CLIP 零样本分类站 backend", "_generate_clip_classification_backend" in cls_gen)
    desktop_main = read_text(REPO / "Desktop/main.js")
    suite.add("M4-S18", cat, "Desktop clipIndex IPC", "clipIndex:start" in desktop_main and "build_clip_index" in desktop_main)
    suite.add("M4-S19", cat, "build_clip_index 脚本", (BACKEND / "scripts/build_clip_index.py").is_file())
    suite.add("M4-S20", cat, "useClipIndexDesktop composable", (FRONTEND / "src/composables/useClipIndexDesktop.js").is_file())
    ret_cfg = read_text(FRONTEND / "src/components/workflow/configs/ClipRetrievalConfig.vue")
    suite.add("M4-S21", cat, "ClipRetrieval indexMode", "indexMode" in ret_cfg)

    desktop_main = read_text(REPO / "Desktop/main.js")
    suite.add("M4-S17", cat, "Desktop clipIndex IPC", "clipIndex:start" in desktop_main, severity="P1")
    suite.add("M4-S18", cat, "build_clip_index.py", (BACKEND / "scripts/build_clip_index.py").is_file(), severity="P1")
    cls = read_text(BACKEND / "website_generator/generators/classification.py")
    suite.add("M4-S19", cat, "M4.7 CLIP 分类站", "_generate_clip_classification_backend" in cls, severity="P1")


def chain_smoke(suite: Suite) -> None:
    cat = "链路"
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts/m4_chain_smoke_test.py")],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=120,
    )
    chain_path = REPO / "test-reports/m4-chain-smoke-result.json"
    data = json.loads(chain_path.read_text(encoding="utf-8")) if chain_path.is_file() else {}
    suite.add("M4-C01", cat, "dataset→index→profiler→WG 链", proc.returncode == 0 and data.get("passed"), (proc.stderr or "")[-200:])


def smoke(suite: Suite) -> None:
    cat = "冒烟"
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts/m4_clip_smoke_test.py")],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=120,
    )
    smoke_path = REPO / "test-reports/m4-smoke-result.json"
    data = json.loads(smoke_path.read_text(encoding="utf-8")) if smoke_path.is_file() else {}
    suite.add("M4-G01", cat, "m4_clip_smoke_test", proc.returncode == 0 and data.get("passed"), (proc.stderr or "")[-200:])


def m3_regression(suite: Suite) -> None:
    cat = "M3 回归"
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts/m3_acceptance_test.py")],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=300,
    )
    suite.add("M4-R01", cat, "M3 仍通过", proc.returncode == 0)


def write_reports(suite: Suite) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    p0_fail = suite.p0_failed
    verdict = "通过" if not p0_fail else "不通过"
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps({
        "timestamp": now, "verdict": verdict,
        "passed": suite.passed_count(), "total": suite.total(),
        "checks": [{"id": c.id, "title": c.title, "passed": c.passed} for c in suite.checks],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_MD.write_text(
        f"# M4 验收报告\n\n> {now} **{verdict}** ({suite.passed_count()}/{suite.total()})\n",
        encoding="utf-8",
    )
    print(f"Verdict: {verdict} ({suite.passed_count()}/{suite.total()})")
    return 0 if not p0_fail else 1


def main() -> int:
    suite = Suite()
    static_structure(suite)
    smoke(suite)
    chain_smoke(suite)
    m3_regression(suite)
    return write_reports(suite)


if __name__ == "__main__":
    sys.exit(main())
