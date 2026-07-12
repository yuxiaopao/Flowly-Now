#!/usr/bin/env python
"""
NL2WF multi-scenario dialogue matrix E2E.

Runs intent/subtype classification, offline mock generation, and multi-turn
dialogue flows across YOLO, QA, email, data, translation, moderation, etc.

Usage:
  python scripts/nl2wf_dialogue_e2e.py
  python scripts/nl2wf_dialogue_e2e.py --live-api   # optional HTTP smoke (needs running backend)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
REPORT_DIR = REPO / "test-reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, str(BACKEND))

import django  # noqa: E402

django.setup()

from nl_to_workflow.constants import (  # noqa: E402
    get_mock_workflow,
    is_generate_command,
    has_sufficient_workflow_detail,
)
from nl_to_workflow.bulk_subtype_generator import generate_bulk_subtype_samples
from nl_to_workflow.dialogue_fixtures import (  # noqa: E402
    BULK_SUBTYPE_SAMPLES,
    DIALOGUE_FLOWS,
    GENERATION_CASES,
    INTENT_SUBTYPE_CASES,
)
from nl_to_workflow.services import (  # noqa: E402
    NLToWorkflowService,
    analyze_intent,
    detect_workflow_subtype,
)
from nl_to_workflow.yolo_workflow import (  # noqa: E402
    has_sufficient_yolo_detail,
    is_yolo_detection_intent,
    yolo_chat_fallback_response,
)

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")


@dataclass
class CaseResult:
    case_id: str
    category: str
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class MatrixReport:
    results: List[CaseResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)


def _offline_service() -> NLToWorkflowService:
    """Service with no LLM — uses mock/template paths."""
    svc = NLToWorkflowService(model="__nl2wf_matrix_offline__")
    svc._llm = None
    return svc


def _node_types(workflow: Optional[Dict]) -> List[str]:
    if not workflow:
        return []
    return [n.get("type", "") for n in workflow.get("nodes", [])]


def _check_types(
    types: List[str],
    must_have: Optional[List[str]] = None,
    forbidden: Optional[List[str]] = None,
    min_nodes: int = 0,
) -> Optional[str]:
    must_have = must_have or []
    forbidden = forbidden or []
    for t in must_have:
        if t not in types:
            return f"missing node type: {t} (got {types})"
    for t in forbidden:
        if t in types:
            return f"forbidden node type present: {t}"
    if min_nodes and len(types) < min_nodes:
        return f"expected >={min_nodes} nodes, got {len(types)}"
    return None


def run_intent_subtype_cases(report: MatrixReport) -> None:
    bulk_extended = generate_bulk_subtype_samples(start_id=100, count=100)
    all_cases = INTENT_SUBTYPE_CASES + BULK_SUBTYPE_SAMPLES + bulk_extended
    for case in all_cases:
        t0 = time.perf_counter()
        cid = case["id"]
        msg = case["message"]
        err_parts: List[str] = []

        if "subtype" in case:
            got_sub = detect_workflow_subtype(msg)
            if got_sub != case["subtype"]:
                err_parts.append(f"subtype: want {case['subtype']}, got {got_sub}")

        if "intent" in case:
            got_int = analyze_intent(msg).get("intent")
            if got_int != case["intent"]:
                err_parts.append(f"intent: want {case['intent']}, got {got_int}")

        report.results.append(
            CaseResult(
                case_id=cid,
                category="intent_subtype",
                passed=not err_parts,
                detail="; ".join(err_parts) or "ok",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )


def run_generation_cases(report: MatrixReport) -> None:
    svc = _offline_service()
    for case in GENERATION_CASES:
        t0 = time.perf_counter()
        cid = case["id"]
        desc = case["description"]

        with patch.object(svc, "_resolve_model", return_value=None):
            wf = svc.generate_workflow(desc)

        types = _node_types(wf)
        err = _check_types(
            types,
            must_have=case.get("must_have_types"),
            forbidden=case.get("must_not_have_types"),
            min_nodes=case.get("min_nodes", 0),
        )
        if "error" in wf:
            err = wf.get("error", "unknown error")

        report.results.append(
            CaseResult(
                case_id=cid,
                category="generation",
                passed=err is None,
                detail=err or f"nodes={len(types)} types={types[:5]}...",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )


def _run_flow_turn(
    svc: NLToWorkflowService,
    prior_msgs: List[Dict[str, str]],
    turn: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute one dialogue turn; returns service response dict."""
    mode = turn.get("mode", "chat")
    action = turn.get("action", "chat_only")
    content = turn["content"]

    if action == "chat_only":
        with patch.object(svc, "_resolve_model", return_value=None):
            return svc._handle_chat_intent(prior_msgs, content, None)

    with patch.object(svc, "_resolve_model", return_value=None):
        return svc.continue_conversation(prior_msgs, content, None, mode=mode)


def run_dialogue_flows(report: MatrixReport) -> None:
    svc = _offline_service()
    for flow in DIALOGUE_FLOWS:
        t0 = time.perf_counter()
        cid = flow["id"]
        expect = flow.get("expect", {})
        err: Optional[str] = None
        last_resp: Dict[str, Any] = {}
        workflow: Optional[Dict] = None

        try:
            turns = flow["turns"]
            prior_msgs: List[Dict[str, str]] = []
            last_resp = {}

            for i, turn in enumerate(turns):
                if turn.get("role") == "assistant":
                    prior_msgs.append({"role": "assistant", "content": turn["content"]})
                    continue

                is_last = i == len(turns) - 1
                if is_last:
                    run_turn = turn
                else:
                    run_turn = {**turn, "action": "chat_only", "mode": "chat"}

                last_resp = _run_flow_turn(svc, prior_msgs, run_turn)
                prior_msgs.append({"role": "user", "content": turn["content"]})
                if last_resp.get("message") and not is_last:
                    prior_msgs.append({"role": "assistant", "content": last_resp["message"]})

            workflow = last_resp.get("workflow")

            if expect.get("no_workflow"):
                if workflow and workflow.get("nodes"):
                    err = "expected no workflow"
            else:
                types = _node_types(workflow)
                err = _check_types(
                    types,
                    must_have=expect.get("must_have_types"),
                    forbidden=expect.get("forbidden_types"),
                    min_nodes=expect.get("min_nodes", 0),
                )

            if expect.get("ready_to_generate") is False:
                if last_resp.get("ready_to_generate"):
                    err = err or "expected ready_to_generate=False"

            if expect.get("chat_contains_any"):
                msg = last_resp.get("message", "")
                if not any(k in msg for k in expect["chat_contains_any"]):
                    err = err or f"chat missing keywords {expect['chat_contains_any']}"

        except Exception as exc:
            err = str(exc)

        report.results.append(
            CaseResult(
                case_id=cid,
                category="dialogue_flow",
                passed=err is None,
                detail=err or flow.get("title", "ok"),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )


def run_utility_cases(report: MatrixReport) -> None:
    """Extra rule-based checks."""
    checks = [
        ("UTIL-GEN-01", is_generate_command("现在就生成工作流"), True),
        ("UTIL-GEN-02", is_generate_command("你好"), False),
        ("UTIL-YOLO-01", is_yolo_detection_intent("YOLO 训练 数据集"), True),
        ("UTIL-YOLO-02", is_yolo_detection_intent("检测表单字段"), False),
        (
            "UTIL-YOLO-03",
            has_sufficient_yolo_detail("YOLO 数据集 训练 30 epoch 建站 网站"),
            True,
        ),
        (
            "UTIL-DET-01",
            has_sufficient_workflow_detail("定时 webhook 触发，读取 CSV 输入，LLM 处理后邮件输出"),
            True,
        ),
    ]
    for cid, got, want in checks:
        report.results.append(
            CaseResult(
                case_id=cid,
                category="utility",
                passed=got == want,
                detail=f"got={got} want={want}",
            )
        )

    msg, ready, _ = yolo_chat_fallback_response([], "我想做 yolo")
    report.results.append(
        CaseResult(
            case_id="UTIL-YOLO-CHAT",
            category="utility",
            passed=bool(msg) and not ready,
            detail=f"ready={ready} len={len(msg)}",
        )
    )


def run_mock_routing_cases(report: MatrixReport) -> None:
    """Verify get_mock_workflow routes to correct template family."""
    routes = [
        ("MOCK-Y01", "yolo 训练 数据集 网站", ["yolo_training"]),
        ("MOCK-Q01", "问答机器人 FAQ", ["llm"]),
        ("MOCK-E01", "send email smtp 通知", ["email"]),
        ("MOCK-D01", "csv 数据清洗 etl", ["tool"]),
    ]
    for cid, desc, must in routes:
        wf = get_mock_workflow(desc)
        types = _node_types(wf)
        err = _check_types(types, must_have=must)
        report.results.append(
            CaseResult(
                case_id=cid,
                category="mock_routing",
                passed=err is None,
                detail=err or str(types),
            )
        )


def _unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and "code" in payload:
        return payload["data"]
    return payload


def _api_call(method, path, token=None, payload=None, timeout=120):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, _unwrap(json.loads(body) if body else {})


def run_live_api_smoke(report: MatrixReport) -> None:
    """Optional: hit real API for 3 representative dialogue paths."""
    try:
        status, data = _api_call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
        token = data.get("access") if isinstance(data, dict) else None
        if not token:
            report.results.append(
                CaseResult("API-LOGIN", "live_api", False, f"login failed {status}")
            )
            return
    except (urllib.error.URLError, TimeoutError) as exc:
        report.results.append(
            CaseResult("API-LOGIN", "live_api", False, f"backend unreachable: {exc}")
        )
        return

    api_flows = [
        {
            "id": "API-YOLO-01",
            "first": "我想做 YOLO 目标检测，有数据集，训练后生成网站。现在就生成工作流",
            "mode": "chat",
        },
        {
            "id": "API-QA-01",
            "first": "做一个 FAQ 问答机器人，用户提问 LLM 回答。现在就生成工作流",
            "mode": "chat",
        },
        {
            "id": "API-EMAIL-01",
            "first": "订单完成自动发邮件通知客户 smtp。现在就生成工作流",
            "mode": "chat",
        },
    ]

    for af in api_flows:
        t0 = time.perf_counter()
        try:
            status2, preview = _api_call(
                "POST",
                "/nl-workflow/preview/",
                token=token,
                payload={"description": af["first"]},
                timeout=120,
            )
            wf = preview.get("workflow_json") or preview.get("workflow") or {}
            types = _node_types(wf)
            err = None
            if af["id"].startswith("API-YOLO") and "yolo_training" not in types:
                err = f"expected yolo_training, got {types}"
            if af["id"].startswith("API-QA") and "llm" not in types:
                err = f"expected llm, got {types}"
            if af["id"].startswith("API-EMAIL") and "email" not in types:
                err = f"expected email, got {types}"

            report.results.append(
                CaseResult(
                    case_id=af["id"],
                    category="live_api",
                    passed=err is None and status2 == 200,
                    detail=err or f"nodes={len(types)} types={types[:4]}",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            )
        except Exception as exc:
            report.results.append(
                CaseResult(af["id"], "live_api", False, str(exc))
            )


def write_report(report: MatrixReport, path: Path) -> None:
    lines = [
        "# NL2WF Dialogue Matrix E2E Report",
        "",
        f"- **Date**: {datetime.now().isoformat(timespec='seconds')}",
        f"- **Total**: {report.total}",
        f"- **Passed**: {report.passed}",
        f"- **Failed**: {report.failed}",
        f"- **Pass rate**: {report.passed / report.total * 100:.1f}%" if report.total else "-",
        "",
        "## Summary by category",
        "",
    ]
    cats: Dict[str, List[CaseResult]] = {}
    for r in report.results:
        cats.setdefault(r.category, []).append(r)
    for cat, items in sorted(cats.items()):
        p = sum(1 for i in items if i.passed)
        lines.append(f"- **{cat}**: {p}/{len(items)} passed")

    lines.extend(["", "## Failures", ""])
    failures = [r for r in report.results if not r.passed]
    if not failures:
        lines.append("_None_")
    else:
        for f in failures:
            lines.append(f"- `{f.case_id}` ({f.category}): {f.detail}")

    lines.extend(["", "## All results", "", "| ID | Category | Pass | Detail | ms |", "|---|---|---|---|---|"])
    for r in report.results:
        mark = "PASS" if r.passed else "FAIL"
        detail = (r.detail or "").replace("|", "\\|")[:80]
        lines.append(f"| {r.case_id} | {r.category} | {mark} | {detail} | {r.duration_ms:.0f} |")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="NL2WF dialogue matrix E2E")
    parser.add_argument("--live-api", action="store_true", help="Run live API smoke tests")
    args = parser.parse_args()

    report = MatrixReport()
    print("Running intent/subtype matrix...")
    run_intent_subtype_cases(report)
    print("Running mock generation cases...")
    run_generation_cases(report)
    print("Running multi-turn dialogue flows...")
    run_dialogue_flows(report)
    print("Running utility + mock routing...")
    run_utility_cases(report)
    run_mock_routing_cases(report)

    if args.live_api:
        print("Running live API smoke...")
        run_live_api_smoke(report)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"NL2WF_DIALOGUE_MATRIX_{ts}.md"
    write_report(report, report_path)

    print(f"\n=== NL2WF Dialogue Matrix: {report.passed}/{report.total} PASSED ===")
    if report.failed:
        print("Failures:")
        for r in report.results:
            if not r.passed:
                print(f"  - {r.case_id}: {r.detail}")
    print(f"Report: {report_path}")

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
