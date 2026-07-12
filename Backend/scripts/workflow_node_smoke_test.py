#!/usr/bin/env python
"""Smoke test workflow nodes via API."""
import json
import sys
import time
import uuid
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
EMAIL = "nlwftest@flowly.test"
PASSWORD = "Test123456!"
TRANSLATION_WF = "58711b23-2968-4572-b065-a4d25cdff3e4"
TRANSLATION_INPUT = {"user_input": "你好，世界", "text": "你好，世界"}


def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and "code" in payload:
        return payload["data"]
    return payload


def req(method, path, token=None, data=None, timeout=120):
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
    status, data = req("POST", "/auth/login/", data={"username": EMAIL, "password": PASSWORD})
    if status != 200:
        raise RuntimeError(f"login failed {status}: {data}")
    return data["access"]


def poll_execution(token, execution_id, max_wait=180):
    deadline = time.time() + max_wait
    last = None
    while time.time() < deadline:
        status, data = req("GET", f"/workflows/executions/{execution_id}/status/", token=token)
        if status != 200:
            return status, data
        last = data
        if data.get("status") in ("completed", "failed", "cancelled"):
            break
        time.sleep(2)
    detail_status, detail = req("GET", f"/workflows/executions/{execution_id}/", token=token)
    return detail_status, detail if detail_status == 200 else last


def run_workflow(token, wf_id, input_data, is_async=False):
    status, data = req(
        "POST",
        f"/workflows/{wf_id}/execute/",
        token=token,
        data={"input_data": input_data, "is_async": is_async},
        timeout=300 if not is_async else 30,
    )
    if not isinstance(data, dict):
        return status, {"raw": data}
    if data.get("execution_id") and "id" not in data:
        data["id"] = data["execution_id"]
    return status, data


def create_node_test_workflow(token, name, nodes, edges):
    status, data = req(
        "POST",
        "/workflows/",
        token=token,
        data={"name": name, "description": "auto smoke test", "status": "draft", "nodes": nodes, "edges": edges},
    )
    return status, data


def build_linear_workflow(node_specs):
    """node_specs: list of (type, name, config)"""
    nodes = []
    edges = []
    ids = []
    x = 100
    for i, (ntype, nname, config) in enumerate(node_specs):
        nid = f"node_{i}_{uuid.uuid4().hex[:8]}"
        ids.append(nid)
        nodes.append(
            {
                "id": nid,
                "type": ntype,
                "data": {"label": nname, "config": config},
                "position": {"x": x, "y": 200},
                "config": config,
            }
        )
        x += 220
    for i in range(len(ids) - 1):
        edges.append({"id": f"edge_{i}", "source": ids[i], "target": ids[i + 1], "label": ""})
    return nodes, edges


def main():
    results = []
    token = login()
    print("OK login")

    # 1) Translation workflow sync
    t0 = time.time()
    st, ex = run_workflow(token, TRANSLATION_WF, TRANSLATION_INPUT, is_async=False)
    exec_id = (ex or {}).get("execution_id") or (ex or {}).get("id")
    detail = ex
    if exec_id:
        _, detail = req("GET", f"/workflows/executions/{exec_id}/", token=token)
    ok = st == 200 and (detail or {}).get("status") == "completed"
    llm_out = ""
    if ok:
        for ns in ((detail or {}).get("node_status") or {}).values():
            out = ns.get("output") if isinstance(ns, dict) else None
            if isinstance(out, dict) and out.get("text"):
                llm_out = str(out.get("text", ""))
                break
        if not llm_out:
            vars_ = ((detail or {}).get("output_data") or {}).get("variables") or {}
            llm_out = str(vars_.get("text", ""))
    results.append(
        {
            "case": "translation_sync",
            "ok": ok and len(llm_out.strip()) > 0,
            "status_code": st,
            "execution_status": (detail or {}).get("status"),
            "llm_preview": llm_out[:120],
            "elapsed_s": round(time.time() - t0, 2),
            "error": (detail or {}).get("error_message") if not ok else None,
        }
    )

    # 2) Translation workflow async + status poll
    t0 = time.time()
    st, ex = run_workflow(token, TRANSLATION_WF, {"user_input": "Hello async test", "text": "Hello async test"}, is_async=True)
    async_ok = st in (200, 202) and ex.get("id")
    poll_st, poll_data = (None, {})
    if async_ok:
        poll_st, poll_data = poll_execution(token, ex["id"], max_wait=180)
    async_completed = poll_st == 200 and poll_data.get("status") == "completed"
    results.append(
        {
            "case": "translation_async_status",
            "ok": async_ok and poll_st == 200 and async_completed,
            "execute_status_code": st,
            "poll_status_code": poll_st,
            "execution_status": poll_data.get("status") if isinstance(poll_data, dict) else None,
            "elapsed_s": round(time.time() - t0, 2),
            "poll_error": poll_data if poll_st != 200 else None,
        }
    )

    # 3) Per-node-type mini workflows
    node_cases = [
        (
            "delay",
            [("start", "Start", {}), ("delay", "Delay", {"seconds": 1}), ("end", "End", {})],
            {},
        ),
        (
            "variable",
            [
                ("start", "Start", {}),
                (
                    "variable",
                    "SetVar",
                    {"assignments": [{"name": "greeting", "value": "hi", "source": "static", "type": "string"}]},
                ),
                ("output", "Out", {"template": "{greeting}"}),
                ("end", "End", {}),
            ],
            {},
        ),
        (
            "code",
            [
                ("start", "Start", {}),
                ("code", "Code", {"language": "python", "code": "output = {'sum': 1 + 2}"}),
                ("output", "Out", {"template": "{sum}"}),
                ("end", "End", {}),
            ],
            {},
        ),
        (
            "condition_true",
            [
                ("start", "Start", {}),
                (
                    "variable",
                    "Flag",
                    {"assignments": [{"name": "flag", "value": "true", "source": "static", "type": "boolean"}]},
                ),
                ("condition", "Cond", {"condition_expression": "{{flag}} == true"}),
                ("output", "Out", {"template": "branch-ok"}),
                ("end", "End", {}),
            ],
            {},
        ),
        (
            "data_transform",
            [
                ("start", "Start", {}),
                (
                    "variable",
                    "Src",
                    {"assignments": [{"name": "payload", "value": '{"a": 1}', "source": "static", "type": "object"}]},
                ),
                ("data_transform", "Transform", {"transform_type": "pick", "source_path": "payload", "fields": ["a"]}),
                ("end", "End", {}),
            ],
            {},
        ),
        (
            "http",
            [
                ("start", "Start", {}),
                (
                    "http_request",
                    "HTTP",
                    {
                        "method": "GET",
                        "url": "https://httpbin.org/get",
                        "timeout": 15,
                    },
                ),
                ("end", "End", {}),
            ],
            {},
        ),
    ]

    for case_name, specs, input_data in node_cases:
        nodes, edges = build_linear_workflow(specs)
        cst, wf = create_node_test_workflow(token, f"smoke-{case_name}-{uuid.uuid4().hex[:6]}", nodes, edges)
        if cst != 201:
            results.append({"case": case_name, "ok": False, "error": f"create workflow {cst}: {wf}"})
            continue
        wf_id = wf["id"]
        tst, tex = run_workflow(token, wf_id, input_data, is_async=False)
        exec_id = (tex or {}).get("execution_id") or (tex or {}).get("id")
        detail = tex
        if exec_id:
            _, detail = req("GET", f"/workflows/executions/{exec_id}/", token=token)
        case_ok = tst == 200 and isinstance(detail, dict) and detail.get("status") == "completed"
        results.append(
            {
                "case": case_name,
                "ok": case_ok,
                "status_code": tst,
                "execution_status": (detail or {}).get("status") if isinstance(detail, dict) else None,
                "error_message": (detail or {}).get("error_message") if isinstance(detail, dict) else str(tex),
                "workflow_id": wf_id,
            }
        )

    failed = [r for r in results if not r.get("ok")]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nSUMMARY: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED:", json.dumps(failed, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
