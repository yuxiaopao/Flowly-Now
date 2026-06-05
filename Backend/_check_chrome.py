import urllib.request
try:
    req = urllib.request.Request('http://localhost:9222/json/version')
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("Chrome debug: " + resp.read().decode()[:100])
except Exception as e:
    print("Chrome debug port NOT available:", e)
