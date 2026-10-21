"""
CodeGraph analysis assistant — retrieve graph/nav evidence then ask LLM.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .ai_explain import _invoke_llm

logger = logging.getLogger(__name__)

_MAX_SNIPPET_FILES = 10
_MAX_CONTEXT_CHARS = 28000

_STOPWORDS = {
    '如何', '怎么', '怎样', '什么', '哪个', '哪些', '为什么', '是否', '可以',
    '的', '了', '吗', '呢', '啊', '吧', '和', '与', '或', '在', '是', '有',
    '我', '你', '他', '她', '它', '这', '那', '一个', '这个', '那个',
    '页面', '文件', '代码', '跳转', '路由', '导航', '分析', '告诉', '一下',
    'how', 'what', 'where', 'when', 'why', 'which', 'does', 'the', 'a', 'an',
    'to', 'of', 'in', 'on', 'for', 'and', 'or', 'is', 'are', 'page', 'route',
    'navigate', 'navigation', 'file', 'code', 'from',
}

_NAV_KEYWORDS = (
    'router', 'route', 'navigate', 'redirect', 'push', 'replace',
    'router-link', 'urlpatterns', 'createRouter', 'useRouter', 'useRoute',
    'path(', 're_path', 'include(', 'window.location', 'href',
)

_ROUTE_FILE_HINTS = (
    'router', 'route', 'routes', 'urls', 'url', 'navigation', 'nav', 'menu',
)

_NAV_LINE_RE = re.compile(
    r'(router\.(?:push|replace|go)|navigateTo|navigate\(|'
    r'<router-link\b|to\s*[:=]\s*[\'"`]|'
    r'createRouter\s*\(|routes\s*[:=]|'
    r'path\s*\(|re_path\s*\(|urlpatterns\s*=|'
    r'redirect\s*[:(]|window\.location|location\.href)',
    re.I,
)

_ROUTE_DEF_RE = re.compile(
    r'''(?:path|name)\s*:\s*['"`]([^'"`]+)['"`]'''
    r'''|path\s*\(\s*['"`]([^'"`]+)['"`]'''
    r'''|['"`](/[^'"`]+)['"`]\s*,\s*(?:component|name|redirect)''',
    re.I,
)

_IMPORT_COMPONENT_RE = re.compile(
    r'''(?:component\s*:\s*)?(?:\(\)\s*=>\s*)?import\(\s*['"`]([^'"`]+)['"`]\s*\)'''
    r'''|component\s*:\s*(\w+)''',
    re.I,
)


def _tokenize_question(question: str) -> List[str]:
    q = question or ''
    tokens: List[str] = []

    def add(tok: str):
        t = (tok or '').strip().lower()
        if not t or t in _STOPWORDS or t.isdigit() or len(t) < 2:
            return
        if t not in tokens:
            tokens.append(t)

    # Latin / path-like tokens (\w is Unicode — avoid matching CJK)
    for m in re.findall(r'[A-Za-z][A-Za-z0-9_./@-]{1,}', q):
        add(m)
        for part in re.split(r'[./\\_-]+', m):
            add(part)

    # CamelCase pieces
    for m in re.findall(r'[A-Za-z]+(?:[A-Z][a-z0-9]+)+', q):
        add(m)

    # Chinese: keep runs + 2/3-grams for fuzzy file matching
    for run in re.findall(r'[\u4e00-\u9fff]{2,}', q):
        add(run)
        for n in (2, 3, 4):
            if len(run) < n:
                continue
            for i in range(0, len(run) - n + 1):
                add(run[i:i + n])

    # Domain hints that often appear in questions
    for hint in ('codegraph', 'router', 'route', 'workflow', '工作流', '图谱', '跳转', '路由'):
        if hint.lower() in q.lower() or hint in q:
            add(hint)

    return tokens[:36]


def _is_nav_question(question: str) -> bool:
    q = (question or '').lower()
    keys = (
        '跳转', '路由', '导航', '打开', '进入', '跳到', 'redirect', 'navigate',
        'router', 'route', 'page', '页面', '链接', '菜单', '入口',
    )
    return any(k in q for k in keys)


def _node_score(node: dict, tokens: List[str]) -> int:
    path = (node.get('path') or node.get('id') or '').lower()
    name = (node.get('name') or '').lower()
    module = (node.get('module') or '').lower()
    score = 0
    for t in tokens:
        if t in path:
            score += 6
        if t in name:
            score += 5
        if t in module:
            score += 2
        if any(h in path for h in _ROUTE_FILE_HINTS) and _is_token_nav_related(t):
            score += 2
    # Prefer route-ish files when asking about navigation
    if any(h in path or h in name for h in _ROUTE_FILE_HINTS):
        score += 3
    return score


def _is_token_nav_related(token: str) -> bool:
    return any(k in token for k in ('route', 'router', 'nav', 'page', 'view', 'url'))


def _search_nodes(nodes: List[dict], tokens: List[str], limit: int = 12) -> List[dict]:
    scored = []
    for n in nodes:
        if n.get('type') == 'function':
            continue
        s = _node_score(n, tokens)
        if s > 0:
            scored.append((s, n))
    scored.sort(key=lambda x: (-x[0], x[1].get('path') or ''))
    return [n for _, n in scored[:limit]]


def _build_adjacency(edges: List[dict]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    fwd: Dict[str, Set[str]] = defaultdict(set)
    rev: Dict[str, Set[str]] = defaultdict(set)
    for e in edges:
        s, t = e.get('source'), e.get('target')
        if not s or not t:
            continue
        if '::' in str(s) or '::' in str(t):
            continue
        fwd[s].add(t)
        rev[t].add(s)
    return fwd, rev


def _neighbors(node_id: str, fwd, rev, node_by_id: Dict[str, dict], hops: int = 1) -> List[dict]:
    if not node_id or node_id not in node_by_id:
        return []
    seen = {node_id}
    frontier = {node_id}
    out = []
    for _ in range(max(1, hops)):
        nxt = set()
        for cur in frontier:
            for nb in list(fwd.get(cur, [])) + list(rev.get(cur, [])):
                if nb in seen:
                    continue
                seen.add(nb)
                nxt.add(nb)
                node = node_by_id.get(nb)
                if node:
                    out.append(node)
        frontier = nxt
    return out[:20]


def _shortest_path(
    start_id: str,
    goal_ids: Set[str],
    fwd: Dict[str, Set[str]],
) -> List[str]:
    if not start_id or not goal_ids:
        return []
    if start_id in goal_ids:
        return [start_id]
    q = deque([start_id])
    parent = {start_id: None}
    while q:
        cur = q.popleft()
        for nb in fwd.get(cur, []):
            if nb in parent:
                continue
            parent[nb] = cur
            if nb in goal_ids:
                path = [nb]
                while path[-1] is not None and parent[path[-1]] is not None:
                    path.append(parent[path[-1]])
                path.reverse()
                return path
            q.append(nb)
    return []


def _read_file(project_path: str, rel: str) -> Optional[str]:
    full = os.path.realpath(os.path.join(project_path, rel))
    base = os.path.realpath(project_path)
    try:
        if os.path.commonpath([base, full]) != base:
            return None
    except ValueError:
        return None
    if not os.path.isfile(full):
        return None
    try:
        with open(full, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except OSError:
        return None


def _extract_nav_hits(content: str, rel_path: str) -> List[dict]:
    hits = []
    lines = content.splitlines()
    for i, line in enumerate(lines, start=1):
        if not _NAV_LINE_RE.search(line):
            continue
        start = max(1, i - 2)
        end = min(len(lines), i + 2)
        snippet = '\n'.join(lines[start - 1:end])
        routes = []
        for m in _ROUTE_DEF_RE.finditer(line):
            val = next((g for g in m.groups() if g), None)
            if val:
                routes.append(val)
        components = []
        for m in _IMPORT_COMPONENT_RE.finditer('\n'.join(lines[max(0, i - 3):min(len(lines), i + 3)])):
            val = next((g for g in m.groups() if g), None)
            if val:
                components.append(val)
        hits.append({
            'path': rel_path,
            'name': os.path.basename(rel_path),
            'start_line': start,
            'end_line': end,
            'line': i,
            'snippet': snippet[:800],
            'routes': routes[:6],
            'components': components[:6],
            'reason': 'navigation/route pattern',
        })
        if len(hits) >= 24:
            break
    return hits


def _content_keyword_hits(content: str, rel_path: str, tokens: List[str]) -> List[dict]:
    if not tokens:
        return []
    lines = content.splitlines()
    hits = []
    lowered_tokens = [t for t in tokens if len(t) >= 2]
    for i, line in enumerate(lines, start=1):
        low = line.lower()
        matched = [t for t in lowered_tokens if t in low]
        if not matched:
            continue
        # Prefer denser matches
        if len(matched) < 1:
            continue
        start = max(1, i - 2)
        end = min(len(lines), i + 3)
        hits.append({
            'path': rel_path,
            'name': os.path.basename(rel_path),
            'start_line': start,
            'end_line': end,
            'line': i,
            'snippet': '\n'.join(lines[start - 1:end])[:800],
            'routes': [],
            'components': [],
            'reason': f"keyword match: {', '.join(matched[:4])}",
        })
        if len(hits) >= 8:
            break
    return hits


def _pick_candidate_files(
    project_path: str,
    nodes: List[dict],
    tokens: List[str],
    selected_path: Optional[str],
    nav_mode: bool,
) -> List[str]:
    ranked = _search_nodes(nodes, tokens, limit=16)
    paths: List[str] = []

    def add(p: Optional[str]):
        if not p:
            return
        p = p.replace('\\', '/')
        if p not in paths:
            paths.append(p)

    add(selected_path)
    for n in ranked:
        add(n.get('path'))

    # Always include likely router files for nav questions
    if nav_mode:
        for n in nodes:
            if n.get('type') == 'function':
                continue
            p = (n.get('path') or '').replace('\\', '/')
            low = p.lower()
            if any(h in low for h in _ROUTE_FILE_HINTS):
                add(p)
            if len(paths) >= 28:
                break

    # Fallback: scan a few high-centrality files
    if len(paths) < 6:
        by_c = sorted(
            [n for n in nodes if n.get('type') != 'function' and n.get('path')],
            key=lambda n: float(n.get('centrality') or 0),
            reverse=True,
        )
        for n in by_c[:8]:
            add(n.get('path'))

    # Keep only existing files
    existing = []
    for p in paths:
        full = os.path.join(project_path, p)
        if os.path.isfile(full):
            existing.append(p)
        if len(existing) >= 22:
            break
    return existing


def _collect_evidence(
    project_path: str,
    nodes: List[dict],
    edges: List[dict],
    question: str,
    selected_path: Optional[str] = None,
    selected_node_id: Optional[str] = None,
) -> Dict[str, Any]:
    tokens = _tokenize_question(question)
    nav_mode = _is_nav_question(question)
    node_by_id = {n['id']: n for n in nodes if n.get('id')}
    path_to_node = {
        (n.get('path') or '').replace('\\', '/'): n
        for n in nodes if n.get('path') and n.get('type') != 'function'
    }
    fwd, rev = _build_adjacency(edges)

    selected = None
    if selected_node_id and selected_node_id in node_by_id:
        selected = node_by_id[selected_node_id]
    elif selected_path:
        selected = path_to_node.get(selected_path.replace('\\', '/'))

    candidate_paths = _pick_candidate_files(
        project_path, nodes, tokens, selected_path or (selected or {}).get('path'), nav_mode,
    )

    references: List[dict] = []
    seen_ref_keys: Set[str] = set()

    def push_ref(ref: dict):
        key = f"{ref.get('path')}:{ref.get('start_line')}:{ref.get('end_line')}"
        if key in seen_ref_keys:
            return
        seen_ref_keys.add(key)
        references.append(ref)

    for rel in candidate_paths:
        content = _read_file(project_path, rel)
        if content is None:
            continue
        if nav_mode or any(k in content[:4000].lower() for k in _NAV_KEYWORDS):
            for hit in _extract_nav_hits(content, rel):
                push_ref(hit)
        for hit in _content_keyword_hits(content, rel, tokens):
            push_ref(hit)

    # Prefer nav hits first, then keyword hits; cap
    references.sort(
        key=lambda r: (
            0 if 'navigation' in (r.get('reason') or '') else 1,
            r.get('path') or '',
            r.get('start_line') or 0,
        )
    )
    references = references[:18]

    related_nodes = _search_nodes(nodes, tokens, limit=10)
    if selected:
        related_nodes = [selected] + [n for n in related_nodes if n.get('id') != selected.get('id')]

    # Graph path from selected view toward a router file
    graph_paths = []
    if selected and selected.get('id'):
        router_ids = {
            n['id'] for n in nodes
            if n.get('type') != 'function'
            and any(h in (n.get('path') or '').lower() for h in _ROUTE_FILE_HINTS)
        }
        # Path from router -> page (import direction) is more common
        for rid in list(router_ids)[:12]:
            path = _shortest_path(rid, {selected['id']}, fwd)
            if path and len(path) > 1:
                path_files = [node_by_id[i].get('path') for i in path if i in node_by_id]
                graph_paths.append({
                    'from': path_files[0] if path_files else None,
                    'to': selected.get('path'),
                    'node_ids': path,
                    'paths': path_files,
                })
                break
        # Also reverse: page imports something that leads to router (rare)
        if not graph_paths:
            path = _shortest_path(selected['id'], router_ids, fwd)
            if path and len(path) > 1:
                path_files = [node_by_id[i].get('path') for i in path if i in node_by_id]
                graph_paths.append({
                    'from': selected.get('path'),
                    'to': path_files[-1] if path_files else None,
                    'node_ids': path,
                    'paths': path_files,
                })

    neighbor_nodes = []
    if selected and selected.get('id'):
        neighbor_nodes = _neighbors(selected['id'], fwd, rev, node_by_id, hops=1)

    return {
        'tokens': tokens,
        'nav_mode': nav_mode,
        'selected': {
            'id': selected.get('id'),
            'path': selected.get('path'),
            'name': selected.get('name'),
            'module': selected.get('module'),
        } if selected else None,
        'related_nodes': [
            {
                'id': n.get('id'),
                'path': n.get('path'),
                'name': n.get('name'),
                'module': n.get('module'),
                'type': n.get('type'),
            }
            for n in related_nodes[:10]
        ],
        'neighbors': [
            {
                'id': n.get('id'),
                'path': n.get('path'),
                'name': n.get('name'),
            }
            for n in neighbor_nodes[:12]
        ],
        'graph_paths': graph_paths[:3],
        'references': references,
        'candidate_files': candidate_paths[:16],
    }


def _format_evidence_for_prompt(evidence: Dict[str, Any]) -> str:
    parts = []
    if evidence.get('selected'):
        s = evidence['selected']
        parts.append(f"当前选中文件: {s.get('path')} (module={s.get('module')})")
    if evidence.get('related_nodes'):
        lines = [f"- {n.get('path')}" for n in evidence['related_nodes'][:8]]
        parts.append('相关文件:\n' + '\n'.join(lines))
    if evidence.get('neighbors'):
        lines = [f"- {n.get('path')}" for n in evidence['neighbors'][:8]]
        parts.append('依赖邻居:\n' + '\n'.join(lines))
    if evidence.get('graph_paths'):
        for gp in evidence['graph_paths']:
            chain = ' → '.join(gp.get('paths') or [])
            parts.append(f"依赖路径: {chain}")
    if evidence.get('references'):
        blocks = []
        for idx, ref in enumerate(evidence['references'][:_MAX_SNIPPET_FILES], start=1):
            blocks.append(
                f"[#{idx}] {ref['path']}:{ref['start_line']}-{ref['end_line']}\n"
                f"原因: {ref.get('reason')}\n"
                f"```\n{ref.get('snippet', '')}\n```"
            )
        parts.append('代码证据:\n' + '\n\n'.join(blocks))
    text = '\n\n'.join(parts)
    if len(text) > _MAX_CONTEXT_CHARS:
        text = text[:_MAX_CONTEXT_CHARS] + '\n…(context truncated)'
    return text


def _heuristic_answer(question: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    refs = evidence.get('references') or []
    related = evidence.get('related_nodes') or []
    lines = ['根据代码图谱检索，未调用到 LLM，以下是规则匹配结果：', '']
    if evidence.get('nav_mode') and refs:
        lines.append('### 跳转 / 路由相关代码')
        for r in refs[:8]:
            lines.append(
                f"- `{r['path']}` 第 {r['start_line']}-{r['end_line']} 行：{r.get('reason')}"
            )
            if r.get('snippet'):
                lines.append(f"```\n{r['snippet']}\n```")
        lines.append('')
    if related:
        lines.append('### 相关文件')
        for n in related[:8]:
            lines.append(f"- `{n.get('path')}`")
    if evidence.get('graph_paths'):
        lines.append('### 依赖路径')
        for gp in evidence['graph_paths']:
            lines.append('- ' + ' → '.join(gp.get('paths') or []))
    if len(lines) <= 2:
        lines.append('暂未找到足够证据。请尝试点选相关页面/路由文件后再问，或使用更具体的页面名、路由 path。')
    return {
        'answer': '\n'.join(lines),
        'references': refs[:12],
        'related_nodes': related[:10],
        'graph_paths': evidence.get('graph_paths') or [],
        'source': 'heuristic',
    }


def _parse_llm_answer(raw: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    answer = (raw or '').strip()
    refs = list(evidence.get('references') or [])

    # Try extract trailing JSON block for structured refs
    m = re.search(r'```json\s*(\{.*?\})\s*```', answer, flags=re.S)
    if m:
        try:
            payload = json.loads(m.group(1))
            if isinstance(payload.get('answer'), str) and payload['answer'].strip():
                answer = payload['answer'].strip()
            elif 'answer' not in payload:
                # Remove json fence from display
                answer = answer[: m.start()].strip()
            else:
                answer = answer[: m.start()].strip() or answer
            llm_refs = payload.get('references') or []
            merged = []
            seen = set()
            for r in list(llm_refs) + refs:
                if not isinstance(r, dict) or not r.get('path'):
                    continue
                key = f"{r.get('path')}:{r.get('start_line')}:{r.get('end_line')}"
                if key in seen:
                    continue
                seen.add(key)
                merged.append({
                    'path': r.get('path'),
                    'name': r.get('name') or os.path.basename(str(r.get('path'))),
                    'start_line': r.get('start_line') or r.get('line') or 1,
                    'end_line': r.get('end_line') or r.get('start_line') or r.get('line') or 1,
                    'snippet': (r.get('snippet') or '')[:800],
                    'reason': r.get('reason') or 'cited',
                })
            refs = merged[:16]
        except Exception:
            pass

    return {
        'answer': answer,
        'references': refs[:16],
        'related_nodes': evidence.get('related_nodes') or [],
        'graph_paths': evidence.get('graph_paths') or [],
        'source': 'llm',
    }


def ask_codegraph(
    *,
    project_path: str,
    project_name: str,
    nodes: List[dict],
    edges: List[dict],
    question: str,
    history: Optional[List[dict]] = None,
    selected_path: Optional[str] = None,
    selected_node_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Answer a CodeGraph analysis question with file/line citations.
    """
    question = (question or '').strip()
    if not question:
        return {
            'answer': '请先输入你的问题，例如：「CodeGraph 页面是如何跳转打开的？」',
            'references': [],
            'related_nodes': [],
            'graph_paths': [],
            'source': 'empty',
        }

    evidence = _collect_evidence(
        project_path=project_path,
        nodes=nodes or [],
        edges=edges or [],
        question=question,
        selected_path=selected_path,
        selected_node_id=selected_node_id,
    )

    history_lines = []
    for item in (history or [])[-6]:
        role = item.get('role') or 'user'
        content = (item.get('content') or '').strip()
        if content:
            history_lines.append(f'{role}: {content[:600]}')

    system = (
        '你是 CodeGraph 代码分析助手，擅长解释前端路由跳转、页面入口、模块依赖与调用关系。\n'
        '规则：\n'
        '1) 只依据提供的「代码证据 / 依赖路径 / 相关文件」回答，禁止编造不存在的文件或行号。\n'
        '2) 回答用简洁中文，结构清晰：结论 → 跳转链路/关键步骤 → 文件与行号 → 简短代码说明。\n'
        '3) 提到文件时必须给出路径，尽量带行号（如 `src/router/index.js:42-58`）。\n'
        '4) 若证据不足，明确说明缺什么，并建议用户点选哪个文件再问。\n'
        '5) 在回答末尾附加一个 JSON 代码块（```json ... ```），格式：\n'
        '{"answer":"可展示的完整回答文本","references":[{"path":"...","start_line":1,"end_line":10,"reason":"..."}]}\n'
        'references 只能引用证据中出现过的 path。'
    )

    user = (
        f'项目: {project_name}\n'
        f'问题: {question}\n\n'
        f'对话历史:\n{chr(10).join(history_lines) if history_lines else "(无)"}\n\n'
        f'{_format_evidence_for_prompt(evidence)}'
    )

    raw = _invoke_llm(system, user, temperature=0.2, max_tokens=2200)
    if not raw:
        result = _heuristic_answer(question, evidence)
    else:
        result = _parse_llm_answer(raw, evidence)

    result['tokens'] = evidence.get('tokens') or []
    result['nav_mode'] = bool(evidence.get('nav_mode'))
    result['selected'] = evidence.get('selected')
    return result
