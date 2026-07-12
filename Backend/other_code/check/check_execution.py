import requests, json

BASE = 'http://127.0.0.1:8000/api/v1'
r = requests.post(f'{BASE}/auth/login/', json={'username': 'admin', 'password': 'admin123'})
token = r.json()['data']['access']
h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

exec_id = '5823b38b-59d8-4e3f-bb37-58f8d5147cb5'
wid = '1aec7865-554a-479a-9389-1c364911d5e2'

# Get execution status
r = requests.get(f'{BASE}/workflows/executions/{exec_id}/', headers=h)
print('Execution status:', r.status_code)
data = r.json()
inner = data.get('data', {})
print('Status:', inner.get('status'))
print('Error:', inner.get('error_message', 'None'))
print('Progress:', inner.get('progress'))

# Get execution timeline (includes logs)
r = requests.get(f'{BASE}/workflows/executions/{exec_id}/timeline/', headers=h)
print('Timeline status:', r.status_code)
tl = r.json().get('data', {})
print('Timeline keys:', list(tl.keys())[:10])
logs = tl.get('execution_logs', [])
print(f'Logs ({len(logs)}):')
for log in logs[:30]:
    msg = str(log.get('message', ''))[:200]
    print(f'  [{log.get("level", "INFO")}] {msg}')
