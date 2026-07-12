import urllib.request, json, urllib.parse

url = 'http://127.0.0.1:8000/api/v1/auth/login/'
data = json.dumps({'username': 'admin@example.com', 'password': 'admin123'}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    resp = urllib.request.urlopen(req, timeout=5)
    print(f"Status: {resp.status}")
    print(json.loads(resp.read()))
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Status: {e.code} {e.reason}")
    print(f"Body: {body[:500]}")
except Exception as e:
    print(f"Error: {e}")
