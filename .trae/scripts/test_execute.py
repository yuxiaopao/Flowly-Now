"""Final execute test."""
from playwright.sync_api import sync_playwright
import json, os, time, requests

BASE = "http://localhost:5200"
API = "http://127.0.0.1:8000"
OUT = r"e:\Flowly-now\.trae\screenshots"
os.makedirs(OUT, exist_ok=True)

lr = requests.post(f"{API}/api/v1/auth/login/", json={"username": "nlwftest@flowly.test", "password": "Test123456!"})
d = lr.json()["data"]
TOKEN = d["access"]
REFRESH = d["refresh"]
HF = {"Authorization": f"Bearer {TOKEN}"}

wf_r = requests.get(f"{API}/api/v1/workflows/?page_size=5", headers=HF)
wfs = wf_r.json()["data"]["results"]
wf = next((w for w in wfs if w.get("node_count", 0) > 0), wfs[0])
WF_ID = wf["id"]
print(f"WF: {WF_ID} ({wf['name']}, {wf['node_count']} nodes)")

api_calls = []
page_errors = []

def snap(page, name):
    try: page.screenshot(path=os.path.join(OUT, name), timeout=8000)
    except: pass

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.new_context()
    page = ctx.new_page()
    page.on("response", lambda r: api_calls.append(f"{r.status} {r.request.method} {r.url.split('8000/')[-1][:140]}") if "8000" in r.url and "/api/" in r.url else None)
    page.on("pageerror", lambda e: page_errors.append(str(e)))

    # Navigate and set token
    tok_js = json.dumps(TOKEN)
    ref_js = json.dumps(REFRESH)
    
    page.goto(BASE, wait_until="domcontentloaded", timeout=15000)
    time.sleep(2)
    page.evaluate(f"() => {{ localStorage.setItem('access_token', {tok_js}); localStorage.setItem('refresh_token', {ref_js}); document.cookie = 'access_token=' + {tok_js} + '; path=/; max-age=86400'; }}")
    
    page.goto(f"{BASE}/home", wait_until="domcontentloaded", timeout=15000)
    time.sleep(5)
    print(f"Home: {page.url}")
    snap(page, "f-01-home.png")

    page.goto(f"{BASE}/workflows/{WF_ID}/edit", wait_until="domcontentloaded", timeout=30000)
    time.sleep(10)
    print(f"Editor: {page.url}")
    snap(page, "f-02-editor.png")

    if "/login" in page.url:
        print("Redirected to login. Trying manual token injection via cookie...")
        # Set cookie at the login page level
        page.evaluate(f"() => {{ localStorage.setItem('access_token', {tok_js}); document.cookie = 'access_token=' + {tok_js} + '; path=/; max-age=86400'; }}")
        page.goto(f"{BASE}/workflows/{WF_ID}/edit", wait_until="domcontentloaded", timeout=30000)
        time.sleep(10)
        print(f"Editor (retry): {page.url}")
    
    if "/login" in page.url:
        print("CANNOT ACCESS EDITOR!")
        snap(page, "f-login-stuck.png")
        browser.close()
        exit(1)

    # Save
    api_before = len(api_calls)
    r = page.evaluate("""() => {
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            if ((t === '保存' || t === 'Save') && !btn.disabled) {
                btn.click(); return 'saved';
            }
        }
        return 'save-not-found';
    }""")
    print(f"Save: {r}")
    time.sleep(3)
    snap(page, "f-03-saved.png")

    # Execute 
    r = page.evaluate("""() => {
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            if ((t.includes('执行') || t === 'Run' || t === 'Execute') && !btn.disabled) {
                btn.click(); return 'executed: ' + t;
            }
        }
        return 'exec-not-found';
    }""")
    print(f"Execute: {r}")
    time.sleep(15)
    snap(page, "f-04-after-exec.png")
    
    new = api_calls[api_before:]
    print(f"\nNew API ({len(new)}):")
    for c in new: print(f"  {c[:200]}")
    
    time.sleep(20)
    snap(page, "f-05-final.png")
    body = page.inner_text("body")[:1200]
    print(f"\nUI: {body}")
    
    print("\n=== DB ===")
    for ep in [f"{API}/api/v1/workflows/{WF_ID}/executions/", f"{API}/api/v1/workflows/executions/", f"{API}/api/v1/executions/"]:
        try:
            r = requests.get(ep, headers=HF)
            print(f"  {ep.split('8000/')[-1]}: {r.status_code} {r.text[:200]}")
        except Exception as ex:
            print(f"  {ep}: {ex}")
    
    print(f"\nPage errors: {len(page_errors)}")
    for e in page_errors[:10]: print(f"  {e[:200]}")
    
    browser.close()
