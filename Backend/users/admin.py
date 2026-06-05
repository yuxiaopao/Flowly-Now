"""
Admin configuration for users app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with additional fields."""

    list_display = ('username', 'email', 'role', 'is_active', 'is_staff', 'total_executions', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'phone')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('个人信息', {
            'fields': ('avatar', 'phone', 'bio')
        }),
        ('AI设置', {
            'fields': ('openai_api_key', 'openai_base_url', 'default_model')
        }),
        ('使用统计', {
            'fields': ('total_executions', 'monthly_executions', 'execution_limit')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at', 'last_login_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = BaseUserAdmin.readonly_fields + ('created_at', 'updated_at', 'last_login_at')

    actions = ['activate_users', 'deactivate_users', 'reset_monthly_executions']

    @admin.action(description='激活选中的用户')
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='禁用选中的用户')
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description='重置月度执行次数')
    def reset_monthly_executions(self, request, queryset):
        queryset.update(monthly_executions=0)
