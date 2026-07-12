import requests

BASE = "http://127.0.0.1:8000/api/v1"
paths = [
    "/training/training-jobs/",
    "/training/datasets/",
    "/training/training-jobs/stats/",
    "/training/datasets/stats/",
]

for p in paths:
    try:
        r = requests.get(BASE + p, timeout=5)
        print(f"{p} -> {r.status_code}")
    except Exception as e:
        print(f"{p} -> ERROR: {e}")
