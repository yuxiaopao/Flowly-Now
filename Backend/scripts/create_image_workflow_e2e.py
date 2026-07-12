#!/usr/bin/env python
"""Create and smoke-test image generation workflow; prints workflow id."""
import json
import os
import sys
import uuid
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
EMAIL = "nlwftest@flowly.test"
PASSWORD = "Test123456!"


def req(method, path, token=None, data=None, timeout=300):
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
            return resp.status, parsed.get("data", parsed)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw).get("data", json.loads(raw))
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return e.code, payload


def main():
    _, login = req("POST", "/auth/login/", data={"username": EMAIL, "password": PASSWORD})
    token = login["access"]

    specs = [
        ("start", "开始", {}),
        ("input", "提示词输入", {"input_name": "prompt", "placeholder": "描述你想生成的图片…"}),
        (
            "image_generation",
            "文生图",
            {
                "provider": "openai",
                "model": "dall-e-3",
                "prompt": "{prompt}",
                "size": "1024x1024",
            },
        ),
        ("output", "图片输出", {"template": "{input}", "format": "image"}),
        ("end", "结束", {}),
    ]

    nodes, edges, ids = [], [], []
    x = 100
    for i, (ntype, label, config) in enumerate(specs):
        nid = f"n{i}_{uuid.uuid4().hex[:6]}"
        ids.append(nid)
        nodes.append(
            {
                "id": nid,
                "type": ntype,
                "data": {"label": label, "config": config},
                "position": {"x": x, "y": 200},
                "config": config,
            }
        )
        x += 240

    for i in range(len(ids) - 1):
        edges.append({"id": f"e{i}", "source": ids[i], "target": ids[i + 1], "label": ""})

    cst, wf = req(
        "POST",
        "/workflows/",
        token,
        {
            "name": f"E2E-文生图-{uuid.uuid4().hex[:6]}",
            "status": "draft",
            "nodes": nodes,
            "edges": edges,
        },
    )
    if cst != 201:
        print(json.dumps({"ok": False, "error": f"create failed {cst}", "detail": wf}, ensure_ascii=False))
        sys.exit(1)

    wf_id = wf["id"]
    tst, tex = req(
        "POST",
        f"/workflows/{wf_id}/execute/",
        token,
        {
            "input_data": {
                "prompt": "一只可爱的橘猫坐在窗台上",
                "user_input": "一只可爱的橘猫坐在窗台上",
            },
            "is_async": False,
        },
    )

    exec_id = (tex or {}).get("execution_id")
    detail = tex
    if exec_id:
        _, detail = req("GET", f"/workflows/executions/{exec_id}/", token)

    node_status = (detail or {}).get("node_status") or {}
    image_url = ""
    for value in node_status.values():
        if not isinstance(value, dict):
            continue
        output = value.get("output") or {}
        if isinstance(output, dict):
            images = output.get("images") or []
            if images and isinstance(images[0], dict) and images[0].get("url"):
                image_url = images[0]["url"]
                break

    completed = sum(
        1 for v in node_status.values() if isinstance(v, dict) and v.get("status") == "completed"
    )
    result = {
        "ok": (detail or {}).get("status") == "completed" and completed >= 5 and bool(image_url),
        "workflow_id": wf_id,
        "status": (detail or {}).get("status"),
        "nodes_completed": f"{completed}/5",
        "image_url": image_url[:120] if image_url else "",
        "error": (detail or {}).get("error_message"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
