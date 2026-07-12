"""
Serializers for Desktop Agent models.
"""

from rest_framework import serializers
from .models_desktop import DesktopAgent


class DesktopAgentSerializer(serializers.ModelSerializer):
    """Serializer for DesktopAgent."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_online = serializers.BooleanField(read_only=True)

    class Meta:
        model = DesktopAgent
        fields = [
            'id', 'agent_id', 'display_name',
            'hostname', 'platform',
            'gpu_info', 'gpu_available', 'gpu_name',
            'capabilities', 'supports_yolo_training',
            'status', 'status_display', 'is_online',
            'last_seen', 'cloud_url', 'connected_at',
            'owner', 'created_at',
        ]
        read_only_fields = ['id', 'last_seen', 'created_at']


class DesktopAgentRegisterSerializer(serializers.ModelSerializer):
    """Serializer for registering a new desktop agent."""

    class Meta:
        model = DesktopAgent
        fields = [
            'agent_id', 'display_name',
            'hostname', 'platform',
            'gpu_info', 'gpu_available', 'gpu_name',
            'capabilities', 'supports_yolo_training',
            'cloud_url',
        ]

    def create(self, validated_data):
        validated_data['status'] = 'online'
        return super().create(validated_data)
