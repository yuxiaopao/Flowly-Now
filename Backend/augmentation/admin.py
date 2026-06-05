"""
Admin configuration for augmentation app.
"""

from django.contrib import admin
from .models import AugmentationJob


@admin.register(AugmentationJob)
class AugmentationJobAdmin(admin.ModelAdmin):
    """Admin configuration for AugmentationJob model."""

    list_display = [
        'id', 'input_dataset', 'strategy', 'ratio',
        'augmented_count', 'status', 'progress',
        'created_by', 'created_at'
    ]
    list_filter = ['strategy', 'status', 'output_mode', 'created_at']
    search_fields = ['input_dataset__name', 'output_dataset__name', 'error_message']
    readonly_fields = [
        'id', 'augmented_count', 'original_count',
        'progress', 'error_message',
        'created_at', 'started_at', 'completed_at'
    ]
    ordering = ['-created_at']
    raw_id_fields = ['input_dataset', 'output_dataset', 'created_by']

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'input_dataset', 'output_dataset', 'created_by', 'tenant')
        }),
        ('增强配置', {
            'fields': ('strategy', 'ratio', 'transformations', 'output_mode', 'output_name')
        }),
        ('状态', {
            'fields': ('status', 'progress', 'augmented_count', 'original_count')
        }),
        ('输出', {
            'fields': ('output_dir', 'error_message')
        }),
        ('时间', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
    )
