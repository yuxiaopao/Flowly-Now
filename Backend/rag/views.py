"""
Views for RAG app.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q

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

logger = logging.getLogger(__name__)


class VectorStoreViewSet(viewsets.ModelViewSet):
    """ViewSet for VectorStore."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VectorStore.objects.filter(
            Q(owner=self.request.user) | Q(owner__isnull=True)
        )

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return VectorStoreCreateSerializer
        return VectorStoreSerializer

    def perform_create(self, serializer):
        if self.request.data.get('is_default'):
            VectorStore.objects.filter(owner=self.request.user, is_default=True).update(is_default=False)
        serializer.save(owner=self.request.user)

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
        return DocumentCollection.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentCollectionListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DocumentCollectionCreateSerializer
        return DocumentCollectionSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

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

        status_counts = collection.documents.values('status').annotate(count=models.Count('status'))

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
            content = file.read().decode('utf-8', errors='ignore')

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
        return Document.objects.filter(
            collection__owner=self.request.user
        )

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
        return Chunk.objects.filter(
            document__collection__owner=self.request.user
        )


class RAGPipelineViewSet(viewsets.ModelViewSet):
    """ViewSet for RAGPipeline."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RAGPipeline.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RAGPipelineCreateSerializer
        return RAGPipelineSerializer

    def perform_create(self, serializer):
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
