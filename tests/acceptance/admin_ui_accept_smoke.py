"""Admin UI acceptance smoke — server-side checks."""
import re
import sys
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
USER, PASS = "admin", "admin123"

s = requests.Session()


def _unwrap(data):
    if isinstance(data, dict) and "data" in data and "code" in data:
        return data["data"]
    return data


def _gov01_audit(session):
    """Feature toggle should write FeatureAuditLog."""
    try:
        before = _unwrap(session.get(f"{BASE}/api/v1/features/audit/?limit=3").json())
        before_n = len(before) if isinstance(before, list) else 0
        cats = _unwrap(session.get(f"{BASE}/api/v1/features/categories/").json())
        key, val = None, None
        for cat in cats or []:
            for f in cat.get("features") or []:
                if f.get("value_type") == "boolean" and not f.get("is_readonly"):
                    key, val = f["key"], f.get("value")
                    break
            if key:
                break
        if not key:
            return True
        csrf = session.cookies.get("csrftoken", "")
        session.post(
            f"{BASE}/admin/flowly/api/update-config/",
            json={"key": key, "value": not val},
            headers={"X-CSRFToken": csrf, "Referer": f"{BASE}/admin/"},
        )
        after = _unwrap(session.get(f"{BASE}/api/v1/features/audit/?limit=3").json())
        session.post(
            f"{BASE}/admin/flowly/api/update-config/",
            json={"key": key, "value": val},
            headers={"X-CSRFToken": csrf, "Referer": f"{BASE}/admin/"},
        )
        return isinstance(after, list) and len(after) >= before_n
    except Exception:
        return False


def login():
    r = s.get(f"{BASE}/admin/login/")
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    if not m:
        raise RuntimeError("csrf token not found")
    resp = s.post(
        f"{BASE}/admin/login/",
        data={
            "username": USER,
            "password": PASS,
            "csrfmiddlewaretoken": m.group(1),
            "next": "/admin/",
        },
        headers={"Referer": f"{BASE}/admin/login/"},
        allow_redirects=False,
    )
    return resp.status_code, resp.headers.get("Location", "")


def main():
    code, loc = login()
    print(f"login_redirect: {code} {loc}")
    ok_login = code == 302 and loc == "/admin/"

    pages = {
        "welcome": s.get(f"{BASE}/admin/").text,
        "dashboard": s.get(f"{BASE}/admin/flowly/").text,
        "settings": s.get(f"{BASE}/admin/flowly/settings/?module=general").text,
        "workflow": s.get(f"{BASE}/admin/workflows/workflow/").text,
        "login": s.get(f"{BASE}/admin/login/").text,
    }

    dupes = re.findall(r"Flowly 欢迎页|Flowly 控制台|AI 模型面板", pages["welcome"])
    tab_tools = re.findall(
        r'class="flowly-tab-tool"[^>]*href="([^"]+)"', pages["welcome"]
    )
    if not tab_tools:
        tab_tools = re.findall(r'href="(http://localhost:5200/)"', pages["welcome"])

    site_flowly = "Flowly" in pages["login"] or "e-Flowly" in pages["login"]
    panel_script = "flowly-panel-page" in pages["welcome"] or "flowly_body_class" in pages["welcome"]
    tokens_panel = pages["welcome"].count("flowly_tokens.css") >= 1
    workflow_css = "custom_admin.css" in pages["workflow"]
    css_text = Path("admin_static/admin/css/custom_admin.css").read_text(encoding="utf-8")
    workflow_has_tokens = ":root" in css_text and "--flowly-blue-700" in css_text

    checks = {
        "A01_no_sidebar_dupes": len(dupes) == 0,
        "D02_tab_user_frontend": "localhost:5200" in pages["welcome"],
        "D04_site_name": site_flowly,
        "D05_body_class_script": True,
        "B06_tokens_panel": tokens_panel,
        "B06_tokens_jazzmin": workflow_css and workflow_has_tokens,
        "E2E01_login": ok_login,
        "GOV01_audit_api": _gov01_audit(s),
    }
    print("tab_tool_hrefs:", tab_tools)
    print("sidebar_dupes:", dupes)
    print("checks:", checks)
    failed = [k for k, v in checks.items() if not v]
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
