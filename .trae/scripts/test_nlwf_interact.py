"""Phase 2: NL Workflow Test - fixed event handler."""
from playwright.sync_api import sync_playwright
import json, os, time

BASE = "http://localhost:5200"
OUT = r"e:\Flowly-now\.trae\screenshots"
os.makedirs(OUT, exist_ok=True)

def snap(page, name):
    try: page.screenshot(path=os.path.join(OUT, name), timeout=8000)
    except: pass

issues = []
api_calls = []
errors = []

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.new_context()
    page = ctx.new_page()

    page.on("pageerror", lambda e: errors.append(str(e)))
    
    # Monitor network via request
    def on_response(response):
        try:
            url = response.url
            if "8000" in url and "/api/" in url:
                api_calls.append(f"{response.status} {response.request.method} {url.split('8000')[-1][:120]}")
        except: pass
    page.on("response", on_response)

    # ==== LOGIN ====
    print("=== 1. Login ===")
    page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=20000)
    time.sleep(3)
    snap(page, "nlwf-01-login.png")

    page.locator('input[type="text"]').first.fill("nlwftest@flowly.test")
    page.locator('input[type="password"]').first.fill("Test123456!")
    page.locator('button[type="submit"]').first.click()
    print(f"  Login -> {page.url}")
    time.sleep(5)
    snap(page, "nlwf-02-dashboard.png")

    # ==== NL CREATE ====
    print("\n=== 2. NL Create Page ===")
    page.goto(f"{BASE}/nl-create", wait_until="domcontentloaded", timeout=20000)
    time.sleep(5)
    snap(page, "nlwf-03-nl-create.png")
    print(f"  URL={page.url}, title={page.title()}")

    # Elements
    print("  --- Buttons ---")
    for btn in page.locator("button").all()[:15]:
        try:
            if btn.is_visible(): print(f"    '{btn.inner_text().strip()[:50]}' d={btn.is_disabled()}")
        except: pass
    
    print("  --- Inputs ---")
    for inp in page.locator("textarea, input:not([type=hidden])").all()[:10]:
        try:
            if inp.is_visible(): print(f"    type={inp.get_attribute('type')} ph={inp.get_attribute('placeholder')}")
        except: pass

    # ==== SEND QUERY ====
    print("\n=== 3. Send NL Query ===")
    chat = page.locator("textarea").first
    if chat.is_visible():
        chat.fill("创建一个工作流：用户输入一个问题，AI进行分析和总结，输出分析报告")
        snap(page, "nlwf-04-query.png")
        
        send = page.locator('button').filter(has_text="发送").first
        if not send.is_visible():
            send = page.locator('button[type="submit"]').first
        
        print(f"  Send visible={send.is_visible()} disabled={send.is_disabled()}")
        if send.is_visible():
            send.click()
            time.sleep(20)
            snap(page, "nlwf-05-response.png")
            body = page.inner_text("body")[:2000]
            print(f"  Body after send:\n{body}")
        else:
            issues.append({"type": "NO_SEND_BTN"})
    else:
        body = page.inner_text("body")[:1000]
        print(f"  No textarea. Body:\n{body}")
        issues.append({"type": "NO_TEXTAREA", "detail": body[:300]})

    # ==== REPORT ====
    print(f"\n=== Report ===")
    print(f"Page errors ({len(errors)}):")
    for e in errors[:10]: print(f"  {e[:200]}")
    print(f"API calls ({len(api_calls)}):")
    for c in api_calls[-15:]: print(f"  {c[:150]}")
    print(f"Issues ({len(issues)}):")
    for i in issues: print(f"  {i}")

    with open(os.path.join(OUT, "..", "nlwf_report.json"), "w", encoding="utf-8") as f:
        json.dump({"issues": issues, "errors": errors, "api": api_calls}, f, indent=2, ensure_ascii=False)
    
    browser.close()
