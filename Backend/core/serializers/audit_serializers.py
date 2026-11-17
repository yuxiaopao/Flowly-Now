"""
Audit log serializers.
"""

from rest_framework import serializers
from ..models.audit import AuditLog, LoginHistory, DataExport, PersonalBackupPolicy
from core.data_constants import EXPORT_FORMATS, EXPORT_TYPES, SNAPSHOT_VERSION, MIN_BACKUP_RETENTION, MAX_BACKUP_RETENTION


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
    restorable = serializers.SerializerMethodField()

    def get_restorable(self, instance):
        if hasattr(instance, '_restorable'):
            return instance._restorable
        return (instance.status == 'completed' and instance.format == 'json'
                and instance.export_type in ('full', 'workflows', 'agents')
                and instance.snapshot.get('schema_version') == SNAPSHOT_VERSION)

    class Meta:
        model = DataExport
        fields = [
            'id', 'export_type', 'export_type_display', 'format', 'format_display',
            'date_from', 'date_to', 'filters',
            'status', 'status_display', 'file_name', 'file_size', 'file_url',
            'download_count', 'expires_at', 'error_message',
            'created_at', 'completed_at', 'is_backup', 'restorable',
        ]
        read_only_fields = fields


class DataExportRequestSerializer(serializers.Serializer):
    export_type = serializers.ChoiceField(choices=EXPORT_TYPES, default='full')
    format = serializers.ChoiceField(choices=EXPORT_FORMATS, default='json')
    date_from = serializers.DateTimeField(required=False, allow_null=True)
    date_to = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, data):
        if data.get('date_from') and data.get('date_to') and data['date_from'] > data['date_to']:
            raise serializers.ValidationError('开始日期必须早于结束日期。')
        return data


class PersonalBackupPolicySerializer(serializers.ModelSerializer):
    scheduler_configured = serializers.SerializerMethodField()
    retention_min = serializers.IntegerField(read_only=True, default=MIN_BACKUP_RETENTION)
    retention_max = serializers.IntegerField(read_only=True, default=MAX_BACKUP_RETENTION)

    class Meta:
        model = PersonalBackupPolicy
        fields = ['enabled', 'frequency', 'keep_count', 'next_run_at', 'last_run_at', 'last_error', 'scheduler_configured', 'retention_min', 'retention_max']
        read_only_fields = ['next_run_at', 'last_run_at', 'last_error', 'scheduler_configured']

    def get_scheduler_configured(self, _instance):
        from core.services.personal_backups import scheduler_configured
        return scheduler_configured()
