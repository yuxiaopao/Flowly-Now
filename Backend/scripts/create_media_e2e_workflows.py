#!/usr/bin/env python
"""Create audio/chart E2E workflows; prints JSON with workflow ids."""
import json
import sys
import uuid
import urllib.error
import urllib.request

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))

BASE = "http://127.0.0.1:8000/api/v1"
EMAIL = "nlwftest@flowly.test"
PASSWORD = "Test123456!"


def req(method, path, token=None, data=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=120) as resp:
        raw = resp.read().decode()
        return json.loads(raw).get("data", json.loads(raw) if raw else {})


def build_workflow(name, specs):
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
    return req("POST", "/workflows/", token, {"name": name, "status": "draft", "nodes": nodes, "edges": edges})


token = req("POST", "/auth/login/", None, {"username": EMAIL, "password": PASSWORD})["access"]

audio_wf = build_workflow(
    f"E2E-audio-{uuid.uuid4().hex[:6]}",
    [
        ("start", "开始", {}),
        ("input", "文本输入", {"input_name": "text", "placeholder": "输入要合成的文本…"}),
        ("audio_generation", "语音合成", {"provider": "openai", "model": "tts-1", "text": "{text}"}),
        ("output", "音频输出", {"template": "{input}", "format": "audio"}),
        ("end", "结束", {}),
    ],
)

chart_wf = build_workflow(
    f"E2E-chart-{uuid.uuid4().hex[:6]}",
    [
        ("start", "开始", {}),
        (
            "code",
            "图表数据",
            {
                "code": (
                    "output = {'labels': ['一月', '二月', '三月'], "
                    "'values': [12, 28, 19], 'title': '月度统计'}"
                ),
            },
        ),
        ("output", "图表展示", {"template": "{input}", "format": "chart"}),
        ("end", "结束", {}),
    ],
)

print(json.dumps({"audio_id": audio_wf["id"], "chart_id": chart_wf["id"]}, ensure_ascii=False))
