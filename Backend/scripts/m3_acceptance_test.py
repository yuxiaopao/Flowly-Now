#!/usr/bin/env python
"""
M3 Desktop ML Site Factory — formal acceptance test suite.

Output: test-reports/M3_ACCEPTANCE_REPORT.md + m3-acceptance-result.json
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
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "Backend"
FRONTEND = REPO / "Frontend"
REPORT_JSON = REPO / "test-reports" / "m3-acceptance-result.json"
REPORT_MD = REPO / "test-reports" / "M3_ACCEPTANCE_REPORT.md"

sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()


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
        ("M3-S01", BACKEND / "website_generator/site_factory/project_agent.py"),
        ("M3-S02", BACKEND / "website_generator/migrations/0004_generatedsite_project_agent_fields.py"),
        ("M3-S03", FRONTEND / "src/components/workflow/nodes/ProjectAgentNode.vue"),
    ]
    for cid, path in files:
        suite.add(cid, cat, f"文件存在: {path.relative_to(REPO)}", path.is_file())

    lc = read_text(BACKEND / "workflows/services/langchain_service.py")
    suite.add("M3-S04", cat, "langchain 注册 project_agent", "'project_agent':" in lc)
    suite.add("M3-S05", cat, "run_project_agent_node 实现", "def run_project_agent_node" in lc)

    views = read_text(BACKEND / "website_generator/views.py")
    suite.add("M3-S06", cat, "API agent/message", "def agent_message" in views and "agent/message" in views)

    ser = read_text(BACKEND / "website_generator/serializers.py")
    suite.add("M3-S07", cat, "Serializer 新字段", "last_agent_reply" in ser and "preview_status" in ser)

    reg = read_text(FRONTEND / "src/config/nodeRegistry.js")
    comp = read_text(FRONTEND / "src/config/nodeComponents.js")
    api = read_text(FRONTEND / "src/api/websiteGenerator.js")
    suite.add("M3-S08", cat, "nodeRegistry 注册", "'project_agent'" in reg)
    suite.add("M3-S09", cat, "nodeComponents 映射", "project_agent:" in comp)
    suite.add("M3-S10", cat, "前端 API agentMessage", "agentMessage" in api)


def yolo_template_chain(suite: Suite) -> None:
    cat = "YOLO 模板"
    tpl = read_text(FRONTEND / "src/config/yoloWorkflowTemplate.js")
    seed = read_text(BACKEND / "workflows/management/commands/seed_domain_templates.py")

    suite.add("M3-T01", cat, "模板含 project_agent 节点", "project_agent_1" in tpl)
    suite.add("M3-T02", cat, "边 site_preview → project_agent", "source: 'site_preview_1', target: 'project_agent_1'" in tpl)
    suite.add("M3-T03", cat, "seed 含 project_agent", "project_agent_1" in seed)


def agent_semantics(suite: Suite) -> None:
    cat = "Agent 语义"
    from website_generator.generators.detection import DetectionGenerator
    from website_generator.site_factory.project_agent import (
        process_agent_message,
        export_conversation_json,
        ProjectAgentSandbox,
    )

    tmp = tempfile.mkdtemp(prefix="flowly_m3_")
    site_dir = os.path.join(tmp, "site")
    gen = DetectionGenerator({
        "output_dir": site_dir,
        "model_path": "",
        "labels": ["helmet"],
        "framework": "pytorch",
        "website_type": "detection",
        "port": 49152,
        "name": "test",
        "description": "",
        "wizard": {"siteName": "测试站", "wizardCompleted": True},
    })
    gen.generate()

    block = process_agent_message(site_dir, "删除 app.py 里的 load_model")
    suite.add("M3-A01", cat, "拒绝删除核心推理", block.get("blocked") is True)

    dark = process_agent_message(site_dir, "把首页改成深色", auto_qa=False)
    html_path = os.path.join(site_dir, "frontend", "index.html")
    html = Path(html_path).read_text(encoding="utf-8")
    suite.add("M3-A02", cat, "深色主题改写", dark.get("success") and "#0a0a0f" in html)
    suite.add("M3-A03", cat, "files_changed 记录", "frontend/index.html" in (dark.get("files_changed") or []))

    audit = os.path.join(site_dir, ".flowly", "agent", "audit.jsonl")
    suite.add("M3-A04", cat, "审计日志写入", os.path.isfile(audit))

    export_conversation_json(site_dir)
    conv_json = os.path.join(site_dir, ".flowly", "agent", "conversation.json")
    suite.add("M3-A05", cat, "conversation.json 导出", os.path.isfile(conv_json))

    sandbox = ProjectAgentSandbox(site_dir)
    blocked_write = False
    try:
        sandbox.write_file("backend/app.py", "# hacked")
    except PermissionError:
        blocked_write = True
    suite.add("M3-A06", cat, "核心 app.py 写保护", blocked_write)


def migration_applied(suite: Suite) -> None:
    cat = "数据库"
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SHOW COLUMNS FROM generated_sites LIKE 'last_agent_reply'")
        row = cur.fetchone()
    suite.add("M3-D01", cat, "迁移 0004 last_agent_reply 列", row is not None)


def m2_regression(suite: Suite) -> None:
    cat = "M2 回归"
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts/m2_acceptance_test.py")],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=300,
    )
    m2_json = REPO / "test-reports/m2-acceptance-result.json"
    verdict = "unknown"
    if m2_json.is_file():
        data = json.loads(m2_json.read_text(encoding="utf-8"))
        verdict = data.get("verdict", "unknown")
    suite.add(
        "M3-R01",
        cat,
        "M2 验收仍通过",
        proc.returncode == 0 and verdict == "通过",
        f"verdict={verdict}",
    )


def deferred_p1(suite: Suite) -> None:
    cat = "P1 待优化"
    suite.add(
        "M3-P01",
        cat,
        "ProjectAgentNode 对话 UI 人工验",
        False,
        "需在画布展开节点发送「深色主题」",
        "P1",
    )
    suite.add(
        "M3-P02",
        cat,
        "RAG collection 向量库端到端",
        False,
        "需用户已有 VectorStore 后验检索",
        "P1",
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
        "# M3 验收报告 — Project Agent + 强制 QA",
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
    lines.extend(["", "## 复验命令", "", "```bash", "cd Backend && python scripts/m3_acceptance_test.py", "```", ""])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {REPORT_MD}")
    print(f"Verdict: {verdict} ({suite.passed_count()}/{suite.total()})")
    return 0 if not p0_fail else 1


def main() -> int:
    suite = Suite()
    static_structure(suite)
    yolo_template_chain(suite)
    agent_semantics(suite)
    migration_applied(suite)
    m2_regression(suite)
    deferred_p1(suite)
    return write_reports(suite)


if __name__ == "__main__":
    sys.exit(main())
