import requests
BASE_URL = 'http://localhost:8000/api/v1'
r = requests.post(f'{BASE_URL}/auth/register/', json={
    'username': 'convdebug3',
    'email': 'convdebug3@test.com',
    'password': 'TestPass123!',
    'password_confirm': 'TestPass123!',
})
print(f'Register: {r.status_code}')
token = r.json()['data']['access']
h = {'Authorization': f'Bearer {token}'}

# Test conversations endpoint directly
print('\n--- Testing conversations endpoint ---')
r2 = requests.get(f'{BASE_URL}/agents/conversations/', headers=h)
print(f'{r2.status_code} /agents/conversations/')
print(f'  Response: {r2.text[:500]}')

# Test executions endpoint directly
print('\n--- Testing executions endpoint ---')
r3 = requests.get(f'{BASE_URL}/agents/executions/', headers=h)
print(f'{r3.status_code} /agents/executions/')
print(f'  Response: {r3.text[:500]}')
