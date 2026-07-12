"""File scope rules per site-factory role agent."""

from __future__ import annotations

import fnmatch
import re
from typing import List, Tuple

ROLE_SCOPES: dict[str, dict[str, List[str] | bool]] = {
    'backend_setup': {
        'allow_globs': ['backend/**'],
        'deny_globs': ['frontend/**'],
        'allow_core_edit_default': False,
    },
    'frontend_setup': {
        'allow_globs': [
            'frontend/src/**',
            'frontend/index.html',
            'frontend/vite.config.js',
            'frontend/package.json',
            'frontend/main.js',
        ],
        'deny_globs': ['backend/app.py'],
        'allow_core_edit_default': False,
    },
    'ui_beautify': {
        'allow_globs': [
            'frontend/**/*.css',
            'frontend/index.html',
            'frontend/src/assets/**',
            'frontend/src/styles/**',
        ],
        'deny_globs': ['backend/**'],
        'allow_core_edit_default': False,
    },
    'site_code_review': {
        'allow_globs': [],
        'deny_globs': ['**'],
        'allow_core_edit_default': False,
    },
}

PROTECTED_PATTERNS = (
    r'backend/db/schema\.sql$',
    r'backend/requirements\.txt$',
)


def normalize_rel_path(rel_path: str) -> str:
    return (rel_path or '').replace('\\', '/').lstrip('/')


def _matches_any(path: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(path, pat):
            return True
    return False


def can_write_path(
    role: str,
    rel_path: str,
    *,
    allow_core_edit: bool = False,
) -> Tuple[bool, str]:
    """Return (allowed, reason)."""
    rel = normalize_rel_path(rel_path)
    scope = ROLE_SCOPES.get(role)
    if not scope:
        return False, f'未知角色: {role}'

    if scope['deny_globs'] and _matches_any(rel, scope['deny_globs']):
        if role != 'backend_setup' or rel != 'backend/app.py':
            return False, f'路径不在 {role} 可写范围: {rel}'

    if role == 'backend_setup' and rel == 'backend/app.py' and not allow_core_edit:
        return False, 'backend/app.py 需开启 allowCoreEdit'

    for pat in PROTECTED_PATTERNS:
        if re.search(pat, rel) and not allow_core_edit:
            return False, f'受保护路径: {rel}'

    allow = scope.get('allow_globs') or []
    if not allow:
        return False, f'{role} 为只读角色'

    if _matches_any(rel, allow):
        return True, ''

    return False, f'路径不在 {role} 白名单: {rel}'
