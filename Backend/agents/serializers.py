"""
Serializers for agents app.
"""

from rest_framework import serializers
from tenants.models import Tenant
from .models import Agent, AgentTool, AgentConversation, AgentExecution, AgentCollaborationRun


class AgentChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)


class AgentToolsRequestSerializer(serializers.Serializer):
    tools = serializers.ListField(child=serializers.CharField())

    def validate_tools(self, value):
        from .engine import AgentEngine
        unsupported = [name for name in value if name not in AgentEngine.TOOLS_REGISTRY]
        if unsupported:
            raise serializers.ValidationError('不支持的工具：' + '、'.join(unsupported))
        return list(dict.fromkeys(value))


class AgentToolRemoveSerializer(serializers.Serializer):
    tool = serializers.CharField(allow_blank=False)


class ConversationMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=('user', 'assistant', 'system'))
    content = serializers.CharField(allow_blank=False)


class AgentToolSerializer(serializers.ModelSerializer):
    """Serializer for AgentTool model."""

    class Meta:
        model = AgentTool
        fields = ['id', 'name', 'tool_type', 'config', 'is_enabled']


class AgentSerializer(serializers.ModelSerializer):
    """Serializer for Agent model."""

    temperature = serializers.FloatField(min_value=0, max_value=2, required=False)
    max_tokens = serializers.IntegerField(min_value=1, required=False)

    tools_detail = AgentToolSerializer(source='agent_tools', many=True, read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    knowledge_collections_detail = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'agent_type',
            'system_prompt', 'model', 'temperature', 'max_tokens',
            'tools', 'skills', 'memory_enabled', 'context_window',
            'knowledge_collections', 'knowledge_collections_detail',
            'is_active', 'is_public', 'settings', 'tools_detail',
            'tenant', 'tenant_name', 'owner', 'owner_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_knowledge_collections_detail(self, obj):
        from rag.models import DocumentCollection
        ids = obj.knowledge_collections or []
        if not ids:
            return []
        collections = DocumentCollection.objects.filter(id__in=ids)
        return [{'id': str(c.id), 'name': c.name} for c in collections]


class AgentMarketplaceSerializer(serializers.ModelSerializer):
    """Desensitized serializer for public Agent marketplace listing/preview.

    Exposes only the owner's username (not id/email) and never includes
    knowledge_collections (those reference the original owner's private/team
    document collections, which a cloner may not have access to).
    """

    owner_username = serializers.CharField(source='owner.username', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'agent_type', 'system_prompt',
            'model', 'temperature', 'tools', 'skills',
            'owner_username', 'tenant_name', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class AgentListSerializer(serializers.ModelSerializer):
    """Serializer for Agent list view."""

    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'agent_type',
            'model', 'temperature', 'max_tokens', 'tools', 'skills',
            'memory_enabled', 'context_window', 'is_active', 'is_public',
            'knowledge_collections',
            'tenant', 'tenant_name', 'owner',
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
        """Return the number of user-assistant exchange rounds in this execution.

        Each execution is a single-turn interaction: one user message in,
        one assistant response out. So this always returns 1.
        """
        return 1


class AgentCollaborationRoleSerializer(serializers.Serializer):
    """A single role slot in a collaboration run request."""

    role = serializers.ChoiceField(choices=['planner', 'executor', 'critic', 'reporter', 'coordinator'])
    agent_id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    system_prompt = serializers.CharField(required=False, allow_blank=True)
    model = serializers.CharField(required=False, allow_blank=True)


class AgentCollaborationRunCreateSerializer(serializers.Serializer):
    """Serializer for launching a new collaboration run."""

    task = serializers.CharField(required=True, allow_blank=False)
    tenant = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(), required=False, allow_null=True
    )
    roles = AgentCollaborationRoleSerializer(many=True, required=False)


class AgentCollaborationRunSerializer(serializers.ModelSerializer):
    """Serializer for AgentCollaborationRun (list & detail)."""

    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = AgentCollaborationRun
        fields = [
            'id', 'task', 'roles_config', 'status', 'trace',
            'final_report', 'error_message',
            'tenant', 'tenant_name', 'created_by', 'created_by_username',
            'started_at', 'completed_at'
        ]
        read_only_fields = fields


class AgentCollaborationRunListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the collaboration run history list."""

    tenant_name = serializers.CharField(source='tenant.name', read_only=True, default=None)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    role_names = serializers.SerializerMethodField()
    report_preview = serializers.SerializerMethodField()

    class Meta:
        model = AgentCollaborationRun
        fields = [
            'id', 'task', 'status', 'role_names', 'report_preview',
            'tenant', 'tenant_name', 'created_by_username', 'started_at', 'completed_at'
        ]

    def get_role_names(self, obj):
        return [r.get('role') for r in (obj.roles_config or [])]

    def get_report_preview(self, obj):
        text = (obj.final_report or '').strip()
        if not text:
            text = _extract_report_from_trace(obj.trace or [])
        if not text:
            return ''
        return text if len(text) <= 200 else f'{text[:200]}…'


def _extract_report_from_trace(trace):
    """Resolve the best report-like text from a collaboration trace."""
    for phase in ('report', 'review', 'execution', 'planning'):
        for step in trace:
            if step.get('phase') == phase:
                content = (step.get('content') or '').strip()
                if content:
                    return content
    return ''
