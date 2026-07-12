import json, urllib.request, urllib.error, uuid
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

# test code node alone
nodes = [
    {"id": "s", "type": "start", "data": {"label": "Start"}, "position": {"x": 100, "y": 200}, "config": {}},
    {"id": "c", "type": "code", "data": {"label": "Code", "config": {"language": "python", "code": "output = {'sum': 1 + 2}"}}, "position": {"x": 320, "y": 200}, "config": {"language": "python", "code": "output = {'sum': 1 + 2}"}},
    {"id": "e", "type": "end", "data": {"label": "End"}, "position": {"x": 540, "y": 200}, "config": {}},
]
edges = [{"id": "e1", "source": "s", "target": "c", "label": ""}, {"id": "e2", "source": "c", "target": "e", "label": ""}]
st, wf = call("POST", "/workflows/", tok, {"name": f"dbg-code-{uuid.uuid4().hex[:6]}", "status": "draft", "nodes": nodes, "edges": edges})
print("create", st, wf if st != 201 else wf.get("id"))
if st == 201:
    st, ex = call("POST", f"/workflows/{wf['id']}/execute/", tok, {"input_data": {}, "is_async": False}, timeout=60)
    print("execute", st, ex)
    if ex and ex.get("execution_id"):
        st, detail = call("GET", f"/workflows/executions/{ex['execution_id']}/", tok)
        print("detail status", detail.get("status"), detail.get("error_message"))

# test condition with proper config
nodes2 = [
    {"id": "s", "type": "start", "data": {"label": "Start"}, "position": {"x": 100, "y": 200}, "config": {}},
    {"id": "v", "type": "variable", "data": {"label": "Var", "config": {"assignments": [{"name": "flag", "value": "true", "source": "static", "type": "boolean"}]}}, "position": {"x": 320, "y": 200}, "config": {"assignments": [{"name": "flag", "value": "true", "source": "static", "type": "boolean"}]}},
    {"id": "cond", "type": "condition", "data": {"label": "Cond", "config": {"condition_expression": "{{flag}} == true"}}, "position": {"x": 540, "y": 200}, "config": {"condition_expression": "{{flag}} == true"}},
    {"id": "e", "type": "end", "data": {"label": "End"}, "position": {"x": 760, "y": 200}, "config": {}},
]
edges2 = [{"id": "e1", "source": "s", "target": "v", "label": ""}, {"id": "e2", "source": "v", "target": "cond", "label": ""}, {"id": "e3", "source": "cond", "target": "e", "label": ""}]
st, wf2 = call("POST", "/workflows/", tok, {"name": f"dbg-cond-{uuid.uuid4().hex[:6]}", "status": "draft", "nodes": nodes2, "edges": edges2})
print("cond create", st, wf2 if st != 201 else wf2.get("id"))
if st == 201:
    st, ex = call("POST", f"/workflows/{wf2['id']}/execute/", tok, {"input_data": {}, "is_async": False}, timeout=60)
    print("cond execute", st, ex)
