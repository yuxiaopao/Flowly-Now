"""
Notification serializers.
"""

from rest_framework import serializers
from ..models.notification import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""

    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display', read_only=True
    )
    recipient_name = serializers.CharField(
        source='recipient.username', read_only=True, allow_null=True
    )
    related_workflow_name = serializers.CharField(
        source='related_workflow.name', read_only=True, allow_null=True
    )
    related_agent_name = serializers.CharField(
        source='related_agent.name', read_only=True, allow_null=True
    )

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name',
            'notification_type', 'notification_type_display',
            'title', 'message', 'link',
            'priority', 'priority_display',
            'is_read', 'is_archived',
            'related_workflow', 'related_workflow_name',
            'related_execution', 'related_agent', 'related_agent_name',
            'metadata', 'icon', 'color',
            'read_at', 'created_at'
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences."""

    class Meta:
        model = NotificationPreference
        fields = [
            'id',
            'workflow_completed', 'workflow_failed', 'workflow_scheduled',
            'agent_completed', 'agent_failed', 'trigger_activated',
            'alert_triggered', 'system_message', 'user_invitation',
            'comment', 'mention',
            'email_enabled', 'push_enabled', 'in_app_enabled',
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            'updated_at'
        ]
