"""Base class for site-factory role agents."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from ..project_agent import ProjectAgentSandbox
from ..qa_runner import run_site_qa
from .design_tokens import load_design_tokens
from .llm import invoke_role_llm, llm_available
from .patch import apply_file_patches, parse_llm_files_json


class SiteRoleAgent:
    role: str = 'base'
    system_prompt: str = ''

    def __init__(
        self,
        output_dir: str,
        *,
        website_type: str = 'detection',
        profile: Optional[Dict[str, Any]] = None,
        wizard: Optional[Dict[str, Any]] = None,
        model_path: str = '',
        port: Optional[int] = None,
        agent_mode: str = 'auto',
        allow_core_edit: bool = False,
        auto_qa: bool = True,
    ):
        self.output_dir = output_dir
        self.website_type = website_type
        self.profile = profile or {}
        self.wizard = wizard or {}
        self.model_path = model_path
        self.port = port
        self.agent_mode = (agent_mode or 'auto').lower()
        self.allow_core_edit = allow_core_edit
        self.auto_qa = auto_qa
        self.sandbox = ProjectAgentSandbox(output_dir, model_path)

    def _context_block(self) -> str:
        tokens = load_design_tokens(self.output_dir)
        return (
            f'站点目录: {self.output_dir}\n'
            f'类型: {self.website_type}\n'
            f'场景: {self.profile.get("scenario", "")}\n'
            f'领域: {self.profile.get("domain", "")}\n'
            f'UI 调性: {self.profile.get("ui_tone", "")}\n'
            f'文案: {json.dumps(self.profile.get("copy_hints") or [], ensure_ascii=False)}\n'
            f'设计令牌: {json.dumps(tokens, ensure_ascii=False)[:4000]}\n'
            f'端口: {self.port or "默认"}\n'
        )

    def apply_rules(self) -> Dict[str, Any]:
        """Override in subclasses."""
        return {'files_changed': [], 'reply': '规则兜底未实现', 'changed': False}

    def apply_llm(self, instruction: str = '') -> Dict[str, Any]:
        if not llm_available() or self.agent_mode == 'rules':
            return {'files_changed': [], 'reply': '', 'changed': False, 'llm_skipped': True}

        user = f'{self._context_block()}\n任务: {instruction or self.role}\n'
        user += self._build_file_context()
        text = invoke_role_llm(self.system_prompt, user)
        files = parse_llm_files_json(text or '')
        if not files:
            return {'files_changed': [], 'reply': '', 'changed': False, 'llm_skipped': True}

        result = apply_file_patches(
            self.output_dir,
            self.role,
            files,
            allow_core_edit=self.allow_core_edit,
            model_path=self.model_path,
        )
        changed = result.get('files_changed') or []
        return {
            'files_changed': changed,
            'reply': 'LLM 已应用补丁',
            'changed': bool(changed),
            'llm_skipped': False,
            'errors': result.get('errors') or [],
        }

    def _build_file_context(self) -> str:
        return ''

    def run_light_qa(self) -> Dict[str, Any]:
        if not self.auto_qa:
            return {'qa_triggered': False}
        try:
            qa = run_site_qa(
                self.output_dir,
                model_path=self.model_path,
                website_type=self.website_type,
                port=self.port,
                skip_playwright=True,
            )
            return {'qa_triggered': True, 'qa_gate': qa.get('gate'), 'qa_summary': qa.get('summary_zh')}
        except Exception as exc:
            return {'qa_triggered': True, 'qa_error': str(exc)}

    def execute(self, instruction: str = '') -> Dict[str, Any]:
        if not self.output_dir or not os.path.isdir(self.output_dir):
            return {'success': False, 'error': 'output_dir 无效'}

        files_changed: List[str] = []
        llm_skipped = False
        reply_parts: List[str] = []

        if self.agent_mode in ('auto', 'rules'):
            rules = self.apply_rules()
            files_changed.extend(rules.get('files_changed') or [])
            if rules.get('reply'):
                reply_parts.append(rules['reply'])

        if self.agent_mode in ('auto', 'llm') and not files_changed:
            llm = self.apply_llm(instruction)
            files_changed.extend(llm.get('files_changed') or [])
            llm_skipped = llm.get('llm_skipped', False)
            if llm.get('reply'):
                reply_parts.append(llm['reply'])
        elif self.agent_mode == 'llm':
            llm = self.apply_llm(instruction)
            files_changed.extend(llm.get('files_changed') or [])
            llm_skipped = llm.get('llm_skipped', False)
            if llm.get('reply'):
                reply_parts.append(llm['reply'])

        qa_info = {}
        if files_changed:
            qa_info = self.run_light_qa()

        return {
            'success': True,
            'files_changed': list(dict.fromkeys(files_changed)),
            'reply': '；'.join(reply_parts) or f'{self.role} 完成',
            'llm_skipped': llm_skipped,
            **qa_info,
        }
