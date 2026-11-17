"""Local readiness evidence; configuration never impersonates an upstream health check."""
import copy
import importlib.util
from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from core.llm_factory import _resolve_provider, _is_ollama_endpoint
from core.runtime_config import resolve_default_chat_model
from rag.constants import DEFAULT_CANDIDATE_LIMIT
from .services import ApplicationFailure, resolve_source


def chat_configuration():
    model = getattr(settings, 'RAG_CHAT_MODEL', '') or resolve_default_chat_model()
    key = getattr(settings, 'RAG_CHAT_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')
    explicit_base = getattr(settings, 'RAG_CHAT_BASE_URL', '')
    base = explicit_base or getattr(settings, 'OPENAI_BASE_URL', '')
    provider = _resolve_provider(model, key, base)
    if explicit_base and not _is_ollama_endpoint(explicit_base):
        provider = 'azure' if 'azure' in explicit_base.lower() else 'openai'
    return {'model': model, 'provider': provider, 'configured': bool(model and (provider == 'ollama' or key)),
            'credential_source': 'platform', 'connection_verified': False}


def _entry(code, label, status, detail, path=None):
    return {'code': code, 'label': label, 'status': status, 'detail': detail, 'repair_path': path}


def inspect_target(application, release=None):
    configuration = release.configuration if release else application.draft
    checks, inputs = [], []
    result = {'target': 'release' if release else 'draft', 'release_id': str(release.pk) if release else None,
        'checked_at': timezone.now(), 'checks': checks, 'inputs': inputs, 'configuration_ready': False,
        'connection_verified': False, 'knowledge_content_policy': 'live' if application.kind == 'knowledge' else None}
    try:
        from .access import can_edit
        if not can_edit(application.owner, application):
            raise ApplicationFailure('应用所有者已停用或失去所属空间的执行权限。', 'permission_revoked', 403)
        if application.kind == 'workflow' and release:
            source = release.workflow_snapshot
            if not source:
                raise ApplicationFailure('发布版本的工作流快照不可用。', 'source_unavailable', 409)
        else:
            source = resolve_source(application, configuration)
        result['source'] = {'id': str(source.pk), 'name': source.name}
        checks.append(_entry('source', '资源归属', 'pass', '当前资源可访问，归属与应用一致。'))
    except ApplicationFailure as exc:
        checks.append(_entry('source', '资源归属', 'blocked', str(exc)))
        return result
    if application.kind == 'workflow':
        from workflows.services.workflow_validation import validate_workflow
        validation = validate_workflow(source, {})
        blockers = [row for row in validation['node_issues'] if row['severity'] == 'error' and row['code'] != 'missing_input']
        checks.extend(_entry(f'workflow_{index}', '工作流配置', 'blocked', row['message'], f'/workflows/{configuration.get("workflow_id")}/edit') for index, row in enumerate(blockers))
        if not blockers:
            checks.append(_entry('graph', '工作流配置', 'pass', '节点、连线与当前支持的配置检查通过。'))
        for node in source.nodes.filter(node_type='input'):
            config = node.config or {}
            inputs.append({'name': config.get('variable_name') or config.get('variableName') or 'input',
                'required': bool(config.get('required', False)), 'has_default': 'default_value' in config or 'defaultValue' in config})
        checks.append(_entry('execution', '外部依赖', 'not_checked', '模型、HTTP 与外部工具尚未实际调用；请用真实输入运行测试。'))
    else:
        from rag.models import Chunk, VectorStore
        from rag.pipeline import index_signature
        pinned = configuration.get('collection_settings')
        if pinned:
            source = copy.copy(source)
            for name, value in pinned['collection'].items():
                setattr(source, name, value)
            store = VectorStore.objects.filter(pk=pinned['vector_store_id']).first()
            if store is None or store.tenant_id != application.tenant_id or not application.tenant_id and store.owner_id != application.owner_id:
                checks.append(_entry('store', '检索存储', 'blocked', '已发布配置的向量存储已不可用。'))
                return result
            source.vector_store = copy.copy(store)
            for name, value in pinned['vector_store'].items():
                setattr(source.vector_store, name, value)
        path = f'/knowledge/{source.pk}'
        states = dict(source.documents.values('status').annotate(count=Count('id')).values_list('status', 'count'))
        chunks = Chunk.objects.filter(document__collection=source, document__status='completed')
        count = chunks.count()
        result['knowledge'] = {'retrieval_mode': source.retrieval_mode, 'documents': sum(states.values()),
            'completed_documents': states.get('completed', 0), 'processing_documents': states.get('processing', 0) + states.get('pending', 0),
            'failed_documents': states.get('failed', 0), 'available_chunks': count}
        checks.append(_entry('content', '知识内容', 'pass' if count else 'blocked',
            f'有 {count} 个已处理分块可检索。' if count else '还没有可检索内容，请先导入并处理文档。', path))
        if states.get('failed') or states.get('processing') or states.get('pending'):
            checks.append(_entry('partial_content', '文档处理', 'warning', '部分文档正在处理或处理失败，当前测试仅覆盖已完成内容。', path))
        if count > getattr(settings, 'RAG_CANDIDATE_LIMIT', DEFAULT_CANDIDATE_LIMIT):
            checks.append(_entry('candidate_limit', '检索容量', 'blocked', '分块数超过当前检索配置上限，请拆分知识库或调整服务端配置。', path))
        if source.retrieval_mode != 'keyword':
            expected = index_signature(source)
            stale = any(not row['embedding'] or row['metadata'].get('index_signature') != expected for row in chunks.values('embedding', 'metadata'))
            checks.append(_entry('index', '语义索引', 'blocked' if stale else 'pass',
                '索引缺失或配置已变化，请重新处理文档。' if stale else '当前已完成分块的索引签名一致。', path))
            model = source.embedding_model
            from config.constants import OLLAMA_MODEL_PREFIXES
            ollama = model.startswith('ollama:') or not model.startswith('openai:') and any(prefix in model.lower() for prefix in OLLAMA_MODEL_PREFIXES)
            configured = ollama or bool(getattr(settings, 'RAG_EMBEDDING_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', ''))
            checks.append(_entry('embedding', '嵌入服务配置', 'pass' if configured else 'blocked',
                '服务配置存在，连接尚未验证。' if configured else '平台未配置嵌入密钥，可配置真实嵌入服务或使用关键词检索。', path))
            result['embedding'] = {'model': model, 'provider': 'ollama' if ollama else 'openai',
                'configured': bool(configured), 'connection_verified': False, 'credential_source': 'platform'}
            drivers = {'qdrant': 'qdrant_client', 'milvus': 'pymilvus', 'chroma': 'chromadb', 'pinecone': 'pinecone', 'weaviate': 'weaviate'}
            driver = drivers.get(source.vector_store.store_type)
            if driver:
                try:
                    present = importlib.util.find_spec(driver) is not None
                except (ImportError, ValueError):
                    present = False
                checks.append(_entry('store_driver', '向量存储驱动', 'pass' if present else 'blocked',
                    '所需驱动可用，外部连接尚未验证。' if present else '缺少该向量后端的驱动，请让管理员安装后再测试连接。'))
        else:
            checks.append(_entry('embedding', '检索模式', 'pass', '关键词检索不需要嵌入模型或外部向量服务。'))
        chat = chat_configuration()
        result['chat'] = chat
        checks.append(_entry('chat', '回答服务配置', 'pass' if chat['configured'] else 'blocked',
            '平台回答服务配置存在，连接与回答质量尚未验证。' if chat['configured'] else '平台回答服务缺少配置，请联系管理员；模型页的个人密钥不会自动用于知识问答。'))
        checks.append(_entry('upstream', '实际连接', 'not_checked', '本检查不会向模型或向量服务发送请求。请运行真实应用测试验证连接和结果。'))
    result['configuration_ready'] = not any(row['status'] == 'blocked' for row in checks)
    return result


def application_readiness(application):
    return {'application_id': str(application.pk), 'checked_at': timezone.now(),
        'draft': inspect_target(application),
        'active_release': inspect_target(application, application.active_release) if application.active_release_id else None,
        'notice': '配置检查与真实连接测试不同。已发布仅表示版本激活，不能代表外部服务当前健康。'}
