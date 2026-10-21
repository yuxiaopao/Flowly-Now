"""
RAG (Retrieval-Augmented Generation) models.
"""

import uuid

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

from .constants import (
    CHUNK_STRATEGIES, RETRIEVAL_MODES, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP,
    DEFAULT_TOP_K, DEFAULT_MIN_SIMILARITY, DEFAULT_SYSTEM_PROMPT,
)

# Import constants for default values
from config.constants import (
    VECTOR_STORE_DEFAULT_HOST,
    VECTOR_STORE_DEFAULT_PORT,
    VECTOR_STORE_DEFAULT_COLLECTION,
    VECTOR_STORE_DEFAULT_DIMENSION,
    DEFAULT_EMBEDDING_MODEL,
)


class VectorStore(models.Model):
    """Vector store configuration."""

    TYPE_CHOICES = [
        ('memory', '本地持久化存储'),
        ('qdrant', 'Qdrant'),
        ('milvus', 'Milvus'),
        ('chroma', 'Chroma'),
        ('pinecone', 'Pinecone'),
        ('weaviate', 'Weaviate'),
        ('ollama', 'Ollama'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200, verbose_name='名称')
    store_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        verbose_name='类型'
    )

    # Connection settings
    host = models.CharField(max_length=255, default=VECTOR_STORE_DEFAULT_HOST, verbose_name='主机')
    port = models.IntegerField(default=VECTOR_STORE_DEFAULT_PORT, verbose_name='端口')
    collection = models.CharField(max_length=200, default=VECTOR_STORE_DEFAULT_COLLECTION, verbose_name='集合名')
    api_key = models.CharField(max_length=500, blank=True, verbose_name='API Key')
    path = models.CharField(max_length=500, blank=True, verbose_name='本地路径')

    # Settings
    dimension = models.IntegerField(default=VECTOR_STORE_DEFAULT_DIMENSION, verbose_name='向量维度')
    metric = models.CharField(max_length=50, default='cosine', verbose_name='度量方式')
    is_default = models.BooleanField(default=False, verbose_name='是否为默认')

    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vector_stores',
        null=True,
        blank=True,
        verbose_name='所有者'
    )

    # Team sharing: when set, all members of this tenant can see/use this vector store
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        related_name='vector_stores',
        null=True,
        blank=True,
        verbose_name='所属团队'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'rag_vector_stores'
        verbose_name = '向量存储'
        verbose_name_plural = '向量存储'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['owner']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_store_type_display()})"


class DocumentCollection(models.Model):
    """Document collection for RAG."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Vector store
    vector_store = models.ForeignKey(
        VectorStore,
        on_delete=models.CASCADE,
        related_name='collections',
        verbose_name='向量存储'
    )

    # Collection settings
    embedding_model = models.CharField(
        max_length=100,
        default=DEFAULT_EMBEDDING_MODEL,
        verbose_name='Embedding 模型'
    )
    chunk_size = models.IntegerField(default=DEFAULT_CHUNK_SIZE, verbose_name='分块大小')
    chunk_overlap = models.IntegerField(default=DEFAULT_CHUNK_OVERLAP, verbose_name='分块重叠')
    chunk_strategy = models.CharField(max_length=20, choices=CHUNK_STRATEGIES, default='recursive')
    retrieval_mode = models.CharField(max_length=20, choices=RETRIEVAL_MODES, default='keyword')

    # Stats
    document_count = models.IntegerField(default=0, verbose_name='文档数')
    chunk_count = models.IntegerField(default=0, verbose_name='分块数')

    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='document_collections',
        verbose_name='所有者'
    )

    # Team sharing: when set, all members of this tenant can see/use this collection
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        related_name='document_collections',
        null=True,
        blank=True,
        verbose_name='所属团队'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'rag_document_collections'
        verbose_name = '文档集合'
        verbose_name_plural = '文档集合'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['owner']),
        ]

    def __str__(self):
        return self.name


class Document(models.Model):
    """Document in a collection."""

    STATUS_CHOICES = [
        ('pending', '等待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    collection = models.ForeignKey(
        DocumentCollection,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='所属集合'
    )

    title = models.CharField(max_length=500, verbose_name='标题')
    source_type = models.CharField(
        max_length=50,
        choices=[
            ('file', '文件'),
            ('url', '网址'),
            ('text', '文本'),
        ],
        default='text',
        verbose_name='来源类型'
    )
    source_url = models.URLField(max_length=2000, blank=True, verbose_name='来源URL')

    # Content
    content = models.TextField(verbose_name='内容')
    metadata = models.JSONField(default=dict, verbose_name='元数据')

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态',
        db_index=True
    )
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    # Stats
    chunk_count = models.IntegerField(default=0, verbose_name='分块数')
    token_count = models.IntegerField(default=0, verbose_name='Token数')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')

    class Meta:
        db_table = 'rag_documents'
        verbose_name = '文档'
        verbose_name_plural = '文档'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Chunk(models.Model):
    """Document chunk."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name='所属文档'
    )

    content = models.TextField(verbose_name='内容')
    chunk_index = models.IntegerField(default=0, verbose_name='分块索引')

    # Vector
    vector_id = models.CharField(max_length=200, blank=True, verbose_name='向量ID')
    embedding = models.JSONField(default=list, blank=True, verbose_name='持久化向量')

    # Metadata
    metadata = models.JSONField(default=dict, verbose_name='元数据')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'rag_chunks'
        verbose_name = '文档分块'
        verbose_name_plural = '文档分块'
        ordering = ['chunk_index']

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"


class RAGPipeline(models.Model):
    """RAG pipeline configuration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Pipeline settings
    collection = models.ForeignKey(
        DocumentCollection,
        on_delete=models.CASCADE,
        related_name='pipelines',
        verbose_name='文档集合'
    )

    # Retrieval settings
    top_k = models.IntegerField(default=DEFAULT_TOP_K, verbose_name='返回数量')
    min_similarity = models.FloatField(default=DEFAULT_MIN_SIMILARITY, verbose_name='最低相似度')

    # Generation settings
    system_prompt = models.TextField(
        default=DEFAULT_SYSTEM_PROMPT,
        verbose_name='系统提示词'
    )
    include_sources = models.BooleanField(default=True, verbose_name='包含来源')

    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rag_pipelines',
        verbose_name='所有者'
    )

    # Usage stats
    usage_count = models.IntegerField(default=0, verbose_name='使用次数')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'rag_pipelines'
        verbose_name = 'RAG流水线'
        verbose_name_plural = 'RAG流水线'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
