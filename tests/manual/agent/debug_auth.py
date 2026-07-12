import requests, json, time
BASE_URL = 'http://localhost:8000/api/v1'
session = requests.Session()
session.headers.update({'Content-Type': 'application/json'})

for username, password in [
    ('TestUser789', 'TestUser123!'),
    ('testuser01', 'TestUser123!'),
    ('sucker', 'TestUser123!'),
]:
    r = session.post(f'{BASE_URL}/auth/login/', json={'username': username, 'password': password})
    print(f'{username}: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'Token: {str(data.get("access", ""))[:30]}...')
        break
else:
    print('All login attempts failed. Trying registration...')
    r = session.post(f'{BASE_URL}/auth/register/', json={
        'username': f'agenttest_{int(time.time())}',
        'email': f'agenttest_{int(time.time())}@test.com',
        'password': 'TestPass123!',
        'password_confirm': 'TestPass123!',
    })
    print(f'Registration status: {r.status_code}')
    print(f'Registration response: {r.text[:500]}')
