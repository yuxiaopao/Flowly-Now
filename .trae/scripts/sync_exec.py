import requests, json
t = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMDM2LCJ1c2VybmFtZSI6Im5sd2Z0ZXN0IiwiZXhwIjoxNzgxMzIxNjI4LCJpYXQiOjE3ODEyMzUyMjgsInR5cGUiOiJhY2Nlc3MifQ.rmyFfOyL3HjhmZOST7brRbzYGY8CxMBjgDH8BtJISIo"
h = {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}
WF_ID = "a4d717cd-aecc-403b-9c2b-c8fc57f6741c"

# First create a NEW simple workflow with proper LLM config to test the compat fix end-to-end
wf_data = {
    "name": "Compat Test Workflow",
    "description": "Test the prompt compatibility fix",
    "status": "draft"
}
r = requests.post("http://127.0.0.1:8000/api/v1/workflows/", json=wf_data, headers=h)
new_wf = r.json()["data"]
new_id = new_wf["id"]
print(f"Created workflow: {new_id}")

# Create nodes: start -> llm (with old prompt format) -> output -> end
nodes_data = [
    {"workflow": new_id, "node_id": "n_start", "node_type": "start", "name": "开始", "position": {"x": 100, "y": 100}, "config": {}},
    {"workflow": new_id, "node_id": "n_llm", "node_type": "llm", "name": "AI分析", "position": {"x": 300, "y": 100}, 
     "config": {"model": "qwen2.5-coder:7b", "prompt": "请用一句话总结以下内容：{{input}}", "temperature": 0.7}},
    {"workflow": new_id, "node_id": "n_output", "node_type": "output", "name": "输出", "position": {"x": 500, "y": 100}, "config": {"format": "text"}},
    {"workflow": new_id, "node_id": "n_end", "node_type": "end", "name": "结束", "position": {"x": 700, "y": 100}, "config": {}},
]
for nd in nodes_data:
    requests.post("http://127.0.0.1:8000/api/v1/workflows/nodes/", json=nd, headers=h)
print("  Nodes created")

# Create edges
edges_data = [
    {"source_node": "n_start", "target_node": "n_llm", "workflow": new_id},
    {"source_node": "n_llm", "target_node": "n_output", "workflow": new_id},
    {"source_node": "n_output", "target_node": "n_end", "workflow": new_id},
]
for ed in edges_data:
    requests.post("http://127.0.0.1:8000/api/v1/workflows/edges/", json=ed, headers=h)
print("  Edges created")

# Now execute synchronously with input data
print("\nExecuting with compat fix (prompt field in LLM config)...")
r = requests.post(f"http://127.0.0.1:8000/api/v1/workflows/{new_id}/execute/",
    json={"is_async": False, "input_data": {"input": "人工智能正在改变世界，让各行各业的工作效率大幅提升"}},
    headers=h, timeout=120)
resp = r.json()
data = resp.get("data", resp)
print(f"HTTP {r.status_code}")
print(f"Status: {data.get('status')}")
print(f"Output: {json.dumps(data.get('output_data',{}), ensure_ascii=False)[:800]}")
print(f"Error: {data.get('error_message','')[:300]}")

# Check execution detail
exec_id = data.get("execution_id")
if exec_id:
    r2 = requests.get(f"http://127.0.0.1:8000/api/v1/workflows/executions/{exec_id}/", headers=h)
    ed = r2.json().get("data", {})
    print(f"\nExecution Detail:")
    print(f"  Status: {ed.get('status')}")
    print(f"  Error: {ed.get('error_message','')[:300]}")
    print(f"  Output: {json.dumps(ed.get('output_data',{}), ensure_ascii=False)[:800]}")
