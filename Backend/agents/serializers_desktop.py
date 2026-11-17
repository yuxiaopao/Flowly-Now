"""
Serializers for Desktop Agent models.
"""

import re

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
        read_only_fields = ['id', 'agent_id', 'owner', 'last_seen', 'connected_at', 'created_at']


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
        extra_kwargs = {'agent_id': {'validators': [], 'trim_whitespace': True}}

    def validate_agent_id(self, value):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
            raise serializers.ValidationError('Agent ID 只能包含字母、数字、下划线和连字符')
        return value

    def create(self, validated_data):
        validated_data['status'] = 'online'
        return super().create(validated_data)
