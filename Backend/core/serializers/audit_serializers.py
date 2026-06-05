"""
Audit log serializers.
"""

from rest_framework import serializers
from ..models.audit import AuditLog, LoginHistory, DataExport


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs."""

    action_display = serializers.CharField(source='get_action_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True, allow_null=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_name', 'action', 'action_display',
            'level', 'level_display', 'description', 'message',
            'target_type', 'target_id', 'target_name',
            'changes', 'old_values', 'new_values',
            'ip_address', 'user_agent', 'request_method', 'request_path',
            'resource_type', 'resource_id', 'metadata',
            'status_code', 'duration_ms', 'created_at'
        ]


class LoginHistorySerializer(serializers.ModelSerializer):
    """Serializer for login history."""

    login_type_display = serializers.CharField(source='get_login_type_display', read_only=True)

    class Meta:
        model = LoginHistory
        fields = [
            'id', 'login_type', 'login_type_display',
            'ip_address', 'user_agent', 'country', 'city',
            'success', 'failure_reason', 'device_type', 'browser', 'os',
            'created_at'
        ]


class DataExportSerializer(serializers.ModelSerializer):
    """Serializer for data exports."""

    export_type_display = serializers.CharField(source='get_export_type_display', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DataExport
        fields = [
            'id', 'export_type', 'export_type_display', 'format', 'format_display',
            'date_from', 'date_to', 'filters',
            'status', 'status_display', 'file_name', 'file_size', 'file_url',
            'download_count', 'expires_at', 'error_message',
            'created_at', 'completed_at'
        ]
