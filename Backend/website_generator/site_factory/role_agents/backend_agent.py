"""Backend setup role agent."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from .base import SiteRoleAgent
from .patch import apply_file_patches
from .prompts import BACKEND_SETUP_PROMPT
from website_generator.generators.detection_fullsite_templates import build_detection_backend_extensions


HEALTH_ENDPOINT = '''
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model_loaded': model is not None})


@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        'name': CONFIG.get('name', 'AI Site'),
        'website_type': CONFIG.get('model_type', 'detection'),
        'labels': LABELS,
        'framework': FRAMEWORK,
    })
'''


class BackendSetupAgent(SiteRoleAgent):
    role = 'backend_setup'
    system_prompt = BACKEND_SETUP_PROMPT

    def _build_file_context(self) -> str:
        parts: List[str] = []
        for rel in ('backend/app.py', 'backend/config.json'):
            try:
                parts.append(f'\n--- {rel} ---\n{self.sandbox.read_file(rel)[:12000]}')
            except Exception:
                pass
        return ''.join(parts)

    def apply_rules(self) -> Dict[str, Any]:
        changed: List[str] = []
        app_path = os.path.join(self.output_dir, 'backend', 'app.py')
        if not os.path.isfile(app_path):
            return {
                'files_changed': [],
                'reply': '缺少 backend/app.py，请先运行网站生成节点',
                'changed': False,
            }

        with open(app_path, encoding='utf-8') as f:
            content = f.read()
        original = content
        reply_parts: List[str] = []
        wtype = (self.website_type or 'detection').lower()

        if '/health' not in content:
            insert_at = content.find('@app.route')
            if insert_at > 0:
                content = content[:insert_at] + HEALTH_ENDPOINT + '\n\n' + content[insert_at:]
                reply_parts.append('已添加 /health 与 /api/info')

        if 'MAX_CONTENT_LENGTH' not in content:
            max_mb = 100 if wtype == 'detection' else 16
            content = content.replace(
                'CORS(app)',
                f'CORS(app)\napp.config["MAX_CONTENT_LENGTH"] = {max_mb} * 1024 * 1024',
            )
            reply_parts.append(f'已设置请求体大小限制（{max_mb}MB）')

        if wtype in ('clip_retrieval', 'retrieval'):
            if '/search/text' not in content and '/search/image' not in content:
                reply_parts.append('检索站 API 需人工检查 /search/* 路由')
        elif '/predict' not in content:
            reply_parts.append('警告：未找到 /predict 路由')
        elif wtype == 'detection' and '/predict/video' not in content:
            insert_before = content.find("if __name__ == '__main__':")
            ext = build_detection_backend_extensions().strip()
            if insert_before > 0 and ext not in content:
                content = content[:insert_before] + ext + '\n\n' + content[insert_before:]
                reply_parts.append('已添加视频识别与历史记录 API')
            if 'log_inference_extended' not in content and 'request.form.get(\'mode\'' not in content:
                content = content.replace(
                    "log_inference(file.filename, f'{len(boxes)} detections', latency_ms)",
                    "log_inference_extended(request.form.get('mode', 'image') or 'image', file.filename, boxes, latency_ms)",
                )
                reply_parts.append('已升级图片识别历史记录')

        if content != original:
            result = apply_file_patches(
                self.output_dir,
                self.role,
                [{'path': 'backend/app.py', 'content': content}],
                allow_core_edit=True,
                model_path=self.model_path,
            )
            changed.extend(result.get('files_changed') or [])

        return {
            'files_changed': changed,
            'reply': '；'.join(reply_parts) or '后端结构已校验',
            'changed': bool(changed),
        }


def run_backend_setup(
    output_dir: str,
    *,
    website_type: str = 'detection',
    profile: Dict[str, Any] | None = None,
    wizard: Dict[str, Any] | None = None,
    model_path: str = '',
    port: int | None = None,
    agent_mode: str = 'auto',
    allow_core_edit: bool = True,
    auto_qa: bool = True,
    instruction: str = '',
) -> Dict[str, Any]:
    agent = BackendSetupAgent(
        output_dir,
        website_type=website_type,
        profile=profile,
        wizard=wizard,
        model_path=model_path,
        port=port,
        agent_mode=agent_mode,
        allow_core_edit=allow_core_edit,
        auto_qa=auto_qa,
    )
    result = agent.execute(instruction or '完善 Flask 后端：健康检查、错误处理、日志')
    endpoints = ['/health', '/api/info']
    wtype = (website_type or '').lower()
    if wtype in ('clip_retrieval', 'retrieval'):
        endpoints.extend(['/search/text', '/search/image'])
    else:
        endpoints.extend(['/predict', '/predict/video', '/api/history'])

    return {
        **result,
        'backend_ready': result.get('success', False),
        'backend_files_changed': result.get('files_changed') or [],
        'backend_endpoints': endpoints,
    }
