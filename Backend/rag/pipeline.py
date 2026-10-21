"""Persistent RAG ingestion, retrieval and grounded generation."""
import hashlib
import json
import logging
import math
import uuid
from collections import defaultdict
from datetime import timedelta

import httpx
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from config.constants import OLLAMA_MODEL_PREFIXES
from core.runtime_config import resolve_default_embedding_model
from .constants import (
    DEFAULT_TOP_K, DEFAULT_MIN_SIMILARITY, MAX_TOP_K, LOCAL_STORE_TYPES,
    DEFAULT_REQUEST_TIMEOUT, DEFAULT_EMBEDDING_BATCH_SIZE, DEFAULT_CONTEXT_CHARS,
    DEFAULT_CANDIDATE_LIMIT, DEFAULT_MAX_QUERY_CHARS, DEFAULT_SYSTEM_PROMPT,
    GROUNDING_INSTRUCTION, NO_EVIDENCE_MESSAGE, RRF_OFFSET,
    DEFAULT_PROCESSING_LEASE_SECONDS,
)
from .parsing import validate_content, fetch_public_text
from .retrieval import keyword_scores, cosine_score, split_text

logger = logging.getLogger(__name__)


class RAGUnavailable(RuntimeError):
    """A dependency or index is unavailable; never substitute fabricated evidence."""


class EmbeddingService:
    def __init__(self, model=None):
        self.model = model or resolve_default_embedding_model()

    def embed_text(self, text):
        return self.embed_texts([text])[0]

    def embed_texts(self, texts):
        if not texts:
            return []
        explicit_ollama = self.model.startswith('ollama:')
        model = self.model.removeprefix('ollama:').removeprefix('openai:')
        ollama = explicit_ollama or (not self.model.startswith('openai:') and any(
            prefix in model.lower() for prefix in OLLAMA_MODEL_PREFIXES
        ))
        timeout = getattr(settings, 'RAG_REQUEST_TIMEOUT', DEFAULT_REQUEST_TIMEOUT)
        batch_size = getattr(settings, 'RAG_EMBEDDING_BATCH_SIZE', DEFAULT_EMBEDDING_BATCH_SIZE)
        vectors = []
        try:
            with httpx.Client(timeout=timeout, trust_env=False) as client:
                for offset in range(0, len(texts), batch_size):
                    batch = texts[offset:offset + batch_size]
                    if ollama:
                        base = settings.OLLAMA_BASE_URL.rstrip('/')
                        response = client.post(f'{base}/api/embed', json={'model': model, 'input': batch})
                        response.raise_for_status()
                        items = response.json()['embeddings']
                    else:
                        key = getattr(settings, 'RAG_EMBEDDING_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')
                        if not key:
                            raise RAGUnavailable('未配置嵌入 API Key。请配置真实嵌入模型，或使用关键词检索。')
                        base = (getattr(settings, 'RAG_EMBEDDING_BASE_URL', '') or settings.OPENAI_BASE_URL).rstrip('/')
                        response = client.post(f'{base}/embeddings', headers={'Authorization': f'Bearer {key}'},
                                               json={'model': model, 'input': batch})
                        response.raise_for_status()
                        data = sorted(response.json()['data'], key=lambda item: item['index'])
                        if [item['index'] for item in data] != list(range(len(batch))):
                            raise RAGUnavailable('嵌入服务返回的条目索引不完整。')
                        items = [item['embedding'] for item in data]
                    if len(items) != len(batch):
                        raise RAGUnavailable('嵌入服务返回的向量数量不匹配。')
                    vectors.extend(items)
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            logger.warning('Embedding request failed (%s)', type(exc).__name__)
            raise RAGUnavailable('嵌入服务不可用，请检查模型名称、地址、凭证和网络后重新处理。') from exc
        self.validate_vectors(vectors)
        return vectors

    @staticmethod
    def validate_vectors(vectors):
        dimension = len(vectors[0]) if vectors and isinstance(vectors[0], list) else 0
        if not dimension or any(not isinstance(v, list) or len(v) != dimension or any(
            not isinstance(x, (float, int)) or not math.isfinite(x) for x in v
        ) or not any(v) for v in vectors):
            raise RAGUnavailable('嵌入服务返回无效或维度不一致的向量。')


def index_signature(collection):
    return hashlib.sha256(json.dumps({
        'model': collection.embedding_model, 'mode': collection.retrieval_mode,
        'size': collection.chunk_size, 'overlap': collection.chunk_overlap,
        'strategy': collection.chunk_strategy,
    }, sort_keys=True).encode()).hexdigest()


def refresh_collection_stats(collection_id):
    from .models import DocumentCollection, Document, Chunk
    DocumentCollection.objects.filter(id=collection_id).update(
        document_count=Document.objects.filter(collection_id=collection_id).count(),
        chunk_count=Chunk.objects.filter(document__collection_id=collection_id).count(),
        updated_at=timezone.now(),
    )


class RAGService:
    def __init__(self, collection, top_k=DEFAULT_TOP_K, min_similarity=DEFAULT_MIN_SIMILARITY):
        self.collection = collection
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= MAX_TOP_K:
            raise ValueError(f'返回数量必须在 1 到 {MAX_TOP_K} 之间。')
        if not isinstance(min_similarity, (int, float)) or not math.isfinite(min_similarity) or not 0 <= min_similarity <= 1:
            raise ValueError('最低相关度必须在 0 到 1 之间。')
        self.top_k, self.min_similarity = top_k, min_similarity
        self.embedding_service = EmbeddingService(collection.embedding_model)
        self.vector_client = None

    @property
    def uses_external_store(self):
        return self.collection.vector_store.store_type not in LOCAL_STORE_TYPES

    def initialize(self):
        if self.collection.retrieval_mode != 'keyword' and self.uses_external_store and self.vector_client is None:
            from .services import get_vector_store_client
            try:
                self.vector_client = get_vector_store_client(self.collection.vector_store)
                if not self.vector_client or not self.vector_client.connect():
                    raise RAGUnavailable('向量存储连接失败。')
            except RAGUnavailable:
                raise
            except Exception as exc:
                raise RAGUnavailable('无法连接向量存储，请检查驱动、地址和凭证。') from exc
        return True

    def _get_collection_name(self):
        # A model change can change dimensions. Keep each model in an isolated index.
        model_key = hashlib.sha256(self.collection.embedding_model.encode()).hexdigest()[:12]
        return f'flowly_{self.collection.id.hex}_{model_key}'

    def process_document(self, content, metadata=None):
        content = validate_content(content)
        pieces = list(split_text(content, self.collection.chunk_size,
                                 self.collection.chunk_overlap, self.collection.chunk_strategy))
        embeddings = self.embedding_service.embed_texts([piece[0] for piece in pieces]) if self.collection.retrieval_mode != 'keyword' else [[] for _ in pieces]
        if len(embeddings) != len(pieces):
            raise RAGUnavailable('嵌入结果数量与分块不一致。')
        if self.collection.retrieval_mode != 'keyword':
            EmbeddingService.validate_vectors(embeddings)
        return [{
            'id': str(uuid.uuid4()), 'vector': embedding,
            'payload': {**(metadata or {}), 'content': text, 'chunk_index': index,
                        'start_char': start, 'end_char': end,
                        'vector_namespace': self._get_collection_name(),
                        'index_signature': index_signature(self.collection)},
        } for index, ((text, start, end), embedding) in enumerate(zip(pieces, embeddings))]

    def index_document(self, document, vectors):
        self.initialize()
        if self.vector_client and vectors:
            name = self._get_collection_name()
            if not self.vector_client.create_collection(name, len(vectors[0]['vector']), 'cosine'):
                raise RAGUnavailable('无法创建或打开向量集合。')
            if not self.vector_client.upsert(name, vectors):
                raise RAGUnavailable('向量写入失败。')
        return True

    def delete_vectors(self, vector_ids, namespace=None):
        if not vector_ids or not self.uses_external_store:
            return
        # Cleanup also works after changing retrieval mode to keyword.
        from .services import get_vector_store_client
        client = self.vector_client or get_vector_store_client(self.collection.vector_store)
        try:
            if not client.delete(namespace or self._get_collection_name(), vector_ids):
                raise RAGUnavailable('删除远程向量失败，请恢复向量服务后重试。')
        finally:
            if client is not self.vector_client:
                client.disconnect()

    def delete_chunk_vectors(self, chunks):
        groups = defaultdict(list)
        for chunk in chunks.exclude(embedding=[]):
            groups[chunk.metadata.get('vector_namespace') or f'flowly_{self.collection.id.hex}'].append(chunk.vector_id)
        for namespace, ids in groups.items():
            self.delete_vectors(ids, namespace)

    def retrieve(self, query, filters=None):
        from .models import Chunk
        if not isinstance(query, str) or not query.strip() or len(query) > getattr(settings, 'RAG_MAX_QUERY_CHARS', DEFAULT_MAX_QUERY_CHARS):
            raise ValueError('请输入有效且长度符合限制的查询。')
        filters = filters or {}
        if not isinstance(filters, dict) or any(not isinstance(k, str) or isinstance(v, (list, dict)) for k, v in filters.items()):
            raise ValueError('过滤条件必须为简单的元数据键值对象。')
        queryset = Chunk.objects.filter(document__collection=self.collection, document__status='completed').select_related('document')
        limit = getattr(settings, 'RAG_CANDIDATE_LIMIT', DEFAULT_CANDIDATE_LIMIT)
        if queryset.count() > limit:
            raise RAGUnavailable('知识库超过当前候选数量限制，请调整 RAG_CANDIDATE_LIMIT 或拆分知识库。')
        chunks = [c for c in queryset if all(c.metadata.get(k) == v for k, v in filters.items())]
        if not chunks:
            return []
        mode = self.collection.retrieval_mode
        lexical = keyword_scores(query, chunks) if mode in {'keyword', 'hybrid'} else {}
        semantic = {}
        if mode != 'keyword':
            signature = index_signature(self.collection)
            if any(not c.embedding or c.metadata.get('index_signature') != signature for c in chunks):
                raise RAGUnavailable('知识库索引缺失或配置已变化，请重新处理文档。')
            query_vector = self.embedding_service.embed_text(query)
            self.initialize()
            if self.vector_client:
                # Rehydrate from authorized DB chunks; never trust remote payload as authority.
                try:
                    hits = self.vector_client.search(self._get_collection_name(), query_vector, top_k=limit)
                except Exception as exc:
                    raise RAGUnavailable('向量检索失败，请检查索引和服务配置。') from exc
                finally:
                    self.vector_client.disconnect()
                    self.vector_client = None
                live = {c.vector_id: str(c.id) for c in chunks}
                semantic = {live[str(hit['id'])]: max(0.0, min(1.0, float(hit['score'])))
                            for hit in hits if str(hit['id']) in live}
            else:
                semantic = {str(c.id): max(0.0, min(1.0, cosine_score(query_vector, c.embedding))) for c in chunks}
        scores = lexical if mode == 'keyword' else semantic
        if mode == 'hybrid':
            scores = {}
            for ranking in (lexical, semantic):
                for rank, (key, score) in enumerate(sorted(ranking.items(), key=lambda item: (-item[1], item[0])), 1):
                    if score > 0:
                        scores[key] = scores.get(key, 0) + (RRF_OFFSET + 1) / (2 * (RRF_OFFSET + rank))
        ranked = sorted((c for c in chunks if scores.get(str(c.id), 0) > 0 and scores[str(c.id)] >= self.min_similarity),
                        key=lambda c: (-scores[str(c.id)], str(c.id)))[:self.top_k]
        return [{'id': str(c.id), 'score': scores[str(c.id)], 'payload': {
            **c.metadata, 'content': c.content, 'doc_id': str(c.document_id), 'title': c.document.title,
            'source_type': c.document.source_type, 'source_url': c.document.source_url,
            'chunk_index': c.chunk_index, 'collection_id': str(self.collection.id),
        }} for c in ranked]

    def generate_response(self, query, context=None, system_prompt=None):
        if not context:
            return {'response': NO_EVIDENCE_MESSAGE, 'sources': [], 'grounded': False, 'answer_status': 'no_evidence'}
        budget = getattr(settings, 'RAG_CONTEXT_CHARS', DEFAULT_CONTEXT_CHARS)
        sources, blocks = [], []
        for result in context:
            content = result['payload'].get('content', '')[:budget]
            if not content:
                break
            source = {**result, 'payload': {**result['payload'], 'content': content}}
            sources.append(source)
            blocks.append(f'[{len(sources)}] {source["payload"].get("title", "")}\n{content}')
            budget -= len(content)
        messages = [
            {'role': 'system', 'content': f'{system_prompt or DEFAULT_SYSTEM_PROMPT}\n{GROUNDING_INSTRUCTION}'},
            {'role': 'user', 'content': json.dumps({'knowledge': blocks, 'question': query}, ensure_ascii=False)},
        ]
        try:
            from core.llm_factory import invoke_chat_messages
            response = invoke_chat_messages(messages, model=getattr(settings, 'RAG_CHAT_MODEL', '') or None,
                api_key=getattr(settings, 'RAG_CHAT_API_KEY', '') or None,
                base_url=getattr(settings, 'RAG_CHAT_BASE_URL', '') or None,
                timeout=getattr(settings, 'RAG_REQUEST_TIMEOUT', DEFAULT_REQUEST_TIMEOUT))
            if not isinstance(response, str) or not response.strip():
                raise RAGUnavailable('模型返回空回答。')
        except Exception as exc:
            logger.warning('RAG generation failed (%s)', type(exc).__name__)
            raise RAGUnavailable('资料已检索到，但回答模型不可用。请检查模型配置，或先使用检索测试。') from exc
        return {'response': response, 'sources': sources, 'grounded': True, 'answer_status': 'answered'}

class DocumentProcessor:
    def __init__(self, collection):
        self.collection = collection
        self.rag_service = RAGService(collection)

    def process_text(self, content, metadata=None):
        from .models import Document
        metadata = metadata or {}
        content = validate_content(content)
        if metadata.get('doc_id'):
            document = Document.objects.get(id=metadata['doc_id'], collection=self.collection)
        else:
            document = Document.objects.create(
                collection=self.collection, title=metadata.get('title') or '未命名文档', content=content,
                source_type=metadata.get('source_type', 'text'), source_url=metadata.get('source_url', ''), metadata=metadata,
            )
        return self.process_document(document)

    def process_document(self, document):
        from .models import DocumentCollection, Document, Chunk
        # Expired claims can be retried after a crashed process; stale workers cannot commit.
        claimed_at = timezone.now()
        expired_at = claimed_at - timedelta(seconds=getattr(settings, 'RAG_PROCESSING_LEASE_SECONDS', DEFAULT_PROCESSING_LEASE_SECONDS))
        with transaction.atomic():
            DocumentCollection.objects.select_for_update().get(id=self.collection.id)
            claimed = Document.objects.filter(id=document.id).filter(
                ~Q(status='processing') | Q(updated_at__lt=expired_at)).update(
                status='processing', error_message='', updated_at=claimed_at)
        if not claimed:
            return {'success': False, 'document_id': str(document.id), 'error': '文档正在处理中，请勿重复提交。'}
        vectors = []
        committed = False
        try:
            document.refresh_from_db()
            vectors = self.rag_service.process_document(document.content, {
                **document.metadata, 'doc_id': str(document.id), 'title': document.title,
                'source_type': document.source_type, 'source_url': document.source_url,
            })
            with transaction.atomic():
                # Serialize collection mutation and counters; re-check config after embedding I/O.
                current = DocumentCollection.objects.select_for_update().get(id=self.collection.id)
                if index_signature(current) != index_signature(self.collection) or current.vector_store_id != self.collection.vector_store_id:
                    raise ValueError('处理期间知识库配置已修改，请重试。')
                current_document = Document.objects.select_for_update().get(id=document.id)
                if current_document.status != 'processing' or current_document.updated_at != claimed_at:
                    raise RAGUnavailable('当前处理已被新的重试任务取代。')
                self.rag_service.index_document(document, vectors)
                self.rag_service.delete_chunk_vectors(document.chunks.all())
                document.chunks.all().delete()
                Chunk.objects.bulk_create([Chunk(
                    id=v['id'], document=document, content=v['payload']['content'], chunk_index=i,
                    vector_id=v['id'], embedding=v['vector'], metadata={k: value for k, value in v['payload'].items() if k != 'content'},
                ) for i, v in enumerate(vectors)])
                Document.objects.filter(id=document.id).update(
                    status='completed', chunk_count=len(vectors), processed_at=timezone.now(),
                    token_count=sum(max(1, len(v['payload']['content']) // 4) for v in vectors),
                    error_message='', updated_at=timezone.now(),
                )
                refresh_collection_stats(self.collection.id)
            committed = True
            document.refresh_from_db()
            return {'success': True, 'document_id': str(document.id), 'chunks': len(vectors), 'status': 'completed'}
        except Exception as exc:
            logger.warning('Document %s indexing failed (%s)', document.id, type(exc).__name__)
            message = str(exc) if isinstance(exc, (ValueError, RAGUnavailable)) else '文档处理失败，请检查模型和向量存储配置后重试。'
            Document.objects.filter(id=document.id, status='processing', updated_at=claimed_at).update(
                status='failed', error_message=message, updated_at=timezone.now())
            refresh_collection_stats(self.collection.id)
            return {'success': False, 'document_id': str(document.id), 'error': message, 'status': 'failed'}
        finally:
            if self.rag_service.vector_client:
                if vectors and not committed:
                    try:
                        self.rag_service.delete_vectors([v['id'] for v in vectors])
                    except Exception:
                        logger.warning('Unable to clean partial index for document %s', document.id)
                self.rag_service.vector_client.disconnect()
                self.rag_service.vector_client = None

    def process_url(self, url, metadata=None):
        try:
            content, final_url = fetch_public_text(url)
            return self.process_text(content, {**(metadata or {}), 'title': (metadata or {}).get('title') or url,
                                              'source_url': final_url, 'source_type': 'url'})
        except (ValueError, httpx.HTTPError, OSError) as exc:
            return {'success': False, 'error': str(exc) if isinstance(exc, ValueError) else '网页获取失败，请检查地址和网络。'}


def import_system_guides(collection):
    """Idempotent import of an allowlist, never arbitrary repository or secret files."""
    from pathlib import Path
    from .constants import SYSTEM_GUIDES
    from .models import DocumentCollection, Document
    root = Path(settings.BASE_DIR).parent
    processor = DocumentProcessor(collection)
    results = []
    for relative in SYSTEM_GUIDES:
        path = root / relative
        if not path.is_file():
            results.append({'success': False, 'source': relative, 'error': '部署目录中缺少该指南文件。'})
            continue
        content = validate_content(path.read_text(encoding='utf-8-sig'))
        with transaction.atomic():
            DocumentCollection.objects.select_for_update().get(id=collection.id)
            document = Document.objects.filter(collection=collection, metadata__system_guide=relative).first()
            if document and document.status == 'processing':
                results.append({'success': False, 'source': relative, 'error': '指南正在处理，请稍后重试。'})
                continue
            if document and document.content == content and document.status == 'completed':
                results.append({'success': True, 'source': relative, 'document_id': str(document.id), 'unchanged': True})
                continue
            if document:
                document.content = content
                document.status = 'pending'
                document.save(update_fields=['content', 'status', 'updated_at'])
            else:
                document = Document.objects.create(collection=collection, title=path.name, content=content,
                    metadata={'system_guide': relative, 'source': 'flowly_guide'})
        results.append({**processor.process_document(document), 'source': relative})
    return {'results': results, 'completed': sum(r['success'] for r in results), 'failed': sum(not r['success'] for r in results)}
