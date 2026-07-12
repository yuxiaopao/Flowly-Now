#!/usr/bin/env python
"""Verify LLM gateway connectivity for E2E / CI."""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("FLOWLY_API_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")


def call(method, path, token=None, payload=None, timeout=120):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        parsed = json.loads(body) if body else None
        if isinstance(parsed, dict) and "code" in parsed and "data" in parsed:
            parsed = parsed["data"]
        return resp.status, parsed


def login():
    status, data = call("POST", "/auth/login/", payload={"username": EMAIL, "password": PASSWORD})
    if status != 200 or not isinstance(data, dict) or not data.get("access"):
        raise RuntimeError(f"login failed: {status} {data}")
    return data["access"]


def main():
    token = login()
    results = {"ok": False, "steps": []}

    try:
        status, models = call("GET", "/gateway/models/", token=token)
        model_list = models if isinstance(models, list) else (models.get("results") if isinstance(models, dict) else [])
        results["steps"].append({"name": "gateway-models", "status": status, "count": len(model_list or [])})
        if not model_list:
            print(json.dumps({"ok": False, "error": "no models available", "results": results}, ensure_ascii=False))
            return 1

        model_id = model_list[0].get("model_id") or model_list[0].get("modelId") or model_list[0].get("id") or model_list[0].get("name")
        provider_id = model_list[0].get("provider_slug") or model_list[0].get("providerSlug") or model_list[0].get("provider") or model_list[0].get("provider_id")
        results["steps"].append({"name": "selected-model", "model_id": model_id, "provider_id": provider_id})

        payload = {
            "messages": [{"role": "user", "content": "Reply with exactly: pong"}],
            "model": model_id,
            "max_tokens": 32,
        }
        if provider_id:
            payload["provider"] = provider_id

        status, chat = call(
            "POST",
            "/gateway/chat/",
            token=token,
            payload=payload,
            timeout=180,
        )
        results["steps"].append({"name": "gateway-chat", "status": status, "response_preview": str(chat)[:200]})
        results["ok"] = status == 200
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        results["error"] = f"HTTP {exc.code}: {body[:300]}"
    except Exception as exc:
        results["error"] = str(exc)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
