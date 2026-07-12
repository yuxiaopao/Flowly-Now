import requests
BASE = 'http://127.0.0.1:8000/api/v1'
r = requests.post(f'{BASE}/auth/login/', json={'username': 'admin', 'password': 'admin123'})
token = r.json()['data']['access']
h = {'Authorization': f'Bearer {token}'}

wid = 'da1306bf-2b17-4530-bcb0-ffa3008be0a6'
exec_id = '22ce47e5-1ee7-4289-a9c6-920126f31246'

# Check execution logs
r = requests.get(f'{BASE}/workflows/executions/{exec_id}/', headers=h)
data = r.json().get('data', {})
print('Execution status:', data.get('status'))
print('Node status:')
for nid, s in data.get('node_status', {}).items():
    print(f'  {nid[:8]}: {s.get("status")} error={s.get("error")}')

# Check DB for new jobs
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password='rootpassword', database='flowly_db')
cur = conn.cursor()
cur.execute("SELECT id, name, framework, training_kind, dataset_yaml_path FROM training_jobs ORDER BY id DESC LIMIT 5")
for row in cur.fetchall():
    print(f'  DB: id={row[0]} name={row[1]} framework={row[2]} kind={row[3]}')
cur.close()
conn.close()
