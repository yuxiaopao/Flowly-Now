"""
Admin configuration for gateway app.
"""

from django.contrib import admin
from .models import ModelProvider, AIModel, UserAPIKey, APICallLog


@admin.register(ModelProvider)
class ModelProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'website', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'model_id', 'model_type', 'is_active', 'is_default')
    list_filter = ('provider', 'model_type', 'is_active', 'is_default')
    search_fields = ('name', 'model_id', 'description')

    fieldsets = (
        ('基本信息', {
            'fields': ('provider', 'name', 'model_id', 'model_type', 'description')
        }),
        ('能力', {
            'fields': ('max_tokens', 'supports_streaming', 'supports_function_calling', 'supports_vision')
        }),
        ('价格 (每百万Token)', {
            'fields': ('input_price', 'output_price')
        }),
        ('默认参数', {
            'fields': ('default_temperature', 'default_top_p')
        }),
        ('元数据', {
            'fields': ('context_window', 'released_at', 'is_active', 'is_default'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserAPIKey)
class UserAPIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'provider', 'is_active', 'last_used_at', 'total_usage')
    list_filter = ('provider', 'is_active')
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'last_used_at', 'total_usage')
    actions = ['activate_keys', 'deactivate_keys']

    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'provider', 'name')
        }),
        ('API密钥', {
            'fields': ('api_key',)
        }),
        ('Azure配置', {
            'fields': ('endpoint', 'api_version'),
            'classes': ('collapse',)
        }),
        ('使用统计', {
            'fields': ('is_active', 'last_used_at', 'total_usage', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.action(description='激活选中的密钥')
    def activate_keys(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='禁用选中的密钥')
    def deactivate_keys(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(APICallLog)
class APICallLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'model', 'status_code', 'input_tokens', 'output_tokens', 'cost', 'timestamp')
    list_filter = ('provider', 'status_code', 'timestamp')
    search_fields = ('user__username', 'model')
    readonly_fields = ('user', 'provider', 'model', 'endpoint', 'input_tokens', 'output_tokens',
                      'total_tokens', 'latency_ms', 'status_code', 'error_message', 'cost', 'timestamp')
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('请求信息', {
            'fields': ('user', 'provider', 'model', 'endpoint')
        }),
        ('使用量', {
            'fields': ('input_tokens', 'output_tokens', 'total_tokens')
        }),
        ('性能', {
            'fields': ('latency_ms', 'status_code', 'error_message')
        }),
        ('成本', {
            'fields': ('cost', 'timestamp')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
