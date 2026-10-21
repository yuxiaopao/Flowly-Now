# -*- coding: utf-8 -*-
"""Generate + validate a large intelligent wuxia story→image→video workflow via live API."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
OUT = r"E:\Flowly-now\test-reports\wuxia_epic_workflow.json"

DESCRIPTION = """
请根据以下需求，自主设计一个完整可执行的「武侠长篇剧情工业化流水线」工作流（不要套用任何固定死模板整图复制）：

主题：创作一部原创武侠短篇剧情，并产出配套分镜图与最终视频。

阶段要求（结构由你自主设计节点与连线，可拆分子流程，允许并行）：
1) 世界观与人物设定：时代背景、门派势力、主角/反派人设、核心矛盾、爽点与伏笔。
2) 分章剧情写作：至少输出 5 个剧情段落（起、承、转、合、终），每段含场景、对白要点、动作场面描述。
3) 分镜脚本：把每段剧情拆成若干镜头（镜号、景别、画面描述、情绪、时长建议）。
4) 文生图：按分镜批量生成关键帧画面（主角亮相、对决、决战、收束等），提示词要可直接用于图像模型。
5) 图生视频/镜头动画：把关键帧扩展为短视频片段，并保留镜头顺序。
6) 旁白/字幕：根据剧情生成旁白文案与字幕时间轴要点。
7) 成片合成：汇总分镜图、视频片段、旁白/字幕，输出一部可播放的完整剧情成片结果（允许给出合成节点与最终输出节点）。

约束：
- 必须是智能生成的完整图，节点类型使用平台已有能力（LLM、提示词、图像生成、视频生成、代码/变量/输出等按需组合）。
- provider/model 仅在缺省时给合理默认，不要强行 dashscope。
- 节点命名语义清晰，边连接完整，从 start 到 end 可走通。
- 输出节点要能拿到：完整剧本文本、分镜列表、关键帧图、视频片段、最终成片说明。
"""


def unwrap(payload):
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload


def req(method, path, token=None, body=None, timeout=300):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status, unwrap(json.loads(resp.read().decode() or "{}"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:800]}
        return e.code, unwrap(payload)


def summarize_workflow(wf: dict) -> dict:
    nodes = wf.get("nodes") or []
    edges = wf.get("edges") or []
    types = {}
    for n in nodes:
        t = (n.get("type") or "unknown").lower()
        types[t] = types.get(t, 0) + 1
    return {
        "name": wf.get("name"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": types,
        "node_names": [n.get("name") for n in nodes],
        "is_intelligent": wf.get("_is_intelligent"),
        "generation_mode": wf.get("_generation_mode"),
        "llm_model": wf.get("_llm_model"),
        "agent_validation": wf.get("_agent_validation"),
        "intelligence_note": wf.get("_intelligence_note"),
    }


def main():
    st, login = req("POST", "/auth/login/", body={"username": "nlwftest", "password": "Test123456!"})
    token = (login or {}).get("access")
    if not token:
        print("LOGIN_FAIL", st, login)
        return 1
    print("LOGIN_OK")

    # Prefer sync generate for reliability of metadata; long timeout for large graph
    print("GENERATING...")
    st, sync = req(
        "POST",
        "/nl-workflow/sessions/",
        token=token,
        body={
            "description": DESCRIPTION.strip(),
            "name": "武侠剧情工业化流水线",
            "mode": "generate",
        },
        timeout=360,
    )
    wf = (sync or {}).get("workflow_json") or (sync or {}).get("workflow") or {}
    sid = (sync or {}).get("session_id")
    summary = summarize_workflow(wf) if wf else {}
    print("SYNC", st, json.dumps(summary, ensure_ascii=False))

    # If empty, try async + poll
    if not (wf.get("nodes") or []):
        print("SYNC_EMPTY_TRY_ASYNC")
        st, async_resp = req(
            "POST",
            "/nl-workflow/sessions/",
            token=token,
            body={
                "description": DESCRIPTION.strip(),
                "name": "武侠剧情工业化流水线-async",
                "mode": "generate",
                "async": True,
            },
            timeout=60,
        )
        sid = async_resp.get("session_id")
        for i in range(80):
            time.sleep(4)
            st, task = req("GET", f"/nl-workflow/sessions/{sid}/task/", token=token, timeout=30)
            n = len((task.get("workflow_json") or {}).get("nodes") or [])
            print(f"poll[{i}] {task.get('status')} celery={task.get('celery_state')} nodes={n}")
            if task.get("status") in ("completed", "failed"):
                sync = task
                wf = task.get("workflow_json") or {}
                summary = summarize_workflow(wf)
                break

    # One intelligent refine pass: strengthen video/storyboard coverage if thin
    refine_msg = (
        "请在不套用死模板的前提下强化工作流：确保覆盖"
        "世界观设定、分章写作、分镜脚本、文生图、图生视频、旁白字幕、成片输出；"
        "补齐缺失阶段节点与连线，保持可执行。"
    )
    if sid and (wf.get("nodes") or []):
        print("REFINING...")
        st, refined = req(
            "POST",
            f"/nl-workflow/sessions/{sid}/message/",
            token=token,
            body={"message": refine_msg, "mode": "editor", "workflow": wf},
            timeout=300,
        )
        rw = refined.get("workflow") or refined.get("workflow_json")
        if rw and rw.get("nodes"):
            wf = rw
            summary = summarize_workflow(wf)
            print("REFINED", json.dumps({
                "intent": refined.get("intent"),
                "changes": refined.get("changes"),
                "summary": summary,
            }, ensure_ascii=False))
        else:
            print("REFINE_NO_WF", st, (refined.get("message") or "")[:200])

    # Confirm save
    wid = None
    if sid and (wf.get("nodes") or []):
        # ensure session has latest workflow
        # confirm uses session.workflow_json
        st, confirmed = req("POST", f"/nl-workflow/sessions/{sid}/confirm/", token=token, timeout=60)
        wid = confirmed.get("workflow_id") or confirmed.get("id")
        print("CONFIRM", st, wid)

    report = {
        "session_id": sid,
        "workflow_id": wid,
        "summary": summary,
        "passes": {
            "has_nodes": bool(wf.get("nodes")),
            "intelligent": wf.get("_is_intelligent") is True,
            "not_offline_template": wf.get("_generation_mode") != "offline_template",
            "has_llm_and_media_types": bool(
                set((summary.get("node_types") or {}).keys())
                & {"llm", "image_generation", "video_generation", "prompt", "output", "code", "variable", "input"}
            ),
            "saved": bool(wid),
        },
        "workflow": {
            "name": wf.get("name"),
            "description": wf.get("description"),
            "nodes": wf.get("nodes"),
            "edges": wf.get("edges"),
            "_is_intelligent": wf.get("_is_intelligent"),
            "_generation_mode": wf.get("_generation_mode"),
            "_llm_model": wf.get("_llm_model"),
            "_agent_validation": wf.get("_agent_validation"),
        },
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("WROTE", OUT)
    ok = all([
        report["passes"]["has_nodes"],
        report["passes"]["intelligent"],
        report["passes"]["not_offline_template"],
        report["passes"]["saved"],
    ])
    print("OVERALL", "PASS" if ok else "FAIL", report["passes"])
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
