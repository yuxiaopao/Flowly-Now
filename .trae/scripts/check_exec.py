import requests, json, time
t = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMDM2LCJ1c2VybmFtZSI6Im5sd2Z0ZXN0IiwiZXhwIjoxNzgxMzIxNjI4LCJpYXQiOjE3ODEyMzUyMjgsInR5cGUiOiJhY2Nlc3MifQ.rmyFfOyL3HjhmZOST7brRbzYGY8CxMBjgDH8BtJISIo"
h = {"Authorization": f"Bearer {t}"}

# Get latest execution
r = requests.get("http://127.0.0.1:8000/api/v1/workflows/executions/", headers=h)
execs = r.json()["data"]["results"]
latest = execs[0]
exec_id = latest["id"]
print(f"Execution: {exec_id}")
print(f"Status: {latest.get('status')}")

# Wait and poll
for attempt in range(4):
    time.sleep(15)
    r2 = requests.get(f"http://127.0.0.1:8000/api/v1/workflows/executions/{exec_id}/", headers=h)
    d = r2.json()["data"]
    print(f"  [{attempt+1}] status={d.get('status')} progress={d.get('progress')} nodes={d.get('completed_nodes')}/{d.get('total_nodes')}")
    if d.get("status") in ("completed", "failed", "cancelled"):
        print(f"  Final: {json.dumps(d, indent=2, ensure_ascii=False)[:800]}")
        break
