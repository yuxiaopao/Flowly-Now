"""
Serializers for RAG app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import VectorStore, DocumentCollection, Document, Chunk, RAGPipeline

User = get_user_model()


class VectorStoreSerializer(serializers.ModelSerializer):
    """Serializer for VectorStore."""

    store_type_display = serializers.CharField(source='get_store_type_display', read_only=True)

    class Meta:
        model = VectorStore
        fields = [
            'id', 'name', 'store_type', 'store_type_display',
            'host', 'port', 'collection', 'dimension', 'metric',
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VectorStoreCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating VectorStore."""

    class Meta:
        model = VectorStore
        fields = [
            'name', 'store_type', 'host', 'port', 'collection',
            'api_key', 'path', 'dimension', 'metric', 'is_default'
        ]


class ChunkSerializer(serializers.ModelSerializer):
    """Serializer for Chunk."""

    class Meta:
        model = Chunk
        fields = ['id', 'content', 'chunk_index', 'metadata', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document."""

    chunks = ChunkSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'source_type', 'source_url',
            'content', 'metadata', 'status', 'status_display',
            'chunk_count', 'token_count',
            'created_at', 'updated_at', 'processed_at',
            'chunks'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentListSerializer(serializers.ModelSerializer):
    """Serializer for Document list view."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'source_type', 'status', 'status_display',
            'chunk_count', 'token_count', 'created_at', 'processed_at'
        ]


class DocumentCreateSerializer(serializers.Serializer):
    """Serializer for creating Document."""

    title = serializers.CharField(max_length=500)
    content = serializers.CharField()
    metadata = serializers.JSONField(required=False, default=dict)


class DocumentURLSerializer(serializers.Serializer):
    """Serializer for adding document from URL."""

    url = serializers.URLField()
    title = serializers.CharField(max_length=500, required=False)


class DocumentCollectionSerializer(serializers.ModelSerializer):
    """Serializer for DocumentCollection."""

    documents = DocumentListSerializer(many=True, read_only=True)
    vector_store_name = serializers.CharField(source='vector_store.name', read_only=True)

    class Meta:
        model = DocumentCollection
        fields = [
            'id', 'name', 'description',
            'vector_store', 'vector_store_name',
            'embedding_model', 'chunk_size', 'chunk_overlap',
            'document_count', 'chunk_count',
            'created_at', 'updated_at',
            'documents'
        ]
        read_only_fields = ['id', 'document_count', 'chunk_count', 'created_at', 'updated_at']


class DocumentCollectionListSerializer(serializers.ModelSerializer):
    """Serializer for DocumentCollection list view."""

    vector_store_name = serializers.CharField(source='vector_store.name', read_only=True)

    class Meta:
        model = DocumentCollection
        fields = [
            'id', 'name', 'description',
            'vector_store', 'vector_store_name',
            'document_count', 'chunk_count',
            'created_at'
        ]


class DocumentCollectionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating DocumentCollection."""

    class Meta:
        model = DocumentCollection
        fields = [
            'name', 'description', 'vector_store',
            'embedding_model', 'chunk_size', 'chunk_overlap'
        ]


class RAGPipelineSerializer(serializers.ModelSerializer):
    """Serializer for RAGPipeline."""

    collection_name = serializers.CharField(source='collection.name', read_only=True)

    class Meta:
        model = RAGPipeline
        fields = [
            'id', 'name', 'description',
            'collection', 'collection_name',
            'top_k', 'min_similarity',
            'system_prompt', 'include_sources',
            'usage_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']


class RAGPipelineCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating RAGPipeline."""

    class Meta:
        model = RAGPipeline
        fields = [
            'name', 'description', 'collection',
            'top_k', 'min_similarity',
            'system_prompt', 'include_sources'
        ]


class RAGQuerySerializer(serializers.Serializer):
    """Serializer for RAG query."""

    query = serializers.CharField(required=True)
    filters = serializers.JSONField(required=False, default=dict)


class RAGResponseSerializer(serializers.Serializer):
    """Serializer for RAG response."""

    response = serializers.CharField()
    sources = serializers.ListField()
    query = serializers.CharField()
    retrieved_count = serializers.IntegerField()
