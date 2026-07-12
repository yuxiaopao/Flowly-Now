"""UI beautify role agent."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from .base import SiteRoleAgent
from .design_tokens import load_design_tokens, tokens_to_css_variables, write_design_tokens, build_design_tokens
from .patch import apply_file_patches
from .prompts import UI_BEAUTIFY_PROMPT


def _inject_css_variables(html: str, css_vars: str) -> str:
    if ':root {' in html and '--color-primary' in html:
        return html
    if '<style>' in html:
        return html.replace('<style>', f'<style>\n{css_vars}', 1)
    if '</head>' in html:
        return html.replace('</head>', f'<style>\n{css_vars}\n</style>\n</head>', 1)
    return css_vars + html


def _apply_glass_effect_css(css: str) -> str:
    extra = """
.glass-card {
  background: rgba(24, 24, 31, 0.72);
  backdrop-filter: blur(12px);
  border: 1px solid var(--color-border, #2e2e42);
  border-radius: var(--radius-lg, 16px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.24);
}
.upload-zone {
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
.upload-zone:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}
.site-header h1 {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent, var(--color-primary)));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
@media (prefers-reduced-motion: reduce) {
  .upload-zone { transition: none; transform: none; }
}
"""
    if '.glass-card' in css:
        return css
    return css + extra


def _heuristic_ui_score(output_dir: str) -> int:
    score = 60
    theme = os.path.join(output_dir, 'frontend', 'src', 'styles', 'theme.css')
    index = os.path.join(output_dir, 'frontend', 'index.html')
    for path in (theme, index):
        if not os.path.isfile(path):
            continue
        with open(path, encoding='utf-8') as f:
            text = f.read()
        if '--color-primary' in text:
            score += 10
        if '@media' in text:
            score += 10
        if 'aria-label' in text:
            score += 10
        if 'gradient' in text or 'backdrop-filter' in text:
            score += 10
    return min(score, 100)


class UiBeautifyAgent(SiteRoleAgent):
    role = 'ui_beautify'
    system_prompt = UI_BEAUTIFY_PROMPT

    def _build_file_context(self) -> str:
        parts: List[str] = []
        for rel in ('frontend/index.html', 'frontend/src/styles/theme.css'):
            try:
                parts.append(f'\n--- {rel} ---\n{self.sandbox.read_file(rel)[:8000]}')
            except Exception:
                pass
        return ''.join(parts)

    def apply_rules(self) -> Dict[str, Any]:
        tokens = load_design_tokens(self.output_dir)
        if not tokens:
            tokens = build_design_tokens(self.profile, self.wizard)
            write_design_tokens(self.output_dir, tokens)

        css_vars = tokens_to_css_variables(tokens)
        theme_css = _apply_glass_effect_css(css_vars)
        files: List[Dict[str, str]] = [
            {'path': 'frontend/src/styles/theme.css', 'content': theme_css},
        ]

        index_rel = 'frontend/index.html'
        index_path = os.path.join(self.output_dir, index_rel)
        if os.path.isfile(index_path):
            with open(index_path, encoding='utf-8') as f:
                html = f.read()
            new_html = _inject_css_variables(html, css_vars)
            if 'glass-card' not in new_html and 'result-panel' in new_html:
                new_html = new_html.replace('class="result-panel"', 'class="result-panel glass-card"', 1)
            if new_html != html:
                files.append({'path': index_rel, 'content': new_html})

        result = apply_file_patches(
            self.output_dir,
            self.role,
            files,
            model_path=self.model_path,
        )
        changed = result.get('files_changed') or []
        return {
            'files_changed': changed,
            'reply': '已注入设计令牌与玻璃态 UI 样式',
            'changed': bool(changed),
        }


def run_ui_beautify(
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
    agent = UiBeautifyAgent(
        output_dir,
        website_type=website_type,
        profile=profile,
        wizard=wizard,
        model_path=model_path,
        port=port,
        agent_mode=agent_mode,
        auto_qa=auto_qa,
    )
    result = agent.execute(instruction or '美化 UI：现代暗色主题、间距、动效')
    ui_score = _heuristic_ui_score(output_dir)
    return {
        **result,
        'ui_score': ui_score,
        'theme_applied': ui_score >= 70,
    }
