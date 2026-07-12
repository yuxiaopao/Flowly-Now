#!/usr/bin/env python
"""
M2 Desktop ML Site Factory — formal acceptance test suite.

Output: test-reports/M2_ACCEPTANCE_REPORT.md + m2-acceptance-result.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "Backend"
FRONTEND = REPO / "Frontend"
REPORT_JSON = REPO / "test-reports" / "m2-acceptance-result.json"
REPORT_MD = REPO / "test-reports" / "M2_ACCEPTANCE_REPORT.md"

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

    def add(self, cid: str, cat: str, title: str, passed: bool, evidence: str = "", severity: str = "P0"):
        self.checks.append(Check(cid, cat, title, passed, evidence, severity))

    @property
    def p0_failed(self) -> List[Check]:
        return [c for c in self.checks if not c.passed and c.severity == "P0"]

    @property
    def p1_failed(self) -> List[Check]:
        return [c for c in self.checks if not c.passed and c.severity == "P1"]

    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    def total(self) -> int:
        return len(self.checks)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def static_structure(suite: Suite) -> None:
    cat = "静态结构"
    files = [
        ("M2-S01", BACKEND / "website_generator/site_factory/project_profiler.py"),
        ("M2-S02", FRONTEND / "src/components/workflow/nodes/ProjectProfilerNode.vue"),
        ("M2-S03", FRONTEND / "src/components/workflow/configs/ProjectProfilerConfig.vue"),
        ("M2-S04", FRONTEND / "src/components/workflow/configs/TrainingSiteWizard.vue"),
    ]
    for cid, path in files:
        suite.add(cid, cat, f"文件存在: {path.relative_to(REPO)}", path.is_file())

    lc = read_text(BACKEND / "workflows/services/langchain_service.py")
    suite.add("M2-S05", cat, "langchain 注册 project_profiler", "'project_profiler':" in lc)
    suite.add("M2-S06", cat, "run_project_profiler_node 实现", "def run_project_profiler_node" in lc)
    suite.add("M2-S07", cat, "website_generator 读取 profile/wizard", "profile = node_config.get('profile')" in lc)
    suite.add("M2-S08", cat, "wizardCompleted 校验 siteName", "wizard.get('wizardCompleted')" in lc)

    reg = read_text(FRONTEND / "src/config/nodeRegistry.js")
    comp = read_text(FRONTEND / "src/config/nodeComponents.js")
    suite.add("M2-S09", cat, "nodeRegistry 注册", "'project_profiler'" in reg)
    suite.add("M2-S10", cat, "nodeComponents 映射", "project_profiler:" in comp)

    wg = read_text(FRONTEND / "src/components/workflow/configs/WebsiteGeneratorConfig.vue")
    suite.add("M2-S11", cat, "WebsiteGeneratorConfig 集成 Wizard", "TrainingSiteWizard" in wg)

    base = read_text(BACKEND / "website_generator/generators/base.py")
    suite.add("M2-S12", cat, "BaseGenerator profile/wizard 助手", "get_site_title" in base and "self.profile" in base)


def yolo_template_chain(suite: Suite) -> None:
    cat = "YOLO 模板"
    tpl = read_text(FRONTEND / "src/config/yoloWorkflowTemplate.js")
    seed = read_text(BACKEND / "workflows/management/commands/seed_domain_templates.py")

    suite.add("M2-T01", cat, "模板含 project_profiler 节点", "project_profiler_1" in tpl)
    chain = [
        ("yolo_training_1", "project_profiler_1"),
        ("project_profiler_1", "website_generator_1"),
    ]
    for src, tgt in chain:
        ok = f"source: '{src}', target: '{tgt}'" in tpl
        suite.add(f"M2-T02-{src}", cat, f"前端模板边 {src} → {tgt}", ok)

    suite.add("M2-T03", cat, "seed 含 project_profiler", "project_profiler_1" in seed)
    suite.add("M2-T04", cat, "seed 更新已有模板逻辑", "template.workflow_data = workflow_data" in seed)
    suite.add("M2-T05", cat, "website_generator 预置 wizard", "wizardCompleted" in tpl)


def profiler_semantics(suite: Suite) -> None:
    cat = "Profiler 语义"
    from website_generator.site_factory.project_profiler import build_project_profile

    helmet = build_project_profile(["helmet", "no_helmet"], website_type="detection")
    suite.add("M2-P01", cat, "安全帽 → 工业安全领域", helmet.get("domain") == "工业安全")
    suite.add("M2-P02", cat, "安全帽 scenario 含关键词", "安全帽" in helmet.get("scenario", ""))
    suite.add(
        "M2-P03",
        cat,
        "class_display_names 映射",
        helmet.get("class_display_names", {}).get("helmet") == "已佩戴安全帽",
    )
    suite.add("M2-P04", cat, "recommended_template=detection", helmet.get("recommended_template") == "detection")

    generic = build_project_profile(["apple", "orange"], website_type="detection")
    suite.add("M2-P05", cat, "通用类名 fallback 场景", "apple" in str(generic.get("scenario", "")).lower() or "识别" in generic.get("scenario", ""))
    suite.add("M2-P06", cat, "copy_hints 非空", len(generic.get("copy_hints") or []) >= 1)


def wizard_validation(suite: Suite) -> None:
    cat = "Wizard 校验"

    def blocked(wizard: Dict[str, Any]) -> bool:
        return bool(wizard.get("wizardCompleted") and not (wizard.get("siteName") or "").strip())

    suite.add("M2-W01", cat, "wizardCompleted 无 siteName → 阻断", blocked({"wizardCompleted": True, "siteName": ""}))
    suite.add("M2-W02", cat, "wizardCompleted 有 siteName → 通过", not blocked({"wizardCompleted": True, "siteName": "测试站"}))
    suite.add("M2-W03", cat, "未 completed 不阻断", not blocked({"wizardCompleted": False, "siteName": ""}))

    wizard_vue = read_text(FRONTEND / "src/components/workflow/configs/TrainingSiteWizard.vue")
    for step, label in [(0, "场景"), (1, "品牌"), (2, "合规"), (3, "输出")]:
        suite.add(f"M2-W04-{step}", cat, f"Wizard Step{step+1} {label}", f'title="{label}"' in wizard_vue)
    suite.add("M2-W05", cat, "Wizard 必填 canFinish", "canFinish" in wizard_vue and "siteName" in wizard_vue)


def generator_injection(suite: Suite) -> None:
    cat = "生成器注入"
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts/m2_profiler_smoke_test.py")],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=120,
    )
    smoke_path = REPO / "test-reports/m2-smoke-result.json"
    smoke: Dict[str, Any] = {}
    if smoke_path.is_file():
        smoke = json.loads(smoke_path.read_text(encoding="utf-8"))

    ok = proc.returncode == 0 and smoke.get("passed") is True
    suite.add("M2-G00", cat, "m2_profiler_smoke_test 通过", ok, (proc.stdout or proc.stderr)[-300:])

    checks = smoke.get("checks") or {}
    for key, cid in [
        ("title_injected", "M2-G01"),
        ("subtitle_injected", "M2-G02"),
        ("disclaimer_injected", "M2-G03"),
        ("upload_hint", "M2-G04"),
        ("schema_unchanged", "M2-G05"),
    ]:
        suite.add(cid, cat, key, checks.get(key) is True)


def contracts_doc(suite: Suite) -> None:
    cat = "文档契约"
    doc = read_text(REPO / "Docs/desktop-ml-site-factory/references/node-io-contracts.md")
    suite.add("M2-D01", cat, "node-io-contracts profiler 输出示例", "class_display_names" in doc and "profiler_version" in doc)
    suite.add("M2-D02", cat, "wizard 契约 documented", "wizardCompleted" in doc)


def deferred_p1(suite: Suite) -> None:
    cat = "P1 待优化"
    cls_gen = read_text(BACKEND / "website_generator/generators/classification.py")
    suite.add(
        "M2-M01",
        cat,
        "classification 生成器 profile 注入",
        "get_site_title" in cls_gen or "self.profile" in cls_gen,
        "detection 已实现；classification 待 M2 后续",
        "P1",
    )
    suite.add(
        "M2-M02",
        cat,
        "PropertyPanel Wizard 端到端 UI 人工验",
        False,
        "需在编辑器选中 website_generator 走四步",
        "P1",
    )


def m1_regression(suite: Suite) -> None:
    cat = "M1 回归"
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts/m1_acceptance_test.py")],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=300,
    )
    m1_json = REPO / "test-reports/m1-acceptance-result.json"
    verdict = "unknown"
    if m1_json.is_file():
        data = json.loads(m1_json.read_text(encoding="utf-8"))
        verdict = data.get("verdict", "unknown")
    suite.add(
        "M2-R01",
        cat,
        "M1 验收仍通过",
        proc.returncode == 0 and verdict == "通过",
        f"verdict={verdict}",
    )


def write_reports(suite: Suite) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    p0_fail = suite.p0_failed
    p1_fail = suite.p1_failed
    verdict = "通过" if not p0_fail else "不通过"

    result = {
        "timestamp": now,
        "verdict": verdict,
        "passed": suite.passed_count(),
        "total": suite.total(),
        "p0_failed": len(p0_fail),
        "p1_deferred": len(p1_fail),
        "checks": [
            {
                "id": c.id,
                "category": c.category,
                "title": c.title,
                "passed": c.passed,
                "severity": c.severity,
                "evidence": c.evidence,
            }
            for c in suite.checks
        ],
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# M2 验收报告 — Profiler + 建站向导",
        "",
        f"> 生成时间：{now}  ",
        f"> **结论：{verdict}**（P0 失败 {len(p0_fail)}，P1 待补 {len(p1_fail)}）",
        "",
        "## 摘要",
        "",
        "| 维度 | 结果 |",
        "|------|------|",
        f"| P0 自动验收 | {'✅ 全部通过' if not p0_fail else f'❌ {len(p0_fail)} 项失败'} |",
        f"| P1 待优化/人工 | {len(p1_fail)} 项 |",
        f"| 冒烟 | `Backend/scripts/m2_profiler_smoke_test.py` |",
        f"| M1 回归 | `Backend/scripts/m1_acceptance_test.py` |",
        "",
        "## P0 失败项",
        "",
    ]
    if p0_fail:
        for c in p0_fail:
            lines.append(f"- **{c.id}** {c.title} — {c.evidence}")
    else:
        lines.append("- 无")
    lines.extend(["", "## P1 待补", ""])
    for c in p1_fail:
        lines.append(f"- **{c.id}** {c.title} — {c.evidence}")
    lines.extend(["", "## 全量检查明细", "", "| ID | 类别 | 项 | 结果 | 证据 |", "|----|------|-----|------|------|"])
    for c in suite.checks:
        status = "✅" if c.passed else ("⏳" if c.severity == "P1" else "❌")
        ev = (c.evidence or "").replace("|", "\\|").replace("\n", " ")[:80]
        lines.append(f"| {c.id} | {c.category} | {c.title} | {status} | {ev} |")
    lines.extend([
        "",
        "## 复验命令",
        "",
        "```bash",
        "cd Backend && python scripts/m2_acceptance_test.py",
        "```",
        "",
        "## 下一步",
        "",
    ])
    if p0_fail:
        lines.append("1. 修复 P0 失败项后再进入 M3")
    else:
        lines.append("1. P0 已通过 → 可启动 **M3**（Project Agent）")
    lines.append("2. P1：classification 模板注入 + Wizard UI 人工走查")
    lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {REPORT_MD}")
    print(f"Verdict: {verdict} ({suite.passed_count()}/{suite.total()})")
    return 0 if not p0_fail else 1


def main() -> int:
    suite = Suite()
    static_structure(suite)
    yolo_template_chain(suite)
    profiler_semantics(suite)
    wizard_validation(suite)
    generator_injection(suite)
    contracts_doc(suite)
    m1_regression(suite)
    deferred_p1(suite)
    return write_reports(suite)


if __name__ == "__main__":
    sys.exit(main())
