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
    list_display = ('name', 'integration_type', 'is_active', 'created_at')
    list_filter = ('integration_type', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'last_sync_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'integration_type')
        }),
        ('配置', {
            'fields': ('is_active', 'config')
        }),
        ('OAuth', {
            'fields': ('oauth_client_id', 'oauth_scopes'),
            'classes': ('collapse',)
        }),
        ('同步状态', {
            'fields': ('last_sync_at', 'sync_status'),
            'classes': ('collapse',)
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(IntegrationTemplate)
class IntegrationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'integration_type', 'is_active', 'created_at')
    list_filter = ('integration_type', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'integration_type')
        }),
        ('配置模板', {
            'fields': ('config_schema', 'auth_flow_instructions')
        }),
        ('图标', {
            'fields': ('icon_svg',)
        }),
        ('状态', {
            'fields': ('is_active', 'created_at'),
            'classes': ('collapse',)
        }),
    )
