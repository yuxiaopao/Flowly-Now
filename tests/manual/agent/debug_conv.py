import requests
BASE_URL = 'http://localhost:8000/api/v1'
r = requests.post(f'{BASE_URL}/auth/register/', json={
    'username': 'convdebug2',
    'email': 'convdebug2@test.com',
    'password': 'TestPass123!',
    'password_confirm': 'TestPass123!',
})
print(f'Register: {r.status_code}')
token = r.json()['data']['access']
h = {'Authorization': f'Bearer {token}'}

# Create agent
r2 = requests.post(f'{BASE_URL}/agents/', json={
    'name': 'ConvDebug2 Agent',
    'agent_type': 'conversational',
}, headers=h)
print(f'Create agent: {r2.status_code}')
agent_id = r2.json()['data']['id']
print(f'Agent ID: {agent_id}')

# Send chat to create conversation
r3 = requests.post(f'{BASE_URL}/agents/{agent_id}/chat/', json={
    'message': 'Hello'
}, headers=h, timeout=60)
print(f'Chat: {r3.status_code}')
if r3.status_code == 200:
    conv_id = r3.json()['data']['conversation_id']
    print(f'Conv ID: {conv_id}')

# Test conversations endpoint
print('\n--- Testing conversations endpoint ---')
for url in [
    '/agents/conversations/',
    '/agents/conversations',
]:
    r4 = requests.get(f'{BASE_URL}{url}', headers=h)
    print(f'{r4.status_code} {url}')
    print(f'  Response: {r4.text[:300]}')

# Test executions endpoint
print('\n--- Testing executions endpoint ---')
for url in [
    '/agents/executions/',
    '/agents/executions',
]:
    r5 = requests.get(f'{BASE_URL}{url}', headers=h)
    print(f'{r5.status_code} {url}')
    print(f'  Response: {r5.text[:300]}')
