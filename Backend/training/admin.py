"""
Training App Admin Configuration
"""
from django.contrib import admin
from .models import TrainingJob, Dataset


@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'framework', 'model_type', 'status',
        'progress', 'current_epoch', 'total_epochs',
        'created_at', 'started_at', 'completed_at'
    ]
    list_filter = ['status', 'framework', 'model_type', 'created_at']
    search_fields = ['id', 'name', 'error_message']
    readonly_fields = [
        'id', 'created_at',
        'current_epoch', 'total_epochs', 'progress',
        'current_loss', 'current_metric', 'metrics_history'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'name', 'framework', 'model_type', 'status')
        }),
        ('配置', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('GPU信息', {
            'fields': ('gpu_info',)
        }),
        ('训练进度', {
            'fields': (
                'current_epoch', 'total_epochs',
                'progress', 'current_loss', 'current_metric'
            )
        }),
        ('指标历史', {
            'fields': ('metrics_history',),
            'classes': ('collapse',)
        }),
        ('输出文件', {
            'fields': ('model_path', 'error_message')
        }),
        ('时间记录', {
            'fields': ('started_at', 'completed_at', 'duration_seconds')
        }),
        ('关联关系', {
            'fields': ('workflow', 'node', 'execution', 'created_by', 'tenant')
        }),
        ('时间戳', {
            'fields': ('created_at',)
        }),
    )


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'format', 'size', 'row_count',
        'created_at', 'created_by'
    ]
    list_filter = ['format', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
