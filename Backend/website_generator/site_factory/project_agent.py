"""Project Agent — sandboxed file edits + mandatory QA loop (M3)."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

PROTECTED_PATTERNS = (
    r'backend/app\.py$',
    r'backend/db/schema\.sql$',
    r'backend/requirements\.txt$',
)

CORE_DELETE_BLOCKED = (
    'backend/app.py',
    'backend/db/init_db.py',
)


class ProjectAgentSandbox:
    """File operations restricted to output_dir."""

    def __init__(self, output_dir: str, model_path: str = ''):
        self.root = os.path.abspath(output_dir or '')
        self.model_path = model_path or ''

    def _resolve(self, rel_path: str) -> str:
        rel = (rel_path or '').replace('\\', '/').lstrip('/')
        full = os.path.abspath(os.path.join(self.root, rel))
        if not full.startswith(self.root):
            raise PermissionError(f'路径越界: {rel_path}')
        return full

    def list_dir(self, rel_path: str = '') -> List[str]:
        base = self._resolve(rel_path or '.')
        if not os.path.isdir(base):
            return []
        out = []
        for name in sorted(os.listdir(base)):
            if name.startswith('.') and name != '.flowly':
                continue
            out.append(name)
        return out

    def read_file(self, rel_path: str) -> str:
        path = self._resolve(rel_path)
        if not os.path.isfile(path):
            raise FileNotFoundError(rel_path)
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()

    def write_file(self, rel_path: str, content: str, allow_core: bool = False) -> None:
        rel = rel_path.replace('\\', '/').lstrip('/')
        if not allow_core and rel in CORE_DELETE_BLOCKED:
            raise PermissionError(f'核心文件受保护，需二次确认: {rel}')
        for pat in PROTECTED_PATTERNS:
            if re.search(pat, rel) and not allow_core:
                raise PermissionError(f'受保护路径不可直接改写: {rel}（请改 frontend 样式）')
        path = self._resolve(rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def delete_file(self, rel_path: str, confirmed: bool = False) -> None:
        rel = rel_path.replace('\\', '/').lstrip('/')
        if rel in CORE_DELETE_BLOCKED or 'app.py' in rel:
            if not confirmed:
                raise PermissionError('删除核心推理文件被拒绝，请确认后重试')
        path = self._resolve(rel)
        if os.path.isfile(path):
            os.remove(path)


def _agent_dir(output_dir: str) -> str:
    d = os.path.join(output_dir, '.flowly', 'agent')
    os.makedirs(d, exist_ok=True)
    return d


def append_audit_log(output_dir: str, entry: Dict[str, Any]) -> None:
    path = os.path.join(_agent_dir(output_dir), 'audit.jsonl')
    entry = {**entry, 'ts': datetime.now(timezone.utc).isoformat()}
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def append_conversation_log(output_dir: str, role: str, content: str) -> str:
    path = os.path.join(_agent_dir(output_dir), 'conversation.jsonl')
    line = {'role': role, 'content': content, 'ts': datetime.now(timezone.utc).isoformat()}
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(line, ensure_ascii=False) + '\n')
    return path


def export_conversation_json(output_dir: str) -> str:
    src = os.path.join(_agent_dir(output_dir), 'conversation.jsonl')
    out = os.path.join(_agent_dir(output_dir), 'conversation.json')
    messages = []
    if os.path.isfile(src):
        with open(src, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    return out


def _apply_dark_theme_html(html: str) -> Tuple[str, bool]:
    if 'background: #0a0a0f' in html:
        return html, False
    html = html.replace('background: #0f0f14', 'background: #0a0a0f')
    html = html.replace('background: #18181f', 'background: #12121a')
    html = html.replace('border: 1px solid #2e2e42', 'border: 1px solid #1f1f2e')
    if 'background: #0a0a0f' not in html:
        html = html.replace(
            'body { font-family',
            'body { background: #0a0a0f; font-family',
            1,
        )
    return html, True


def _apply_title_html(html: str, new_title: str) -> Tuple[str, bool]:
    if not new_title:
        return html, False
    pattern = re.compile(r'(<h1[^>]*>)(.*?)(</h1>)', re.DOTALL)
    if not pattern.search(html):
        return html, False
    new_html = pattern.sub(rf'\1{new_title}\3', html, count=1)
    return new_html, new_html != html


def _apply_primary_color(html: str, color: str) -> Tuple[str, bool]:
    if not color or not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        return html, False
    old = html
    html = re.sub(r'color: #[0-9A-Fa-f]{6};(\s*/\* primary \*/)?', f'color: {color};', html)
    html = re.sub(r'background: #[0-9A-Fa-f]{6};(\s*border-radius: 3px)?', f'background: {color};\\1', html)
    html = html.replace('#f59e0b', color).replace('#ef4444', color)
    return html, html != old


def _llm_available() -> bool:
    """True when any LLM provider (OpenAI-compatible / Ollama) is configured."""
    try:
        from django.conf import settings
        if getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY'):
            return True
        if getattr(settings, 'SITE_AGENT_PREFER_LLM', True):
            from gateway.providers.registry import get_registry, register_default_providers
            registry = get_registry()
            if not registry.get_all():
                register_default_providers()
            if registry.get_all():
                return True
    except Exception:
        pass
    return bool(os.environ.get('OPENAI_API_KEY'))


def _resolve_agent_model() -> str:
    try:
        from django.conf import settings
        model = getattr(settings, 'SITE_AGENT_MODEL', '') or getattr(settings, 'NL_WORKFLOW_MODEL', '')
        if model:
            return model
    except Exception:
        pass
    return 'gpt-4o-mini'


def _invoke_agent_llm(system: str, user: str) -> Optional[str]:
    """Call configured LLM via provider registry; fallback to ChatOpenAI."""
    try:
        from django.conf import settings
        from gateway.providers.registry import get_registry, register_default_providers

        model = _resolve_agent_model()
        registry = get_registry()
        if not registry.get_all():
            register_default_providers()
        provider = None
        for name in registry.get_all():
            candidate = registry.get(name)
            if candidate and candidate.supports_model(model):
                provider = candidate
                break
        if not provider:
            provider = registry.get('openai') or registry.get('ollama')
        if provider:
            result = provider.chat(
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                model=model,
                temperature=0.2,
                max_tokens=8000,
            )
            if isinstance(result, dict):
                return result.get('content') or ''
            return str(result or '')
    except Exception:
        pass

    if not (getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')):
        return None
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.2, max_tokens=8000)
        resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return (resp.content or '').strip()
    except Exception:
        return None


def _apply_rules_to_html(html: str, msg: str) -> Tuple[str, bool, List[str]]:
    changed = False
    reply_parts: List[str] = []

    if re.search(r'深色|dark|暗色', msg, re.I):
        html, ok = _apply_dark_theme_html(html)
        changed = changed or ok
        if ok:
            reply_parts.append('已将首页调整为深色主题。')

    title_match = re.search(r'(?:标题|名称)(?:改为|改成|设为|为)[「"\']?([^「」"\']+)[」"\']?', msg)
    if title_match:
        html, ok = _apply_title_html(html, title_match.group(1).strip())
        changed = changed or ok
        if ok:
            reply_parts.append(f'标题已更新为「{title_match.group(1).strip()}」。')

    color_match = re.search(r'(?:主色|主题色|颜色)(?:改为|改成|设为|为)\s*(#[0-9A-Fa-f]{6})', msg)
    if color_match:
        html, ok = _apply_primary_color(html, color_match.group(1))
        changed = changed or ok
        if ok:
            reply_parts.append(f'主色已更新为 {color_match.group(1)}。')

    return html, changed, reply_parts


def _run_project_agent_llm(
    html: str,
    message: str,
    *,
    site_name: str = '',
    website_type: str = 'detection',
    profile: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """LLM path: return {html, reply} or None on failure."""
    if not _llm_available():
        return None
    try:
        scenario = (profile or {}).get('scenario', '')
        domain = (profile or {}).get('domain', '')
        ui_tone = (profile or {}).get('ui_tone', '')
        copy_hints = (profile or {}).get('copy_hints') or []
        class_labels = (profile or {}).get('class_display_names') or {}
        metrics = metrics or (profile or {}).get('metrics') or {}

        system = (
            '你是 Flowly 生成站的 **AI 项目 Agent**，负责根据用户需求自主修改 frontend/index.html。\n'
            '能力：调整视觉风格、文案、布局、情绪/检测类产品的用户体验；保持推理 API 与上传表单可用。\n'
            '仅输出 JSON：{"reply":"中文说明（含设计理由）","html":"完整 HTML 字符串"}。\n'
            '禁止删除 script、上传表单、推理结果展示区域。不要输出 markdown。'
        )
        context_block = (
            f'站点: {site_name or "未命名"}\n'
            f'类型: {website_type}\n'
            f'场景: {scenario}\n'
            f'领域: {domain}\n'
            f'UI 调性: {ui_tone}\n'
            f'类别展示: {json.dumps(class_labels, ensure_ascii=False)}\n'
            f'文案提示: {json.dumps(copy_hints, ensure_ascii=False)}\n'
            f'训练指标: {json.dumps(metrics, ensure_ascii=False)}\n'
        )
        user = f'{context_block}\n用户修改需求: {message}\n\n当前 HTML:\n{html[:14000]}'
        text = _invoke_agent_llm(system, user)
        if not text:
            return None
        m = re.search(r'\{[\s\S]*\}', text)
        if not m:
            return None
        data = json.loads(m.group(0))
        new_html = data.get('html') or ''
        reply = data.get('reply') or '已完成 AI 修改。'
        if not new_html or len(new_html) < 50:
            return None
        return {'html': new_html, 'reply': reply}
    except Exception:
        return None


def _load_qa_summary(output_dir: str) -> str:
    report_path = os.path.join(output_dir, '.flowly', 'qa', 'qa_report.json')
    if not os.path.isfile(report_path):
        return ''
    try:
        with open(report_path, encoding='utf-8') as f:
            report = json.load(f)
        return str(report.get('summary_zh') or report.get('gate') or '')
    except Exception:
        return ''


def process_agent_message(
    output_dir: str,
    message: str,
    *,
    site_name: str = '',
    model_path: str = '',
    qa_profile: str = 'default',
    auto_qa: bool = True,
    website_type: str = 'detection',
    metrics: Optional[Dict[str, Any]] = None,
    port: Optional[int] = None,
    confirm_core_edit: bool = False,
    agent_mode: str = 'auto',
) -> Dict[str, Any]:
    """
    Apply user message to site files, optionally run QA, return agent output contract.
    """
    if not output_dir or not os.path.isdir(output_dir):
        return {
            'success': False,
            'error': 'output_dir 无效',
            'reply': '找不到站点目录，请先完成网站生成。',
        }

    msg = (message or '').strip()
    if not msg:
        return {'success': False, 'error': '消息为空', 'reply': '请输入修改需求。'}

    append_conversation_log(output_dir, 'user', msg)
    sandbox = ProjectAgentSandbox(output_dir, model_path)

    # Block destructive requests
    if re.search(r'删除|删掉|remove|delete', msg, re.I) and re.search(r'app\.py|load_model|infer', msg, re.I):
        reply = '无法删除核心推理文件 app.py / load_model。如需换模型请回到训练节点重新导出权重。'
        append_conversation_log(output_dir, 'assistant', reply)
        return {
            'success': True,
            'reply': reply,
            'files_changed': [],
            'qa_triggered': False,
            'blocked': True,
        }

    files_changed: List[str] = []
    index_rel = 'frontend/index.html'
    if not os.path.isfile(sandbox._resolve(index_rel)):
        index_rel = 'frontend/index.html'

    try:
        html = sandbox.read_file(index_rel)
    except FileNotFoundError:
        return {
            'success': False,
            'error': '缺少 frontend/index.html',
            'reply': '站点前端文件不存在，无法修改样式。',
        }

    changed = False
    reply_parts: List[str] = []
    mode = (agent_mode or 'auto').lower()

    if mode in ('auto', 'rules'):
        html, changed, reply_parts = _apply_rules_to_html(html, msg)

    if not changed and mode in ('auto', 'llm'):
        profile: Dict[str, Any] = {}
        profile_path = os.path.join(output_dir, '.flowly', 'profile.json')
        if os.path.isfile(profile_path):
            try:
                with open(profile_path, encoding='utf-8') as pf:
                    profile = json.load(pf)
            except Exception:
                profile = {}
        llm_result = _run_project_agent_llm(
            html,
            msg,
            site_name=site_name,
            website_type=website_type,
            profile=profile,
            metrics=metrics,
        )
        if llm_result:
            html = llm_result['html']
            reply_parts = [llm_result['reply']]
            changed = True

    if not changed:
        qa_hint = _load_qa_summary(output_dir)
        hint = f' 最近 QA：{qa_hint}' if qa_hint else ''
        reply = (
            '暂未识别可自动执行的修改。支持：深色主题、改标题、改主色；'
            '配置 LLM（Ollama / OpenAI 兼容 API）后，AI Agent 可自主改布局、文案与视觉风格。'
            f'{hint}'
        )
        append_conversation_log(output_dir, 'assistant', reply)
        return {
            'success': True,
            'reply': reply,
            'files_changed': [],
            'qa_triggered': False,
        }

    sandbox.write_file(index_rel, html, allow_core=confirm_core_edit)
    files_changed.append(index_rel)
    append_audit_log(output_dir, {'action': 'write', 'files': files_changed, 'message': msg})

    reply = ' '.join(reply_parts) if reply_parts else '已完成修改。'
    result: Dict[str, Any] = {
        'success': True,
        'reply': reply,
        'files_changed': files_changed,
        'qa_triggered': False,
        'qa_gate': None,
        'preview_url': None,
    }

    if auto_qa and files_changed:
        from .qa_runner import run_site_qa

        qa = run_site_qa(
            output_dir=output_dir,
            model_path=model_path,
            website_type=website_type,
            qa_profile=qa_profile,
            metrics=dict(metrics or {}),
            port=port,
            skip_playwright=True,
        )
        gate = qa.get('gate', 'red')
        result['qa_triggered'] = True
        result['qa_gate'] = gate
        result['qa_report'] = qa.get('qa_report', {})
        result['summary_zh'] = qa.get('summary_zh', '')

        if gate == 'red':
            result['reply'] = f'{reply} QA 红灯：{qa.get("summary_zh", "请查看报告")}。预览未更新。'
            result['preview_status'] = 'blocked'
        else:
            assigned = qa.get('assigned_port') or port or 49152
            preview_url = f'http://127.0.0.1:{int(assigned)}/'
            result['preview_url'] = preview_url
            result['preview_status'] = 'live' if gate == 'green' else 'live'
            result['reply'] = f'{reply} QA {gate}，预览已刷新。'
            if gate == 'yellow':
                result['warning'] = True

    append_conversation_log(output_dir, 'assistant', result['reply'])
    return result


def ensure_project_rag_collection(site_id: str, user, existing_id=None):
    """Get or create RAG collection `project-{site_id}` when vector store exists."""
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_authenticated:
        return None
    try:
        from rag.models import DocumentCollection, VectorStore
    except ImportError:
        return None

    if existing_id:
        coll = DocumentCollection.objects.filter(id=existing_id, owner=user).first()
        if coll:
            return coll

    name = f'project-{site_id}'
    coll = DocumentCollection.objects.filter(owner=user, name=name).first()
    if coll:
        return coll

    vector_store = VectorStore.objects.filter(owner=user, is_default=True).first()
    if not vector_store:
        vector_store = VectorStore.objects.filter(owner=user).first()
    if not vector_store:
        return None

    return DocumentCollection.objects.create(
        name=name,
        description=f'Project Agent 对话记忆 — 站点 {site_id}',
        vector_store=vector_store,
        owner=user,
    )


def append_rag_memory(collection, user_message: str, assistant_reply: str) -> bool:
    """Append one conversation turn to RAG collection."""
    if not collection:
        return False
    try:
        from rag.services import DocumentProcessor
    except ImportError:
        return False

    summary = f'用户: {user_message}\n助手: {assistant_reply}'
    processor = DocumentProcessor(collection)
    result = processor.process_text(
        content=summary,
        metadata={'title': f'agent-turn-{uuid.uuid4().hex[:8]}', 'source': 'project_agent'},
    )
    return bool(result.get('success'))


def resolve_rag_status(site, user) -> str:
    """Return rag_status: missing | ready | synced."""
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_authenticated:
        return 'missing'
    try:
        from rag.models import VectorStore
    except ImportError:
        return 'missing'
    has_store = VectorStore.objects.filter(owner=user).exists()
    if not has_store:
        return 'missing'
    if site.rag_collection_id:
        return 'synced'
    return 'ready'


def run_agent_for_site(
    site,
    message: str,
    *,
    qa_profile: str = 'default',
    auto_qa: bool = True,
    confirm_core_edit: bool = False,
    user=None,
    agent_mode: str = 'auto',
) -> Dict[str, Any]:
    """Shared entry for API and workflow node."""
    site.mark_iterating()
    metrics = {}
    if isinstance(site.last_qa_report, dict):
        metrics = site.last_qa_report.get('metrics') or {}

    result = process_agent_message(
        output_dir=site.output_dir,
        message=message,
        site_name=site.name,
        model_path=site.model_path,
        qa_profile=qa_profile,
        auto_qa=auto_qa,
        website_type=site.website_type,
        metrics=metrics,
        port=site.port,
        confirm_core_edit=confirm_core_edit,
        agent_mode=agent_mode or 'auto',
    )

    if not result.get('success'):
        return result

    site.last_agent_reply = {
        'reply': result.get('reply'),
        'files_changed': result.get('files_changed', []),
        'qa_triggered': result.get('qa_triggered'),
        'qa_gate': result.get('qa_gate'),
    }
    update_fields = ['last_agent_reply', 'status']

    if result.get('qa_triggered'):
        gate = result.get('qa_gate')
        site.last_qa_gate = gate or ''
        if result.get('qa_report'):
            site.last_qa_report = result['qa_report']
        update_fields.extend(['last_qa_gate', 'last_qa_report'])
        if gate == 'red':
            site.preview_status = 'blocked'
            site.status = 'iterating'
        else:
            site.preview_status = 'live'
            site.status = 'completed'
            if result.get('preview_url'):
                site.last_preview_url = result['preview_url']
                update_fields.append('last_preview_url')
        update_fields.append('preview_status')

    collection = ensure_project_rag_collection(str(site.id), user, site.rag_collection_id)
    rag_synced = False
    if collection:
        site.rag_collection_id = collection.id
        update_fields.append('rag_collection_id')
        rag_synced = append_rag_memory(collection, message, result.get('reply', ''))

    site.save(update_fields=update_fields)
    export_conversation_json(site.output_dir)
    result['site_id'] = str(site.id)
    result['preview_url'] = site.last_preview_url or result.get('preview_url')
    result['rag_collection_id'] = str(site.rag_collection_id) if site.rag_collection_id else None
    rag_status = resolve_rag_status(site, user)
    if rag_status == 'ready' and collection:
        rag_status = 'synced' if rag_synced else 'ready'
    result['rag_status'] = rag_status
    return result
