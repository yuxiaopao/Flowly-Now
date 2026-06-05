import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Step 1: Login to get token
print("=" * 60)
print("Task 1: Login to get auth token")
print("=" * 60)

login_response = requests.post(
    f"{BASE_URL}/auth/login/",
    json={"username": "admin", "password": "admin123"}
)

print(f"Status Code: {login_response.status_code}")
print(f"Response: {login_response.text[:500]}")

if login_response.status_code == 200:
    data = login_response.json()
    token = data.get("access")
    refresh_token = data.get("refresh")
    print(f"\nAccess Token (first 50 chars): {token[:50] if token else 'None'}...")
    print(f"Refresh Token (first 50 chars): {refresh_token[:50] if refresh_token else 'None'}...")
else:
    print("Login failed!")
    token = None

print()

# Task 2: Test Agent APIs
print("=" * 60)
print("Task 2: Test Agent API Endpoints")
print("=" * 60)

headers = {"Authorization": f"Bearer {token}"} if token else {}

# Test 1: GET /api/v1/agents/
print("\n1. GET /api/v1/agents/ (list agents)")
try:
    r = requests.get(f"{BASE_URL}/agents/", headers=headers)
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.text[:200]}")
    agents_data = r.json() if r.status_code == 200 else None
    first_agent_id = None
    if agents_data:
        results = agents_data.get("results", agents_data)
        if isinstance(results, list) and len(results) > 0:
            first_agent_id = results[0].get("id")
            print(f"   Found {len(results)} agents, first agent ID: {first_agent_id}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: POST /api/v1/agents/ (create agent)
print("\n2. POST /api/v1/agents/ (create agent)")
try:
    new_agent = {
        "name": "Test Agent via API",
        "description": "Created by API test",
        "agent_type": "conversational",
        "system_prompt": "You are a helpful assistant."
    }
    r = requests.post(f"{BASE_URL}/agents/", json=new_agent, headers=headers)
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.text[:200]}")
    if r.status_code in [200, 201]:
        created_agent = r.json()
        created_agent_id = created_agent.get("id")
        print(f"   Created agent ID: {created_agent_id}")
    else:
        created_agent_id = None
except Exception as e:
    print(f"   Error: {e}")
    created_agent_id = None

# Test 3: GET /api/v1/agents/{id}/ (get agent detail)
target_id = first_agent_id or created_agent_id
if target_id:
    print(f"\n3. GET /api/v1/agents/{target_id}/ (get agent detail)")
    try:
        r = requests.get(f"{BASE_URL}/agents/{target_id}/", headers=headers)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
else:
    print("\n3. GET /api/v1/agents/{id}/ - Skipped (no agent ID available)")

# Test 4: PUT /api/v1/agents/{id}/ (update agent)
if target_id:
    print(f"\n4. PUT /api/v1/agents/{target_id}/ (update agent)")
    try:
        update_data = {
            "name": "Updated Test Agent",
            "description": "Updated via API test"
        }
        r = requests.put(f"{BASE_URL}/agents/{target_id}/", json=update_data, headers=headers)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")

# Test 5: DELETE /api/v1/agents/{id}/ (delete agent)
if created_agent_id:
    print(f"\n5. DELETE /api/v1/agents/{created_agent_id}/ (delete agent)")
    try:
        r = requests.delete(f"{BASE_URL}/agents/{created_agent_id}/", headers=headers)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.text[:200] if r.text else 'Empty (expected 204)'}")
    except Exception as e:
        print(f"   Error: {e}")

# Test 6: POST /api/v1/agents/{id}/chat/ (send chat message)
if target_id:
    print(f"\n6. POST /api/v1/agents/{target_id}/chat/ (send chat message)")
    try:
        chat_data = {"message": "Hello, how are you?"}
        r = requests.post(f"{BASE_URL}/agents/{target_id}/chat/", json=chat_data, headers=headers)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.text[:300]}")
    except Exception as e:
        print(f"   Error: {e}")

# Test 7: GET /api/v1/agents/{id}/conversations/ (get conversations)
if target_id:
    print(f"\n7. GET /api/v1/agents/{target_id}/conversations/ (get conversations)")
    try:
        r = requests.get(f"{BASE_URL}/agents/{target_id}/conversations/", headers=headers)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")

# Test 8: GET /api/v1/agents/tools/ (get available tools)
print("\n8. GET /api/v1/agents/tools/ (get available tools)")
try:
    r = requests.get(f"{BASE_URL}/agents/tools/", headers=headers)
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)
print("API Testing Complete")
print("=" * 60)
