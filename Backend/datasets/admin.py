"""
Admin configuration for datasets app.
"""

from django.contrib import admin
from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Admin configuration for Dataset model."""

    list_display = [
        'name', 'source', 'format', 'size_bytes',
        'row_count', 'column_count', 'status',
        'created_by', 'created_at'
    ]
    list_filter = ['source', 'format', 'status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = [
        'id', 'row_count', 'column_count', 'columns',
        'preview_data', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'name', 'description', 'created_by', 'tenant')
        }),
        ('数据来源', {
            'fields': ('source', 'file', 'file_path', 'url', 's3_path', 's3_bucket')
        }),
        ('数据信息', {
            'fields': ('format', 'size_bytes', 'row_count', 'column_count', 'columns')
        }),
        ('状态', {
            'fields': ('status', 'error_message')
        }),
        ('元数据', {
            'fields': ('metadata', 'preview_data')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at')
        }),
    )
