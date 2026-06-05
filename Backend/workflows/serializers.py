"""
Serializers for workflows app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Workflow, Node, Edge, WorkflowExecution, NodeExecution,
    Variable, Tool, APICredential, AuditLog,
    TemplateCategory, WorkflowTemplate,
    ExecutionCache, ExecutionCacheConfig,
    ExecutionLog,
)

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    """Simple user serializer for nested representations."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar']


class NodeSerializer(serializers.ModelSerializer):
    """Serializer for Node model."""

    node_type_display = serializers.CharField(
        source='get_node_type_display',
        read_only=True
    )
    error_handling_display = serializers.CharField(
        source='get_error_handling_display',
        read_only=True
    )
    workflow = serializers.UUIDField(source='workflow.id', read_only=True)

    class Meta:
        model = Node
        fields = [
            'id', 'workflow', 'node_type', 'node_type_display',
            'name', 'description', 'position_x', 'position_y',
            'sort_order',
            'config', 'style',
            'error_handling', 'error_handling_display',
            'max_retries', 'retry_delay_seconds', 'fallback_value',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Support both model instances (via context) and plain dicts."""
        if isinstance(instance, dict):
            return instance
        return super().to_representation(instance)


class NodeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating nodes."""

    # 直接字段
    sort_order = serializers.IntegerField(required=False, default=0)
    error_handling = serializers.CharField(required=False, default='stop')
    max_retries = serializers.IntegerField(required=False, default=3)
    retry_delay_seconds = serializers.FloatField(required=False, default=5.0)

    class Meta:
        model = Node
        fields = [
            'id', 'node_type', 'name', 'description',
            'position_x', 'position_y', 'sort_order', 'config', 'style',
            'error_handling', 'max_retries', 'retry_delay_seconds', 'fallback_value'
        ]
class EdgeSerializer(serializers.ModelSerializer):
    """Serializer for Edge model."""

    source_node_name = serializers.CharField(
        source='source_node.name',
        read_only=True
    )
    target_node_name = serializers.CharField(
        source='target_node.name',
        read_only=True
    )
    source_node_id = serializers.UUIDField(source='source_node.id', read_only=True)
    target_node_id = serializers.UUIDField(source='target_node.id', read_only=True)
    workflow = serializers.UUIDField(source='workflow.id', read_only=True)
    source_node = serializers.UUIDField(source='source_node.id', read_only=True)
    target_node = serializers.UUIDField(source='target_node.id', read_only=True)

    class Meta:
        model = Edge
        fields = [
            'id', 'workflow', 'source_node', 'source_node_id', 'target_node', 'target_node_id',
            'source_handle', 'target_handle', 'label', 'style',
            'condition_expression', 'condition_priority', 'animated',
            'created_at', 'updated_at',
            'source_node_name', 'target_node_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Support both model instances (via context) and plain dicts."""
        if isinstance(instance, dict):
            return instance
        return super().to_representation(instance)


class EdgeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating edges."""

    # 前端传入 source/target (字符串UUID)，映射到 source_node/target_node
    source = serializers.CharField(required=True, write_only=True, source='source_node')
    target = serializers.CharField(required=True, write_only=True, source='target_node')

    class Meta:
        model = Edge
        fields = [
            'id',
            'source_handle', 'target_handle', 'label', 'style',
            'condition_expression', 'condition_priority', 'animated',
            'source', 'target'
        ]

class WorkflowExecutionSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowExecution model."""

    workflow_name = serializers.CharField(
        source='workflow.name',
        read_only=True
    )
    triggered_by_name = serializers.CharField(
        source='triggered_by.username',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    duration = serializers.FloatField(read_only=True)
    node_status_summary = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'workflow', 'workflow_name', 'status', 'status_display',
            'input_data', 'output_data', 'error_message',
            'node_status', 'node_status_summary',
            'started_at', 'completed_at', 'duration',
            'triggered_by', 'triggered_by_name', 'trigger_type',
            'task_id', 'version'
        ]
        read_only_fields = [
            'id', 'started_at', 'completed_at', 'duration'
        ]

    def get_node_status_summary(self, obj) -> dict:
        """Get summary of node execution status."""
        node_status = obj.node_status or {}
        summary = {
            'total': len(node_status),
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'skipped': 0
        }
        for node_data in node_status.values():
            status = node_data if isinstance(node_data, str) else node_data.get('status', '')
            if status in summary:
                summary[status] += 1
        return summary


class WorkflowExecutionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating workflow execution."""

    class Meta:
        model = WorkflowExecution
        fields = ['id', 'input_data', 'trigger_type']


class WorkflowListSerializer(serializers.ModelSerializer):
    """Serializer for workflow list view."""

    owner = UserSimpleSerializer(read_only=True)
    owner_id = serializers.IntegerField(write_only=True, required=False)
    node_count = serializers.IntegerField(read_only=True)
    execution_count = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    # 卡片预览：取前6个节点简略数据（不返回完整config，减轻payload）
    nodes_preview = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'owner', 'owner_id',
            'status', 'status_display', 'is_public',
            'version', 'tags', 'config', 'node_count', 'execution_count',
            'created_at', 'updated_at',
            'nodes_preview',
        ]
        read_only_fields = [
            'id', 'owner', 'version', 'created_at', 'updated_at'
        ]

    def get_nodes_preview(self, obj):
        """Return a lightweight preview of nodes for the card mini-canvas."""
        nodes = list(obj.nodes.all()[:12])
        if not nodes:
            return []
        # 计算包围框
        xs = [n.position_x for n in nodes]
        ys = [n.position_y for n in nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        padding = 60
        view_w, view_h = max(max_x - min_x + padding * 2, 200), max(max_y - min_y + padding * 2, 120)

        return [
            {
                'id': str(n.id),
                'type': n.node_type,
                'name': n.name,
                'position': {
                    'x': n.position_x - min_x + padding,
                    'y': n.position_y - min_y + padding,
                },
            }
            for n in nodes
        ]


class WorkflowDetailSerializer(serializers.ModelSerializer):
    """Serializer for workflow detail view."""

    owner = UserSimpleSerializer(read_only=True)
    nodes = serializers.SerializerMethodField()
    edges = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'owner',
            'status', 'status_display', 'is_public',
            'version', 'parent_version', 'tags', 'config',
            'nodes', 'edges', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'version', 'created_at', 'updated_at'
        ]

    def get_nodes(self, obj):
        nodes = self.context.get('nodes', None)
        if nodes is not None:
            return nodes
        node_serializer = NodeSerializer(
            obj.nodes.all(),
            many=True,
            context={'request': self.context.get('request')}
        )
        return node_serializer.data

    def get_edges(self, obj):
        edges = self.context.get('edges', None)
        if edges is not None:
            return edges
        edge_serializer = EdgeSerializer(
            obj.edges.all(),
            many=True,
            context={'request': self.context.get('request')}
        )
        return edge_serializer.data


class WorkflowCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating workflow with nodes and edges."""

    nodes = serializers.JSONField(required=False, allow_null=True, default=list)
    edges = serializers.JSONField(required=False, allow_null=True, default=list)

    # Max sizes to prevent DoS
    MAX_NAME_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_NODES = 500
    MAX_NODE_DATA_SIZE = 1024 * 1024  # 1MB
    MAX_TAGS = 50
    MAX_TAG_LENGTH = 100

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'status',
            'is_public', 'tags', 'config',
            'nodes', 'edges'
        ]

    def validate_name(self, value):
        if value and len(value) > self.MAX_NAME_LENGTH:
            raise serializers.ValidationError(
                f"名称不能超过 {self.MAX_NAME_LENGTH} 字符"
            )
        return value.strip() if value else value

    def validate_description(self, value):
        if value and len(value) > self.MAX_DESCRIPTION_LENGTH:
            raise serializers.ValidationError(
                f"描述不能超过 {self.MAX_DESCRIPTION_LENGTH} 字符"
            )
        return value

    def validate_tags(self, value):
        if value and len(value) > self.MAX_TAGS:
            raise serializers.ValidationError(
                f"标签数量不能超过 {self.MAX_TAGS}"
            )
        if value:
            for tag in value:
                if len(tag) > self.MAX_TAG_LENGTH:
                    raise serializers.ValidationError(
                        f"单个标签不能超过 {self.MAX_TAG_LENGTH} 字符"
                    )
        return value

    def validate_nodes(self, value):
        if value is None:
            return []
        if len(str(value)) > self.MAX_NODE_DATA_SIZE:
            raise serializers.ValidationError(
                f"节点数据不能超过 {self.MAX_NODE_DATA_SIZE // 1024}KB"
            )
        if len(value) > self.MAX_NODES:
            raise serializers.ValidationError(
                f"节点数量不能超过 {self.MAX_NODES}"
            )
        return value

    def validate_edges(self, value):
        if value is None:
            return []
        if len(str(value)) > self.MAX_NODE_DATA_SIZE:
            raise serializers.ValidationError(
                f"边数据不能超过 {self.MAX_NODE_DATA_SIZE // 1024}KB"
            )
        return value

    def get_fields(self):
        """Override to ensure nodes/edges use JSONField (not reverse FK fields)."""
        fields = super().get_fields()
        # Prevent DRF from auto-generating reverse FK fields for nodes/edges.
        # Input uses writable JSONField above; output is provided by
        # to_representation() which delegates to NodeSerializer/EdgeSerializer.
        if 'nodes' in fields and not isinstance(fields['nodes'], serializers.JSONField):
            fields.pop('nodes')
        if 'edges' in fields and not isinstance(fields['edges'], serializers.JSONField):
            fields.pop('edges')
        return fields

    def to_representation(self, instance):
        """Serialize workflow instance for response.
        Manually serializes all fields to prevent RelatedManager leaking through.
        """
        from .serializers import NodeSerializer, EdgeSerializer

        ret = super().to_representation(instance)
        ret['nodes'] = NodeSerializer(
            instance.nodes.all(), many=True, context=self.context
        ).data
        ret['edges'] = EdgeSerializer(
            instance.edges.all(), many=True, context=self.context
        ).data
        return ret

    def validate(self, attrs):
        """Transform frontend node/edge data to backend format."""
        type_mapping = {
            'http': 'http_request',
            'transform': 'data_transform',
            'switch': 'switch',
            'delay': 'delay',
            'subworkflow': 'subworkflow',
        }

        # Transform nodes
        nodes_raw = attrs.get('nodes', [])
        if nodes_raw:
            nodes_transformed = []
            for node in nodes_raw:
                if not isinstance(node, dict):
                    raise serializers.ValidationError({'nodes': 'Each node must be an object'})

                # Support both flat (snake_case from handleSave) and nested (Vue Flow) formats
                position = node.get('position', {})
                pos_x = node.get('position_x', 0)
                pos_y = node.get('position_y', 0)
                if isinstance(position, dict):
                    pos_x = position.get('x', 0)
                    pos_y = position.get('y', 0)

                data_obj = node.get('data', {}) or {}
                raw_type = node.get('type', '') or node.get('node_type', '')
                node_type = type_mapping.get(raw_type, raw_type)

                nodes_transformed.append({
                    'id': node.get('id'),
                    'node_type': node_type,
                    'name': data_obj.get('label', data_obj.get('name', '')) or node.get('name', ''),
                    'description': data_obj.get('description', '') or node.get('description', ''),
                    'position_x': pos_x,
                    'position_y': pos_y,
                    'sort_order': node.get('sortOrder', 0) or node.get('sort_order', 0),
                    'config': data_obj.get('config', {}) or node.get('config', {}),
                    'style': data_obj.get('style', {}) or node.get('style', {}),
                    'error_handling': data_obj.get('errorHandling', 'stop') or node.get('error_handling', 'stop'),
                    'max_retries': data_obj.get('maxRetries', 3) or node.get('max_retries', 3),
                    'retry_delay_seconds': data_obj.get('retryDelay', 5) or node.get('retry_delay_seconds', 5),
                    'fallback_value': data_obj.get('fallbackValue') or node.get('fallback_value'),
                })
            attrs['nodes'] = nodes_transformed

        # Transform edges
        edges_raw = attrs.get('edges', [])
        if edges_raw:
            edges_transformed = []
            for edge in edges_raw:
                if not isinstance(edge, dict):
                    raise serializers.ValidationError({'edges': 'Each edge must be an object'})

                source = edge.get('source') or edge.get('sourceNode') or edge.get('source_node')
                target = edge.get('target') or edge.get('targetNode') or edge.get('target_node')

                edges_transformed.append({
                    'id': edge.get('id'),
                    'source_node': source,
                    'target_node': target,
                    'source_handle': edge.get('sourceHandle', 'default') or edge.get('source_handle', 'default'),
                    'target_handle': edge.get('targetHandle', 'default') or edge.get('target_handle', 'default'),
                    'label': edge.get('label', ''),
                    'animated': edge.get('animated', False),
                    'condition_expression': edge.get('condition_expression', ''),
                    'condition_priority': edge.get('condition_priority', 0),
                })
            attrs['edges'] = edges_transformed

        return attrs

    def create(self, validated_data):
        nodes_data = validated_data.pop('nodes', [])
        edges_data = validated_data.pop('edges', [])

        if validated_data.get('tags') is None:
            validated_data['tags'] = []
        if validated_data.get('config') is None:
            validated_data['config'] = {}

        workflow = Workflow.objects.create(**validated_data)

        node_id_map = {}

        for node_data in nodes_data:
            node = Node.objects.create(
                workflow=workflow,
                node_type=node_data.get('node_type', ''),
                name=node_data.get('name', ''),
                description=node_data.get('description', ''),
                position_x=node_data.get('position_x', 0),
                position_y=node_data.get('position_y', 0),
                sort_order=node_data.get('sort_order', 0),
                config=node_data.get('config', {}),
                style=node_data.get('style', {}),
                error_handling=node_data.get('error_handling', 'stop'),
                max_retries=node_data.get('max_retries', 3),
                retry_delay_seconds=node_data.get('retry_delay_seconds', 5),
                fallback_value=node_data.get('fallback_value')
            )
            node_id_map[node_data.get('id', node.id)] = node.id
            node_id_map[node.id] = node.id

        for edge_data in edges_data:
            source = edge_data.get('source_node') or edge_data.get('source')
            target = edge_data.get('target_node') or edge_data.get('target')
            source_id = node_id_map.get(source) if isinstance(source, str) else source
            target_id = node_id_map.get(target) if isinstance(target, str) else target
            Edge.objects.create(
                workflow=workflow,
                source_node_id=source_id,
                target_node_id=target_id,
                label=edge_data.get('label', ''),
                animated=edge_data.get('animated', False),
                condition_expression=edge_data.get('condition_expression', ''),
                condition_priority=edge_data.get('condition_priority', 0),
            )

        return workflow

    def update(self, instance, validated_data):
        nodes_data = validated_data.pop('nodes', None)
        edges_data = validated_data.pop('edges', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        node_id_map = {}

        if nodes_data is not None:
            instance.nodes.all().delete()

            for node_data in nodes_data:
                frontend_id = node_data.get('id')

                node = Node.objects.create(
                    workflow=instance,
                    node_type=node_data.get('node_type', ''),
                    name=node_data.get('name', ''),
                    description=node_data.get('description', ''),
                    position_x=node_data.get('position_x', 0),
                    position_y=node_data.get('position_y', 0),
                    sort_order=node_data.get('sort_order', 0),
                    config=node_data.get('config', {}),
                    style=node_data.get('style', {}),
                    error_handling=node_data.get('error_handling', 'stop'),
                    max_retries=node_data.get('max_retries', 3),
                    retry_delay_seconds=node_data.get('retry_delay_seconds', 5),
                    fallback_value=node_data.get('fallback_value')
                )
                if frontend_id:
                    node_id_map[frontend_id] = node.id
                node_id_map[node.id] = node.id

        if edges_data is not None:
            instance.edges.all().delete()

            for edge_data in edges_data:
                source = edge_data.get('source_node') or edge_data.get('source')
                target = edge_data.get('target_node') or edge_data.get('target')

                source_id = node_id_map.get(source) if isinstance(source, str) else source
                target_id = node_id_map.get(target) if isinstance(target, str) else target

                Edge.objects.create(
                    workflow=instance,
                    source_node_id=source_id,
                    target_node_id=target_id,
                    label=edge_data.get('label', ''),
                    animated=edge_data.get('animated', False),
                    condition_expression=edge_data.get('condition_expression', ''),
                    condition_priority=edge_data.get('condition_priority', 0),
                )

        return instance

    def to_representation(self, instance):
        """Serialize workflow instance for response — handles inherited nodes/edges fields."""
        from .serializers import NodeSerializer, EdgeSerializer
        ret = super().to_representation(instance)
        if hasattr(instance, 'nodes'):
            ret['nodes'] = NodeSerializer(
                instance.nodes.all(), many=True,
                context=self.context
            ).data
        if hasattr(instance, 'edges'):
            ret['edges'] = EdgeSerializer(
                instance.edges.all(), many=True,
                context=self.context
            ).data
        return ret


class WorkflowExecuteSerializer(serializers.Serializer):
    """Serializer for workflow execution request."""

    MAX_INPUT_SIZE = 100 * 1024  # 100KB

    input_data = serializers.JSONField(default=dict)
    trigger_type = serializers.CharField(default='manual')
    is_async = serializers.BooleanField(default=False)

    def validate_input_data(self, value):
        if value and len(str(value)) > self.MAX_INPUT_SIZE:
            raise serializers.ValidationError(
                f"输入数据不能超过 {self.MAX_INPUT_SIZE // 1024}KB"
            )
        return value


class WorkflowExecuteResponseSerializer(serializers.Serializer):
    """Serializer for workflow execution response."""

    execution_id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField(required=False)
    stream_url = serializers.CharField(required=False)
    output_data = serializers.JSONField(required=False)
    error_message = serializers.CharField(required=False)


class NodeExecutionLogSerializer(serializers.Serializer):
    """Serializer for node execution log entry."""

    node_id = serializers.IntegerField()
    node_name = serializers.CharField()
    status = serializers.CharField()
    started_at = serializers.DateTimeField(required=False)
    completed_at = serializers.DateTimeField(required=False)
    duration = serializers.FloatField(required=False)
    input_data = serializers.JSONField(required=False)
    output_data = serializers.JSONField(required=False)
    error_message = serializers.CharField(required=False)
    retry_count = serializers.IntegerField(required=False, default=0)
    used_fallback = serializers.BooleanField(required=False, default=False)


# ==================== New Model Serializers ====================

class NodeExecutionSerializer(serializers.ModelSerializer):
    """Serializer for NodeExecution model."""

    node_name = serializers.CharField(source='node.name', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    duration_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model = NodeExecution
        fields = [
            'id', 'execution', 'node', 'node_name', 'node_version',
            'status', 'status_display',
            'input_data', 'output_data',
            'started_at', 'completed_at', 'duration_ms', 'duration_seconds',
            'error_message', 'retry_count', 'max_retries_exceeded',
            'model_name', 'prompt_tokens', 'completion_tokens', 'total_tokens',
            'model_latency_ms', 'cache_hit', 'cache_key',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VariableSerializer(serializers.ModelSerializer):
    """Serializer for Variable model."""

    var_type_display = serializers.CharField(
        source='get_var_type_display',
        read_only=True
    )
    source_display = serializers.CharField(
        source='get_source_display',
        read_only=True
    )

    class Meta:
        model = Variable
        fields = [
            'id', 'workflow', 'name', 'display_name', 'description',
            'var_type', 'var_type_display',
            'default_value', 'validation_rules',
            'source', 'source_display', 'secret_path',
            'is_required', 'is_sensitive',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VariableCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating variables."""

    class Meta:
        model = Variable
        fields = [
            'workflow', 'name', 'display_name', 'description',
            'var_type', 'default_value', 'validation_rules',
            'source', 'secret_path', 'is_required', 'is_sensitive'
        ]


class ToolSerializer(serializers.ModelSerializer):
    """Serializer for Tool model."""

    tool_type_display = serializers.CharField(
        source='get_tool_type_display',
        read_only=True
    )
    auth_type_display = serializers.CharField(
        source='get_auth_type_display',
        read_only=True
    )

    class Meta:
        model = Tool
        fields = [
            'id', 'name', 'display_name', 'description', 'category',
            'tool_type', 'tool_type_display',
            'definition', 'input_schema', 'output_schema',
            'auth_type', 'auth_type_display', 'credential',
            'timeout_seconds', 'retry_policy', 'rate_limit',
            'is_enabled', 'is_public',
            'usage_count', 'avg_execution_time_ms', 'success_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'usage_count']


class ToolCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tools."""

    class Meta:
        model = Tool
        fields = [
            'name', 'display_name', 'description', 'category',
            'tool_type', 'definition', 'input_schema', 'output_schema',
            'auth_type', 'credential', 'timeout_seconds',
            'retry_policy', 'rate_limit', 'is_enabled', 'is_public'
        ]


class APICredentialSerializer(serializers.ModelSerializer):
    """Serializer for APICredential model."""

    credential_type_display = serializers.CharField(
        source='get_credential_type_display',
        read_only=True
    )
    service_type_display = serializers.CharField(
        source='get_service_type_display',
        read_only=True
    )
    masked_credential = serializers.SerializerMethodField()

    class Meta:
        model = APICredential
        fields = [
            'id', 'name', 'description',
            'credential_type', 'credential_type_display',
            'credential_data', 'masked_credential', 'credential_data_hash',
            'service_type', 'service_type_display', 'service_config',
            'scope', 'owner', 'is_encrypted',
            'is_active', 'expires_at', 'last_used_at', 'usage_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'masked_credential', 'credential_data_hash', 'is_encrypted',
            'owner', 'last_used_at', 'usage_count',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'credential_data': {'write_only': True}
        }

    def get_masked_credential(self, obj):
        """Return masked credential for display."""
        return obj.get_masked_data()


class APICredentialCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating API credentials."""

    class Meta:
        model = APICredential
        fields = [
            'name', 'description', 'credential_type',
            'credential_data', 'service_type', 'service_config',
            'scope', 'expires_at', 'is_active'
        ]
        extra_kwargs = {
            'credential_data': {'write_only': True}
        }

    def create(self, validated_data):
        """Create credential with encrypted data."""
        raw_data = validated_data.pop('credential_data', '')
        credential = APICredential(**validated_data)
        if raw_data:
            credential.set_encrypted_data(raw_data)
        credential.save()
        return credential


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""

    user_name = serializers.CharField(
        source='user.username',
        read_only=True,
        default=None
    )
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_name', 'action', 'action_display',
            'resource_type', 'resource_id',
            'old_value', 'new_value',
            'ip_address', 'user_agent', 'request_id',
            'status', 'status_display', 'error_message',
            'timestamp'
        ]
        read_only_fields = fields


class AuditLogFilterSerializer(serializers.Serializer):
    """Serializer for audit log filtering."""

    user_id = serializers.IntegerField(required=False)
    action = serializers.CharField(required=False)
    resource_type = serializers.CharField(required=False)
    resource_id = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=50, min_value=1, max_value=100)


# ==================== Template Serializers ====================

class TemplateCategorySerializer(serializers.ModelSerializer):
    """Serializer for TemplateCategory model."""

    template_count = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'color',
            'sort_order', 'is_active', 'template_count', 'created_at'
        ]

    def get_template_count(self, obj):
        return obj.templates.filter(is_active=True).count()


class WorkflowTemplateListSerializer(serializers.ModelSerializer):
    """Serializer for workflow template list view."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'category', 'category_name', 'category_slug', 'name',
            'description', 'difficulty', 'tags', 'thumbnail_url',
            'estimated_duration', 'required_apis', 'use_count', 'rating',
            'rating_count', 'is_featured', 'is_verified', 'creator_name',
            'created_at'
        ]


class WorkflowTemplateDetailSerializer(serializers.ModelSerializer):
    """Serializer for workflow template detail view."""

    category = TemplateCategorySerializer(read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'category', 'name', 'description', 'difficulty', 'tags',
            'thumbnail_url', 'workflow_data', 'variables_schema',
            'estimated_duration', 'required_apis', 'use_count', 'rating',
            'rating_count', 'is_featured', 'is_verified', 'version',
            'creator_name', 'created_at', 'updated_at'
        ]


class WorkflowTemplateCreateFromSerializer(serializers.Serializer):
    """Serializer for creating workflow from template."""

    name = serializers.CharField(max_length=200, required=False)
    variables = serializers.DictField(required=False, default=dict)


class ExecutionCacheSerializer(serializers.ModelSerializer):
    """Serializer for ExecutionCache model."""

    is_expired = serializers.BooleanField(read_only=True)
    node_type_display = serializers.SerializerMethodField()

    class Meta:
        model = ExecutionCache
        fields = [
            'id', 'config_hash', 'node_type', 'node_type_display',
            'node_config', 'output_data', 'created_at',
            'access_count', 'last_accessed', 'is_valid',
            'expires_at', 'checksum', 'is_expired'
        ]
        read_only_fields = fields

    def get_node_type_display(self, obj):
        """Get display name for node type."""
        node_types = dict(Node.NODE_TYPE_CHOICES)
        return node_types.get(obj.node_type, obj.node_type)


class ExecutionCacheConfigSerializer(serializers.ModelSerializer):
    """Serializer for ExecutionCacheConfig model."""

    class Meta:
        model = ExecutionCacheConfig
        fields = [
            'node_type', 'enabled', 'ttl_hours', 'max_size_mb',
            'created_at', 'updated_at'
        ]


class ExecutionCacheStatsSerializer(serializers.Serializer):
    """Serializer for cache statistics."""

    total = serializers.IntegerField()
    valid = serializers.IntegerField()
    expired = serializers.IntegerField()
    invalid = serializers.IntegerField()
    hit_rate = serializers.FloatField()
    by_node_type = serializers.ListField()


class ExecutionLogSerializer(serializers.ModelSerializer):
    """Serializer for ExecutionLog model."""

    node_name = serializers.CharField(source='node_execution.node.name', read_only=True, allow_null=True)

    class Meta:
        model = ExecutionLog
        fields = [
            'id', 'execution', 'node_execution', 'node_name',
            'level', 'message', 'details', 'timestamp'
        ]
        read_only_fields = fields
