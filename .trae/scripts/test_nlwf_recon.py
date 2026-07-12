"""Phase 1: Reconnaissance — connect via CDP to running Chrome."""
from playwright.sync_api import sync_playwright
import json, os

TEST_USER = {"email": "nlwftest@flowly.test", "password": "Test123456!"}
BASE = "http://localhost:5200"
OUTPUT_DIR = r"e:\Flowly-now\.trae\screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class Reporter:
    def __init__(self):
        self.issues = []
    def add(self, page_name, issue_type, detail):
        self.issues.append({"page": page_name, "type": issue_type, "detail": detail})
        print(f"  [ISSUE] {page_name} | {issue_type}: {detail}")

rep = Reporter()

with sync_playwright() as p:
    # Connect to already-running Chrome with remote debugging on port 9222
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    
    # Find or create a page
    pages = browser.contexts[0].pages if browser.contexts else []
    if pages:
        page = pages[0]
    else:
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
    
    viewport = page.viewport_size
    print(f"  Connected via CDP, viewport: {viewport}")

    console_errors = []
    page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda err: console_errors.append(f"[PAGE_ERROR] {err}"))

    # ==== 1. LANDING PAGE ====
    print("\n=== 1. Landing Page ===")
    page.goto(BASE, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "01-landing.png"), full_page=True)

    current_url = page.url
    page_title = page.title()
    print(f"  URL: {current_url}")
    print(f"  Title: {page_title}")

    buttons = page.locator("button").all()
    links = page.locator("a").all()
    print(f"  Found {len(buttons)} buttons, {len(links)} links")

    for i, btn in enumerate(buttons[:15]):
        try:
            text = btn.inner_text()[:50] if btn.is_visible() else "(hidden)"
            print(f"    Button[{i}]: {text}")
        except:
            pass
    for i, link in enumerate(links[:15]):
        try:
            text = link.inner_text()[:50] if link.is_visible() else "(hidden)"
            href = link.get_attribute("href") or ""
            print(f"    Link[{i}]: {text} -> {href}")
        except:
            pass

    # Navigate to login
    login_link = page.locator('a:has-text("登录"), a:has-text("Login"), a[href*="login"]').first
    if login_link.is_visible():
        print("\n  Found login link, clicking...")
        login_link.click()
    else:
        print("\n  Navigating to /login directly...")
        page.goto(f"{BASE}/login", wait_until="networkidle", timeout=30000)

    page.wait_for_timeout(2000)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "02-login-page.png"), full_page=True)
    print(f"  Login page URL: {page.url}")

    # ==== 2. LOGIN ====
    print("\n=== 2. Login ===")
    
    email_input = page.locator('input[type="email"], input[placeholder*="邮箱"], input[placeholder*="email"], input[placeholder*="用户名"], input[name="email"], input[name="username"]').first
    password_input = page.locator('input[type="password"], input[placeholder*="密码"]').first
    submit_btn = page.locator('button[type="submit"], button:has-text("登录"), button:has-text("Sign In")').first

    print(f"  Email visible: {email_input.is_visible()}, Password visible: {password_input.is_visible()}")
    
    if not email_input.is_visible():
        rep.add("Login", "FORM_MISSING", "Login form not found")
        page.screenshot(path=os.path.join(OUTPUT_DIR, "02-error-login-notfound.png"), full_page=True)
        browser.close()
        exit(1)

    email_input.fill(TEST_USER["email"])
    password_input.fill(TEST_USER["password"])
    page.screenshot(path=os.path.join(OUTPUT_DIR, "03-login-filled.png"), full_page=True)

    submit_btn.click()
    page.wait_for_timeout(3000)
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except:
        pass
    page.screenshot(path=os.path.join(OUTPUT_DIR, "04-post-login.png"), full_page=True)
    post_login_url = page.url
    print(f"  URL after login: {post_login_url}")

    if "login" in post_login_url.lower():
        rep.add("Login", "LOGIN_FAILED", f"Still on login page: {post_login_url}")
        error_msg = page.locator(".el-message--error, .el-alert--error, [class*=error]").first
        if error_msg.is_visible():
            print(f"  Error: {error_msg.inner_text()}")
        browser.close()
        exit(1)

    # ==== 3. DASHBOARD ====
    print("\n=== 3. Dashboard ===")
    page.wait_for_timeout(2000)
    nav_items = page.locator("nav a, .el-menu-item, .sidebar a").all()
    print(f"  Nav items: {len(nav_items)}")
    for item in nav_items[:20]:
        try:
            if item.is_visible():
                print(f"    {item.inner_text()[:60]}")
        except:
            pass

    # Navigate to NL create
    print("\n  Navigating to /nl-create...")
    page.goto(f"{BASE}/nl-create", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "05-nl-create.png"), full_page=True)
    nl_url = page.url
    print(f"  NL create URL: {nl_url}")

    # ==== 4. NL CREATE PAGE ====
    print("\n=== 4. NL Create Page ===")
    print(f"  Title: {page.title()}")

    inputs = page.locator("input, textarea").all()
    btns = page.locator("button").all()
    print(f"  Inputs: {len(inputs)}, Buttons: {len(btns)}")

    for i, inp in enumerate(inputs[:10]):
        try:
            if inp.is_visible():
                ph = inp.get_attribute("placeholder") or ""
                tp = inp.get_attribute("type") or "text"
                print(f"    Input[{i}]: type={tp}, placeholder='{ph}'")
        except:
            pass

    for i, btn in enumerate(btns[:15]):
        try:
            if btn.is_visible():
                text = btn.inner_text()[:60]
                disabled = btn.is_disabled()
                cls = btn.get_attribute("class") or ""
                print(f"    Button[{i}]: '{text}' disabled={disabled} class={cls[:60]}")
        except:
            pass

    # Find chat/send
    chat_input = page.locator('textarea, [contenteditable="true"], .chat-input textarea').first
    send_btn = page.locator('button:has-text("发送"), button:has-text("Send"), button:has-text("生成"), button[type="submit"]').first
    print(f"\n  Chat visible: {chat_input.is_visible()}, Send visible: {send_btn.is_visible()}")
    
    if not chat_input.is_visible():
        body_text = page.inner_text("body")[:800]
        print(f"  Body text: {body_text}")
        rep.add("NL_Create", "CHAT_MISSING", f"Chat input not found")

    # Console errors
    if console_errors:
        print(f"\n  Console Errors ({len(console_errors)}):")
        for err in console_errors[:15]:
            print(f"    {err[:200]}")
    else:
        print("\n  No console errors.")

    page.screenshot(path=os.path.join(OUTPUT_DIR, "06-final.png"), full_page=True)

    rep_path = os.path.join(OUTPUT_DIR, "..", "recon_report.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump({
            "issues": rep.issues,
            "console_errors": console_errors,
            "landing_url": current_url,
            "post_login_url": post_login_url,
            "nl_url": nl_url,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n=== Recon Complete ===")
    print(f"Issues: {len(rep.issues)}")
    print(f"Report: {rep_path}")
    print(f"Screenshots: {OUTPUT_DIR}")
    browser.close()
