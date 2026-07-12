#!/usr/bin/env python
"""Comprehensive workflow node execution tests (direct + API workflow)."""
import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from workflows.services.langchain_service import LangChainService

BASE = "http://127.0.0.1:8000/api/v1"
EMAIL = "nlwftest@flowly.test"
PASSWORD = "Test123456!"
TRANSLATION_WF = "58711b23-2968-4572-b065-a4d25cdff3e4"

BASE_CTX = {
    "input_data": {"user_input": "hello", "text": "hello"},
    "variables": {"flag": True, "greeting": "hi", "payload": {"a": 1, "b": 2}},
    "node_outputs": {},
    "metadata": {},
}

# (node_type, config, context_override, require_success, require_output_keys)
DIRECT_CASES = [
    ("input", {"input_name": "user_input"}, {"input_data": {"user_input": "test"}}, True, None),
    ("output", {"template": "{greeting}"}, {"variables": {"greeting": "ok"}}, True, ["result"]),
    ("variable", {"assignments": [{"name": "x", "value": "1", "source": "static", "type": "number"}]}, {}, True, None),
    ("delay", {"seconds": 1}, {}, True, None),
    ("code", {"code": "output = {'sum': 3}"}, {}, True, None),
    ("condition", {"condition_expression": "{{flag}} == true"}, {}, True, None),
    ("data_transform", {"transform_type": "pick", "source_path": "payload", "fields": ["a"]}, {}, True, None),
    ("http_request", {"method": "GET", "url": "https://example.com", "timeout": 20}, {}, True, None),
    ("prompt", {"template": "Say hi to {input}", "model": ""}, {"variables": {"input": "world"}}, True, None),
    ("llm", {"model": "qwen3:1.7b", "user_template": "Reply with one word: {input}"}, {"variables": {"input": "ping"}}, True, ["text"]),
    ("loop", {"loop_type": "for_each", "items_path": "items", "max_iterations": 3}, {"variables": {"items": [1, 2]}}, True, None),
    ("switch", {"branches": [{"field": "greeting", "operator": "equals", "value": "hi", "label": "yes"}], "defaultBranch": "no"}, {}, True, None),
    ("merge", {"mode": "combine"}, {"items": [{"a": 1}, {"b": 2}]}, True, None),
    ("filter", {"conditions": [{"field": "value", "operator": "equals", "value": "1"}], "combineMode": "and"}, {"items": [{"value": "1"}, {"value": "2"}]}, True, None),
    ("split", {"batch_size": 2}, {"items": [1, 2, 3, 4]}, True, None),
    ("set", {"fields": [{"name": "k", "value": "v"}]}, {}, True, None),
    ("datetime", {"operation": "now"}, {}, True, None),
    ("json_transform", {"operation": "map", "schema": {"mappings": {"out": "a"}}}, {"data": {"a": 1}}, True, None),
    ("json_parser", {"action": "parse", "source_key": "input"}, {"input": '{"name":"flowly"}'}, True, None),
    ("text_template", {"template": "Hi {{name}}"}, {"variables": {"name": "world"}}, True, None),
    ("csv_transform", {"operation": "filter", "params": {"column": "x", "value": 1, "operator": "=="}}, {"data": [{"x": 1}, {"x": 2}]}, True, None),
    ("tool", {"tool": "calculator", "parameters": {"expression": "1+2"}}, {}, True, None),
    ("memory", {"memoryType": "buffer", "maxItems": 10}, {"operation": "read"}, True, None),
    ("agent", {"model": "qwen3:1.7b", "prompt": "Say ok"}, {"input": "go"}, True, None),
    ("planner", {"model": "qwen3:1.7b", "task": "plan test"}, {}, True, None),
    ("executor", {"model": "qwen3:1.7b"}, {"plan": {"subtasks": [{"id": 1, "description": "step"}]}}, True, None),
    ("email", {"to": "test@example.com", "subject": "t", "body": "b"}, {}, False, None),
    ("redis", {"operation": "get", "key": "test"}, {}, False, None),
    ("slack", {"webhook_url": "", "message": "hi"}, {}, False, None),
    ("embedding", {"model": "qwen3:1.7b", "text": "hello"}, {}, False, None),
    ("document_loader", {"sourceType": "file", "path": __file__}, {}, True, None),
    ("file_reader", {"path": __file__}, {}, True, None),
    ("web_scraper", {"url": "https://example.com", "timeout": 15}, {}, True, None),
]

WORKFLOW_CASES = [
    ("input_output", [
        ("start", "Start", {}),
        ("input", "In", {"input_name": "msg"}),
        ("output", "Out", {"template": "{msg}"}),
        ("end", "End", {}),
    ], {"msg": "display-test", "text": "display-test"}),
    ("variable_output", [
        ("start", "Start", {}),
        ("variable", "Var", {"assignments": [{"name": "greeting", "value": "hello", "source": "static", "type": "string"}]}),
        ("output", "Out", {"template": "{greeting}"}),
        ("end", "End", {}),
    ], {}),
    ("code_output", [
        ("start", "Start", {}),
        ("code", "Code", {"code": "output = {'value': 42}"}),
        ("output", "Out", {"template": "{value}"}),
        ("end", "End", {}),
    ], {}),
    ("condition_output", [
        ("start", "Start", {}),
        ("variable", "V", {"assignments": [{"name": "flag", "value": "true", "source": "static", "type": "boolean"}]}),
        ("condition", "C", {"condition_expression": "{{flag}} == true"}),
        ("output", "Out", {"template": "yes"}),
        ("end", "End", {}),
    ], {}),
    ("delay_chain", [
        ("start", "Start", {}),
        ("delay", "D", {"seconds": 1}),
        ("output", "Out", {"template": "done"}),
        ("end", "End", {}),
    ], {}),
    ("http_output", [
        ("start", "Start", {}),
        ("http_request", "H", {"method": "GET", "url": "https://example.com", "timeout": 20}),
        ("end", "End", {}),
    ], {}),
    ("json_transform_chain", [
        ("start", "Start", {}),
        ("variable", "V", {"assignments": [{"name": "data", "value": '{"a":1}', "source": "static", "type": "object"}]}),
        ("json_transform", "J", {"operation": "map", "schema": {"mappings": {"out": "a"}}}),
        ("end", "End", {}),
    ], {}),
    ("set_datetime", [
        ("start", "Start", {}),
        ("set", "S", {"fields": [{"name": "k", "value": "v"}]}),
        ("datetime", "DT", {"operation": "now"}),
        ("end", "End", {}),
    ], {}),
    ("text_template_output", [
        ("start", "Start", {}),
        ("variable", "V", {"assignments": [{"name": "name", "value": "Flowly", "source": "static", "type": "string"}]}),
        ("text_template", "T", {"template": "Hello {{name}}"}),
        ("output", "Out", {"template": "{text}"}),
        ("end", "End", {}),
    ], {}),
]


def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and "code" in payload:
        return payload["data"]
    return payload


def api_req(method, path, token=None, data=None, timeout=120):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode()
            parsed = json.loads(raw) if raw else {}
            return resp.status, unwrap(parsed)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = unwrap(json.loads(raw))
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return e.code, payload


def login():
    st, data = api_req("POST", "/auth/login/", data={"username": EMAIL, "password": PASSWORD})
    if st != 200:
        raise RuntimeError(f"login failed: {data}")
    return data["access"]


def build_linear(specs):
    nodes, edges, ids = [], [], []
    x = 100
    for i, (ntype, nname, config) in enumerate(specs):
        nid = f"n{i}_{uuid.uuid4().hex[:6]}"
        ids.append(nid)
        nodes.append({"id": nid, "type": ntype, "data": {"label": nname, "config": config}, "position": {"x": x, "y": 200}, "config": config})
        x += 220
    for i in range(len(ids) - 1):
        edges.append({"id": f"e{i}", "source": ids[i], "target": ids[i + 1], "label": ""})
    return nodes, edges


def has_output(result, keys):
    if not keys:
        return bool(result.get("output"))
    out = result.get("output") or {}
    if not isinstance(out, dict):
        return bool(out)
    return any(out.get(k) not in (None, "") for k in keys)


def run_direct_tests(svc):
    results = []
    for ntype, config, ctx_over, require_success, out_keys in DIRECT_CASES:
        ctx = dict(BASE_CTX)
        ctx.update(ctx_over)
        if "variables" in ctx_over:
            ctx["variables"] = {**BASE_CTX["variables"], **ctx_over["variables"]}
        try:
            t0 = time.time()
            result = svc.execute_node(ntype, config, ctx, use_cache=False)
            elapsed = round(time.time() - t0, 2)
            ok = isinstance(result, dict) and result.get("success") is not False if require_success else isinstance(result, dict)
            if require_success and ok and out_keys:
                ok = has_output(result, out_keys)
            results.append({
                "case": f"direct:{ntype}",
                "ok": ok,
                "success": result.get("success") if isinstance(result, dict) else None,
                "error": result.get("error") if isinstance(result, dict) else str(result),
                "elapsed_s": elapsed,
            })
        except Exception as e:
            results.append({"case": f"direct:{ntype}", "ok": False, "error": str(e)})
    return results


def run_workflow_tests(token):
    results = []
    for name, specs, input_data in WORKFLOW_CASES:
        nodes, edges = build_linear(specs)
        cst, wf = api_req("POST", "/workflows/", token, {"name": f"allnodes-{name}-{uuid.uuid4().hex[:5]}", "status": "draft", "nodes": nodes, "edges": edges})
        if cst != 201:
            results.append({"case": f"wf:{name}", "ok": False, "error": f"create {cst}"})
            continue
        tst, tex = api_req("POST", f"/workflows/{wf['id']}/execute/", token, {"input_data": input_data, "is_async": False}, timeout=300)
        exec_id = (tex or {}).get("execution_id")
        detail = tex
        if exec_id:
            _, detail = api_req("GET", f"/workflows/executions/{exec_id}/", token)
        status = (detail or {}).get("status")
        node_status = (detail or {}).get("node_status") or {}
        completed_count = sum(1 for v in node_status.values() if isinstance(v, dict) and v.get("status") == "completed")
        total_nodes = len(specs)
        ok = tst == 200 and status == "completed" and completed_count >= total_nodes - 0  # start/end now tracked
        # verify output node if present
        out_text = ""
        for ns in node_status.values():
            out = (ns or {}).get("output") if isinstance(ns, dict) else None
            if isinstance(out, dict) and out.get("result"):
                out_text = str(out.get("result"))
        results.append({
            "case": f"wf:{name}",
            "ok": ok,
            "status": status,
            "nodes_completed": f"{completed_count}/{total_nodes}",
            "output_preview": out_text[:80],
            "error": (detail or {}).get("error_message"),
            "workflow_id": wf["id"],
        })

    # translation full chain
    tst, tex = api_req("POST", f"/workflows/{TRANSLATION_WF}/execute/", token, {"input_data": {"user_input": "你好", "text": "你好"}, "is_async": False}, timeout=300)
    exec_id = (tex or {}).get("execution_id")
    detail = {}
    if exec_id:
        _, detail = api_req("GET", f"/workflows/executions/{exec_id}/", token)
    ns = (detail or {}).get("node_status") or {}
    completed = sum(1 for v in ns.values() if isinstance(v, dict) and v.get("status") == "completed")
    llm_text = ""
    for v in ns.values():
        o = (v or {}).get("output") if isinstance(v, dict) else None
        if isinstance(o, dict) and o.get("text"):
            llm_text = o["text"]
    results.append({
        "case": "wf:translation_full",
        "ok": (detail or {}).get("status") == "completed" and completed >= 5 and len(llm_text.strip()) > 0,
        "nodes_completed": f"{completed}/5",
        "llm_preview": llm_text[:100],
        "error": (detail or {}).get("error_message"),
    })

    # image generation full chain (demo fallback when OpenAI key invalid)
    img_specs = [
        ("start", "开始", {}),
        ("input", "提示词", {"input_name": "prompt"}),
        ("image_generation", "文生图", {"provider": "openai", "model": "dall-e-3", "prompt": "{prompt}"}),
        ("output", "输出", {"template": "{input}", "format": "image"}),
        ("end", "结束", {}),
    ]
    img_nodes, img_edges = build_linear(img_specs)
    cst, img_wf = api_req("POST", "/workflows/", token, {"name": f"allnodes-image-{uuid.uuid4().hex[:5]}", "status": "draft", "nodes": img_nodes, "edges": img_edges})
    if cst != 201:
        results.append({"case": "wf:image_generation_full", "ok": False, "error": f"create {cst}"})
    else:
        tst, tex = api_req("POST", f"/workflows/{img_wf['id']}/execute/", token, {"input_data": {"prompt": "cute cat", "user_input": "cute cat"}, "is_async": False}, timeout=300)
        exec_id = (tex or {}).get("execution_id")
        detail = tex
        if exec_id:
            _, detail = api_req("GET", f"/workflows/executions/{exec_id}/", token)
        ns = (detail or {}).get("node_status") or {}
        completed = sum(1 for v in ns.values() if isinstance(v, dict) and v.get("status") == "completed")
        image_url = ""
        for v in ns.values():
            o = (v or {}).get("output") if isinstance(v, dict) else None
            if isinstance(o, dict):
                images = o.get("images") or []
                if images and isinstance(images[0], dict) and images[0].get("url"):
                    image_url = images[0]["url"]
                    break
        results.append({
            "case": "wf:image_generation_full",
            "ok": (detail or {}).get("status") == "completed" and completed >= 5 and bool(image_url),
            "nodes_completed": f"{completed}/5",
            "image_url": image_url[:80],
            "error": (detail or {}).get("error_message"),
        })

    def run_media_chain(case_name, specs, input_data, media_key):
        nodes, edges = build_linear(specs)
        cst, wf = api_req("POST", "/workflows/", token, {"name": f"allnodes-{case_name}-{uuid.uuid4().hex[:5]}", "status": "draft", "nodes": nodes, "edges": edges})
        if cst != 201:
            return {"case": case_name, "ok": False, "error": f"create {cst}"}
        tst, tex = api_req("POST", f"/workflows/{wf['id']}/execute/", token, {"input_data": input_data, "is_async": False}, timeout=300)
        exec_id = (tex or {}).get("execution_id")
        detail = tex
        if exec_id:
            _, detail = api_req("GET", f"/workflows/executions/{exec_id}/", token)
        ns = (detail or {}).get("node_status") or {}
        completed = sum(1 for v in ns.values() if isinstance(v, dict) and v.get("status") == "completed")
        media_url = ""
        for v in ns.values():
            o = (v or {}).get("output") if isinstance(v, dict) else None
            if not isinstance(o, dict):
                continue
            if o.get(media_key):
                media_url = str(o.get(media_key))
                break
            if media_key == "labels" and o.get("labels") and o.get("values"):
                media_url = "chart"
                break
            images = o.get("images") or []
            if images and isinstance(images[0], dict) and images[0].get("url"):
                media_url = images[0]["url"]
                break
        return {
            "case": case_name,
            "ok": (detail or {}).get("status") == "completed" and completed >= max(4, len(specs) - 1) and bool(media_url),
            "nodes_completed": f"{completed}/5",
            "media_url": media_url[:80],
            "error": (detail or {}).get("error_message"),
        }

    results.append(run_media_chain(
        "wf:video_generation_full",
        [
            ("start", "开始", {}),
            ("input", "脚本", {"input_name": "prompt"}),
            ("video_generation", "文生视频", {"provider": "replicate", "prompt": "{prompt}", "duration": 4}),
            ("output", "输出", {"template": "{input}", "format": "video"}),
            ("end", "结束", {}),
        ],
        {"prompt": "ocean waves", "user_input": "ocean waves"},
        "video_url",
    ))

    results.append(run_media_chain(
        "wf:audio_generation_full",
        [
            ("start", "开始", {}),
            ("input", "文本", {"input_name": "text"}),
            ("audio_generation", "语音合成", {"provider": "openai", "model": "tts-1", "text": "{text}"}),
            ("output", "输出", {"template": "{input}", "format": "audio"}),
            ("end", "结束", {}),
        ],
        {"text": "Hello world", "user_input": "Hello world"},
        "audio_url",
    ))

    results.append(run_media_chain(
        "wf:chart_output_full",
        [
            ("start", "开始", {}),
            ("code", "图表数据", {"code": "output = {'labels': ['一月', '二月', '三月'], 'values': [12, 28, 19], 'title': '月度统计'}"}),
            ("output", "图表输出", {"template": "{input}", "format": "chart"}),
            ("end", "结束", {}),
        ],
        {},
        "labels",
    ))

    return results


def main():
    print("=== Direct node executor tests ===")
    svc = LangChainService()
    direct = run_direct_tests(svc)
    print("=== API workflow tests ===")
    token = login()
    workflow = run_workflow_tests(token)
    all_results = direct + workflow
    failed = [r for r in all_results if not r.get("ok")]
    print(json.dumps(all_results, ensure_ascii=False, indent=2))
    print(f"\nSUMMARY: {len(all_results) - len(failed)}/{len(all_results)} passed")
    if failed:
        print("FAILED:", json.dumps(failed, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
