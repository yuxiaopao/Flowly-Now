"""Debug login failure - detailed inspection."""
from playwright.sync_api import sync_playwright
import json, os, time

BASE = "http://localhost:5200"
OUTPUT_DIR = r"e:\Flowly-now\.trae\screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    pages = browser.contexts[0].pages if browser.contexts else []
    page = pages[0] if pages else browser.contexts[0].new_page()

    network_logs = []
    page.on("request", lambda r: network_logs.append(f"REQ {r.method} {r.url[:120]}") if "/api/" in r.url or "/auth/" in r.url else None)
    page.on("response", lambda r: network_logs.append(f"RES {r.status} {r.url[:120]}") if "/api/" in r.url or "/auth/" in r.url else None)

    print("=== Login Page Investigation ===")
    page.goto(f"{BASE}/login", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "debug-login-01.png"), full_page=True)

    # Find ALL forms
    forms = page.locator("form").all()
    print(f"Forms found: {len(forms)}")

    # Find ALL inputs with ALL attributes
    all_inputs = page.locator("input").all()
    for i, inp in enumerate(all_inputs):
        try:
            if inp.is_visible():
                tp = inp.get_attribute("type") or ""
                name = inp.get_attribute("name") or ""
                plc = inp.get_attribute("placeholder") or ""
                vid = inp.get_attribute("id") or ""
                cls = inp.get_attribute("class") or ""
                print(f"  Input[{i}]: type='{tp}', name='{name}', placeholder='{plc}', id='{vid}', class='{cls[:60]}'")
        except:
            pass

    # Find ALL buttons
    all_btns = page.locator("button, [role=button]").all()
    for i, btn in enumerate(all_btns):
        try:
            if btn.is_visible():
                text = btn.inner_text().strip()[:50]
                tp = btn.get_attribute("type") or ""
                cls = btn.get_attribute("class") or ""
                disabled = btn.is_disabled()
                print(f"  Button[{i}]: text='{text}', type='{tp}', disabled={disabled}, class='{cls[:80]}'")
        except:
            pass

    # Try different login approaches
    print("\n=== Attempting Login ===")
    
    # Use very specific Element Plus selectors
    email_input = page.locator('input[type="text"]').first
    password_input = page.locator('input[type="password"]').first
    
    if email_input.is_visible():
        email_input.click()
        email_input.fill("")
        email_input.fill("nlwftest@flowly.test", timeout=3000)
        print(f"  Email filled: {email_input.input_value()}")
    
    if password_input.is_visible():
        password_input.click()
        password_input.fill("Test123456!")
        print(f"  Password filled: {'*' * len(password_input.input_value())}")
    
    page.screenshot(path=os.path.join(OUTPUT_DIR, "debug-login-02-filled.png"), full_page=True)
    
    # Find the login button - try multiple strategies
    login_btn = (
        page.locator('button:has-text("登 录"), button:has-text("登录"), button[type="submit"]').first
    )
    
    for strategy_name, btn in [
        ("1-has-text-denglu", page.locator('button:has-text("登录")')),
        ("2-has-text-Login", page.locator('button:has-text("Login")')),
        ("3-type-submit", page.locator('button[type="submit"]')),
        ("4-el-button-primary", page.locator('button.el-button--primary')),
        ("5-form-button", page.locator('form button')),
    ]:
        try:
            if btn.count > 0:
                text = btn.first.inner_text().strip()[:50]
                disabled = btn.first.is_disabled()
                print(f"  Strategy {strategy_name}: found '{text}', disabled={disabled}")
        except:
            print(f"  Strategy {strategy_name}: error")
    
    # Try clicking each button
    if login_btn.is_visible() and not login_btn.is_disabled():
        print("\n  Clicking login button...")
        login_btn.click()
    else:
        print(f"  Login button not clickable! visible={login_btn.is_visible()}, disabled={login_btn.is_disabled()}")
        # Try pressing Enter in password field
        print("  Trying Enter key...")
        password_input.press("Enter")

    page.wait_for_timeout(5000)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "debug-login-03-after-click.png"), full_page=True)
    print(f"  URL after submit: {page.url}")
    
    # Check all possible error messages
    for sel in [".el-message", ".el-message__content", ".el-alert", ".el-notification", "[class*=error]", "[class*=toast]", ".login-error", ".error-text"]:
        elems = page.locator(sel).all()
        for e in elems:
            try:
                if e.is_visible():
                    print(f"  ERROR element ({sel}): {e.inner_text()[:200]}")
            except:
                pass

    # Check network logs
    print(f"\n  Network API calls ({len(network_logs)}):")
    for log in network_logs[:20]:
        print(f"    {log[:200]}")
    
    page.screenshot(path=os.path.join(OUTPUT_DIR, "debug-login-04-final.png"), full_page=True)
    browser.close()
