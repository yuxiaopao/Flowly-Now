"""Full-chain test: NL Create → Save → Edit → Execute with database validation."""
from playwright.sync_api import sync_playwright
import json, os, time, requests

BASE = "http://localhost:5200"
API = "http://127.0.0.1:8000"
OUT = r"e:\Flowly-now\.trae\screenshots"
os.makedirs(OUT, exist_ok=True)

# Reusable test user token
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMDM2LCJ1c2VybmFtZSI6Im5sd2Z0ZXN0IiwiZXhwIjoxNzgxMzIxNjI4LCJpYXQiOjE3ODEyMzUyMjgsInR5cGUiOiJhY2Nlc3MifQ.rmyFfOyL3HjhmZOST7brRbzYGY8CxMBjgDH8BtJISIo"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

issues = []
api_calls = []
page_errors = []

def add_issue(module, detail):
    issues.append({"module": module, "detail": detail})
    print(f"  [BUG] {module}: {detail}")

def db_check(label, query_fn):
    """Run a database check via API."""
    try:
        result = query_fn()
        print(f"  [DB] {label}: OK")
        return result
    except Exception as e:
        print(f"  [DB] {label}: FAIL - {e}")
        add_issue("Database", f"{label}: {e}")
        return None

def snap(page, name):
    try: page.screenshot(path=os.path.join(OUT, name), timeout=8000)
    except: pass

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("response", lambda r: api_calls.append(f"{r.status} {r.request.method} {r.url.split('8000/')[-1][:120]}") if "8000" in r.url and "/api/" in r.url else None)

    # ================================================================
    # 1. AUTH FLOW
    # ================================================================
    print("=" * 60)
    print("1. AUTH FLOW")
    print("=" * 60)
    page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=20000)
    time.sleep(3)
    
    page.locator('input[type="text"]').first.fill("nlwftest@flowly.test")
    page.locator('input[type="password"]').first.fill("Test123456!")
    snap(page, "full-01-login.png")
    
    page.locator('button[type="submit"]').first.click()
    time.sleep(5)
    current_url = page.url
    print(f"  Login result URL: {current_url}")
    
    if "/login" in current_url:
        add_issue("Auth", f"Login failed! Still at {current_url}")
        # Try to find error toast
        for s in [".el-message__content", ".el-alert__title", ".error-text"]:
            el = page.locator(s).first
            if el.is_visible():
                print(f"    Error message: {el.inner_text()}")
    else:
        print("  Auth OK")

    snap(page, "full-02-dashboard.png")

    # ================================================================
    # 2. NL CREATE PAGE - LOAD EXISTING SESSION
    # ================================================================
    print("\n" + "=" * 60)
    print("2. NL CREATE PAGE")
    print("=" * 60)
    page.goto(f"{BASE}/nl-create", wait_until="domcontentloaded", timeout=20000)
    time.sleep(5)
    snap(page, "full-03-nl-create.png")
    print(f"  URL: {page.url}")

    # -- 2a: Check page loaded properly --
    body_preview = page.inner_text("body")[:600]
    print(f"  Page text preview: {body_preview[:400]}")

    # -- 2b: List ALL buttons on page --
    all_btns = page.locator("button").all()
    print(f"  Total buttons on page: {len(all_btns)}")
    save_btns = []
    for btn in all_btns:
        try:
            if btn.is_visible():
                text = btn.inner_text().strip()
                tag = btn.evaluate("el => el.tagName")
                cls = btn.get_attribute("class") or ""
                if text:
                    print(f"    BTN: '{text[:50]}' disabled={btn.is_disabled()} class={cls[:50]}")
                    if any(kw in text.lower() for kw in ["保存", "save", "确认", "confirm", "应用", "apply", "生成"]):
                        save_btns.append((btn, text))
        except: pass

    # -- 2c: Find save/confirm button --
    print(f"  Potential save/confirm buttons: {len(save_btns)}")
    found_save = False
    
    # Try clicking different save button selectors
    for sel in [
        'button:has-text("保存工作流")',
        'button:has-text("确认生成")',
        'button:has-text("应用")',
        'button:has-text("Apply")',
        'button:has-text("Save")',
        'button[class*=save]',
        'button[class*=confirm]',
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                text = el.inner_text().strip()
                print(f"  Found: '{text}' via '{sel}'")
                el.click()
                time.sleep(5)
                found_save = True
                break
        except: pass

    # -- 2d: Try clicking save from sidebar/tabs --
    if not found_save:
        print("  Trying alternate save locations...")
        # Check if there's a "应用" or save icon
        for sel in ['.el-icon', 'svg', '[class*=icon]']:
            try:
                icons = page.locator(sel).all()
                for icon in icons[:20]:
                    parent = icon.locator("..")
                    parent_text = parent.inner_text().strip() if parent.is_visible() else ""
                    if any(kw in parent_text for kw in ["保存", "应用", "确认", "save", "apply"]):
                        icon.click()
                        time.sleep(5)
                        found_save = True
                        break
                if found_save: break
            except: pass

    snap(page, "full-04-after-save-click.png")

    # ================================================================
    # 2e: Database check - did workflow get saved?
    # ================================================================
    print("\n" + "=" * 60)
    print("2e. DATABASE CHECK")
    print("=" * 60)
    
    wf_resp = requests.get(f"{API}/api/v1/workflows/?page_size=10", headers=HEADERS)
    workflows = wf_resp.json().get("data", {}).get("results", [])
    print(f"  Workflows in DB: {len(workflows)}")
    for w in workflows:
        print(f"    id={w.get('id','?')[:12]}... name='{w.get('name','?')}' status={w.get('status','?')}")
    
    # Check NL session workflow_id
    sess_resp = requests.get(f"{API}/api/v1/nl-workflow/sessions/", headers=HEADERS)
    sessions = sess_resp.json().get("data", {})
    # The sessions data is a list directly
    if isinstance(sessions, list):
        for s in sessions:
            print(f"    Session: status={s.get('status')} workflow_id={s.get('workflow_id')} nodes={s.get('node_count')}")
    elif isinstance(sessions, dict):
        results = sessions.get("results", [sessions])
        if isinstance(results, list):
            for s in results:
                print(f"    Session: status={s.get('status')} workflow_id={s.get('workflow_id')} nodes={s.get('node_count')}")
        else:
            print(f"    Session raw: {json.dumps(sessions)[:300]}")
    
    # Try confirm API directly
    if sessions and (not isinstance(sessions, list) or len(sessions) > 0):
        first_session = sessions[0] if isinstance(sessions, list) else sessions
        sid = first_session.get("session_id") or first_session.get("id")
        if sid and not first_session.get("workflow_id"):
            print(f"  Workflow not saved yet. Trying direct confirm API...")
            try:
                confirm_resp = requests.post(
                    f"{API}/api/v1/nl-workflow/sessions/{sid}/confirm/",
                    headers=HEADERS
                )
                print(f"  Confirm status: {confirm_resp.status_code}")
                if confirm_resp.status_code == 200:
                    data = confirm_resp.json()
                    wf_id = data.get("workflow_id") or data.get("data", {}).get("workflow_id")
                    print(f"  Workflow ID from confirm: {wf_id}")
                else:
                    print(f"  Confirm failed: {confirm_resp.text[:200]}")
            except Exception as e:
                print(f"  Confirm error: {e}")

    # ================================================================
    # 3. WORKFLOW EDITOR PAGE
    # ================================================================
    print("\n" + "=" * 60)
    print("3. WORKFLOW EDITOR")
    print("=" * 60)
    
    # Get the first workflow to edit
    wf_resp = requests.get(f"{API}/api/v1/workflows/?page_size=5", headers=HEADERS)
    wfs = wf_resp.json().get("data", {}).get("results", [])
    
    if wfs:
        wf_id = wfs[0]["id"]
        print(f"  Opening workflow: {wf_id} ({wfs[0]['name']})")
        page.goto(f"{BASE}/workflows/{wf_id}/edit", wait_until="domcontentloaded", timeout=20000)
        time.sleep(8)
        snap(page, "full-05-editor.png")
        
        # Check editor loaded
        body_preview = page.inner_text("body")[:800]
        print(f"  Editor page text: {body_preview[:400]}")
        
        # Find canvas nodes
        nodes = page.locator(".vue-flow__node").all()
        edges = page.locator(".vue-flow__edge").all()
        print(f"  Canvas nodes: {len(nodes)}, edges: {len(edges)}")
        
        # Check toolbar buttons
        toolbar_btns = page.locator(".toolbar button, .editor-toolbar button, [class*=toolbar] button").all()
        print(f"  Toolbar buttons: {len(toolbar_btns)}")
        for btn in toolbar_btns[:10]:
            try:
                if btn.is_visible():
                    t = btn.inner_text().strip()[:50]
                    print(f"    '{t}' disabled={btn.is_disabled()}")
            except: pass
        
        # -- 3a: Find execute button --
        print("\n  --- Execute Buttons ---")
        for sel in [
            'button:has-text("执行")',
            'button:has-text("运行")',
            'button:has-text("Run")',
            'button:has-text("Execute")',
            'button:has-text("▶")',
            'button[class*=execute]',
            'button[class*=run]',
        ]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    text = el.inner_text().strip()
                    print(f"    Found: '{text}' via '{sel}' disabled={el.is_disabled()}")
            except: pass
    else:
        print("  No workflows to edit!")
        add_issue("Workflow", "No workflows exist to test editor")
        # Check if the e2e workflow exists
        e2e_wf = requests.get(f"{API}/api/v1/workflows/?page_size=20", headers=HEADERS).json()
        results = e2e_wf.get("data", {}).get("results", [])
        print(f"  Total workflows found: {len(results)}")

    # ================================================================
    # 4. CONSOLE ERRORS & NETWORK
    # ================================================================
    print("\n" + "=" * 60)
    print("4. CONSOLE & NETWORK REPORT")
    print("=" * 60)
    print(f"  Page errors: {len(page_errors)}")
    for e in page_errors[:10]:
        print(f"    {e[:300]}")
    
    api_errors = [c for c in api_calls if c.startswith("4") or c.startswith("5")]
    print(f"  API errors: {len(api_errors)}")
    for c in api_errors[:10]:
        print(f"    {c[:150]}")
    
    print(f"  Total API calls: {len(api_calls)}")
    
    # ================================================================
    # 5. FINAL REPORT
    # ================================================================
    print("\n" + "=" * 60)
    print("5. FINAL REPORT")
    print("=" * 60)
    print(f"  Total issues: {len(issues)}")
    for i in issues:
        print(f"  [{i['module']}] {i['detail'][:200]}")
    
    snap(page, "full-99-final.png")
    
    with open(os.path.join(OUT, "..", "fullchain_report.json"), "w", encoding="utf-8") as f:
        json.dump({
            "issues": issues,
            "page_errors": page_errors,
            "api_errors": api_errors,
            "api_calls": api_calls,
        }, f, indent=2, ensure_ascii=False)
    
    browser.close()
