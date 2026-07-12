#!/usr/bin/env python
"""Crawl live Django admin via HTTP session."""
import os
import re
import sys

import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse

BASE = os.getenv('ADMIN_CRAWL_BASE', 'http://127.0.0.1:8000')
ADMIN_USER = os.getenv('ADMIN_CRAWL_USER', 'admin')
ADMIN_PASS = os.getenv('ADMIN_CRAWL_PASS', 'admin123')

FLOWLY_PANELS = [
    '/admin/',
    '/admin/flowly/',
    '/admin/flowly/settings/',
    '/admin/flowly/features/',
    '/admin/flowly/ai-models/',
    '/admin/flowly/audit/',
    '/admin/flowly/system/',
    '/admin/flowly/dashboard-data/',
    '/admin/flowly/system-data/',
    '/admin/flowly/ai-models-data/',
    '/api/v1/admin/settings/modules/',
]

ISSUE_PATTERNS = [
    (re.compile(r'TemplateSyntaxError|TemplateDoesNotExist|NoReverseMatch', re.I), 'template'),
    (re.compile(r'TypeError|AttributeError|KeyError|ValueError at', re.I), 'python'),
    (re.compile(r'404 Not Found|Page not found at', re.I), '404'),
    (re.compile(r'500 Internal Server Error', re.I), '500'),
    (re.compile(r'PermissionDenied|403 Forbidden', re.I), '403'),
]


def login_session():
    s = requests.Session()
    login_url = f'{BASE}/admin/login/'
    r = s.get(login_url, timeout=30)
    r.raise_for_status()
    csrf = s.cookies.get('csrftoken') or re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    token = csrf.group(1) if hasattr(csrf, 'group') else csrf
    r = s.post(login_url, data={
        'username': ADMIN_USER,
        'password': ADMIN_PASS,
        'csrfmiddlewaretoken': token,
        'next': '/admin/',
    }, headers={'Referer': login_url}, timeout=30, allow_redirects=True)
    if 'login' in r.url and r.status_code == 200 and 'csrfmiddlewaretoken' in r.text:
        raise RuntimeError('Admin login failed')
    return s


def get_admin_urls():
    urls = set(FLOWLY_PANELS)
    for model in admin.site._registry:
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        for name in ('changelist', 'add'):
            try:
                urls.add(reverse(f'admin:{app_label}_{model_name}_{name}'))
            except Exception:
                pass
    return sorted(urls)


def classify(body, status):
    if status >= 500:
        return 'http_500'
    if status == 404:
        return 'http_404'
    if status == 403:
        return 'http_403'
    if status >= 400:
        return f'http_{status}'
    for pattern, kind in ISSUE_PATTERNS:
        if pattern.search(body[:12000]):
            return kind
    return None


def main():
    if not get_user_model().objects.filter(is_superuser=True).exists():
        print('ERROR: no superuser in DB')
        return 1

    session = login_session()
    urls = get_admin_urls()
    ok, bad = [], []

    for path in urls:
        url = BASE + path
        try:
            resp = session.get(url, timeout=60, allow_redirects=True)
            body = resp.text
            issue = classify(body, resp.status_code)
            row = {'path': path, 'status': resp.status_code, 'issue': issue}
            if issue:
                bad.append(row)
            else:
                ok.append(row)
        except Exception as exc:
            bad.append({'path': path, 'status': 'EXC', 'issue': str(exc)})

    print(f'OK: {len(ok)}  ISSUES: {len(bad)}  TOTAL: {len(urls)}')
    for row in bad:
        print(f"  [{row['issue']}] {row.get('status')} {row['path']}")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
