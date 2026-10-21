"""
Admin configuration for RAG app.
"""

from django.contrib import admin
from .models import VectorStore, DocumentCollection, Document, Chunk, RAGPipeline


@admin.register(VectorStore)
class VectorStoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'store_type', 'host', 'port', 'dimension', 'is_default')
    list_filter = ('store_type', 'is_default')
    search_fields = ('name', 'host', 'collection')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'store_type', 'is_default')
        }),
        ('连接设置', {
            'fields': ('host', 'port', 'collection', 'api_key')
        }),
        ('本地路径', {
            'fields': ('path',),
            'classes': ('collapse',)
        }),
        ('配置', {
            'fields': ('dimension', 'metric')
        }),
        ('所有者', {
            'fields': ('owner',)
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DocumentCollection)
class DocumentCollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'vector_store', 'embedding_model', 'document_count', 'chunk_count', 'created_at')
    list_filter = ('embedding_model',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'vector_store', 'owner')
        }),
        ('Embedding配置', {
            'fields': ('retrieval_mode', 'embedding_model', 'chunk_strategy', 'chunk_size', 'chunk_overlap')
        }),
        ('统计', {
            'fields': ('document_count', 'chunk_count')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'collection', 'source_type', 'status', 'chunk_count', 'token_count', 'created_at')
    list_filter = ('source_type', 'status')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at', 'processed_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('collection', 'title', 'source_type', 'source_url')
        }),
        ('内容', {
            'fields': ('content', 'metadata')
        }),
        ('处理状态', {
            'fields': ('status', 'error_message', 'chunk_count', 'token_count')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['reprocess_documents', 'mark_as_failed']

    @admin.action(description='重新处理选中的文档')
    def reprocess_documents(self, request, queryset):
        from .pipeline import DocumentProcessor
        results = [DocumentProcessor(document.collection).process_document(document) for document in queryset]
        completed = sum(result['success'] for result in results)
        self.message_user(request, f'{completed} 个文档完成，{len(results) - completed} 个失败；请查看文档状态。')

    @admin.action(description='标记为失败')
    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ('document', 'chunk_index', 'vector_id', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'document__title')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RAGPipeline)
class RAGPipelineAdmin(admin.ModelAdmin):
    list_display = ('name', 'collection', 'top_k', 'min_similarity', 'usage_count', 'created_at')
    list_filter = ('include_sources',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'usage_count')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'collection', 'owner')
        }),
        ('检索设置', {
            'fields': ('top_k', 'min_similarity')
        }),
        ('生成设置', {
            'fields': ('system_prompt', 'include_sources')
        }),
        ('统计', {
            'fields': ('usage_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
