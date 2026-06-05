import urllib.request
import json

urls = [
    'http://127.0.0.1:8000/api/health/',
    'http://127.0.0.1:8000/api/ping/',
    'http://127.0.0.1:8000/api/v1/',
    'http://127.0.0.1:5200/',
]

for url in urls:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            print(f'[OK] {url} -> {resp.status} {body[:100]}')
    except Exception as e:
        print(f'[FAIL] {url} -> {type(e).__name__}: {e}')
