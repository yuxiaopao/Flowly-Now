"""Confirm NL workflow session and save to DB."""
import requests, json

t = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMDM2LCJ1c2VybmFtZSI6Im5sd2Z0ZXN0IiwiZXhwIjoxNzgxMzIxNjI4LCJpYXQiOjE3ODEyMzUyMjgsInR5cGUiOiJhY2Nlc3MifQ.rmyFfOyL3HjhmZOST7brRbzYGY8CxMBjgDH8BtJISIo"
h = {"Authorization": f"Bearer {t}"}

r = requests.get("http://127.0.0.1:8000/api/v1/nl-workflow/sessions/", headers=h)
data = r.json().get("data")
print(f"Sessions result type: {type(data)}")

if isinstance(data, list):
    sessions = data
elif isinstance(data, dict) and "results" in data:
    sessions = data["results"]
else:
    sessions = [data] if data else []

for s in sessions:
    sid = s.get("session_id")
    status = s.get("status")
    wf_id = s.get("workflow_id")
    nodes = s.get("node_count")
    wf_name = s.get("workflow_name", "")
    print(f"Session: id={sid} status={status} wf_id={wf_id} nodes={nodes} name={wf_name}")
    
    if sid and not wf_id:
        print(f"  -> Saving workflow...")
        cr = requests.post(
            f"http://127.0.0.1:8000/api/v1/nl-workflow/sessions/{sid}/confirm/",
            headers=h
        )
        print(f"  -> Confirm response: {cr.status_code}")
        print(f"  -> Body: {cr.text[:300]}")

# Final check
r2 = requests.get("http://127.0.0.1:8000/api/v1/workflows/?page_size=10", headers=h)
wfs = r2.json().get("data", {}).get("results", [])
print(f"\nWorkflows in DB: {len(wfs)}")
for w in wfs:
    nid = w.get("id", "")[:16]
    print(f"  id={nid}... name={w.get('name')} nodes={w.get('node_count')}")
