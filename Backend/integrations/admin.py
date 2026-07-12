"""
Admin configuration for integrations app.
"""

from django.contrib import admin
from .models import Webhook, WebhookDelivery, Integration, IntegrationTemplate


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'url', 'is_active', 'created_at')
    list_filter = ('is_active', 'events')
    search_fields = ('name', 'user__username', 'url')
    readonly_fields = ('created_at', 'updated_at', 'last_triggered_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'user')
        }),
        ('配置', {
            'fields': ('url', 'events', 'is_active')
        }),
        ('认证', {
            'fields': ('secret',)
        }),
        ('Headers', {
            'fields': ('headers',)
        }),
        ('配置', {
            'fields': ('retry_count', 'timeout_seconds', 'content_type')
        }),
        ('统计', {
            'fields': ('total_deliveries', 'successful_deliveries', 'failed_deliveries', 'last_triggered_at'),
            'classes': ('collapse',)
        }),
        ('过滤', {
            'fields': ('workflow_filter', 'tag_filter'),
            'classes': ('collapse',)
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ('webhook', 'status', 'status_code', 'duration_ms', 'created_at')
    list_filter = ('status', 'status_code')
    search_fields = ('webhook__name',)
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'integration_type', 'is_active', 'is_connected', 'created_at')
    list_filter = ('integration_type', 'is_active', 'is_connected')
    search_fields = ('name', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'last_sync_at', 'total_syncs', 'failed_syncs')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'user', 'integration_type')
        }),
        ('配置', {
            'fields': ('is_active', 'is_connected', 'config', 'credentials')
        }),
        ('同步状态', {
            'fields': ('last_sync_at', 'sync_status', 'total_syncs', 'failed_syncs'),
            'classes': ('collapse',)
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(IntegrationTemplate)
class IntegrationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'integration_type', 'category', 'is_active', 'is_featured', 'usage_count', 'created_at')
    list_filter = ('integration_type', 'is_active', 'is_featured', 'category')
    search_fields = ('name', 'description', 'category')
    readonly_fields = ('created_at', 'updated_at', 'usage_count')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'integration_type', 'category')
        }),
        ('展示', {
            'fields': ('icon', 'color', 'is_active', 'is_featured')
        }),
        ('配置模板', {
            'fields': ('config_template', 'required_config', 'optional_config')
        }),
        ('能力与文档', {
            'fields': ('trigger_events', 'supported_actions', 'documentation_url', 'setup_guide')
        }),
        ('统计', {
            'fields': ('usage_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
