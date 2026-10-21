"""
n8n open-source workflow corpus for 语创 Soft RAG.

Builds searchable training summaries from imported `[n8n]` Workflows so NL
generation can retrieve structure/node-type patterns. Full graphs are NEVER
pasted into the final answer — only compact summaries / topology hints.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

N8N_NAME_PREFIX = '[n8n]'
N8N_TAGS = frozenset({'n8n-import', 'n8n-batch'})
SKIP_NODE_TYPES = frozenset({'start', 'end'})
PLACEHOLDER_TYPES = frozenset({'variable', 'code'})

_CORPUS_LOCK = threading.RLock()
_CORPUS_CACHE: Optional[List['N8nCorpusEntry']] = None
_CORPUS_MTIME: Optional[float] = None


def default_corpus_path() -> Path:
    configured = getattr(settings, 'NL_WORKFLOW_N8N_CORPUS_PATH', '') or ''
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR) / 'data' / 'n8n_training_corpus.json'


@dataclass
class N8nCorpusEntry:
    id: str
    name: str
    clean_name: str
    description: str
    category: str
    tags: List[str]
    node_types: List[str]
    node_type_sequence: str
    node_count: int
    edge_count: int
    search_text: str
    structure_summary: str
    quality_score: float
    source: str
    n8n_source_path: str
    compact_example: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'N8nCorpusEntry':
        return cls(
            id=str(data.get('id') or ''),
            name=str(data.get('name') or ''),
            clean_name=str(data.get('clean_name') or ''),
            description=str(data.get('description') or ''),
            category=str(data.get('category') or 'n8n'),
            tags=list(data.get('tags') or []),
            node_types=list(data.get('node_types') or []),
            node_type_sequence=str(data.get('node_type_sequence') or ''),
            node_count=int(data.get('node_count') or 0),
            edge_count=int(data.get('edge_count') or 0),
            search_text=str(data.get('search_text') or ''),
            structure_summary=str(data.get('structure_summary') or ''),
            quality_score=float(data.get('quality_score') or 0.0),
            source=str(data.get('source') or 'n8n-import'),
            n8n_source_path=str(data.get('n8n_source_path') or ''),
            compact_example=dict(data.get('compact_example') or {}),
        )


def _clean_workflow_name(name: str) -> str:
    text = (name or '').strip()
    if text.startswith(N8N_NAME_PREFIX):
        text = text[len(N8N_NAME_PREFIX):].strip()
    # Drop trailing "(filename_stem)" often appended during import
    text = re.sub(r'\s*\([^)]*_[0-9A-Za-z]+\)\s*$', '', text).strip()
    return text or name


def _infer_category(source_path: str, tags: Sequence[str], node_types: Sequence[str]) -> str:
    path = (source_path or '').replace('\\', '/')
    parts = [p for p in path.split('/') if p]
    # .../workflows/<Vendor>/<file>.json
    if 'workflows' in parts:
        idx = parts.index('workflows')
        if idx + 1 < len(parts):
            vendor = parts[idx + 1]
            if vendor and not vendor.endswith('.json'):
                return vendor.lower()
    type_set = set(node_types)
    if {'email', 'gmail'} & type_set or 'email' in type_set:
        return 'email'
    if {'slack', 'discord', 'telegram', 'microsoft_teams'} & type_set:
        return 'communication'
    if {'google_sheets', 'airtable', 'postgres', 'mysql', 'mongodb'} & type_set:
        return 'data'
    if 'http_request' in type_set:
        return 'http'
    if tags:
        return str(tags[0])
    return 'n8n'


def _tokenize(text: str) -> List[str]:
    raw = (text or '').lower()
    parts = re.findall(r'[a-z0-9_\u4e00-\u9fff]{2,}', raw)
    return parts


def compute_quality_score(
    *,
    node_types: Sequence[str],
    edge_count: int,
    unmapped_nodes: int = 0,
    has_n8n_params: bool = True,
) -> float:
    meaningful = [t for t in node_types if t not in SKIP_NODE_TYPES]
    if not meaningful:
        return 0.0
    score = 0.35
    score += min(0.25, len(meaningful) * 0.03)
    score += min(0.15, edge_count * 0.02)
    unique_ratio = len(set(meaningful)) / max(len(meaningful), 1)
    score += 0.1 * unique_ratio
    placeholder_ratio = sum(1 for t in meaningful if t in PLACEHOLDER_TYPES) / len(meaningful)
    score -= 0.25 * placeholder_ratio
    if unmapped_nodes:
        score -= min(0.4, unmapped_nodes * 0.05)
    if has_n8n_params:
        score += 0.05
    # Prefer graphs that are more than trigger→end
    if len(meaningful) >= 3 and edge_count >= 2:
        score += 0.1
    return max(0.0, min(1.0, round(score, 4)))


def summarize_workflow_for_corpus(workflow) -> Optional[N8nCorpusEntry]:
    """Build one corpus entry from a Django Workflow instance."""
    nodes_qs = list(workflow.nodes.all().order_by('sort_order', 'created_at'))
    if not nodes_qs:
        return None

    node_types: List[str] = []
    node_labels: List[str] = []
    id_to_type: Dict[str, str] = {}
    compact_nodes: List[Dict[str, str]] = []
    unmapped = 0

    for node in nodes_qs:
        ntype = (node.node_type or 'unknown').strip()
        node_types.append(ntype)
        label = (node.name or ntype)[:80]
        node_labels.append(label)
        id_to_type[str(node.id)] = ntype
        cfg = node.config if isinstance(node.config, dict) else {}
        if cfg.get('n8n_unmapped'):
            unmapped += 1
        if ntype not in SKIP_NODE_TYPES:
            compact_nodes.append({'type': ntype, 'name': label})

    edges_qs = list(workflow.edges.all())
    compact_edges: List[Dict[str, str]] = []
    for edge in edges_qs:
        src_node = getattr(edge, 'source_node', None)
        tgt_node = getattr(edge, 'target_node', None)
        src = ''
        tgt = ''
        if src_node is not None:
            src = id_to_type.get(str(src_node.id), '') or (src_node.node_type or '')
        if tgt_node is not None:
            tgt = id_to_type.get(str(tgt_node.id), '') or (tgt_node.node_type or '')
        if src and tgt:
            compact_edges.append({'source_type': src, 'target_type': tgt})

    cfg = workflow.config if isinstance(workflow.config, dict) else {}
    source_path = str(cfg.get('n8n_source_path') or '')
    tags = list(workflow.tags or [])
    if 'n8n-import' not in tags:
        tags = ['n8n-import', *tags]

    clean_name = _clean_workflow_name(workflow.name or '')
    category = _infer_category(source_path, tags, node_types)
    sequence = ' -> '.join(node_types[:24])
    if len(node_types) > 24:
        sequence += ' -> ...'

    description = (workflow.description or '').strip()
    # Strip import meta footer noise for search
    description = re.sub(
        r'\n*Imported from n8n.*$',
        '',
        description,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    structure_summary = (
        f"{clean_name} | category={category} | nodes={len(nodes_qs)} edges={len(edges_qs)} | "
        f"flow: {sequence}"
    )
    search_text = ' '.join([
        clean_name,
        description[:500],
        category,
        ' '.join(tags),
        ' '.join(node_types),
        ' '.join(node_labels[:30]),
        source_path.replace('/', ' ').replace('\\', ' '),
    ]).lower()

    quality = compute_quality_score(
        node_types=node_types,
        edge_count=len(edges_qs),
        unmapped_nodes=unmapped,
    )

    return N8nCorpusEntry(
        id=str(workflow.id),
        name=workflow.name or clean_name,
        clean_name=clean_name,
        description=description[:800],
        category=category,
        tags=tags,
        node_types=node_types,
        node_type_sequence=sequence,
        node_count=len(nodes_qs),
        edge_count=len(edges_qs),
        search_text=search_text,
        structure_summary=structure_summary,
        quality_score=quality,
        source='n8n-import',
        n8n_source_path=source_path,
        compact_example={
            'name': clean_name,
            'nodes': compact_nodes[:40],
            'edges': compact_edges[:50],
        },
    )


def queryset_n8n_workflows():
    from workflows.models import Workflow

    return (
        Workflow.objects.filter(is_deleted=False)
        .filter(name__startswith=N8N_NAME_PREFIX)
        .prefetch_related('nodes', 'edges')
        .order_by('name')
    )


def build_corpus_from_db(
    *,
    min_quality: float = 0.25,
    min_nodes: int = 2,
    limit: Optional[int] = None,
) -> List[N8nCorpusEntry]:
    from workflows.models import Workflow

    entries: List[N8nCorpusEntry] = []
    ids = list(queryset_n8n_workflows().values_list('id', flat=True))
    if limit:
        ids = ids[:limit]
    for i in range(0, len(ids), 80):
        chunk = (
            Workflow.objects.filter(id__in=ids[i:i + 80])
            .prefetch_related('nodes', 'edges__source_node', 'edges__target_node')
        )
        for workflow in chunk:
            entry = summarize_workflow_for_corpus(workflow)
            if not entry:
                continue
            if entry.node_count < min_nodes:
                continue
            if entry.quality_score < min_quality:
                continue
            entries.append(entry)
    entries.sort(key=lambda e: (-e.quality_score, e.clean_name.lower()))
    return entries


def save_corpus(entries: Sequence[N8nCorpusEntry], path: Optional[Path] = None) -> Path:
    out = path or default_corpus_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'version': 1,
        'source': 'n8n-open-workflows',
        'count': len(entries),
        'entries': [e.to_dict() for e in entries],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    invalidate_corpus_cache()
    return out


def load_corpus(path: Optional[Path] = None, *, force_reload: bool = False) -> List[N8nCorpusEntry]:
    global _CORPUS_CACHE, _CORPUS_MTIME
    corpus_path = path or default_corpus_path()
    with _CORPUS_LOCK:
        mtime = corpus_path.stat().st_mtime if corpus_path.exists() else None
        if (
            not force_reload
            and _CORPUS_CACHE is not None
            and mtime is not None
            and _CORPUS_MTIME == mtime
        ):
            return _CORPUS_CACHE

        if not corpus_path.exists():
            _CORPUS_CACHE = []
            _CORPUS_MTIME = None
            return _CORPUS_CACHE

        data = json.loads(corpus_path.read_text(encoding='utf-8'))
        raw_entries = data.get('entries') if isinstance(data, dict) else data
        entries = [
            N8nCorpusEntry.from_dict(item)
            for item in (raw_entries or [])
            if isinstance(item, dict)
        ]
        _CORPUS_CACHE = entries
        _CORPUS_MTIME = mtime
        return entries


def invalidate_corpus_cache() -> None:
    global _CORPUS_CACHE, _CORPUS_MTIME
    with _CORPUS_LOCK:
        _CORPUS_CACHE = None
        _CORPUS_MTIME = None


def _score_entry(query_tokens: Sequence[str], entry: N8nCorpusEntry) -> float:
    if not query_tokens:
        return entry.quality_score * 0.2
    hay = entry.search_text
    type_blob = ' '.join(entry.node_types)
    score = 0.0
    hits = 0
    for tok in query_tokens:
        if tok in hay:
            hits += 1
            score += 1.0
            if tok in entry.clean_name.lower():
                score += 1.5
            if tok in type_blob:
                score += 0.8
            if tok in (entry.category or '').lower():
                score += 0.6
    if hits == 0:
        return 0.0
    coverage = hits / max(len(query_tokens), 1)
    score = score * (0.5 + 0.5 * coverage)
    score += entry.quality_score * 0.5
    # Prefer richer graphs slightly
    score += min(0.3, entry.node_count * 0.01)
    return score


def search_n8n_corpus(
    query: str,
    *,
    limit: int = 5,
    min_score: float = 0.5,
    path: Optional[Path] = None,
) -> List[Tuple[N8nCorpusEntry, float]]:
    entries = load_corpus(path)
    if not entries:
        return []
    tokens = _tokenize(query)
    scored: List[Tuple[N8nCorpusEntry, float]] = []
    for entry in entries:
        score = _score_entry(tokens, entry)
        if score >= min_score:
            scored.append((entry, score))
    scored.sort(key=lambda item: (-item[1], -item[0].quality_score))
    return scored[: max(1, limit)]


def format_corpus_reference(
    query: str,
    *,
    limit: Optional[int] = None,
    include_compact_example: bool = True,
    path: Optional[Path] = None,
) -> str:
    """Soft RAG text block for NL generation prompts."""
    if not getattr(settings, 'NL_WORKFLOW_USE_N8N_CORPUS', True):
        return ''
    limit = limit or int(getattr(settings, 'NL_WORKFLOW_N8N_CORPUS_LIMIT', 3) or 3)
    hits = search_n8n_corpus(query, limit=limit, path=path)
    if not hits:
        # Fallback: top quality examples so cold queries still get patterns
        entries = load_corpus(path)
        if not entries:
            return ''
        hits = [(e, e.quality_score) for e in entries[:limit]]

    lines = [
        '以下是 n8n 开源工作流训练语料中的相似结构摘要（仅供启发节点组合与拓扑，禁止整图复制）：',
    ]
    for idx, (entry, score) in enumerate(hits, start=1):
        lines.append(
            f"{idx}. {entry.clean_name} [{entry.category}] "
            f"score={score:.2f} quality={entry.quality_score:.2f} "
            f"nodes={entry.node_count}"
        )
        if entry.description:
            lines.append(f"   描述: {entry.description[:140]}")
        lines.append(f"   拓扑: {entry.node_type_sequence}")
        if include_compact_example and entry.compact_example:
            nodes = entry.compact_example.get('nodes') or []
            preview = ', '.join(
                f"{n.get('type')}:{n.get('name')}" for n in nodes[:8] if isinstance(n, dict)
            )
            if preview:
                lines.append(f"   节点预览: {preview}")
    return '\n'.join(lines)


def promote_entries_to_templates(
    entries: Sequence[N8nCorpusEntry],
    *,
    max_promote: int = 200,
    user=None,
) -> Dict[str, int]:
    """
    Promote top corpus entries into WorkflowTemplate for marketplace/RAG reuse.
    Stores compact topology in workflow_data (not full n8n credentials).
    """
    from workflows.models import TemplateCategory, WorkflowTemplate, Workflow

    category, _ = TemplateCategory.objects.get_or_create(
        slug='n8n-community',
        defaults={
            'name': 'n8n Community',
            'description': 'Imported open-source n8n workflow patterns for 语创 Soft RAG',
            'icon': 'workflow',
            'color': '#ea4b71',
            'sort_order': 80,
            'is_active': True,
        },
    )

    created = 0
    updated = 0
    skipped = 0
    for entry in list(entries)[:max_promote]:
        if entry.quality_score < 0.35:
            skipped += 1
            continue
        tag = f'n8n-corpus:{entry.id}'
        short_id = entry.id.replace('-', '')[:8]
        template_name = f'[n8n] {entry.clean_name} ({short_id})'[:200]
        existing = (
            WorkflowTemplate.objects.filter(required_apis__contains=[tag]).first()
            or WorkflowTemplate.objects.filter(category=category, name=template_name).first()
        )
        workflow_data = {
            'nodes': entry.compact_example.get('nodes') or [],
            'edges': entry.compact_example.get('edges') or [],
            'meta': {
                'source': 'n8n-corpus',
                'workflow_id': entry.id,
                'node_type_sequence': entry.node_type_sequence,
            },
        }
        try:
            wf = (
                Workflow.objects.filter(id=entry.id, is_deleted=False)
                .prefetch_related('nodes', 'edges__source_node', 'edges__target_node')
                .first()
            )
            if wf:
                live_nodes = []
                for node in wf.nodes.all().order_by('sort_order', 'created_at'):
                    nid = str(node.id)
                    live_nodes.append({
                        'id': nid,
                        'type': node.node_type,
                        'name': node.name,
                        'position': {
                            'x': float(node.position_x or 0),
                            'y': float(node.position_y or 0),
                        },
                        'data': {
                            'label': node.name,
                            'config': {
                                k: v for k, v in (node.config or {}).items()
                                if k not in ('n8n_credentials',)
                            },
                        },
                    })
                live_edges = []
                for edge in wf.edges.all():
                    src = str(edge.source_node_id) if edge.source_node_id else ''
                    tgt = str(edge.target_node_id) if edge.target_node_id else ''
                    if src and tgt:
                        live_edges.append({
                            'id': str(edge.id),
                            'source': src,
                            'target': tgt,
                        })
                if live_nodes:
                    workflow_data = {
                        'nodes': live_nodes,
                        'edges': live_edges,
                        'meta': {
                            'source': 'n8n-corpus',
                            'workflow_id': entry.id,
                            'node_type_sequence': entry.node_type_sequence,
                        },
                    }
        except Exception as exc:
            logger.debug('live workflow hydrate failed for %s: %s', entry.id, exc)

        defaults = {
            'category': category,
            'name': template_name,
            'description': (
                entry.description
                or f'n8n community pattern: {entry.node_type_sequence}'
            )[:4000],
            'difficulty': 'intermediate' if entry.node_count >= 6 else 'beginner',
            'tags': list({*entry.tags, 'n8n-corpus', 'flowspeak-training', tag}),
            'required_apis': [tag, 'n8n-open-source'],
            'workflow_data': workflow_data,
            'is_active': True,
            'is_public': True,
            'is_verified': False,
            'is_featured': entry.quality_score >= 0.7,
            'created_by': user,
        }
        if existing:
            for key, value in defaults.items():
                setattr(existing, key, value)
            existing.save()
            updated += 1
        else:
            WorkflowTemplate.objects.create(**defaults)
            created += 1

    return {'created': created, 'updated': updated, 'skipped': skipped}


def corpus_stats(path: Optional[Path] = None) -> Dict[str, Any]:
    entries = load_corpus(path)
    categories: Dict[str, int] = {}
    for e in entries:
        categories[e.category] = categories.get(e.category, 0) + 1
    return {
        'count': len(entries),
        'path': str(path or default_corpus_path()),
        'avg_quality': round(sum(e.quality_score for e in entries) / len(entries), 4) if entries else 0.0,
        'categories': dict(sorted(categories.items(), key=lambda kv: -kv[1])[:30]),
    }
