#!/usr/bin/env python
"""Agent + Knowledge Base + Team closed-loop E2E validation.

Flow: login → create team → invite (email) → shared KB with Ollama embedding
      → bind agents → multi-agent collaboration → team visibility → marketplace.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
DATE = datetime.now().strftime("%Y%m%d")
REPORT = REPO / "test-reports" / f"AGENT_KB_TEAM_E2E_{DATE}.md"

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")
OLLAMA_MODEL = os.environ.get("FLOWLY_E2E_OLLAMA_MODEL", "llama3.2:latest")

KB_DOC_CONTENT = """
Flowly 团队知识库测试文档 — AGI 协作闭环验证

核心产品能力：
1. Agent 智能体：支持工具调用、知识库检索、多轮对话调试。
2. 知识库 RAG：团队共享文档集合，使用 Ollama nomic-embed-text 本地向量化。
3. 团队协作：租户级资源共享，成员可查看/使用团队 Agent 与知识库。
4. 多智能体协作：Planner → Executor → Critic → Reporter 四角色编排。
5. Agent 市场：发布公开 Agent，其他用户可克隆复用。

本段内容用于验证知识库检索能否命中「多智能体协作」与「Agent 市场」关键词。
""".strip()

COLLAB_TASK = (
    "基于团队知识库，总结 Flowly 的三大核心能力，并说明多智能体协作如何帮助团队完成复杂任务。"
)


def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and "code" in payload:
        return payload["data"]
    return payload


def call(method, path, token=None, payload=None, timeout=300, expect=(200, 201, 202, 204)):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body) if body else None
            return resp.status, unwrap(parsed), resp.status in expect
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = unwrap(json.loads(body) if body else None)
        except json.JSONDecodeError:
            parsed = body[:500]
        return exc.code, parsed, exc.code in expect


def login():
    status, data, ok = call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
    if not ok or not isinstance(data, dict) or not data.get("access"):
        raise RuntimeError(f"login failed: {status} {data}")
    return data["access"]


def as_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("results") or data.get("items") or []
    return []


class E2ERunner:
    def __init__(self):
        self.steps: list[dict] = []
        self.token: str | None = None
        self.tenant_id: str | None = None
        self.collection_id: str | None = None
        self.agent_ids: list[str] = []
        self.collab_run_id: str | None = None
        self.marketplace_agent_id: str | None = None

    def record(self, name: str, ok: bool, detail: str = "", extra: dict | None = None):
        self.steps.append({"name": name, "ok": ok, "detail": detail, **(extra or {})})
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    def run(self):
        self.token = login()
        self.record("登录", True, EMAIL)

        self._step_create_team()
        self._step_invite_member()
        self._step_create_knowledge_base()
        self._step_create_agents()
        self._step_collaboration()
        self._step_team_visibility()
        self._step_marketplace()
        self._write_report()

        failed = [s for s in self.steps if not s["ok"]]
        if failed:
            print(f"\n{len(failed)} step(s) failed.")
            sys.exit(1)
        print(f"\nAll {len(self.steps)} steps passed. Report: {REPORT}")

    def _step_create_team(self):
        slug = f"agi-team-{uuid.uuid4().hex[:8]}"
        status, data, ok = call(
            "POST", "/tenants/tenants/",
            token=self.token,
            payload={
                "name": f"AGI协作团队 {slug}",
                "slug": slug,
                "description": "E2E 闭环测试团队",
                "billing_email": EMAIL,
            },
        )
        if ok and isinstance(data, dict) and data.get("id"):
            self.tenant_id = str(data["id"])
            self.record("创建团队", True, f"tenant_id={self.tenant_id}")
            return

        self.record("创建团队", False, f"{status} {data}")

    def _step_invite_member(self):
        if not self.tenant_id:
            self.record("邀请成员(邮件)", False, "无团队 ID")
            return
        invite_email = f"invite-{uuid.uuid4().hex[:6]}@flowly.test"
        status, data, ok = call(
            "POST", f"/tenants/tenants/{self.tenant_id}/invite/",
            token=self.token,
            payload={"email": invite_email, "role": "member"},
        )
        invitation_ok = isinstance(data, dict) and bool(data.get("invitation"))
        email_sent = isinstance(data, dict) and data.get("email_sent")
        self.record(
            "邀请成员(邮件)",
            ok and invitation_ok,
            f"email_sent={email_sent}, invitee={invite_email}",
            extra={"email_sent": email_sent},
        )

    def _ensure_vector_store(self):
        status, data, ok = call("GET", "/rag/vector-stores/", token=self.token)
        stores = as_list(data)
        if stores:
            return str(stores[0]["id"])

        status, data, ok = call(
            "POST", "/rag/vector-stores/",
            token=self.token,
            payload={
                "name": f"E2E Vector Store {uuid.uuid4().hex[:6]}",
                "store_type": "memory",
                "host": "localhost",
                "port": 0,
                "collection": f"e2e_{uuid.uuid4().hex[:8]}",
                "dimension": 768,
                "metric": "cosine",
                "is_default": True,
            },
        )
        if ok and isinstance(data, dict) and data.get("id"):
            return str(data["id"])
        return None

    def _step_create_knowledge_base(self):
        if not self.tenant_id:
            self.record("创建团队知识库", False, "无团队 ID")
            return

        vs_id = self._ensure_vector_store()
        if not vs_id:
            self.record("创建团队知识库", False, "无法创建向量存储")
            return

        coll_name = f"AGI-KB-{uuid.uuid4().hex[:6]}"
        status, data, ok = call(
            "POST", "/rag/collections/",
            token=self.token,
            payload={
                "name": coll_name,
                "description": "E2E 团队共享知识库",
                "vector_store": vs_id,
                "tenant": self.tenant_id,
                "embedding_model": "nomic-embed-text",
                "chunk_size": 500,
                "chunk_overlap": 50,
            },
        )
        if not ok or not isinstance(data, dict) or not data.get("id"):
            self.record("创建团队知识库", False, f"{status} {data}")
            return

        self.collection_id = str(data["id"])
        self.record("创建团队知识库", True, f"collection_id={self.collection_id}")

        status, data, ok = call(
            "POST", f"/rag/collections/{self.collection_id}/add_document/",
            token=self.token,
            payload={"title": "Flowly AGI 能力说明", "content": KB_DOC_CONTENT},
            timeout=120,
        )
        if ok:
            self.record("摄入知识库文档(Ollama embedding)", True, "文档已处理")
        else:
            self.record("摄入知识库文档(Ollama embedding)", False, f"{status} {data}")

        status, data, ok = call(
            "POST", "/rag/pipelines/",
            token=self.token,
            payload={
                "name": f"E2E Pipeline {uuid.uuid4().hex[:6]}",
                "collection": self.collection_id,
                "top_k": 3,
                "min_similarity": 0.0,
            },
        )
        pipeline_id = data.get("id") if isinstance(data, dict) else None
        if not pipeline_id:
            status, list_data, list_ok = call("GET", "/rag/pipelines/", token=self.token)
            items = as_list(list_data) if list_ok else []
            for item in reversed(items):
                if str(item.get("collection")) == self.collection_id:
                    pipeline_id = item.get("id")
                    break
        if pipeline_id:
            import urllib.parse
            q = urllib.parse.quote("多智能体协作")
            status, data, ok = call(
                "GET", f"/rag/pipelines/{pipeline_id}/retrieve/?query={q}",
                token=self.token,
                timeout=120,
            )
        hits = 0
        if isinstance(data, dict):
            hits = data.get("count") or len(data.get("results") or [])
        self.record("知识库检索验证", ok and hits > 0, f"hits={hits}")

    def _create_agent(self, name: str, role_prompt: str, tools: list):
        if not self.collection_id:
            return None
        status, data, ok = call(
            "POST", "/agents/",
            token=self.token,
            payload={
                "name": name,
                "description": f"E2E {name}",
                "agent_type": "conversational",
                "system_prompt": role_prompt,
                "model": OLLAMA_MODEL,
                "temperature": 0.3,
                "tools": tools,
                "knowledge_collections": [self.collection_id],
                "tenant": self.tenant_id,
                "is_active": True,
            },
        )
        if ok and isinstance(data, dict) and data.get("id"):
            return str(data["id"])
        return None

    def _step_create_agents(self):
        planner_id = self._create_agent(
            "E2E Planner",
            "你是规划专家，负责分解任务并制定执行计划。",
            ["knowledge_base"],
        )
        executor_id = self._create_agent(
            "E2E Executor",
            "你是执行专家，负责检索知识库并完成任务。",
            ["knowledge_base"],
        )
        self.agent_ids = [aid for aid in [planner_id, executor_id] if aid]
        ok = len(self.agent_ids) >= 2
        self.record("创建绑定知识库的 Agent", ok, f"agent_ids={self.agent_ids}")

    def _step_collaboration(self):
        if not self.tenant_id or not self.agent_ids:
            self.record("多智能体协作", False, "缺少团队或 Agent")
            return

        roles = []
        role_map = [("planner", 0), ("executor", 1), ("critic", None), ("reporter", None)]
        for role_name, idx in role_map:
            item = {"role": role_name}
            if idx is not None and idx < len(self.agent_ids):
                item["agent_id"] = self.agent_ids[idx]
            roles.append(item)

        status, data, ok = call(
            "POST", "/agents/collaborations/run/",
            token=self.token,
            payload={"task": COLLAB_TASK, "tenant": self.tenant_id, "roles": roles},
            timeout=360,
        )
        if ok and isinstance(data, dict):
            self.collab_run_id = str(data.get("id", ""))
            run_status = data.get("status", "")
            has_report = bool((data.get("final_report") or "").strip())
            trace_len = len(data.get("trace") or [])
            self.record(
                "多智能体协作",
                run_status == "completed" and (has_report or trace_len >= 3),
                f"status={run_status}, trace_steps={trace_len}, has_report={has_report}",
            )
        else:
            self.record("多智能体协作", False, f"{status} {str(data)[:300]}")

    def _step_team_visibility(self):
        if not self.tenant_id:
            self.record("团队页可见性", False, "无团队 ID")
            return

        checks = []
        for label, path in [
            ("团队知识库", f"/rag/collections/?tenant={self.tenant_id}"),
            ("团队 Agent", f"/agents/?tenant={self.tenant_id}"),
            ("协作记录", f"/agents/collaborations/?tenant={self.tenant_id}"),
        ]:
            status, data, ok = call("GET", path, token=self.token)
            count = len(as_list(data)) if ok else 0
            checks.append(ok and count > 0)
            self.record(f"团队可见性 — {label}", ok and count > 0, f"count={count}")

    def _step_marketplace(self):
        if not self.agent_ids:
            self.record("Agent 市场发布", False, "无 Agent")
            return

        agent_id = self.agent_ids[0]
        status, data, ok = call("POST", f"/agents/{agent_id}/publish/", token=self.token)
        self.record("Agent 市场发布", ok, f"agent_id={agent_id}")

        status, data, ok = call("GET", "/agents/marketplace/", token=self.token)
        items = as_list(data) if ok else []
        published = any(str(i.get("id")) == agent_id for i in items)
        self.record("市场浏览", ok and published, f"marketplace_count={len(items)}")

        status, data, ok = call("POST", f"/agents/{agent_id}/clone/", token=self.token)
        cloned_id = data.get("id") if isinstance(data, dict) else None
        self.marketplace_agent_id = str(cloned_id) if cloned_id else None
        self.record("市场克隆", ok and bool(cloned_id), f"cloned_id={cloned_id}")

    def _write_report(self):
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        passed = sum(1 for s in self.steps if s["ok"])
        failed = len(self.steps) - passed
        lines = [
            f"# Agent + 知识库 + 团队 闭环 E2E 报告",
            f"",
            f"- **日期**: {datetime.now().isoformat(timespec='seconds')}",
            f"- **测试用户**: {EMAIL}",
            f"- **Ollama 模型**: {OLLAMA_MODEL}",
            f"- **团队 ID**: {self.tenant_id or 'N/A'}",
            f"- **知识库 ID**: {self.collection_id or 'N/A'}",
            f"- **结果**: {passed}/{len(self.steps)} 通过",
            f"",
            f"## 步骤明细",
            f"",
            f"| 步骤 | 结果 | 详情 |",
            f"|------|------|------|",
        ]
        for s in self.steps:
            mark = "✅" if s["ok"] else "❌"
            lines.append(f"| {s['name']} | {mark} | {s.get('detail', '')} |")

        lines.extend([
            "",
            "## 闭环验证摘要",
            "",
            "1. **团队共享知识库** — DocumentCollection 绑定 tenant，成员可按租户过滤查看。",
            "2. **Agent 检索知识库** — knowledge_collections + knowledge_base 工具绑定。",
            "3. **多智能体协作** — Planner/Executor/Critic/Reporter 编排，继承 Agent 知识库配置。",
            "4. **团队可见性** — 团队页 Tab 对应 API 按 tenant 过滤返回数据。",
            "5. **Agent 市场** — publish → marketplace 浏览 → clone 克隆复用。",
            "",
            f"## 统计",
            f"- 通过: {passed}",
            f"- 失败: {failed}",
        ])
        if self.collab_run_id:
            lines.append(f"- 协作运行 ID: {self.collab_run_id}")
        if self.marketplace_agent_id:
            lines.append(f"- 克隆 Agent ID: {self.marketplace_agent_id}")

        REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    E2ERunner().run()
