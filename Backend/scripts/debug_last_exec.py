import json, urllib.request, urllib.error
BASE = "http://127.0.0.1:8000/api/v1"

def call(m, p, t=None, payload=None, timeout=120):
    h = {"Content-Type": "application/json"}
    if t:
        h["Authorization"] = f"Bearer {t}"
    b = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(BASE + p, data=b, headers=h, method=m)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode()
            pld = json.loads(raw) if raw else {}
            return resp.status, pld.get("data", pld)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            p = json.loads(raw)
        except json.JSONDecodeError:
            p = {"raw": raw}
        return e.code, p

st, login = call("POST", "/auth/login/", payload={"username": "nlwftest@flowly.test", "password": "Test123456!"})
tok = login["access"]
st, resp = call("GET", "/workflows/executions/?workflow=58711b23-2968-4572-b065-a4d25cdff3e4&ordering=-created_at&page_size=3", tok)
items = resp.get("results", resp) if isinstance(resp, dict) else resp
for ex in items[:2]:
    print("===", ex.get("id"), ex.get("status"))
    st, detail = call("GET", f"/workflows/executions/{ex['id']}/", tok)
    print("error:", detail.get("error_message"))
    print("output_data snippet:", json.dumps(detail.get("output_data"), ensure_ascii=False)[:500])
    for nid, ns in (detail.get("node_status") or {}).items():
        print(" node", nid, ns.get("status"), json.dumps(ns.get("output"), ensure_ascii=False)[:150] if ns.get("output") else ns.get("error"))
