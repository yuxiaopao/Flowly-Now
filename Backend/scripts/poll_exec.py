#!/usr/bin/env python
"""Poll workflow execution until complete."""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
EXEC_ID = sys.argv[1] if len(sys.argv) > 1 else open(r"e:\Flowly-now\.trae\nl2mm_exec_id.txt").read().strip()
OUT = r"e:\Flowly-now\.trae\nl2mm_exec_result.json"


def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def api(method, path, token=None, payload=None, timeout=60):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return unwrap(json.loads(resp.read().decode()))


def main():
    token = api(
        "POST",
        "/auth/login/",
        payload={"username": "nlwftest@flowly.test", "password": "Test123456!"},
    )["access"]
    for i in range(120):
        detail = api("GET", f"/workflows/executions/{EXEC_ID}/", token=token)
        status = detail.get("status")
        node_status = detail.get("node_status") or {}
        done = sum(
            1
            for info in node_status.values()
            if isinstance(info, dict) and info.get("status") == "completed"
        )
        print(f"[{i * 15}s] status={status} completed={done}/6")
        if status in ("completed", "failed"):
            variables = (detail.get("output_data") or {}).get("variables") or {}
            images = variables.get("images") or []
            videos = variables.get("videos") or []
            print("prompt", variables.get("prompt"))
            if images:
                first = images[0]
                print("image", first.get("url") if isinstance(first, dict) else first)
            if videos:
                first = videos[0]
                print("video", first.get("url") if isinstance(first, dict) else first)
            with open(OUT, "w", encoding="utf-8") as fh:
                json.dump(detail, fh, ensure_ascii=False, indent=2)
            return 0 if status == "completed" else 1
        time.sleep(15)
    print("TIMEOUT")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
