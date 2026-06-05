"""
Workflow admin configuration.
"""

from django.contrib import admin
from .models import (
    Workflow, Node, Edge, WorkflowExecution, NodeExecution,
    Variable, Tool, APICredential, AuditLog, WebhookDeliveryLog
)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin for Workflow model."""

    list_display = [
        'name', 'owner', 'status', 'is_public',
        'node_count', 'execution_count', 'created_at'
    ]
    list_filter = ['status', 'is_public', 'is_deleted', 'created_at']
    search_fields = ['name', 'description']
    raw_id_fields = ['owner', 'parent_version', 'tenant']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
    ordering = ['-created_at']


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    """Admin for Node model."""

    list_display = [
        'name', 'node_type', 'workflow', 'position_x', 'position_y', 'created_at'
    ]
    list_filter = ['node_type', 'is_enabled', 'created_at']
    search_fields = ['name', 'description']
    raw_id_fields = ['workflow', 'parent_node']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    """Admin for Edge model."""

    list_display = [
        'workflow', 'source_node', 'target_node', 'label', 'animated'
    ]
    list_filter = ['workflow', 'animated']
    raw_id_fields = ['workflow', 'source_node', 'target_node']


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    """Admin for WorkflowExecution model."""

    list_display = [
        'workflow', 'status', 'triggered_by', 'started_at', 'completed_at'
    ]
    list_filter = ['status', 'trigger_type', 'started_at']
    search_fields = ['workflow__name']
    raw_id_fields = ['workflow', 'triggered_by', 'tenant']
    readonly_fields = ['queued_at', 'started_at', 'completed_at']
    ordering = ['-queued_at']


@admin.register(NodeExecution)
class NodeExecutionAdmin(admin.ModelAdmin):
    """Admin for NodeExecution model."""

    list_display = [
        'node', 'execution', 'status', 'started_at', 'completed_at', 'duration_ms'
    ]
    list_filter = ['status', 'cache_hit', 'started_at']
    search_fields = ['node__name', 'execution__workflow__name']
    raw_id_fields = ['execution', 'node']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Variable)
class VariableAdmin(admin.ModelAdmin):
    """Admin for Variable model."""

    list_display = [
        'name', 'var_type', 'workflow', 'source', 'is_required', 'is_sensitive'
    ]
    list_filter = ['var_type', 'source', 'is_required', 'is_sensitive']
    search_fields = ['name', 'display_name', 'description']
    raw_id_fields = ['workflow']


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    """Admin for Tool model."""

    list_display = [
        'name', 'tool_type', 'category', 'auth_type', 'is_enabled', 'usage_count'
    ]
    list_filter = ['tool_type', 'auth_type', 'is_enabled', 'is_public', 'category']
    search_fields = ['name', 'display_name', 'description']
    raw_id_fields = ['credential', 'tenant']
    readonly_fields = ['created_at', 'updated_at', 'usage_count']


@admin.register(APICredential)
class APICredentialAdmin(admin.ModelAdmin):
    """Admin for APICredential model."""

    list_display = [
        'name', 'credential_type', 'service_type', 'owner', 'is_active', 'last_used_at'
    ]
    list_filter = ['credential_type', 'service_type', 'is_active']
    search_fields = ['name', 'description']
    raw_id_fields = ['owner', 'tenant']
    readonly_fields = ['created_at', 'updated_at', 'last_used_at', 'usage_count']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin for AuditLog model."""

    list_display = [
        'user', 'action', 'resource_type', 'resource_id', 'status', 'timestamp'
    ]
    list_filter = ['action', 'resource_type', 'status', 'timestamp']
    search_fields = ['user__username', 'resource_id', 'action']
    raw_id_fields = ['user', 'tenant']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']


@admin.register(WebhookDeliveryLog)
class WebhookDeliveryLogAdmin(admin.ModelAdmin):
    """Admin for WebhookDeliveryLog model."""

    list_display = [
        'webhook_url', 'execution', 'status', 'success', 'response_status_code', 'created_at'
    ]
    list_filter = ['status', 'success', 'created_at']
    search_fields = ['webhook_url']
    raw_id_fields = ['execution']
    readonly_fields = ['created_at']
