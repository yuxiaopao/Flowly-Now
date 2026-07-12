import requests, json

BASE = 'http://127.0.0.1:8000/api/v1'
r = requests.post(f'{BASE}/auth/login/', json={'username': 'admin', 'password': 'admin123'})
token = r.json()['data']['access']
h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

wid = '0811e8c5-1a9d-4a7f-8aee-d958dc3cb85c'

r = requests.get(f'{BASE}/workflows/{wid}/', headers=h)
data = r.json().get('data', {})
nodes = data.get('nodes', [])

print('=== All Node Details ===')
for n in nodes:
    print(f'\nNode [{n["id"][:8]}]: {n["node_type"]} - {n["name"]}')
    print(f'  Config: {json.dumps(n.get("config", {}), ensure_ascii=False)[:500]}')
    print(f'  Style: {json.dumps(n.get("style", {}), ensure_ascii=False)}')
    print(f'  Full data keys: {list(n.keys())}')
