"""Authenticated knowledge-base APIs shared by the UI and automation clients."""
import json
import logging
from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from tenants.access import get_accessible_tenant_ids, is_tenant_admin, is_tenant_member
from .access import accessible_collections, can_manage_collection
from .constants import (
    DEFAULT_TOP_K, DEFAULT_MIN_SIMILARITY, DEFAULT_STORE_NAME, LOCAL_STORE_TYPES,
    FILE_EXTENSIONS, DEFAULT_MAX_FILE_BYTES, RETRIEVAL_MODES, CHUNK_STRATEGIES, INDEX_FIELDS,
)
from .models import VectorStore, DocumentCollection, Document, Chunk, RAGPipeline
from .parsing import extract_file_content
from .pipeline import RAGUnavailable, refresh_collection_stats, import_system_guides
from .serializers import (
    VectorStoreSerializer, VectorStoreCreateSerializer, DocumentSerializer, DocumentListSerializer,
    DocumentCreateSerializer, DocumentURLSerializer, DocumentCollectionSerializer,
    DocumentCollectionListSerializer, DocumentCollectionCreateSerializer,
    RAGPipelineSerializer, RAGPipelineCreateSerializer, RAGQuerySerializer, ChunkSerializer,
)
from .services import RAGService, DocumentProcessor, get_vector_store_client

logger = logging.getLogger(__name__)


def _validate_tenant_membership(request, tenant):
    if tenant is not None and not is_tenant_member(request.user, tenant.id):
        raise PermissionDenied('您不是该团队的成员，无法将资源共享到此团队。')


def require_manager(user, collection):
    if not can_manage_collection(user, collection):
        raise PermissionDenied('仅所有者或团队管理员可修改或删除这些知识库资源。')


def serialize_results(results):
    return [{'id': r['id'], 'content': r['payload']['content'], 'score': r['score'],
             'metadata': r['payload'], 'citation': i} for i, r in enumerate(results, 1)]


def processing_response(result):
    return Response(result, status=status.HTTP_201_CREATED if result.get('success') else status.HTTP_400_BAD_REQUEST)


def query_options(request):
    data = request.data.copy() if request.method == 'POST' else request.query_params.dict()
    if isinstance(data.get('filters'), str):
        try:
            data['filters'] = json.loads(data['filters'])
        except ValueError:
            raise ValidationError({'filters': '过滤条件必须是 JSON 对象。'})
    serializer = RAGQuerySerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class RAGViewMixin:
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, RAGUnavailable):
            return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if isinstance(exc, (ValueError, TypeError)):
            exc = ValidationError({'error': str(exc)})
        return super().handle_exception(exc)


class VectorStoreViewSet(RAGViewMixin, viewsets.ModelViewSet):
    def get_queryset(self):
        user = self.request.user
        return VectorStore.objects.filter(Q(owner=user) | Q(owner__isnull=True) |
            Q(tenant_id__in=get_accessible_tenant_ids(user))).select_related('tenant').distinct()

    def get_serializer_class(self):
        return VectorStoreCreateSerializer if self.action in {'create', 'update', 'partial_update'} else VectorStoreSerializer

    def require_owner(self, instance):
        user = self.request.user
        if user.is_superuser or instance.owner_id == user.id:
            return
        if instance.tenant_id and is_tenant_admin(user, instance.tenant_id):
            return
        raise PermissionDenied('仅所有者或团队管理员可管理该存储；公共存储由管理员管理。')

    def perform_create(self, serializer):
        _validate_tenant_membership(self.request, serializer.validated_data.get('tenant'))
        with transaction.atomic():
            if serializer.validated_data.get('is_default'):
                VectorStore.objects.filter(owner=self.request.user).update(is_default=False)
            serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        self.require_owner(serializer.instance)
        _validate_tenant_membership(self.request, serializer.validated_data.get('tenant'))
        connection_fields = {'store_type', 'host', 'port', 'path', 'collection', 'dimension', 'metric'}
        if serializer.instance.collections.filter(documents__isnull=False).exists() and any(
            key in serializer.validated_data and serializer.validated_data[key] != getattr(serializer.instance, key)
            for key in connection_fields
        ):
            raise ValidationError('此存储已有知识文档。请先迁移或清空关联知识库，再变更连接参数。')
        with transaction.atomic():
            if serializer.validated_data.get('is_default'):
                VectorStore.objects.filter(owner=serializer.instance.owner).exclude(pk=serializer.instance.pk).update(is_default=False)
            serializer.save()

    def perform_destroy(self, instance):
        self.require_owner(instance)
        if instance.collections.exists():
            raise ValidationError('请先删除或迁移关联知识库，再删除向量存储。')
        instance.delete()

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        store = self.get_object()
        if store.store_type in LOCAL_STORE_TYPES:
            DocumentCollection.objects.filter(vector_store=store).exists()
            return Response({'message': '本地数据库可用；知识库索引随业务数据库持久化。'})
        try:
            client = get_vector_store_client(store)
            try:
                if not client.connect():
                    raise RAGUnavailable('连接检查失败。')
                return Response({'message': '连接成功'})
            finally:
                client.disconnect()
        except Exception as exc:
            logger.warning('Vector-store connection check failed (%s)', type(exc).__name__)
            return Response({'error': '连接失败，请检查驱动、服务地址和凭证。'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def create_collection(self, request, pk=None):
        store = self.get_object()
        self.require_owner(store)
        name = request.data.get('name', '')
        if not isinstance(name, str) or not name or name.lower().startswith('flowly_'):
            raise ValidationError('请填写集合名称；flowly_ 前缀由知识库管理。')
        if store.store_type in LOCAL_STORE_TYPES:
            raise ValidationError('本地存储请在知识库页面创建集合。')
        dimension = request.data.get('dimension', store.dimension)
        if not isinstance(dimension, int) or dimension < 1:
            raise ValidationError('向量维度必须为正整数。')
        try:
            client = get_vector_store_client(store)
            if not client.create_collection(name, dimension, request.data.get('metric', store.metric)):
                raise RAGUnavailable('集合创建失败。')
        except Exception as exc:
            raise RAGUnavailable('集合创建失败，请检查向量服务配置。') from exc
        return Response({'message': '集合已创建'})

    @action(detail=True, methods=['delete'])
    def delete_collection(self, request, pk=None):
        store = self.get_object()
        self.require_owner(store)
        name = request.data.get('name', '')
        if not isinstance(name, str) or not name or name.lower().startswith('flowly_'):
            raise ValidationError('受管理的集合请通过知识库页面删除。')
        if store.store_type in LOCAL_STORE_TYPES:
            raise ValidationError('本地集合请通过知识库页面删除。')
        try:
            if not get_vector_store_client(store).delete_collection(name):
                raise RAGUnavailable('集合删除失败。')
        except Exception as exc:
            raise RAGUnavailable('集合删除失败，请检查向量服务配置。') from exc
        return Response({'message': '集合已删除'})

    @action(detail=False, methods=['get'])
    def list_types(self, request):
        return Response({'types': [{'value': value, 'label': label} for value, label in VectorStore.TYPE_CHOICES if value != 'ollama']})


def remove_documents(collection, documents):
    """Remote deletion is checked before committing the local deletion."""
    with transaction.atomic():
        DocumentCollection.objects.select_for_update().get(id=collection.id)
        if documents.filter(status='processing').exists():
            raise ValidationError('文档正在处理，请处理结束后再删除。')
        documents.delete()
        refresh_collection_stats(collection.id)


class DocumentCollectionViewSet(RAGViewMixin, viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = accessible_collections(self.request.user).select_related('tenant', 'vector_store', 'owner').annotate(
            documents_total=Count('documents', distinct=True), chunks_total=Count('documents__chunks', distinct=True),
        ).order_by('-created_at')
        if self.request.query_params.get('tenant'):
            queryset = queryset.filter(tenant_id=self.request.query_params['tenant'])
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentCollectionListSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return DocumentCollectionCreateSerializer
        return DocumentCollectionSerializer

    def perform_create(self, serializer):
        _validate_tenant_membership(self.request, serializer.validated_data.get('tenant'))
        store = serializer.validated_data.get('vector_store')
        if not store:
            store = VectorStore.objects.filter(owner=self.request.user, is_default=True).first()
        if not store:
            store, _ = VectorStore.objects.get_or_create(owner=self.request.user, store_type='memory', name=DEFAULT_STORE_NAME,
                                                        defaults={'is_default': True})
        serializer.save(owner=self.request.user, vector_store=store)

    def perform_update(self, serializer):
        require_manager(self.request.user, serializer.instance)
        _validate_tenant_membership(self.request, serializer.validated_data.get('tenant'))
        with transaction.atomic():
            collection = DocumentCollection.objects.select_for_update().get(id=serializer.instance.id)
            changed = any(key in serializer.validated_data and serializer.validated_data[key] != getattr(collection, key)
                          for key in INDEX_FIELDS)
            if changed and collection.documents.filter(status='processing').exists():
                raise ValidationError('有文档正在处理，请完成后修改索引配置。')
            if 'vector_store' in serializer.validated_data and serializer.validated_data['vector_store'] is None:
                serializer.validated_data['vector_store'] = collection.vector_store
            serializer.save()
            if changed:
                collection.documents.update(status='pending', error_message='索引配置已修改，请重新处理文档。')

    def perform_destroy(self, instance):
        require_manager(self.request.user, instance)
        remove_documents(instance, instance.documents.all())
        instance.delete()

    @action(detail=False, methods=['get'])
    def capabilities(self, request):
        return Response({'retrieval_modes': RETRIEVAL_MODES, 'chunk_strategies': CHUNK_STRATEGIES,
                         'file_extensions': sorted(FILE_EXTENSIONS),
                         'max_file_bytes': getattr(settings, 'RAG_MAX_FILE_BYTES', DEFAULT_MAX_FILE_BYTES)})

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        return Response(DocumentCollectionSerializer(self.get_object()).data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        collection = self.get_object()
        docs = collection.documents.all()
        return Response({'document_count': docs.count(), 'chunk_count': Chunk.objects.filter(document__collection=collection).count(),
                         'status_breakdown': list(docs.values('status').annotate(count=Count('status'))),
                         'storage_bytes': sum(len(content.encode('utf-8')) for content in docs.values_list('content', flat=True)),
                         'token_count': docs.aggregate(total=Sum('token_count'))['total'] or 0,
                         'embedding_model': collection.embedding_model, 'retrieval_mode': collection.retrieval_mode,
                         'chunk_size': collection.chunk_size, 'chunk_overlap': collection.chunk_overlap})

    @action(detail=True, methods=['post'])
    def add_document(self, request, pk=None):
        collection = self.get_object()
        serializer = DocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        metadata = {k: v for k, v in data.get('metadata', {}).items() if k not in {'doc_id', 'source_type', 'source_url', 'system_guide', 'index_signature', 'vector_namespace', 'collection_id'}}
        return processing_response(DocumentProcessor(collection).process_text(data['content'], {**metadata, 'title': data['title']}))

    @action(detail=True, methods=['post'])
    def add_url(self, request, pk=None):
        collection = self.get_object()
        serializer = DocumentURLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return processing_response(DocumentProcessor(collection).process_url(serializer.validated_data['url'],
                                    {'title': serializer.validated_data.get('title')}))

    @action(detail=True, methods=['post'])
    def upload_file(self, request, pk=None):
        collection = self.get_object()
        file = request.FILES.get('file')
        if not file:
            raise ValidationError('请选择文件。')
        try:
            content = extract_file_content(file)
        except ValueError:
            raise
        except Exception as exc:
            raise ValidationError('无法解析该文档，请检查文件是否损坏、加密或缺少解析依赖。') from exc
        return processing_response(DocumentProcessor(collection).process_text(content, {
            'title': file.name[:500], 'source_type': 'file', 'file_type': file.content_type, 'file_size': file.size,
        }))

    @action(detail=True, methods=['get', 'post'])
    def search(self, request, pk=None):
        collection = self.get_object()
        options = query_options(request)
        service = RAGService(collection, options.get('top_k', DEFAULT_TOP_K), options.get('min_similarity', DEFAULT_MIN_SIMILARITY))
        results = service.retrieve(options['query'], options.get('filters'))
        return Response({'results': serialize_results(results), 'count': len(results), 'retrieval_mode': collection.retrieval_mode})

    @action(detail=True, methods=['post'])
    def ask(self, request, pk=None):
        collection = self.get_object()
        options = query_options(request)
        service = RAGService(collection, options.get('top_k', DEFAULT_TOP_K), options.get('min_similarity', DEFAULT_MIN_SIMILARITY))
        retrieved = service.retrieve(options['query'], options.get('filters'))
        answer = service.generate_response(options['query'], retrieved)
        return Response({**answer, 'sources': serialize_results(answer['sources']), 'query': options['query'], 'retrieved_count': len(retrieved)})

    @action(detail=True, methods=['post'])
    def import_guides(self, request, pk=None):
        collection = self.get_object()
        require_manager(request.user, collection)
        return Response(import_system_guides(collection))

    @action(detail=True, methods=['post'])
    def reindex(self, request, pk=None):
        collection = self.get_object()
        require_manager(request.user, collection)
        processor = DocumentProcessor(collection)
        results = [processor.process_document(document) for document in collection.documents.all()]
        return Response({'results': results, 'completed': sum(r['success'] for r in results),
                         'failed': sum(not r['success'] for r in results)})

    @action(detail=True, methods=['delete'])
    def clear(self, request, pk=None):
        collection = self.get_object()
        require_manager(request.user, collection)
        remove_documents(collection, collection.documents.all())
        return Response({'message': '集合已清空'})


class DocumentViewSet(RAGViewMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    def get_queryset(self):
        queryset = Document.objects.filter(collection__in=accessible_collections(self.request.user)).select_related('collection__vector_store')
        if self.request.query_params.get('collection'):
            queryset = queryset.filter(collection_id=self.request.query_params['collection'])
        if self.request.query_params.get('status'):
            queryset = queryset.filter(status=self.request.query_params['status'])
        if self.request.query_params.get('search'):
            queryset = queryset.filter(title__icontains=self.request.query_params['search'])
        return queryset

    def get_serializer_class(self):
        return DocumentListSerializer if self.action == 'list' else DocumentSerializer

    def perform_update(self, serializer):
        document = serializer.instance
        require_manager(self.request.user, document.collection)
        with transaction.atomic():
            DocumentCollection.objects.select_for_update().get(id=document.collection_id)
            if Document.objects.get(id=document.id).status == 'processing':
                raise ValidationError('文档正在处理中。')
            serializer.save(status='pending')
        result = DocumentProcessor(document.collection).process_document(document)
        if not result['success']:
            raise ValidationError({'error': result['error'], 'document_id': result['document_id']})
        document.refresh_from_db()

    def perform_destroy(self, instance):
        require_manager(self.request.user, instance.collection)
        remove_documents(instance.collection, Document.objects.filter(id=instance.id))

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        document = self.get_object()
        require_manager(request.user, document.collection)
        result = DocumentProcessor(document.collection).process_document(document)
        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        document.refresh_from_db()
        return Response(DocumentSerializer(document).data)

    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        return Response(ChunkSerializer(self.get_object().chunks.all(), many=True).data)


class ChunkViewSet(RAGViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ChunkSerializer

    def get_queryset(self):
        queryset = Chunk.objects.filter(document__collection__in=accessible_collections(self.request.user)).select_related('document')
        if self.request.query_params.get('collection'):
            queryset = queryset.filter(document__collection_id=self.request.query_params['collection'])
        return queryset


class RAGPipelineViewSet(RAGViewMixin, viewsets.ModelViewSet):
    def get_queryset(self):
        return RAGPipeline.objects.filter(collection__in=accessible_collections(self.request.user)).select_related('collection__vector_store')

    def get_serializer_class(self):
        return RAGPipelineCreateSerializer if self.action in {'create', 'update', 'partial_update'} else RAGPipelineSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        require_manager(self.request.user, serializer.instance.collection)
        serializer.save()

    def perform_destroy(self, instance):
        require_manager(self.request.user, instance.collection)
        instance.delete()

    @action(detail=True, methods=['post'])
    def query(self, request, pk=None):
        pipeline = self.get_object()
        options = query_options(request)
        service = RAGService(pipeline.collection, options.get('top_k', pipeline.top_k), options.get('min_similarity', pipeline.min_similarity))
        retrieved = service.retrieve(options['query'], options.get('filters'))
        answer = service.generate_response(options['query'], retrieved, pipeline.system_prompt)
        RAGPipeline.objects.filter(id=pipeline.id).update(usage_count=F('usage_count') + 1)
        return Response({**answer, 'sources': serialize_results(answer['sources']) if pipeline.include_sources else [],
                         'query': options['query'], 'retrieved_count': len(retrieved)})

    @action(detail=True, methods=['get'], url_path='retrieve')
    def retrieve_documents(self, request, pk=None):
        pipeline = self.get_object()
        options = query_options(request)
        service = RAGService(pipeline.collection, options.get('top_k', pipeline.top_k), options.get('min_similarity', pipeline.min_similarity))
        results = service.retrieve(options['query'], options.get('filters'))
        return Response({'results': serialize_results(results), 'count': len(results)})
