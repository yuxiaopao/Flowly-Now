"""Website scrape → format → email delivery workflow template."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

COLLECT_KEYWORDS = (
    '收集信息', '采集信息', '抓取', '爬取', '网页抓取', '网站抓取', '网站上',
    '从网站', '从网页', '抓取网站', '收集网站', 'web scrape', 'scrape', 'crawl',
    'fetch', '抓取信息', '采集', '收集',
)

FORMAT_KEYWORDS = (
    '排版', '整理', '格式化', '排版好', '排版之后', '排版后', '润色', '编排',
    'format', 'layout', '排版整理', '整理排版',
)

EMAIL_KEYWORDS = (
    '发邮件', '发送邮件', '发邮箱', '发送邮箱', '邮件发送', 'send email',
    'email', 'smtp', '收件', '发到邮箱', '发到对应邮箱', '对应邮箱',
)

EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
URL_RE = re.compile(r'https?://[^\s<>"\'\]]+', re.I)

DEFAULT_LLM_MODEL = getattr(settings, 'NL_WORKFLOW_MODEL', 'agnes-2.0-flash') or 'agnes-2.0-flash'

DEFAULT_SELECTORS = [
    {'name': 'title', 'selector': 'h1, title'},
    {'name': 'headings', 'selector': 'h2, h3'},
    {'name': 'content', 'selector': 'article, main, .content, .article, #content, body'},
]


def extract_recipient_email(description: str, default: str = '') -> str:
    match = EMAIL_RE.search(description or '')
    return match.group(0) if match else default


def extract_target_url(description: str, default: str = '') -> str:
    match = URL_RE.search(description or '')
    return match.group(0).rstrip('.,;') if match else default


def is_web_scrape_email_intent(description: str) -> bool:
    text = (description or '').lower()
    has_collect = any(kw.lower() in text for kw in COLLECT_KEYWORDS) or bool(
        re.search(r'网站.*(收集|抓取|采集)|收集.*网站|抓取.*网页', text, re.I)
    )
    has_format = any(kw.lower() in text for kw in FORMAT_KEYWORDS)
    has_email = any(kw.lower() in text for kw in EMAIL_KEYWORDS) or bool(EMAIL_RE.search(text))
    # Primary user theme: collect from web + format + email
    if has_collect and has_format and has_email:
        return True
    if has_collect and has_email and bool(re.search(r'网站|网页|web', text, re.I)):
        return True
    return False


def has_sufficient_web_scrape_email_detail(description: str) -> bool:
    text = description or ''
    has_generate = bool(re.search(r'生成工作流|现在就生成|立即生成|开始生成', text, re.I))
    has_email = bool(EMAIL_RE.search(text))
    has_url = bool(URL_RE.search(text))
    has_topic = len(text.strip()) >= 10
    return has_generate and has_email and (has_url or has_topic)


def build_web_scrape_email_workflow(
    description: str,
    *,
    default_recipient: str = '',
    default_url: str = 'https://example.com',
) -> Dict[str, Any]:
    """Build: input → web_scraper → LLM(format HTML) → email → output → end."""
    recipient = extract_recipient_email(description, default_recipient)
    target_url = extract_target_url(description, default_url)
    topic_hint = description.strip()[:80] or '网站信息摘要'

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
            'name': '目标网站',
            'position': {'x': 260, 'y': 200},
            'config': {
                'input_name': 'target_url',
                'input_type': 'text',
                'placeholder': '输入要采集信息的网站 URL，如 https://example.com',
            },
        },
        {
            'id': 'node_scraper',
            'type': 'web_scraper',
            'name': '采集网站信息',
            'position': {'x': 480, 'y': 200},
            'config': {
                'url': '{target_url}',
                'selectors': DEFAULT_SELECTORS,
            },
        },
        {
            'id': 'node_llm',
            'type': 'llm',
            'name': '排版整理',
            'position': {'x': 700, 'y': 200},
            'config': {
                'model': llm_model,
                'provider': 'agnes',
                'prompt': (
                    '你是专业内容编辑。根据以下从网站抓取的信息，整理排版为**结构清晰、适合邮件阅读的 HTML 正文**'
                    '（内联 CSS，标题层级分明，段落/列表清晰，中文表述）：\n\n'
                    '来源 URL：{url}\n'
                    '抓取数据：{data}\n\n'
                    '要求：\n'
                    '1. 仅输出 HTML（含基本 html/body 结构或可直接嵌入邮件的片段）\n'
                    '2. 提炼要点，去除导航/页脚等噪音\n'
                    '3. 不要使用外部 CSS/JS 链接\n'
                    '4. 信息详实、排版美观'
                ),
                'temperature': 0.5,
            },
        },
        {
            'id': 'node_email',
            'type': 'email',
            'name': '发送邮件',
            'position': {'x': 920, 'y': 200},
            'config': {
                'to': recipient,
                'subject': f'【网站信息摘要】{topic_hint[:36]}',
                'body': '{text}',
                'isHtml': True,
                'useGlobalSmtp': True,
            },
        },
        {
            'id': 'node_output',
            'type': 'output',
            'name': '输出结果',
            'position': {'x': 1120, 'y': 200},
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
            'position': {'x': 1300, 'y': 200},
            'config': {},
        },
    ]

    if target_url and target_url != default_url:
        nodes[1]['config']['default_value'] = target_url

    edges = [
        {'id': 'e_start_input', 'source': 'node_start', 'target': 'node_input', 'label': ''},
        {'id': 'e_input_scraper', 'source': 'node_input', 'target': 'node_scraper', 'label': ''},
        {'id': 'e_scraper_llm', 'source': 'node_scraper', 'target': 'node_llm', 'label': ''},
        {'id': 'e_llm_email', 'source': 'node_llm', 'target': 'node_email', 'label': ''},
        {'id': 'e_email_output', 'source': 'node_email', 'target': 'node_output', 'label': ''},
        {'id': 'e_output_end', 'source': 'node_output', 'target': 'node_end', 'label': ''},
    ]

    workflow: Dict[str, Any] = {
        'name': '网站信息采集排版并发送邮件',
        'description': description,
        'nodes': nodes,
        'edges': edges,
        '_generation_mode': 'template_web_scrape_email',
    }
    if recipient:
        workflow['_email_guidance'] = {
            'to': recipient,
            'hint': '请在邮件节点或系统 SMTP 中配置 QQ 邮箱授权码（smtp.qq.com:587）',
        }
    if target_url:
        workflow['_url_hint'] = target_url
    return workflow


def should_use_web_scrape_email_template(description: str) -> bool:
    return is_web_scrape_email_intent(description)


def web_scrape_email_chat_fallback_response(
    session_messages,
    user_message,
    *,
    default_recipient: str = '',
) -> Tuple[str, bool, List[str]]:
    combined = ' '.join(
        (m.get('content') or '') for m in (session_messages or []) if isinstance(m, dict)
    ) + ' ' + (user_message or '')

    if not is_web_scrape_email_intent(combined):
        return '', False, []

    recipient = extract_recipient_email(combined, default_recipient)
    target_url = extract_target_url(combined)
    email_line = f'收件邮箱：**{recipient}**' if recipient else '请提供收件邮箱（如 xxx@qq.com）'
    url_line = f'目标网站：**{target_url}**' if target_url else '请提供要采集的网站 URL'

    if has_sufficient_web_scrape_email_detail(combined):
        msg = (
            '我将生成 **网站采集 → 排版整理 → 发邮件** 工作流：\n'
            f'- {url_line}\n'
            '- web_scraper 抓取页面标题与正文\n'
            '- LLM（agnes-2.0-flash）排版为 HTML 邮件正文\n'
            f'- 邮件节点 HTML 发送（{email_line}）\n\n'
            '若确认无误，请回复「现在就生成工作流」。'
        )
        return msg, True, ['现在就生成工作流', '修改收件邮箱', '更换目标网站']

    msg = (
        '您需要 **从网站收集信息 → 排版整理 → 发送邮件**。请确认：\n'
        f'1. {url_line}\n'
        f'2. {email_line}\n'
        '3. 是否需要 HTML 格式邮件正文\n\n'
        '确认后回复「现在就生成工作流」。'
    )
    suggestions = ['现在就生成工作流', '收件邮箱 3488394996@qq.com', '目标网站 https://example.com']
    if recipient:
        suggestions.append(f'补充说明：{combined[:28]}…')
    return msg, False, suggestions[:4]
