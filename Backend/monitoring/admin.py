"""
Admin configuration for monitoring app.
"""

from django.contrib import admin
from .models import ExecutionLog, AlertRule, Alert, Metric, NotificationChannel


@admin.register(ExecutionLog)
class ExecutionLogAdmin(admin.ModelAdmin):
    list_display = ('level', 'message', 'workflow_execution', 'node_name', 'timestamp')
    list_filter = ('level', 'timestamp')
    search_fields = ('message', 'node_name')
    readonly_fields = ('workflow_execution', 'node_id', 'node_name', 'level', 'message', 'details', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'condition', 'severity', 'is_active', 'owner', 'created_at')
    list_filter = ('condition', 'severity', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'owner')
        }),
        ('触发条件', {
            'fields': ('condition', 'severity', 'threshold', 'time_window_minutes')
        }),
        ('通知设置', {
            'fields': ('notify_email', 'notify_webhook', 'webhook_url')
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'severity', 'status', 'rule', 'triggered_by_type', 'created_at')
    list_filter = ('severity', 'status', 'rule')
    search_fields = ('title', 'message')
    readonly_fields = ('rule', 'severity', 'title', 'message', 'triggered_by_type', 'triggered_by_id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('告警信息', {
            'fields': ('rule', 'severity', 'title', 'message')
        }),
        ('触发对象', {
            'fields': ('triggered_by_type', 'triggered_by_id')
        }),
        ('状态', {
            'fields': ('status', 'resolved_by', 'resolved_at', 'resolution_note')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['acknowledge_alerts', 'resolve_alerts', 'mute_alerts']

    @admin.action(description='确认选中的告警')
    def acknowledge_alerts(self, request, queryset):
        queryset.update(status='acknowledged')

    @admin.action(description='解决选中的告警')
    def resolve_alerts(self, request, queryset):
        queryset.update(status='resolved', resolved_by=request.user)

    @admin.action(description='静默选中的告警')
    def mute_alerts(self, request, queryset):
        queryset.update(status='muted')


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ('metric_type', 'value', 'unit', 'user', 'workflow', 'timestamp')
    list_filter = ('metric_type', 'timestamp')
    search_fields = ('metric_type',)
    readonly_fields = ('metric_type', 'value', 'unit', 'tags', 'user', 'workflow', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'channel_type', 'is_active', 'owner', 'created_at')
    list_filter = ('channel_type', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'channel_type', 'owner')
        }),
        ('配置', {
            'fields': ('config', 'is_active')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
