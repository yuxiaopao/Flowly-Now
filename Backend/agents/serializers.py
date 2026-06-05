"""
Serializers for agents app.
"""

from rest_framework import serializers
from .models import Agent, AgentTool, AgentConversation, AgentExecution


class AgentToolSerializer(serializers.ModelSerializer):
    """Serializer for AgentTool model."""

    class Meta:
        model = AgentTool
        fields = ['id', 'name', 'tool_type', 'config', 'is_enabled']


class AgentSerializer(serializers.ModelSerializer):
    """Serializer for Agent model."""

    tools_detail = AgentToolSerializer(source='agent_tools', many=True, read_only=True)

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'agent_type',
            'system_prompt', 'model', 'temperature', 'max_tokens',
            'tools', 'skills', 'memory_enabled', 'context_window',
            'is_active', 'settings', 'tools_detail',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AgentListSerializer(serializers.ModelSerializer):
    """Serializer for Agent list view."""

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'agent_type',
            'model', 'temperature', 'max_tokens', 'tools', 'skills',
            'memory_enabled', 'context_window', 'is_active',
            'created_at', 'updated_at'
        ]


class AgentConversationSerializer(serializers.ModelSerializer):
    """Serializer for AgentConversation model."""

    class Meta:
        model = AgentConversation
        fields = [
            'id', 'agent', 'messages', 'summary',
            'message_count', 'token_count', 'created_at', 'updated_at'
        ]


class AgentExecutionSerializer(serializers.ModelSerializer):
    """Serializer for AgentExecution model."""

    agent_name = serializers.CharField(source='agent.name', read_only=True)
    exchange_count = serializers.SerializerMethodField()

    class Meta:
        model = AgentExecution
        fields = [
            'id', 'agent', 'agent_name', 'conversation',
            'status', 'input_data', 'output_data', 'error_message',
            'started_at', 'completed_at', 'exchange_count'
        ]

    def get_exchange_count(self, obj):
        """Calculate exchange count from input_data and output_data.

        Returns the number of user-assistant message exchanges in this execution.
        Typically 1 (one user message + one assistant response).
        """
        count = 0
        if obj.input_data and isinstance(obj.input_data, dict) and 'message' in obj.input_data:
            count += 1
        if obj.output_data and isinstance(obj.output_data, dict) and 'response' in obj.output_data:
            count += 1
        return count
