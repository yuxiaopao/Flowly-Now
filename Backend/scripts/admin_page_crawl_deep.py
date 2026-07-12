#!/usr/bin/env python
"""Deep crawl: changelist + first change + add for all admin models."""
import os
import re
import sys

import django
import requests
from bs4 import BeautifulSoup

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse

BASE = os.getenv('ADMIN_CRAWL_BASE', 'http://127.0.0.1:8000')
ADMIN_USER = os.getenv('ADMIN_CRAWL_USER', 'admin')
ADMIN_PASS = os.getenv('ADMIN_CRAWL_PASS', 'admin123')

ISSUE_PATTERNS = [
    (re.compile(r'TemplateSyntaxError|TemplateDoesNotExist|NoReverseMatch', re.I), 'template'),
    (re.compile(r'FieldError|TypeError|AttributeError|KeyError|ValueError at', re.I), 'python'),
    (re.compile(r'404 Not Found|Page not found at', re.I), '404'),
    (re.compile(r'500 Internal Server Error', re.I), '500'),
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
        if pattern.search(body[:16000]):
            return kind
    return None


def first_change_link(html, path_prefix):
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.select('#result_list tbody tr th a, #result_list tbody tr td.field-__str__ a, #result_list tbody tr td a'):
        href = a.get('href', '')
        if href and '/change/' in href:
            if href.startswith('/'):
                return href
            if href.startswith('http'):
                return href.replace(BASE, '')
    for a in soup.select('a'):
        href = a.get('href', '')
        if href and path_prefix in href and '/change/' in href:
            if href.startswith('/'):
                return href
    return None


def get_model_urls():
    urls = []
    for model in admin.site._registry:
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        prefix = f'/admin/{app_label}/{model_name}/'
        for name in ('changelist', 'add'):
            try:
                urls.append((name, reverse(f'admin:{app_label}_{model_name}_{name}')))
            except Exception:
                pass
    return urls


def main():
    if not get_user_model().objects.filter(is_superuser=True).exists():
        print('ERROR: no superuser in DB')
        return 1

    session = login_session()
    model_urls = get_model_urls()
    ok, bad, skipped = [], [], []

    for kind, path in model_urls:
        url = BASE + path
        try:
            resp = session.get(url, timeout=60, allow_redirects=True)
            body = resp.text
            issue = classify(body, resp.status_code)
            row = {'path': path, 'kind': kind, 'status': resp.status_code, 'issue': issue}
            if issue and issue != 'http_403':
                bad.append(row)
            elif issue == 'http_403' and kind == 'add':
                skipped.append(row)
            else:
                ok.append(row)

            if kind == 'changelist' and resp.status_code == 200 and not issue:
                change_path = first_change_link(body, path)
                if change_path:
                    resp2 = session.get(BASE + change_path, timeout=60, allow_redirects=True)
                    issue2 = classify(resp2.text, resp2.status_code)
                    row2 = {'path': change_path, 'kind': 'change', 'status': resp2.status_code, 'issue': issue2}
                    if issue2 and issue2 != 'http_403':
                        bad.append(row2)
                    else:
                        ok.append(row2)
        except Exception as exc:
            bad.append({'path': path, 'kind': kind, 'status': 'EXC', 'issue': str(exc)})

    print(f'OK: {len(ok)}  ISSUES: {len(bad)}  SKIPPED(403 add): {len(skipped)}  TOTAL: {len(model_urls)}')
    for row in bad:
        print(f"  [{row['issue']}] {row.get('status')} {row.get('kind')} {row['path']}")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
