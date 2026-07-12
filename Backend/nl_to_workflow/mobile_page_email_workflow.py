"""Mobile-responsive HTML page generation + email delivery workflow template."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from django.conf import settings

MOBILE_PAGE_EMAIL_KEYWORDS = (
    '手机网页', '移动端页面', '手机页面', 'h5页面', 'h5 页面', '响应式网页',
    'mobile page', 'mobile web', 'responsive html', '手机网页详细',
    '详细手机网页', '移动端网页', '手机端页面',
)

EMAIL_KEYWORDS = (
    '发邮件', '发送邮件', '发邮箱', '发送邮箱', '邮件发送', 'send email',
    'email', 'smtp', '收件', '发到邮箱',
)

EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')

DEFAULT_LLM_MODEL = getattr(settings, 'NL_WORKFLOW_MODEL', 'agnes-2.0-flash') or 'agnes-2.0-flash'


def extract_recipient_email(description: str, default: str = '') -> str:
    match = EMAIL_RE.search(description or '')
    return match.group(0) if match else default


def is_mobile_page_email_intent(description: str) -> bool:
    text = (description or '').lower()
    has_page = any(kw.lower() in text for kw in MOBILE_PAGE_EMAIL_KEYWORDS) or bool(
        re.search(r'手机.*网页|网页.*手机|mobile.*page|h5', text, re.I)
    )
    has_email = any(kw.lower() in text for kw in EMAIL_KEYWORDS) or bool(EMAIL_RE.search(text))
    return has_page and has_email


def has_sufficient_mobile_page_email_detail(description: str) -> bool:
    text = description or ''
    has_generate = bool(re.search(r'生成工作流|现在就生成|立即生成|开始生成', text, re.I))
    has_topic = len(text.strip()) >= 8
    has_email = bool(EMAIL_RE.search(text))
    return has_generate and has_topic and has_email


def build_mobile_page_email_workflow(
    description: str,
    *,
    default_recipient: str = '',
) -> Dict[str, Any]:
    """Build: input → LLM(mobile HTML) → email(HTML) → output → end."""
    recipient = extract_recipient_email(description, default_recipient)
    topic_hint = description.strip()[:120] or '手机端展示页'

    llm_model = DEFAULT_LLM_MODEL
    if not str(llm_model).startswith('agnes'):
        llm_model = 'agnes-2.0-flash'

    nodes: List[Dict[str, Any]] = [
        {
            'id': 'node_start',
            'type': 'start',
            'name': '开始',
            'position': {'x': 80, 'y': 200},
            'config': {},
        },
        {
            'id': 'node_input',
            'type': 'input',
            'name': '页面主题',
            'position': {'x': 280, 'y': 200},
            'config': {
                'input_name': 'page_topic',
                'input_type': 'text',
                'placeholder': '描述要生成的手机网页主题与要点…',
            },
        },
        {
            'id': 'node_llm',
            'type': 'llm',
            'name': '生成手机网页',
            'position': {'x': 520, 'y': 200},
            'config': {
                'model': llm_model,
                'provider': 'agnes',
                'prompt': (
                    '你是移动端网页设计专家。根据以下主题生成一份**完整、可直接发送的 HTML 邮件正文**'
                    '（内联 CSS，max-width 480px，适配手机竖屏）：\n'
                    '主题：{page_topic}\n\n'
                    '要求：\n'
                    '1. 仅输出 HTML 片段（含 <!DOCTYPE html> 或完整 html 结构）\n'
                    '2. 布局清晰：标题、分区、列表或卡片，视觉层次分明\n'
                    '3. 不要使用外部 CSS/JS 链接\n'
                    '4. 中文内容，信息详实'
                ),
                'temperature': 0.6,
            },
        },
        {
            'id': 'node_email',
            'type': 'email',
            'name': '发送邮件',
            'position': {'x': 760, 'y': 200},
            'config': {
                'to': recipient,
                'subject': f'【手机网页】{topic_hint[:40]}',
                'body': '{text}',
                'isHtml': True,
                'smtpConfig': {
                    'server': 'smtp.qq.com',
                    'port': 587,
                    'useTls': True,
                    'username': '',
                    'password': '',
                },
            },
        },
        {
            'id': 'node_output',
            'type': 'output',
            'name': '输出结果',
            'position': {'x': 980, 'y': 200},
            'config': {
                'template': '{text}',
                'format': 'text',
                'output_variable': 'result',
            },
        },
        {
            'id': 'node_end',
            'type': 'end',
            'name': '结束',
            'position': {'x': 1180, 'y': 200},
            'config': {},
        },
    ]

    edges = [
        {'id': 'e_start_input', 'source': 'node_start', 'target': 'node_input', 'label': ''},
        {'id': 'e_input_llm', 'source': 'node_input', 'target': 'node_llm', 'label': ''},
        {'id': 'e_llm_email', 'source': 'node_llm', 'target': 'node_email', 'label': ''},
        {'id': 'e_email_output', 'source': 'node_email', 'target': 'node_output', 'label': ''},
        {'id': 'e_output_end', 'source': 'node_output', 'target': 'node_end', 'label': ''},
    ]

    workflow: Dict[str, Any] = {
        'name': '手机网页生成并发送邮件',
        'description': description,
        'nodes': nodes,
        'edges': edges,
        '_generation_mode': 'template_mobile_page_email',
    }
    if recipient:
        workflow['_email_guidance'] = {
            'to': recipient,
            'hint': '请在邮件节点或系统 SMTP 中配置 QQ 邮箱授权码（smtp.qq.com:587）',
        }
    return workflow


def should_use_mobile_page_email_template(description: str) -> bool:
    return is_mobile_page_email_intent(description)


def mobile_page_email_chat_fallback_response(
    session_messages,
    user_message,
    *,
    default_recipient: str = '',
) -> tuple:
    combined = ' '.join(
        (m.get('content') or '') for m in (session_messages or []) if isinstance(m, dict)
    ) + ' ' + (user_message or '')

    if not is_mobile_page_email_intent(combined):
        return '', False, []

    recipient = extract_recipient_email(combined, default_recipient)
    email_line = f'收件邮箱：**{recipient}**' if recipient else '请提供收件邮箱（如 xxx@qq.com）'

    if has_sufficient_mobile_page_email_detail(combined):
        msg = (
            '我将生成 **手机网页 + 发邮件** 工作流：\n'
            '- 输入页面主题\n'
            '- LLM 生成移动端 HTML 详情页\n'
            f'- 邮件节点 HTML 发送（{email_line}）\n\n'
            '若确认无误，请回复「现在就生成工作流」。'
        )
        return msg, True, ['现在就生成工作流', '修改收件邮箱', '补充页面内容要求']

    msg = (
        '您需要 **手机端详细网页 + 邮件发送**。请确认：\n'
        '1. 网页主题与要展示的内容\n'
        f'2. {email_line}\n'
        '3. 邮件正文是否为 HTML 格式\n\n'
        '确认后回复「现在就生成工作流」。'
    )
    suggestions = ['现在就生成工作流', '收件邮箱 3488394996@qq.com']
    if recipient:
        suggestions.append(f'主题补充：{combined[:30]}…')
    return msg, False, suggestions[:4]
