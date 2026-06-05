"""
Admin configuration for nl_to_workflow app.
"""

from django.contrib import admin
from .models import NLSession


@admin.register(NLSession)
class NLSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'status', 'workflow_name', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description', 'user__username', 'workflow_name')
    readonly_fields = ('id', 'user', 'name', 'description', 'messages', 'workflow_json', 'workflow_name', 'workflow_id', 'status', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'user', 'name', 'description')
        }),
        ('工作流信息', {
            'fields': ('workflow_name', 'workflow_id')
        }),
        ('状态', {
            'fields': ('status',)
        }),
        ('消息历史', {
            'fields': ('messages',),
            'classes': ('collapse',)
        }),
        ('生成的工作流JSON', {
            'fields': ('workflow_json',),
            'classes': ('collapse',)
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
