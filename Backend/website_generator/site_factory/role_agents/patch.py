"""Apply file patches from role agents."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from ..project_agent import ProjectAgentSandbox, append_audit_log
from .scopes import can_write_path


def apply_file_patches(
    output_dir: str,
    role: str,
    files: List[Dict[str, str]],
    *,
    allow_core_edit: bool = False,
    model_path: str = '',
) -> Dict[str, Any]:
    """Apply {path, content} patches within role sandbox."""
    sandbox = ProjectAgentSandbox(output_dir, model_path)
    changed: List[str] = []
    errors: List[str] = []

    for item in files or []:
        rel = (item.get('path') or '').strip()
        content = item.get('content')
        if not rel or content is None:
            continue
        allowed, reason = can_write_path(role, rel, allow_core_edit=allow_core_edit)
        if not allowed:
            errors.append(f'{rel}: {reason}')
            continue
        try:
            core = rel.replace('\\', '/').lstrip('/') == 'backend/app.py'
            sandbox.write_file(rel, content, allow_core=allow_core_edit and core)
            changed.append(rel)
        except Exception as exc:
            errors.append(f'{rel}: {exc}')

    append_audit_log(output_dir, {
        'role': role,
        'action': 'patch',
        'files_changed': changed,
        'errors': errors,
    })
    return {'files_changed': changed, 'errors': errors}


def parse_llm_files_json(text: str) -> List[Dict[str, str]]:
    """Parse LLM JSON response with files array."""
    if not text:
        return []
    start = text.find('{')
    end = text.rfind('}')
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    files = data.get('files') or []
    out: List[Dict[str, str]] = []
    for f in files:
        if isinstance(f, dict) and f.get('path') and f.get('content') is not None:
            out.append({'path': str(f['path']), 'content': str(f['content'])})
    return out


def read_site_files(sandbox: ProjectAgentSandbox, paths: List[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for rel in paths:
        try:
            if os.path.isfile(sandbox._resolve(rel)):
                result[rel] = sandbox.read_file(rel)
        except Exception:
            pass
    return result
