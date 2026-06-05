"""
Django Admin configuration for core app.
Registers notification and audit models.
"""

from django.contrib import admin
from .models.notification import Notification, NotificationPreference
from .models.audit import AuditLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'priority', 'is_read', 'is_archived', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'is_archived', 'created_at']
    search_fields = ['recipient__username', 'title', 'message']
    raw_id_fields = ['recipient', 'related_workflow', 'related_agent']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'push_enabled', 'in_app_enabled', 'quiet_hours_enabled']
    list_filter = ['email_enabled', 'push_enabled', 'in_app_enabled', 'quiet_hours_enabled']
    search_fields = ['user__username']
    raw_id_fields = ['user']
    readonly_fields = ['updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'level', 'description', 'ip_address', 'created_at']
    list_filter = ['action', 'level', 'created_at']
    search_fields = ['user__username', 'description', 'ip_address']
    raw_id_fields = ['user']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
