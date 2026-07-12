"""Site code review role agent with critic loop."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..qa_runner import run_site_qa
from .backend_agent import run_backend_setup
from .frontend_agent import run_frontend_setup
from .llm import invoke_role_llm, llm_available
from .prompts import SITE_CODE_REVIEW_PROMPT
from .ui_agent import run_ui_beautify


def _static_review(output_dir: str, website_type: str, port: int | None) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    backend_app = os.path.join(output_dir, 'backend', 'app.py')
    frontend_index = os.path.join(output_dir, 'frontend', 'index.html')

    if not os.path.isfile(backend_app):
        issues.append({'severity': 'error', 'category': 'backend', 'message': '缺少 backend/app.py'})
    if not os.path.isfile(frontend_index):
        issues.append({'severity': 'error', 'category': 'frontend', 'message': '缺少 frontend/index.html'})

    wtype = (website_type or 'detection').lower()
    if os.path.isfile(backend_app):
        with open(backend_app, encoding='utf-8') as f:
            app_text = f.read()
        if wtype in ('clip_retrieval', 'retrieval'):
            if '/search/text' not in app_text:
                issues.append({'severity': 'error', 'category': 'backend', 'message': '检索站缺少 /search/text'})
        elif '/predict' not in app_text:
            issues.append({'severity': 'error', 'category': 'backend', 'message': '缺少 /predict 路由'})
        if '/health' not in app_text:
            issues.append({'severity': 'warn', 'category': 'backend', 'message': '建议添加 /health 端点'})

    if os.path.isfile(frontend_index):
        with open(frontend_index, encoding='utf-8') as f:
            html = f.read()
        if 'fetch(' not in html and 'App.vue' not in os.listdir(os.path.join(output_dir, 'frontend', 'src')) if os.path.isdir(os.path.join(output_dir, 'frontend', 'src')) else True:
            vue_app = os.path.join(output_dir, 'frontend', 'src', 'App.vue')
            if os.path.isfile(vue_app):
                with open(vue_app, encoding='utf-8') as vf:
                    if 'fetch(' not in vf.read():
                        issues.append({'severity': 'warn', 'category': 'frontend', 'message': '前端未发现 API 调用'})
            else:
                issues.append({'severity': 'warn', 'category': 'frontend', 'message': '前端未发现 fetch API 调用'})

        if port and str(port) not in html:
            config_path = os.path.join(output_dir, 'backend', 'config.json')
            if os.path.isfile(config_path):
                with open(config_path, encoding='utf-8') as cf:
                    cfg = json.load(cf)
                cfg_port = cfg.get('port')
                if cfg_port and str(cfg_port) != str(port):
                    issues.append({
                        'severity': 'warn',
                        'category': 'frontend',
                        'message': f'端口不一致: config={cfg_port}, context={port}',
                    })

    return issues


def _llm_critic(output_dir: str, website_type: str, static_issues: List[Dict[str, str]]) -> Dict[str, Any]:
    if not llm_available():
        return {'issues': static_issues, 'fixes': []}

    snippets: List[str] = []
    for rel in ('backend/app.py', 'frontend/index.html', 'frontend/src/App.vue'):
        path = os.path.join(output_dir, rel.replace('/', os.sep))
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                snippets.append(f'--- {rel} ---\n{f.read()[:6000]}')

    user = (
        f'站点类型: {website_type}\n'
        f'静态问题: {json.dumps(static_issues, ensure_ascii=False)}\n'
        f'代码片段:\n{"".join(snippets)[:20000]}'
    )
    text = invoke_role_llm(SITE_CODE_REVIEW_PROMPT, user, max_tokens=4000)
    if not text:
        return {'issues': static_issues, 'fixes': []}
    try:
        start = text.find('{')
        end = text.rfind('}')
        data = json.loads(text[start:end + 1])
        issues = data.get('issues') or static_issues
        fixes = data.get('fixes') or []
        return {'issues': issues, 'fixes': fixes}
    except Exception:
        return {'issues': static_issues, 'fixes': []}


def _dispatch_fix(
    role: str,
    instruction: str,
    output_dir: str,
    *,
    website_type: str,
    profile: Dict[str, Any],
    wizard: Dict[str, Any],
    model_path: str,
    port: int | None,
    agent_mode: str,
) -> Dict[str, Any]:
    common = dict(
        output_dir=output_dir,
        website_type=website_type,
        profile=profile,
        wizard=wizard,
        model_path=model_path,
        port=port,
        agent_mode=agent_mode,
        auto_qa=False,
        instruction=instruction,
    )
    if role == 'backend_setup':
        return run_backend_setup(**common, allow_core_edit=True)
    if role == 'frontend_setup':
        return run_frontend_setup(**common)
    if role == 'ui_beautify':
        return run_ui_beautify(**common)
    return {'success': False, 'files_changed': []}


def run_site_code_review(
    output_dir: str,
    *,
    website_type: str = 'detection',
    profile: Dict[str, Any] | None = None,
    wizard: Dict[str, Any] | None = None,
    model_path: str = '',
    port: int | None = None,
    agent_mode: str = 'auto',
    max_rounds: int = 2,
) -> Dict[str, Any]:
    if not output_dir or not os.path.isdir(output_dir):
        return {'success': False, 'error': 'output_dir 无效', 'review_gate': 'red'}

    profile = profile or {}
    wizard = wizard or {}
    static_issues = _static_review(output_dir, website_type, port)
    if (agent_mode or 'auto').lower() == 'rules':
        critic = {'issues': static_issues, 'fixes': []}
    else:
        critic = _llm_critic(output_dir, website_type, static_issues)
    all_issues = critic.get('issues') or static_issues
    fixes = critic.get('fixes') or []

    issues_fixed: List[str] = []
    for rnd in range(max(1, max_rounds)):
        errors = [i for i in all_issues if i.get('severity') == 'error']
        if not errors and rnd > 0:
            break

        round_fixes = fixes if rnd == 0 else []
        if not round_fixes and errors:
            for err in errors:
                cat = err.get('category', 'frontend')
                role = 'backend_setup' if cat == 'backend' else ('ui_beautify' if cat == 'ui' else 'frontend_setup')
                round_fixes.append({'role': role, 'instruction': err.get('message', '修复问题')})

        for fix in round_fixes[:5]:
            role = fix.get('role', 'frontend_setup')
            instruction = fix.get('instruction', '修复检测到的问题')
            result = _dispatch_fix(
                role,
                instruction,
                output_dir,
                website_type=website_type,
                profile=profile,
                wizard=wizard,
                model_path=model_path,
                port=port,
                agent_mode=agent_mode,
            )
            changed = result.get('files_changed') or result.get('backend_files_changed') or []
            issues_fixed.extend(changed)

        qa = run_site_qa(
            output_dir,
            model_path=model_path,
            website_type=website_type,
            port=port,
            skip_playwright=True,
        )
        if qa.get('layers', {}).get('l1') == 'pass':
            all_issues = _static_review(output_dir, website_type, port)
            errors = [i for i in all_issues if i.get('severity') == 'error']
            if not errors:
                break
        else:
            all_issues = _static_review(output_dir, website_type, port)

    final_issues = _static_review(output_dir, website_type, port)
    error_count = sum(1 for i in final_issues if i.get('severity') == 'error')
    review_gate = 'green' if error_count == 0 else ('yellow' if error_count <= 2 else 'red')

    report_dir = os.path.join(output_dir, '.flowly', 'review')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, 'review_report.json')
    report = {
        'gate': review_gate,
        'issues': final_issues,
        'issues_fixed': list(dict.fromkeys(issues_fixed)),
        'ts': datetime.now(timezone.utc).isoformat(),
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return {
        'success': True,
        'review_gate': review_gate,
        'issues': final_issues,
        'issues_fixed': list(dict.fromkeys(issues_fixed)),
        'review_report_path': report_path,
    }
