import requests

# Test ALL the exact paths used in the test file
BASE = "http://127.0.0.1:8000"
API_BASE = f"{BASE}/api/v1"

paths = [
    f"{API_BASE}/training/training-jobs/",
    f"{API_BASE}/training/datasets/",
    f"{API_BASE}/training/training-jobs/stats/",
]

print("Testing EXACT paths from test file:")
for p in paths:
    try:
        r = requests.get(p, timeout=5)
        print(f"  {p} -> {r.status_code}")
    except Exception as e:
        print(f"  {p} -> ERROR: {e}")

print("\nTest with params:")
r = requests.get(f"{API_BASE}/training/datasets/", params={"format": "csv"}, timeout=5)
print(f"  /training/datasets/?format=csv -> {r.status_code}")

r2 = requests.get(f"{API_BASE}/training/datasets/?format=csv", timeout=5)
print(f"  /training/datasets/?format=csv (URL encoded) -> {r2.status_code}")
