"""Frontend setup role agent."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from website_generator.generators.detection_fullsite_templates import build_detection_index_html
from website_generator.generators.modern_templates import (
    build_index_html_shell,
    build_main_js,
    build_result_panel_component,
    build_theme_css,
    build_upload_zone_component,
    build_vue_app_vue,
)
from .base import SiteRoleAgent
from .design_tokens import load_design_tokens, tokens_to_css_variables
from .patch import apply_file_patches
from .prompts import FRONTEND_SETUP_PROMPT


class FrontendSetupAgent(SiteRoleAgent):
    role = 'frontend_setup'
    system_prompt = FRONTEND_SETUP_PROMPT

    def _build_file_context(self) -> str:
        parts: List[str] = []
        for rel in ('frontend/index.html', 'frontend/src/App.vue'):
            try:
                parts.append(f'\n--- {rel} ---\n{self.sandbox.read_file(rel)[:8000]}')
            except Exception:
                pass
        return ''.join(parts)

    def apply_rules(self) -> Dict[str, Any]:
        tokens = load_design_tokens(self.output_dir)
        title = tokens.get('site_name') or self.wizard.get('siteName') or 'AI 识别系统'
        subtitle = self.wizard.get('usageDescription') or self.profile.get('scenario') or ''
        hints = self.profile.get('copy_hints') or []
        upload_hint = hints[0] if hints else '点击或拖拽上传图片'
        primary = (tokens.get('colors') or {}).get('primary') or '#f59e0b'

        wtype = (self.website_type or 'detection').lower()
        api_path = '/search/text' if wtype in ('clip_retrieval', 'retrieval') else '/predict'

        theme_css = build_theme_css(tokens_to_css_variables(tokens) if tokens else '')
        files = [
            {'path': 'frontend/src/styles/theme.css', 'content': theme_css},
            {'path': 'frontend/src/components/UploadZone.vue', 'content': build_upload_zone_component(upload_hint)},
            {'path': 'frontend/src/components/ResultPanel.vue', 'content': build_result_panel_component()},
            {'path': 'frontend/src/App.vue', 'content': build_vue_app_vue(title, subtitle, upload_hint, api_path)},
            {'path': 'frontend/src/main.js', 'content': build_main_js()},
        ]

        index_path = os.path.join(self.output_dir, 'frontend', 'index.html')
        if os.path.isfile(index_path):
            with open(index_path, encoding='utf-8') as f:
                old_html = f.read()
            if 'mode-nav' not in old_html:
                if wtype == 'detection':
                    labels = []
                    cfg_path = os.path.join(self.output_dir, 'backend', 'config.json')
                    if os.path.isfile(cfg_path):
                        try:
                            with open(cfg_path, encoding='utf-8') as cf:
                                labels = json.loads(cf.read()).get('labels') or []
                        except Exception:
                            pass
                    files.append({
                        'path': 'frontend/index.html',
                        'content': build_detection_index_html(
                            title, subtitle, primary, upload_hint, labels,
                        ),
                    })
                elif 'site-header' not in old_html:
                    files.append({
                        'path': 'frontend/index.html',
                        'content': build_index_html_shell(title, subtitle, primary, upload_hint),
                    })

        result = apply_file_patches(
            self.output_dir,
            self.role,
            files,
            model_path=self.model_path,
        )
        changed = result.get('files_changed') or []
        return {
            'files_changed': changed,
            'reply': f'已生成现代化前端结构（{len(changed)} 个文件）',
            'changed': bool(changed),
        }


def run_frontend_setup(
    output_dir: str,
    *,
    website_type: str = 'detection',
    profile: Dict[str, Any] | None = None,
    wizard: Dict[str, Any] | None = None,
    model_path: str = '',
    port: int | None = None,
    agent_mode: str = 'auto',
    auto_qa: bool = True,
    instruction: str = '',
) -> Dict[str, Any]:
    agent = FrontendSetupAgent(
        output_dir,
        website_type=website_type,
        profile=profile,
        wizard=wizard,
        model_path=model_path,
        port=port,
        agent_mode=agent_mode,
        auto_qa=auto_qa,
    )
    result = agent.execute(instruction or '搭建现代化 Vue 3 前端布局')
    return {
        **result,
        'frontend_ready': result.get('success', False),
        'layout_version': '2.0',
    }
