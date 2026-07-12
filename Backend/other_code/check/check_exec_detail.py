import requests, json

BASE = 'http://127.0.0.1:8000/api/v1'
r = requests.post(f'{BASE}/auth/login/', json={'username': 'admin', 'password': 'admin123'})
token = r.json()['data']['access']
h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

exec_id = '06eb5414-18f2-4df6-b074-a3537ef75932'

# Get execution detail
r = requests.get(f'{BASE}/workflows/executions/{exec_id}/', headers=h)
data = r.json().get('data', {})
print('=== Execution Detail ===')
print('Status:', data.get('status'))
print('Error message:', data.get('error_message', ''))
print('Progress:', data.get('progress'))
print('Node status:', json.dumps(data.get('node_status', {}), indent=2, ensure_ascii=False))

# Get node executions
r2 = requests.get(f'{BASE}/node-executions/?execution={exec_id}', headers=h)
print('\n=== Node Executions ===')
print('Status:', r2.status_code)
nodes_data = r2.json()
inner2 = nodes_data.get('data', {})
results = inner2.get('results', [])
print(f'Found {len(results)} node executions')
for node_exec in results:
    print(f'\n  [{node_exec.get("node_id", "")[:8]}] {node_exec.get("node_name", "")}')
    print(f'    Status: {node_exec.get("status")}')
    print(f'    Error: {node_exec.get("error_message", "")}')
    print(f'    Output: {json.dumps(node_exec.get("output", {}) or node_exec.get("output_data", {}), ensure_ascii=False)[:300]}')
