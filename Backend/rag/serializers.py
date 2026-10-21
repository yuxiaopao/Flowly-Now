"""
Serializers for RAG app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from tenants.models import Tenant
from tenants.access import get_accessible_tenant_ids
from django.db.models import Q
from .models import VectorStore, DocumentCollection, Document, Chunk, RAGPipeline
from .constants import VECTOR_PORT_MIN, VECTOR_PORT_MAX, VECTOR_DIMENSION_MIN, CHUNK_SIZE_MIN, CHUNK_OVERLAP_MIN
from .constants import MAX_CHUNK_SIZE, MAX_TOP_K, DEFAULT_MAX_QUERY_CHARS, DEFAULT_MAX_TEXT_CHARS
from .access import accessible_collections
from django.conf import settings
import math

User = get_user_model()


class VectorStoreSerializer(serializers.ModelSerializer):
    """Serializer for VectorStore."""

    store_type_display = serializers.CharField(source='get_store_type_display', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)

    class Meta:
        model = VectorStore
        fields = [
            'id', 'name', 'store_type', 'store_type_display',
            'host', 'port', 'collection', 'dimension', 'metric', 'path',
            'is_default', 'tenant', 'tenant_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VectorStoreCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating VectorStore."""

    port = serializers.IntegerField(min_value=VECTOR_PORT_MIN, max_value=VECTOR_PORT_MAX, required=False)
    dimension = serializers.IntegerField(min_value=VECTOR_DIMENSION_MIN, required=False)
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if self.instance and not attrs.get('api_key'):
            attrs.pop('api_key', None)
        return attrs

    class Meta:
        model = VectorStore
        fields = [
            'id', 'name', 'store_type', 'host', 'port', 'collection',
            'api_key', 'path', 'dimension', 'metric', 'is_default', 'tenant'
        ]
        read_only_fields = ['id']


class ChunkSerializer(serializers.ModelSerializer):
    """Serializer for Chunk."""

    document_id = serializers.UUIDField(read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)

    class Meta:
        model = Chunk
        fields = ['id', 'content', 'chunk_index', 'metadata', 'created_at', 'document_id', 'document_title']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document."""

    chunks = ChunkSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    metadata = serializers.DictField(required=False)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'source_type', 'source_url',
            'content', 'metadata', 'status', 'status_display', 'error_message',
            'chunk_count', 'token_count',
            'created_at', 'updated_at', 'processed_at',
            'chunks'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'source_type', 'source_url', 'error_message', 'chunk_count', 'token_count', 'processed_at']


class DocumentListSerializer(serializers.ModelSerializer):
    """Serializer for Document list view."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'source_type', 'status', 'status_display',
            'chunk_count', 'token_count', 'created_at', 'processed_at', 'error_message', 'source_url'
        ]


class DocumentCreateSerializer(serializers.Serializer):
    """Serializer for creating Document."""

    title = serializers.CharField(max_length=500)
    content = serializers.CharField(max_length=getattr(settings, 'RAG_MAX_TEXT_CHARS', DEFAULT_MAX_TEXT_CHARS))
    metadata = serializers.DictField(required=False, default=dict)


class DocumentURLSerializer(serializers.Serializer):
    """Serializer for adding document from URL."""

    url = serializers.URLField()
    title = serializers.CharField(max_length=500, required=False)


class DocumentCollectionSerializer(serializers.ModelSerializer):
    """Serializer for DocumentCollection."""

    documents = DocumentListSerializer(many=True, read_only=True)
    vector_store_name = serializers.CharField(source='vector_store.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)

    class Meta:
        model = DocumentCollection
        fields = [
            'id', 'name', 'description',
            'vector_store', 'vector_store_name',
            'embedding_model', 'chunk_size', 'chunk_overlap', 'chunk_strategy', 'retrieval_mode',
            'document_count', 'chunk_count',
            'tenant', 'tenant_name', 'owner',
            'created_at', 'updated_at',
            'documents'
        ]
        read_only_fields = ['id', 'owner', 'document_count', 'chunk_count', 'created_at', 'updated_at']


class DocumentCollectionListSerializer(serializers.ModelSerializer):
    """Serializer for DocumentCollection list view."""

    vector_store_name = serializers.CharField(source='vector_store.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)
    document_count = serializers.SerializerMethodField()
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentCollection
        fields = [
            'id', 'name', 'description',
            'vector_store', 'vector_store_name',
            'embedding_model', 'chunk_size', 'chunk_overlap', 'chunk_strategy', 'retrieval_mode',
            'document_count', 'chunk_count',
            'tenant', 'tenant_name', 'owner',
            'created_at'
        ]

    def get_document_count(self, obj):
        live = getattr(obj, 'documents_total', None)
        if live is not None:
            return live
        return obj.document_count or 0

    def get_chunk_count(self, obj):
        live = getattr(obj, 'chunks_total', None)
        if live is not None:
            return live
        return obj.chunk_count or 0


class DocumentCollectionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating DocumentCollection."""

    chunk_size = serializers.IntegerField(min_value=CHUNK_SIZE_MIN, max_value=MAX_CHUNK_SIZE, required=False)
    chunk_overlap = serializers.IntegerField(min_value=CHUNK_OVERLAP_MIN, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            self.fields['vector_store'].queryset = VectorStore.objects.filter(
                Q(owner=request.user) | Q(owner__isnull=True) |
                Q(tenant_id__in=get_accessible_tenant_ids(request.user))
            ).distinct()

    def validate(self, attrs):
        if self.instance and attrs.get('vector_store', self.instance.vector_store) is None:
            attrs.pop('vector_store', None)
        size = attrs.get('chunk_size', self.instance.chunk_size if self.instance else DocumentCollection._meta.get_field('chunk_size').get_default())
        overlap = attrs.get('chunk_overlap', self.instance.chunk_overlap if self.instance else DocumentCollection._meta.get_field('chunk_overlap').get_default())
        if overlap >= size:
            raise serializers.ValidationError({'chunk_overlap': '分块重叠必须小于分块大小。'})
        if self.instance and 'vector_store' in attrs and attrs['vector_store'] != self.instance.vector_store and self.instance.documents.exists():
            raise serializers.ValidationError({'vector_store': '已有文档时不能直接切换存储，请新建知识库并重新导入。'})
        return attrs

    # Make vector_store optional since it will be auto-assigned
    vector_store = serializers.PrimaryKeyRelatedField(
        queryset=VectorStore.objects.all(),
        required=False,
        allow_null=True
    )
    tenant = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = DocumentCollection
        fields = [
            'id', 'name', 'description', 'vector_store', 'tenant',
            'embedding_model', 'chunk_size', 'chunk_overlap', 'chunk_strategy', 'retrieval_mode'
        ]
        read_only_fields = ['id']


class RAGPipelineSerializer(serializers.ModelSerializer):
    """Serializer for RAGPipeline."""

    collection_name = serializers.CharField(source='collection.name', read_only=True)
    tenant = serializers.PrimaryKeyRelatedField(source='collection.tenant', read_only=True)
    tenant_name = serializers.CharField(source='collection.tenant.name', read_only=True, default=None)

    class Meta:
        model = RAGPipeline
        fields = [
            'id', 'name', 'description',
            'collection', 'collection_name',
            'top_k', 'min_similarity',
            'system_prompt', 'include_sources',
            'usage_count', 'tenant', 'tenant_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']


class RAGPipelineCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating RAGPipeline."""

    id = serializers.UUIDField(read_only=True)
    top_k = serializers.IntegerField(min_value=1, max_value=MAX_TOP_K, required=False)
    min_similarity = serializers.FloatField(min_value=0, max_value=1, required=False)

    def validate_min_similarity(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError('最低相关度必须是有限数值。')
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        self.fields['collection'].queryset = accessible_collections(request.user if request else None)

    class Meta:
        model = RAGPipeline
        fields = [
            'id', 'name', 'description', 'collection',
            'top_k', 'min_similarity',
            'system_prompt', 'include_sources'
        ]


class RAGQuerySerializer(serializers.Serializer):
    """Serializer for RAG query."""

    query = serializers.CharField(required=True, max_length=getattr(settings, 'RAG_MAX_QUERY_CHARS', DEFAULT_MAX_QUERY_CHARS))
    filters = serializers.DictField(required=False, default=dict)
    top_k = serializers.IntegerField(min_value=1, max_value=MAX_TOP_K, required=False)
    min_similarity = serializers.FloatField(min_value=0, max_value=1, required=False)


