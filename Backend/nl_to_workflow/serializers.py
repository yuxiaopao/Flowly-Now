"""
NL to Workflow serializers.
"""

from rest_framework import serializers
from .models import NLSession


class NLSessionSerializer(serializers.ModelSerializer):
    """Serializer for NL to Workflow sessions."""

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    workflow_name_from_json = serializers.SerializerMethodField()
    node_count = serializers.SerializerMethodField()
    edge_count = serializers.SerializerMethodField()
    provider = serializers.CharField(read_only=True)
    model_used = serializers.CharField(read_only=True)

    class Meta:
        model = NLSession
        fields = [
            'id', 'user', 'user_name', 'name', 'description',
            'workflow', 'workflow_name', 'workflow_json',
            'workflow_name_from_json', 'node_count', 'edge_count',
            'status', 'error_message', 'messages', 'provider', 'model_used',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'workflow', 'workflow_json', 'status', 'error_message', 
                           'messages', 'provider', 'model_used', 'created_at', 'updated_at']

    def get_workflow_name_from_json(self, obj):
        """Extract workflow name from workflow_json if available."""
        if obj.workflow_json:
            return obj.workflow_json.get('name', '')
        return ''

    def get_node_count(self, obj):
        """Count nodes in workflow_json."""
        if obj.workflow_json and 'nodes' in obj.workflow_json:
            return len(obj.workflow_json['nodes'])
        return 0

    def get_edge_count(self, obj):
        """Count edges in workflow_json."""
        if obj.workflow_json and 'edges' in obj.workflow_json:
            return len(obj.workflow_json['edges'])
        return 0


class NLSessionCreateSerializer(serializers.Serializer):
    """Serializer for creating NL to Workflow sessions."""

    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    model = serializers.CharField(required=False, allow_blank=True)
    temperature = serializers.FloatField(required=False, default=0.7)


class NLSessionMessageSerializer(serializers.Serializer):
    """Serializer for sending messages to NL session."""

    message = serializers.CharField()
    continue_generation = serializers.BooleanField(default=False)
    model = serializers.CharField(required=False, allow_blank=True)
    temperature = serializers.FloatField(required=False, default=0.7)


class NLSessionConfirmSerializer(serializers.Serializer):
    """Serializer for confirming/saving generated workflow."""

    workflow_name = serializers.CharField(max_length=200)
    workflow_json = serializers.JSONField()


class NLSessionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating NL sessions."""

    class Meta:
        model = NLSession
        fields = ['name', 'description']


class MessageSerializer(serializers.Serializer):
    """Serializer for chat messages."""

    role = serializers.ChoiceField(choices=['user', 'assistant', 'system'])
    content = serializers.CharField()
    timestamp = serializers.DateTimeField(read_only=True)


class WorkflowPreviewSerializer(serializers.Serializer):
    """Serializer for workflow preview."""

    name = serializers.CharField()
    description = serializers.CharField()
    nodes = serializers.ListField(child=serializers.DictField())
    edges = serializers.ListField(child=serializers.DictField())
    variables = serializers.ListField(child=serializers.DictField(), required=False)
    model = serializers.CharField(required=False, allow_blank=True)
    temperature = serializers.FloatField(required=False, default=0.7)


class IntentAnalysisSerializer(serializers.Serializer):
    """Serializer for intent analysis."""

    message = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)


class IntentAnalysisResultSerializer(serializers.Serializer):
    """Serializer for intent analysis result."""

    intent = serializers.CharField()  # 'create', 'modify', 'delete', 'chat'
    details = serializers.DictField()
    message = serializers.CharField()


class StreamChunkSerializer(serializers.Serializer):
    """Serializer for streaming chunks."""

    type = serializers.ChoiceField(choices=['progress', 'token', 'workflow', 'error', 'session'])
    content = serializers.CharField(required=False)
    progress = serializers.IntegerField(required=False)
    stage = serializers.CharField(required=False)
    message = serializers.CharField(required=False)
    workflow = serializers.DictField(required=False)
    error = serializers.CharField(required=False)
    session_id = serializers.CharField(required=False)


class SuggestionSerializer(serializers.Serializer):
    """Serializer for workflow suggestions."""

    suggestions = serializers.ListField(child=serializers.CharField())
    count = serializers.IntegerField()
