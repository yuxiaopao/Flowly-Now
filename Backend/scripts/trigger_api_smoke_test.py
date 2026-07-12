#!/usr/bin/env python
"""Quick smoke test for workflow trigger CRUD API."""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from workflow_all_nodes_test import TRANSLATION_WF, api_req, login

token = login()
assert token, "login failed"

# list
st, data = api_req("GET", "/workflows/triggers/", token, {"workflow_id": TRANSLATION_WF})
print("list", st, "count", (data or {}).get("count"), "results", len((data or {}).get("results") or []))

# create manual trigger
payload = {
    "name": f"smoke-trigger-{uuid.uuid4().hex[:6]}",
    "description": "API smoke test",
    "trigger_type": "manual",
    "is_enabled": True,
    "config": {"max_executions": 0, "input_mappings": []},
}
st, created = api_req("POST", f"/workflows/{TRANSLATION_WF}/triggers/", token, payload)
print("create", st, json.dumps(created, ensure_ascii=False)[:800])
if st not in (200, 201):
    raise SystemExit(1)

trigger_id = created.get("id")
st, updated = api_req(
    "PATCH",
    f"/workflows/triggers/{trigger_id}/",
    token,
    {"description": "updated by smoke test"},
)
print("patch", st, (updated or {}).get("description"))

st, _ = api_req("DELETE", f"/workflows/triggers/{trigger_id}/", token)
print("delete", st)
print("TRIGGER API OK")
