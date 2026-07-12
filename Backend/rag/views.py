"""
Views for RAG app.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Count

from .models import VectorStore, DocumentCollection, Document, Chunk, RAGPipeline
from .serializers import (
    VectorStoreSerializer, VectorStoreCreateSerializer,
    DocumentSerializer, DocumentListSerializer, DocumentCreateSerializer,
    DocumentURLSerializer, DocumentCollectionSerializer,
    DocumentCollectionListSerializer, DocumentCollectionCreateSerializer,
    RAGPipelineSerializer, RAGPipelineCreateSerializer,
    RAGQuerySerializer, RAGResponseSerializer, ChunkSerializer
)
from .services import RAGService, DocumentProcessor, get_vector_store_client
from tenants.access import get_accessible_tenant_ids, is_tenant_member, is_tenant_admin

logger = logging.getLogger(__name__)


def _validate_tenant_membership(request, tenant):
    """Raise ValidationError if the caller is not an active member of the given tenant."""
    if tenant is None:
        return
    if not is_tenant_member(request.user, tenant.id):
        raise ValidationError({'tenant': '您不是该团队的成员，无法将资源共享到此团队。'})


TEXT_DECODE_ENCODINGS = ('utf-8', 'gbk', 'gb18030', 'utf-16', 'latin-1')


def _extract_pdf_text(file) -> str:
    from pypdf import PdfReader
    reader = PdfReader(file)
    pages_text = []
    for page in reader.pages:
        page_text = page.extract_text() or ''
        if page_text.strip():
            pages_text.append(page_text)
    text = '\n\n'.join(pages_text).strip()
    if not text:
        raise ValueError('无法从该 PDF 中提取到任何文本（可能是纯图片扫描件，暂不支持 OCR）')
    return text


def _extract_docx_text(file) -> str:
    import docx
    document = docx.Document(file)
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            row_text = '\t'.join(cell.text for cell in row.cells if cell.text.strip())
            if row_text.strip():
                paragraphs.append(row_text)
    text = '\n'.join(paragraphs).strip()
    if not text:
        raise ValueError('无法从该 Word 文档中提取到任何文本')
    return text


def _extract_plain_text(raw_bytes: bytes) -> str:
    for encoding in TEXT_DECODE_ENCODINGS:
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError('无法识别该文件的文本编码，仅支持 UTF-8/GBK 等常见编码的文本文件，或 PDF/Word 文档')


def extract_file_content(file) -> str:
    """Extract plain text content from an uploaded file based on its extension.

    Supports .pdf (via pypdf), .docx (via python-docx), and falls back to
    common text encodings for everything else. Raises ValueError with a
    user-facing message on failure instead of silently returning mojibake.
    """
    filename = (file.name or '').lower()

    if filename.endswith('.pdf'):
        return _extract_pdf_text(file)
    if filename.endswith('.docx'):
        return _extract_docx_text(file)
    if filename.endswith('.doc'):
        raise ValueError('不支持旧版 .doc 格式，请先将文件另存为 .docx 或 .pdf 后重新上传')

    return _extract_plain_text(file.read())


class VectorStoreViewSet(viewsets.ModelViewSet):
    """ViewSet for VectorStore."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        return VectorStore.objects.filter(
            Q(owner=user) | Q(owner__isnull=True) | Q(tenant_id__in=tenant_ids)
        ).distinct()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return VectorStoreCreateSerializer
        return VectorStoreSerializer

    def perform_create(self, serializer):
        _validate_tenant_membership(self.request, serializer.validated_data.get('tenant'))
        if self.request.data.get('is_default'):
            VectorStore.objects.filter(owner=self.request.user, is_default=True).update(is_default=False)
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        user = self.request.user
        if instance.owner_id and instance.owner_id != user.id and not user.is_superuser:
            if not (instance.tenant_id and is_tenant_admin(user, instance.tenant_id)):
                raise ValidationError({'detail': '仅所有者或团队管理员可编辑该向量存储。'})
        _validate_tenant_membership(self.request, serializer.validated_data.get('tenant'))
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.owner_id and instance.owner_id != user.id and not user.is_superuser:
            if not (instance.tenant_id and is_tenant_admin(user, instance.tenant_id)):
                raise ValidationError({'detail': '仅所有者或团队管理员可删除该向量存储。'})
        instance.delete()

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test vector store connection."""
        vector_store = self.get_object()

        client = get_vector_store_client(vector_store)
        if not client:
            return Response({'error': 'Unsupported vector store type'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            success = client.connect()
            if success:
                return Response({'message': 'Connection successful'})
            return Response({'error': 'Connection failed'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def create_collection(self, request, pk=None):
        """Create a collection in the vector store."""
        vector_store = self.get_object()
        name = request.data.get('name', f'collection_{pk}')
        dimension = request.data.get('dimension', vector_store.dimension)
        metric = request.data.get('metric', vector_store.metric)

        client = get_vector_store_client(vector_store)
        if not client:
            return Response({'error': 'Unsupported vector store type'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            success = client.create_collection(name, dimension, metric)
            if success:
                return Response({'message': f'Collection {name} created successfully'})
            return Response({'error': 'Failed to create collection'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def delete_collection(self, request, pk=None):
        """Delete a collection from the vector store."""
        vector_store = self.get_object()
        name = request.data.get('name')

        if not name:
            return Response({'error': 'Collection name is required'}, status=status.HTTP_400_BAD_REQUEST)

        client = get_vector_store_client(vector_store)
        if not client:
            return Response({'error': 'Unsupported vector store type'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            success = client.delete_collection(name)
            if success:
                return Response({'message': f'Collection {name} deleted'})
            return Response({'error': 'Failed to delete collection'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def list_types(self, request):
        """List available vector store types."""
        return Response({
            'types': [
                {'value': 'memory', 'label': '内存存储 (开发/测试)'},
                {'value': 'qdrant', 'label': 'Qdrant'},
                {'value': 'milvus', 'label': 'Milvus'},
                {'value': 'chroma', 'label': 'Chroma'},
                {'value': 'pinecone', 'label': 'Pinecone'},
                {'value': 'weaviate', 'label': 'Weaviate'},
            ]
        })



class DocumentCollectionViewSet(viewsets.ModelViewSet):
    """ViewSet for DocumentCollection."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        queryset = DocumentCollection.objects.filter(
            Q(owner=user) | Q(tenant_id__in=tenant_ids)
        ).distinct().select_related('tenant', 'vector_store', 'owner').annotate(
            documents_total=Count('documents', distinct=True),
            chunks_total=Count('documents__chunks', distinct=True),
        ).order_by('-created_at')
        tenant_param = self.request.query_params.get('tenant')
        if tenant_param:
            queryset = queryset.filter(tenant_id=tenant_param)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentCollectionListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DocumentCollectionCreateSerializer
        return DocumentCollectionSerializer

    def perform_create(self, serializer):
        tenant = serializer.validated_data.get('tenant')
        _validate_tenant_membership(self.request, tenant)

        # Auto-assign default vector store if not specified
        vector_store = serializer.validated_data.get('vector_store')
        if not vector_store:
            # Try to find user's default or first vector store
            vector_store = VectorStore.objects.filter(owner=self.request.user, is_default=True).first()
            if not vector_store:
                vector_store = VectorStore.objects.filter(owner=self.request.user).first()

        if vector_store:
            serializer.save(owner=self.request.user, vector_store=vector_store)
        else:
            # No vector store available - raise validation error with helpful message
            raise ValidationError({
                'vector_store': '请先创建向量存储。前往「向量存储」页面创建一个向量数据库。'
            })

    def perform_update(self, serializer):
        # Only the owner or a tenant admin (when shared) may edit a shared knowledge base;
        # regular members may still view/search/upload documents via other actions.
        instance = serializer.instance
        user = self.request.user
        if instance.owner_id != user.id and not user.is_superuser:
            if not (instance.tenant_id and is_tenant_admin(user, instance.tenant_id)):
                raise ValidationError({'detail': '仅所有者或团队管理员可编辑该知识库。'})
        _validate_tenant_membership(self.request, serializer.validated_data.get('tenant'))
        serializer.save()

    def perform_destroy(self, instance):
        # Only the owner or a tenant admin (when shared) may delete a shared knowledge base.
        user = self.request.user
        if instance.owner_id != user.id and not user.is_superuser:
            if not (instance.tenant_id and is_tenant_admin(user, instance.tenant_id)):
                raise ValidationError({'detail': '仅所有者或团队管理员可删除该知识库。'})
        instance.delete()

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Get detailed information about a collection."""
        collection = self.get_object()
        serializer = DocumentCollectionSerializer(collection)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get collection statistics."""
        collection = self.get_object()

        document_count = collection.documents.count()
        chunk_count = Chunk.objects.filter(document__collection=collection).count()

        status_counts = collection.documents.values('status').annotate(count=Count('status'))

        return Response({
            'document_count': document_count,
            'chunk_count': chunk_count,
            'status_breakdown': list(status_counts),
            'embedding_model': collection.embedding_model,
            'chunk_size': collection.chunk_size,
            'chunk_overlap': collection.chunk_overlap
        })

    @action(detail=True, methods=['post'])
    def add_document(self, request, pk=None):
        """Add a document to collection."""
        collection = self.get_object()

        serializer = DocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        processor = DocumentProcessor(collection)
        result = processor.process_text(
            content=serializer.validated_data['content'],
            metadata={'title': serializer.validated_data['title']}
        )

        if result.get('success'):
            return Response({
                'message': 'Document processed successfully',
                'chunks': result.get('chunks')
            }, status=status.HTTP_201_CREATED)

        return Response({
            'error': result.get('error', 'Processing failed')
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_url(self, request, pk=None):
        """Add a document from URL."""
        collection = self.get_object()

        serializer = DocumentURLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        processor = DocumentProcessor(collection)
        result = processor.process_url(
            url=serializer.validated_data['url'],
            metadata={'title': serializer.validated_data.get('title')}
        )

        if result.get('success'):
            return Response({
                'message': 'Document processed successfully',
                'chunks': result.get('chunks')
            }, status=status.HTTP_201_CREATED)

        return Response({
            'error': result.get('error', 'Processing failed')
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def upload_file(self, request, pk=None):
        """Upload and process a file."""
        collection = self.get_object()

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = extract_file_content(file)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to extract content from uploaded file {file.name}: {e}")
            return Response({'error': f'文件解析失败: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            processor = DocumentProcessor(collection)
            result = processor.process_text(
                content=content,
                metadata={
                    'title': file.name,
                    'file_type': file.content_type,
                    'file_size': file.size
                }
            )

            if result.get('success'):
                return Response({
                    'message': 'File processed successfully',
                    'chunks': result.get('chunks')
                }, status=status.HTTP_201_CREATED)

            return Response({
                'error': result.get('error', 'Processing failed')
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def search(self, request, pk=None):
        """Search within collection."""
        collection = self.get_object()
        query = request.query_params.get('query', '')
        top_k = int(request.query_params.get('top_k', 5))

        if not query:
            return Response({'error': 'Query is required'}, status=status.HTTP_400_BAD_REQUEST)

        rag_service = RAGService(
            collection=collection,
            top_k=top_k,
            min_similarity=0.0
        )
        rag_service.initialize()

        results = rag_service.retrieve(query)

        return Response({
            'results': [
                {
                    'content': r['payload'].get('content', ''),
                    'score': r.get('score', 0),
                    'metadata': r['payload']
                }
                for r in results
            ],
            'count': len(results)
        })

    @action(detail=True, methods=['delete'])
    def clear(self, request, pk=None):
        """Clear all documents from collection."""
        collection = self.get_object()

        collection.documents.all().delete()
        collection.document_count = 0
        collection.chunk_count = 0
        collection.save()

        return Response({'message': 'Collection cleared'})


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Document."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        queryset = Document.objects.filter(
            Q(collection__owner=user) | Q(collection__tenant_id__in=tenant_ids)
        ).distinct()
        collection_id = self.request.query_params.get('collection')
        if collection_id:
            queryset = queryset.filter(collection_id=collection_id)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentListSerializer
        return DocumentSerializer

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess a document."""
        document = self.get_object()

        processor = DocumentProcessor(document.collection)
        result = processor.process_text(
            content=document.content,
            metadata={'title': document.title, 'doc_id': str(document.id)}
        )

        if result.get('success'):
            document.refresh_from_db()
            serializer = DocumentSerializer(document)
            return Response(serializer.data)

        return Response({
            'error': result.get('error', 'Processing failed')
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        """Get document chunks."""
        document = self.get_object()
        chunks = document.chunks.all()
        serializer = ChunkSerializer(chunks, many=True)
        return Response(serializer.data)


class ChunkViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Chunk."""

    serializer_class = ChunkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        return Chunk.objects.filter(
            Q(document__collection__owner=user) | Q(document__collection__tenant_id__in=tenant_ids)
        ).distinct()


class RAGPipelineViewSet(viewsets.ModelViewSet):
    """ViewSet for RAGPipeline."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        return RAGPipeline.objects.filter(
            Q(owner=user) | Q(collection__owner=user) | Q(collection__tenant_id__in=tenant_ids)
        ).distinct()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RAGPipelineCreateSerializer
        return RAGPipelineSerializer

    def perform_create(self, serializer):
        collection = serializer.validated_data.get('collection')
        if collection and collection.owner_id != self.request.user.id:
            tenant_ids = get_accessible_tenant_ids(self.request.user)
            if not (collection.tenant_id and collection.tenant_id in tenant_ids):
                raise ValidationError({'collection': '您无权在该知识库上创建流水线。'})
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def query(self, request, pk=None):
        """Query the RAG pipeline."""
        pipeline = self.get_object()

        serializer = RAGQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data['query']
        filters = serializer.validated_data.get('filters', {})

        # Initialize RAG service
        rag_service = RAGService(
            collection=pipeline.collection,
            top_k=pipeline.top_k,
            min_similarity=pipeline.min_similarity
        )

        # Initialize and get context
        rag_service.initialize()

        # Retrieve relevant documents
        retrieved = rag_service.retrieve(query, filters)

        # Generate response
        response = rag_service.generate_response(
            query=query,
            context=retrieved,
            system_prompt=pipeline.system_prompt
        )

        # Update usage count
        pipeline.usage_count += 1
        pipeline.save()

        return Response({
            'response': response.get('response', ''),
            'sources': [
                {
                    'content': r['payload'].get('content', ''),
                    'score': r.get('score', 0),
                    'metadata': r['payload']
                }
                for r in retrieved
            ] if pipeline.include_sources else [],
            'query': query,
            'retrieved_count': len(retrieved)
        })

    @action(detail=True, methods=['get'], url_path='retrieve')
    def retrieve_documents(self, request, pk=None):
        """Retrieve documents without generating response (GET .../retrieve/)."""
        pipeline = self.get_object()
        query = request.query_params.get('query', '')

        if not query:
            return Response({'error': 'Query is required'}, status=status.HTTP_400_BAD_REQUEST)

        rag_service = RAGService(
            collection=pipeline.collection,
            top_k=pipeline.top_k,
            min_similarity=pipeline.min_similarity
        )
        rag_service.initialize()

        results = rag_service.retrieve(query)

        return Response({
            'results': [
                {
                    'content': r['payload'].get('content', ''),
                    'score': r.get('score', 0),
                    'metadata': r['payload']
                }
                for r in results
            ],
            'count': len(results)
        })
