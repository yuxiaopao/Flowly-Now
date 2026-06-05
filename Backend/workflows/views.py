"""
Views for workflows app.
"""

import json
import logging
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.db import models
from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def _get_accessible_tenant_ids(user):
    """Return active tenant ids the user belongs to."""
    if not user or not user.is_authenticated:
        return []

    if user.is_superuser:
        from tenants.models import Tenant
        return list(Tenant.objects.values_list('id', flat=True))

    from tenants.models import TenantMembership
    return list(
        TenantMembership.objects.filter(user=user, is_active=True)
        .values_list('tenant_id', flat=True)
        .distinct()
    )


def _get_accessible_workflow_queryset(user):
    """Return workflows visible to the current user with tenant boundary enforced."""
    queryset = Workflow.objects.filter(is_deleted=False)

    if not user or not user.is_authenticated:
        return queryset.filter(is_public=True, tenant__isnull=True)

    if user.is_superuser:
        return queryset

    tenant_ids = _get_accessible_tenant_ids(user)
    return queryset.filter(
        Q(owner=user)
        | Q(tenant_id__in=tenant_ids)
        | Q(is_public=True, tenant__isnull=True)
    ).distinct()


def _get_accessible_workflow(user, workflow_id):
    """Resolve a workflow only if it is accessible to the current user."""
    return _get_accessible_workflow_queryset(user).get(id=workflow_id)


class CheckEnvView(APIView):
    """返回 PyTorch / GPU 环境信息，无需认证，供前端模型训练节点配置时展示."""
    permission_classes = [AllowAny]

    def get(self, request):
        gpu_info = {'available': False, 'name': None, 'memory_total': 0}
        try:
            import torch
            gpu_info['available'] = torch.cuda.is_available()
            if gpu_info['available']:
                gpu_info['name'] = torch.cuda.get_device_name(0)
                gpu_info['memory_total'] = torch.cuda.get_device_properties(0).total_memory
            gpu_info['torch_version'] = torch.__version__
        except ImportError:
            gpu_info['error'] = 'PyTorch not installed'
        except Exception as e:
            gpu_info['error'] = str(e)

        try:
            import transformers
            gpu_info['transformers_version'] = transformers.__version__
        except ImportError:
            pass

        try:
            import torchvision
            gpu_info['torchvision_version'] = torchvision.__version__
        except ImportError:
            pass

        return Response({'success': True, 'gpu_info': gpu_info})


from .models import (
    Workflow, Node, Edge, WorkflowExecution, NodeExecution,
    Variable, Tool, APICredential, AuditLog,
    TemplateCategory, WorkflowTemplate,
    ExecutionCache, ExecutionCacheConfig,
    ExecutionLog,
)
from .serializers import (
    WorkflowListSerializer, WorkflowDetailSerializer, WorkflowCreateSerializer,
    WorkflowExecuteSerializer, WorkflowExecutionSerializer, WorkflowExecuteResponseSerializer,
    NodeSerializer, NodeCreateSerializer,
    EdgeSerializer, EdgeCreateSerializer,
    NodeExecutionSerializer, VariableSerializer, VariableCreateSerializer,
    ToolSerializer, ToolCreateSerializer,
    APICredentialSerializer, APICredentialCreateSerializer,
    AuditLogSerializer,
    TemplateCategorySerializer, WorkflowTemplateListSerializer,
    WorkflowTemplateDetailSerializer, WorkflowTemplateCreateFromSerializer,
    ExecutionCacheSerializer, ExecutionCacheConfigSerializer, ExecutionCacheStatsSerializer,
    ExecutionLogSerializer,
)
from .services.workflow_executor import WorkflowExecutor
from .services.cache_service import ExecutionCacheService
from .tasks import execute_workflow_task


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners to edit."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if isinstance(obj, Workflow):
            return obj.owner == request.user
        elif hasattr(obj, 'workflow'):
            return obj.workflow.owner == request.user

        return False


class WorkflowViewSet(viewsets.ModelViewSet):
    """ViewSet for Workflow model."""

    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        """Filter workflows based on tenant membership and visibility."""
        queryset = _get_accessible_workflow_queryset(self.request.user)

        # Filter by owner
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(owner=self.request.user) | Q(is_public=True)
            )

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        # Filter by tags
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__contains=[tag])

        return queryset.select_related('owner').prefetch_related('nodes', 'edges')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return WorkflowListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return WorkflowCreateSerializer
        return WorkflowDetailSerializer

    def perform_create(self, serializer):
        """Set owner and tenant on create."""
        tenant_ids = _get_accessible_tenant_ids(self.request.user)
        tenant = None
        requested_tenant_id = self.request.data.get('tenant') or self.request.data.get('tenant_id')
        if requested_tenant_id:
            tenant = self.request.user.is_superuser and Workflow._meta.get_field('tenant').remote_field.model.objects.filter(id=requested_tenant_id).first() or None
            if not self.request.user.is_superuser:
                from tenants.models import Tenant
                tenant = Tenant.objects.filter(id=requested_tenant_id, id__in=tenant_ids).first()
        serializer.save(owner=self.request.user, tenant=tenant)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute the workflow."""
        workflow = self.get_object()
        serializer = WorkflowExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        input_data = serializer.validated_data.get('input_data', {})
        trigger_type = serializer.validated_data.get('trigger_type', 'manual')
        async_execute = serializer.validated_data.get('is_async', False)

        # Create execution record with version tracking
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            status='pending',
            input_data=input_data,
            triggered_by=request.user,
            trigger_type=trigger_type,
            version=workflow.version,
            trigger_source={
                'user_id': request.user.id,
                'username': request.user.username,
                'ip_address': self._get_client_ip(request)
            }
        )

        # Broadcast execution creation
        self._broadcast_execution_create(execution)

        if async_execute:
            # Execute asynchronously with Celery
            task = execute_workflow_task.delay(execution.id)
            execution.task_id = task.id
            execution.save(update_fields=['task_id'])

            return Response({
                'execution_id': execution.id,
                'task_id': task.id,
                'status': 'pending',
                'message': '工作流已加入执行队列'
            }, status=status.HTTP_202_ACCEPTED)

        # Execute synchronously
        try:
            executor = WorkflowExecutor(workflow, execution)
            result = executor.execute()

            return Response({
                'execution_id': execution.id,
                'status': execution.status,
                'output_data': execution.output_data,
                'message': '工作流执行完成'
            })
        except Exception as e:
            import traceback
            execution.mark_failed(
                error_message=str(e),
                traceback=traceback.format_exc()
            )

            return Response({
                'execution_id': execution.id,
                'status': 'failed',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @action(detail=True, methods=['get'])
    def stream_execute(self, request, pk=None):
        """Execute workflow with streaming output."""
        workflow = self.get_object()
        input_data = request.query_params.get('input_data', {})

        if isinstance(input_data, str):
            try:
                input_data = json.loads(input_data)
            except json.JSONDecodeError:
                input_data = {}

        # Create execution record
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            status='pending',
            input_data=input_data,
            triggered_by=request.user,
            trigger_type='manual'
        )

        def generate():
            """Generator for streaming execution updates."""
            try:
                executor = WorkflowExecutor(workflow, execution)

                # Send initial status
                yield f"data: {json.dumps({'type': 'execution_start', 'execution_id': execution.id})}\n\n"

                # Create a callback to send updates
                def send_update(event_type, data):
                    yield f"data: {json.dumps({'type': event_type, 'data': data})}\n\n"

                # Modify executor to yield streaming updates
                for chunk in executor.stream_execute():
                    yield f"data: {json.dumps(chunk)}\n\n"

                # Send completion
                execution.refresh_from_db()
                yield f"data: {json.dumps({'type': 'execution_complete', 'data': {'status': execution.status, 'output_data': execution.output_data}})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        response = StreamingHttpResponse(
            generate(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    def _broadcast_execution_create(self, execution):
        """Broadcast execution creation via WebSocket."""
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'workflow_{execution.workflow_id}',
                    {
                        'type': 'workflow_update',
                        'data': {
                            'event': 'execution_created',
                            'execution_id': execution.id,
                            'status': execution.status
                        }
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to broadcast execution creation: {e}")

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate the workflow."""
        original = self.get_object()

        # Create new workflow
        new_workflow = Workflow.objects.create(
            name=f"{original.name} (副本)",
            description=original.description,
            owner=request.user,
            status='draft',
            tags=(original.tags or []).copy(),
            config=original.config.copy() if original.config else {}
        )

        # Copy nodes with error handling fields
        node_id_map = {}
        for node in original.nodes.all():
            new_node = Node.objects.create(
                workflow=new_workflow,
                node_type=node.node_type,
                name=node.name,
                description=node.description,
                position_x=node.position_x,
                position_y=node.position_y,
                config=node.config.copy() if node.config else {},
                style=node.style.copy() if node.style else {},
                error_handling=node.error_handling,
                max_retries=node.max_retries,
                retry_delay_seconds=node.retry_delay_seconds,
                fallback_value=node.fallback_value.copy() if node.fallback_value else None
            )
            node_id_map[node.id] = new_node.id

        # Copy edges
        for edge in original.edges.all():
            Edge.objects.create(
                workflow=new_workflow,
                source_node_id=node_id_map.get(edge.source_node_id),
                target_node_id=node_id_map.get(edge.target_node_id),
                source_handle=edge.source_handle,
                target_handle=edge.target_handle,
                label=edge.label,
                style=edge.style.copy() if edge.style else None,
                animated=edge.animated,
                condition_expression=edge.condition_expression,
                condition_priority=edge.condition_priority,
            )

        serializer = WorkflowDetailSerializer(new_workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """Export workflow as JSON."""
        workflow = self.get_object()
        serializer = WorkflowDetailSerializer(workflow)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def import_workflow(self, request, pk=None):
        """Import workflow from JSON."""
        serializer = WorkflowCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Validate workflow structure."""
        workflow = self.get_object()

        errors = []
        warnings = []

        # Check for start nodes
        start_nodes = workflow.nodes.filter(node_type='start')
        if not start_nodes.exists():
            errors.append('缺少开始节点')

        # Check for end nodes
        end_nodes = workflow.nodes.filter(node_type='end')
        if not end_nodes.exists():
            warnings.append('缺少结束节点')

        # Check for orphan nodes (no connections)
        nodes_with_edges = set()
        for edge in workflow.edges.all():
            nodes_with_edges.add(edge.source_node_id)
            nodes_with_edges.add(edge.target_node_id)

        orphan_nodes = workflow.nodes.exclude(id__in=nodes_with_edges)
        if orphan_nodes.exists():
            warnings.append(f'存在未连接的节点: {", ".join([n.name for n in orphan_nodes])}')

        # Check for unconnected starts/ends
        for start in start_nodes:
            has_outgoing = workflow.edges.filter(source_node=start).exists()
            if not has_outgoing:
                errors.append(f'开始节点 "{start.name}" 没有连接')

        for end in end_nodes:
            has_incoming = workflow.edges.filter(target_node=end).exists()
            if not has_incoming:
                warnings.append(f'结束节点 "{end.name}" 没有输入连接')

        return Response({
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        })


class NodeViewSet(viewsets.ModelViewSet):
    """ViewSet for Node model."""

    serializer_class = NodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter nodes by accessible workflow."""
        queryset = Node.objects.filter(workflow__in=_get_accessible_workflow_queryset(self.request.user))

        workflow_id = self.request.query_params.get('workflow')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)

        return queryset.select_related('workflow')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return NodeCreateSerializer
        return NodeSerializer

    def perform_create(self, serializer):
        """Set workflow on create."""
        workflow_id = self.request.data.get('workflow')
        if workflow_id:
            workflow = _get_accessible_workflow(self.request.user, workflow_id)
            serializer.save(workflow=workflow)

    @action(detail=False, methods=['get'])
    def available_types(self, request):
        """Get available node types."""
        from config.constants import NodeType
        node_types = []
        for attr in dir(NodeType):
            if not attr.startswith('_') and attr.isupper():
                value = getattr(NodeType, attr)
                label = attr.replace('_', ' ').title()
                node_types.append({'type': value, 'label': label})
        return Response(node_types)

    @action(detail=False, methods=['post'])
    def batch_update_positions(self, request):
        """Batch update node positions."""
        positions = request.data.get('positions', [])
        accessible_node_ids = set(self.get_queryset().values_list('id', flat=True))

        for pos in positions:
            node_id = pos.get('id')
            if node_id not in accessible_node_ids:
                continue
            position = pos.get('position', {})
            Node.objects.filter(id=node_id).update(
                position_x=position.get('x', 0),
                position_y=position.get('y', 0)
            )

        return Response({'message': '位置已更新'})

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """Batch create nodes."""
        nodes_data = request.data.get('nodes', [])
        workflow_id = request.data.get('workflow_id')

        if not workflow_id:
            return Response(
                {'error': 'workflow_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        workflow = _get_accessible_workflow(request.user, workflow_id)
        created_nodes = []

        for node_data in nodes_data:
            node = Node.objects.create(
                workflow=workflow,
                node_type=node_data.get('node_type', 'llm'),
                name=node_data.get('name', 'Node'),
                position_x=node_data.get('position_x', 0),
                position_y=node_data.get('position_y', 0),
                config=node_data.get('config', {}),
                style=node_data.get('style', {})
            )
            created_nodes.append(node)

        serializer = NodeSerializer(created_nodes, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EdgeViewSet(viewsets.ModelViewSet):
    """ViewSet for Edge model."""

    serializer_class = EdgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter edges by accessible workflow."""
        queryset = Edge.objects.filter(workflow__in=_get_accessible_workflow_queryset(self.request.user))

        workflow_id = self.request.query_params.get('workflow')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)

        return queryset.select_related('workflow', 'source_node', 'target_node')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return EdgeCreateSerializer
        return EdgeSerializer

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """Batch create edges."""
        edges_data = request.data.get('edges', [])
        workflow_id = request.data.get('workflow_id')

        if not workflow_id:
            return Response(
                {'error': 'workflow_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        workflow = _get_accessible_workflow(request.user, workflow_id)
        created_edges = []

        for edge_data in edges_data:
            edge = Edge.objects.create(
                workflow=workflow,
                source_node_id=edge_data.get('source_node_id'),
                target_node_id=edge_data.get('target_node_id'),
                source_handle=edge_data.get('source_handle', 'default'),
                target_handle=edge_data.get('target_handle', 'default'),
                label=edge_data.get('label', ''),
                animated=edge_data.get('animated', False),
                condition_expression=edge_data.get('condition_expression', ''),
                condition_priority=edge_data.get('condition_priority', 0),
            )
            created_edges.append(edge)

        serializer = EdgeSerializer(created_edges, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WorkflowExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for WorkflowExecution model."""

    serializer_class = WorkflowExecutionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter executions by accessible workflow or current user."""
        queryset = WorkflowExecution.objects.filter(
            workflow__in=_get_accessible_workflow_queryset(self.request.user)
        )

        workflow_id = self.request.query_params.get('workflow')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)
        else:
            queryset = queryset.filter(
                Q(workflow__owner=self.request.user) |
                Q(triggered_by=self.request.user) |
                Q(workflow__tenant_id__in=_get_accessible_tenant_ids(self.request.user))
            ).distinct()

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related('workflow', 'triggered_by')

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel running execution."""
        execution = self.get_object()

        if execution.status not in ['pending', 'running', 'paused']:
            return Response(
                {'error': '只能取消等待中、运行中或已暂停的执行'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.cancel()

        # Cancel Celery task if exists
        if execution.task_id:
            from celery.result import AsyncResult
            AsyncResult(execution.task_id).revoke(terminate=True)

        # Broadcast cancellation
        self._broadcast_execution_event(execution, 'execution_cancelled', {
            'execution_id': execution.id,
            'status': 'cancelled'
        })

        return Response({
            'status': 'cancelled',
            'message': '执行已取消'
        })

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed or cancelled execution."""
        execution = self.get_object()

        if execution.status not in ['failed', 'cancelled', 'completed']:
            return Response(
                {'error': '只能重试失败、已取消或已完成的执行'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create a new execution based on the failed one
        new_execution = WorkflowExecution.objects.create(
            workflow=execution.workflow,
            trigger_type='manual',
            triggered_by=request.user if request.user.is_authenticated else None,
            status='pending',
            input_data=execution.input_data
        )

        # Queue the new execution
        from .tasks import execute_workflow_task
        task = execute_workflow_task.delay(new_execution.id)
        new_execution.task_id = task.id
        new_execution.save()

        return Response({
            'execution_id': new_execution.id,
            'task_id': task.id,
            'status': 'pending',
            'message': '重试已启动'
        })

    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        """Delete an execution record."""
        execution = self.get_object()

        if execution.status == 'running':
            return Response(
                {'error': '无法删除运行中的执行'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution_id = execution.id
        execution.delete()

        logger.info(f"Deleted execution {execution_id} by user {request.user}")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause running execution."""
        execution = self.get_object()

        if execution.status != 'running':
            return Response(
                {'error': '只能暂停运行中的执行'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.pause()

        # Save context snapshot for resume
        # Note: In a real implementation, you would get the current context from the executor
        execution.save_context_snapshot({})

        # Broadcast pause
        self._broadcast_execution_event(execution, 'execution_paused', {
            'execution_id': execution.id,
            'status': 'paused'
        })

        return Response({
            'status': 'paused',
            'message': '执行已暂停'
        })

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume paused execution."""
        execution = self.get_object()

        if execution.status != 'paused':
            return Response(
                {'error': '只能恢复已暂停的执行'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get context snapshot
        context_snapshot = execution.get_context_snapshot()

        execution.resume()

        # Broadcast resume
        self._broadcast_execution_event(execution, 'execution_resumed', {
            'execution_id': execution.id,
            'status': 'running',
            'context_snapshot': context_snapshot
        })

        return Response({
            'status': 'running',
            'message': '执行已恢复'
        })

    @action(detail=True, methods=['get'])
    def legacy_logs(self, request, pk=None):
        """Legacy execution log payload retained for backward compatibility."""
        execution = self.get_object()
        return Response({
            'node_status': execution.node_status,
            'execution_logs': execution.execution_logs,
            'error_message': execution.error_message,
            'traceback': execution.traceback
        })

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get current execution status."""
        execution = self.get_object()
        return Response({
            'execution_id': execution.id,
            'status': execution.status,
            'node_status': execution.node_status,
            'node_status_summary': self._get_node_status_summary(execution),
            'output_data': execution.output_data,
            'error_message': execution.error_message,
            'progress': execution.progress,
            'current_node_id': execution.current_node_id,
            'started_at': execution.started_at,
            'completed_at': execution.completed_at,
            'duration': execution.duration
        })

    @action(detail=True, methods=['get'])
    def output(self, request, pk=None):
        """Get execution output."""
        execution = self.get_object()
        return Response({
            'output_data': execution.output_data,
            'status': execution.status
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get execution statistics for the current user."""
        from django.db.models import Count

        queryset = self.get_queryset()

        total = queryset.count()
        by_status = list(queryset.values('status').annotate(count=Count('id')))

        completed_count = queryset.filter(status='completed').count()

        return Response({
            'total_executions': total,
            'by_status': by_status,
            'completed_count': completed_count
        })

    def _get_node_status_summary(self, execution):
        """Get summary of node execution status."""
        node_status = execution.node_status or {}
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

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """
        Get execution logs for a specific execution.

        Query params:
            - level: Filter by log level (DEBUG, INFO, WARNING, ERROR)
            - node_id: Filter by node execution UUID
        """
        execution = self.get_object()
        level = request.query_params.get('level')
        node_id = request.query_params.get('node_id')

        logs = ExecutionLog.objects.filter(execution=execution)

        if level:
            logs = logs.filter(level=level.upper())

        if node_id:
            try:
                import uuid as uuid_lib
                node_uuid = uuid_lib.UUID(node_id)
                logs = logs.filter(node_execution_id=node_uuid)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid node_id format'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        logs = logs.order_by('timestamp')

        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = ExecutionLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ExecutionLogSerializer(logs, many=True)
        return Response(serializer.data)

    def _broadcast_execution_event(self, execution, event_type, data):
        """Broadcast execution event via WebSocket."""
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'execution_{execution.id}',
                    {
                        'type': event_type,
                        'data': data
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to broadcast execution event: {e}")


class PublicWorkflowTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for exposing public Workflows as templates (legacy compatibility)."""

    serializer_class = WorkflowListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get public workflows as templates."""
        return Workflow.objects.filter(is_public=True).select_related('owner')

    @action(detail=True, methods=['post'])
    def create_from_template(self, request, pk=None):
        """Create a new workflow from template."""
        template = self.get_object()

        # Create new workflow
        new_workflow = Workflow.objects.create(
            name=request.data.get('name', f"{template.name} (副本)"),
            description=template.description,
            owner=request.user,
            status='draft',
            tags=template.tags.copy() if template.tags else [],
            config=template.config.copy() if template.config else {}
        )

        # Copy nodes with position offset
        node_id_map = {}
        offset_x = request.data.get('offset_x', 100)
        offset_y = request.data.get('offset_y', 100)

        for node in template.nodes.all():
            new_node = Node.objects.create(
                workflow=new_workflow,
                node_type=node.node_type,
                name=node.name,
                description=node.description,
                position_x=node.position_x + offset_x,
                position_y=node.position_y + offset_y,
                config=node.config.copy() if node.config else {},
                style=node.style.copy() if node.style else {}
            )
            node_id_map[node.id] = new_node.id

        # Copy edges
        for edge in template.edges.all():
            Edge.objects.create(
                workflow=new_workflow,
                source_node_id=node_id_map.get(edge.source_node_id),
                target_node_id=node_id_map.get(edge.target_node_id),
                source_handle=edge.source_handle,
                target_handle=edge.target_handle,
                label=edge.label,
                style=edge.style.copy() if edge.style else None,
                animated=edge.animated,
                condition_expression=edge.condition_expression,
                condition_priority=edge.condition_priority,
            )

        serializer = WorkflowDetailSerializer(new_workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WorkflowImportView(APIView):
    """API view for importing workflows from JSON."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Import workflow from JSON data.
        Accepts either JSON body or multipart/form-data with workflow_json file.
        """
        # Handle JSON body
        if request.content_type and 'application/json' in request.content_type:
            data = request.data
        else:
            # Handle file upload
            workflow_file = request.FILES.get('workflow_json') or request.FILES.get('file')
            if workflow_file:
                try:
                    import json as json_module
                    content = workflow_file.read().decode('utf-8')
                    data = json_module.loads(content)
                except Exception as e:
                    return Response(
                        {'error': f'Invalid JSON file: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {'error': 'No workflow data provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Create workflow
        serializer = WorkflowCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ==================== New ViewSets for Additional Models ====================

class NodeExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for NodeExecution model."""

    serializer_class = NodeExecutionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by execution or node."""
        queryset = NodeExecution.objects.all()

        execution_id = self.request.query_params.get('execution')
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)

        node_id = self.request.query_params.get('node')
        if node_id:
            queryset = queryset.filter(node_id=node_id)

        return queryset.select_related('execution', 'node')

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get statistics for node executions."""
        from django.db.models import Avg, Count

        queryset = self.get_queryset()
        execution_id = request.query_params.get('execution')

        if execution_id:
            stats = queryset.filter(execution_id=execution_id).aggregate(
                total=Count('id'),
                completed=Count('id', filter=models.Q(status='completed')),
                failed=Count('id', filter=models.Q(status='failed')),
                skipped=Count('id', filter=models.Q(status='skipped')),
                avg_duration=Avg('duration_ms'),
                total_tokens=Count('total_tokens')
            )
        else:
            stats = {
                'total': 0,
                'completed': 0,
                'failed': 0,
                'skipped': 0,
                'avg_duration': 0,
                'total_tokens': 0
            }

        return Response(stats)


class VariableViewSet(viewsets.ModelViewSet):
    """ViewSet for Variable model."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by workflow or list all for accessible workflows."""
        queryset = Variable.objects.all()
        accessible_workflows = _get_accessible_workflow_queryset(self.request.user)

        workflow_id = self.request.query_params.get('workflow')
        if workflow_id:
            _get_accessible_workflow(self.request.user, workflow_id)
            queryset = queryset.filter(workflow_id=workflow_id)
        else:
            queryset = queryset.filter(
                Q(workflow__in=accessible_workflows) | Q(workflow__isnull=True)
            )

        return queryset.select_related('workflow')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return VariableCreateSerializer
        return VariableSerializer


class ToolViewSet(viewsets.ModelViewSet):
    """ViewSet for Tool model."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter tools by type, category, or accessibility."""
        queryset = Tool.objects.all()

        if not self.request.user.is_superuser:
            tenant_ids = _get_accessible_tenant_ids(self.request.user)
            queryset = queryset.filter(
                Q(is_public=True, tenant__isnull=True)
                | Q(credential__owner=self.request.user)
                | Q(tenant_id__in=tenant_ids)
            ).distinct()

        tool_type = self.request.query_params.get('type')
        if tool_type:
            queryset = queryset.filter(tool_type=tool_type)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        enabled_only = self.request.query_params.get('enabled')
        if enabled_only and enabled_only.lower() == 'true':
            queryset = queryset.filter(is_enabled=True)

        return queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ToolCreateSerializer
        return ToolSerializer

    def perform_create(self, serializer):
        tenant = None
        requested_tenant_id = self.request.data.get('tenant') or self.request.data.get('tenant_id')
        if requested_tenant_id:
            if self.request.user.is_superuser:
                from tenants.models import Tenant
                tenant = Tenant.objects.filter(id=requested_tenant_id).first()
            else:
                from tenants.models import Tenant
                tenant = Tenant.objects.filter(
                    id=requested_tenant_id,
                    id__in=_get_accessible_tenant_ids(self.request.user)
                ).first()
        serializer.save(tenant=tenant)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test tool configuration."""
        tool = self.get_object()

        try:
            # Execute a simple test
            test_input = request.data.get('input', {})

            # Import tool executor
            from .services.tool_executor import ToolExecutor
            executor = ToolExecutor(tool)
            result = executor.execute(test_input)

            return Response({
                'success': True,
                'output': result,
                'message': 'Tool executed successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get all tool categories."""
        categories = Tool.objects.exclude(
            category__isnull=True
        ).exclude(
            category=''
        ).values_list('category', flat=True).distinct()

        return Response({
            'categories': list(categories)
        })


class APICredentialViewSet(viewsets.ModelViewSet):
    """ViewSet for APICredential model with encryption support."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Only show credentials the user owns or can manage within their tenants."""
        queryset = APICredential.objects.filter(owner=self.request.user)
        if self.request.user.is_superuser:
            return APICredential.objects.all()

        tenant_ids = _get_accessible_tenant_ids(self.request.user)
        return queryset.filter(Q(tenant__isnull=True) | Q(tenant_id__in=tenant_ids)).distinct()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return APICredentialCreateSerializer
        return APICredentialSerializer

    def perform_create(self, serializer):
        """Save with owner and encrypt credential data."""
        tenant = None
        requested_tenant_id = self.request.data.get('tenant') or self.request.data.get('tenant_id')
        if requested_tenant_id:
            if self.request.user.is_superuser:
                from tenants.models import Tenant
                tenant = Tenant.objects.filter(id=requested_tenant_id).first()
            else:
                from tenants.models import Tenant
                tenant = Tenant.objects.filter(
                    id=requested_tenant_id,
                    id__in=_get_accessible_tenant_ids(self.request.user)
                ).first()
        credential = serializer.save(owner=self.request.user, tenant=tenant)
        raw_data = serializer.validated_data.get('credential_data', '')
        if raw_data:
            credential.set_encrypted_data(raw_data)

    def perform_update(self, serializer):
        """Update and re-encrypt credential data if changed."""
        credential = serializer.save()
        # Re-encrypt if credential data was changed
        raw_data = serializer.validated_data.get('credential_data', '')
        if raw_data:
            credential.set_encrypted_data(raw_data)

    @action(detail=False, methods=['get'])
    def providers(self, request):
        """List available service providers for credentials."""
        providers = [
            {'id': choice[0], 'name': choice[1]}
            for choice in APICredential.SERVICE_TYPE_CHOICES
        ]
        return Response({
            'providers': providers,
            'count': len(providers)
        })

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify credential validity."""
        credential = self.get_object()

        try:
            from .services.credential_verifier import verify_credential
            is_valid, message = verify_credential(credential)

            return Response({
                'valid': is_valid,
                'message': message
            })
        except Exception as e:
            return Response({
                'valid': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def rotate(self, request, pk=None):
        """Rotate credential (update secret with encryption)."""
        credential = self.get_object()
        new_value = request.data.get('new_credential')

        if not new_value:
            return Response(
                {'error': 'new_credential is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use encryption method
        credential.set_encrypted_data(new_value)
        credential.save()

        return Response({
            'message': 'Credential rotated successfully'
        })


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for AuditLog model."""

    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter audit logs."""
        queryset = AuditLog.objects.all()

        # Regular users can only see their own logs
        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)

        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)

        # Filter by resource type
        resource_type = self.request.query_params.get('resource_type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        # Filter by resource ID
        resource_id = self.request.query_params.get('resource_id')
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        return queryset.select_related('user')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get audit log summary statistics."""
        from django.db.models import Count

        queryset = self.get_queryset()
        cutoff_date = request.query_params.get('days', 30)

        try:
            from datetime import timedelta
            from django.utils import timezone
            cutoff = timezone.now() - timedelta(days=int(cutoff_date))
            queryset = queryset.filter(timestamp__gte=cutoff)
        except (ValueError, TypeError):
            logger.debug(f"Invalid cutoff_date parameter: {cutoff_date}, ignoring filter")

        summary = queryset.values('action', 'resource_type', 'status').annotate(
            count=Count('id')
        ).order_by('-count')

        return Response({
            'total_logs': queryset.count(),
            'by_action': list(summary.filter(action__isnull=False).values('action').annotate(count=Count('id'))),
            'by_resource_type': list(summary.filter(resource_type__isnull=False).values('resource_type').annotate(count=Count('id'))),
            'by_status': list(summary.filter(status__isnull=False).values('status').annotate(count=Count('id'))),
            'recent_summary': list(summary[:20])
        })

    @action(detail=False, methods=['get'])
    def actions(self, request):
        """Get available action types."""
        return Response({
            'actions': [choice[0] for choice in AuditLog.ACTION_CHOICES]
        })

    @action(detail=False, methods=['get'])
    def resource_types(self, request):
        """Get available resource types from logs."""
        resource_types = AuditLog.objects.values_list(
            'resource_type', flat=True
        ).distinct()

        return Response({
            'resource_types': list(resource_types)
        })


# ==================== Template ViewSets ====================

class TemplateCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for TemplateCategory model."""

    queryset = TemplateCategory.objects.filter(is_active=True)
    serializer_class = TemplateCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class WorkflowTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for WorkflowTemplate model."""

    queryset = WorkflowTemplate.objects.filter(is_active=True).select_related('category', 'created_by')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowTemplateListSerializer
        return WorkflowTemplateDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        difficulty = self.request.query_params.get('difficulty')
        featured = self.request.query_params.get('featured')
        search = self.request.query_params.get('search')
        tag = self.request.query_params.get('tag')

        if category:
            queryset = queryset.filter(category__slug=category)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        if featured:
            queryset = queryset.filter(is_featured=True)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        if tag:
            queryset = queryset.filter(tags__contains=[tag])

        return queryset.order_by('-use_count', '-rating')

    @action(detail=True, methods=['post'])
    def create_from_template(self, request, pk=None):
        """Create a new workflow from this template."""
        template = self.get_object()
        serializer = WorkflowTemplateCreateFromSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        workflow_name = data.get('name') or f"{template.name} (副本)"
        variables = data.get('variables', {})

        workflow = Workflow.objects.create(
            name=workflow_name,
            description=template.description,
            owner=request.user,
            tenant=getattr(request.user, 'tenant', None),
            status='draft',
            tags=template.tags.copy() if template.tags else [],
            config=template.workflow_data.get('settings', {}).copy() if template.workflow_data.get('settings') else {},
        )

        node_id_map = {}
        for node_data in template.workflow_data.get('nodes', []):
            new_node = Node.objects.create(
                workflow=workflow,
                node_type=node_data['type'],
                name=node_data.get('data', {}).get('name', node_data.get('data', {}).get('label', 'Node')),
                description=node_data.get('data', {}).get('description', ''),
                position_x=node_data['position']['x'],
                position_y=node_data['position']['y'],
                config=node_data.get('data', {}).get('config', {}),
            )
            node_id_map[node_data['id']] = str(new_node.id)

        for edge_data in template.workflow_data.get('edges', []):
            source_node_id = node_id_map.get(edge_data['source'])
            target_node_id = node_id_map.get(edge_data['target'])
            if not source_node_id or not target_node_id:
                continue

            Edge.objects.create(
                workflow=workflow,
                source_node_id=source_node_id,
                source_handle=edge_data.get('sourceHandle', 'default'),
                target_node_id=target_node_id,
                target_handle=edge_data.get('targetHandle', 'default'),
                label=edge_data.get('label', ''),
                style=edge_data.get('style', {}),
            )

        template.use_count += 1
        template.save(update_fields=['use_count'])

        return Response(WorkflowDetailSerializer(workflow).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured templates."""
        queryset = self.get_queryset().filter(is_featured=True)[:6]
        serializer = WorkflowTemplateListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get templates grouped by category."""
        categories = TemplateCategory.objects.filter(is_active=True).prefetch_related('templates')
        result = []
        for cat in categories:
            templates = cat.templates.filter(is_active=True).order_by('-use_count')[:4]
            result.append({
                'category': TemplateCategorySerializer(cat).data,
                'templates': WorkflowTemplateListSerializer(templates, many=True).data,
            })
        return Response(result)


# ==================== Execution Cache ViewSets ====================

class ExecutionCacheViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for managing execution cache."""

    queryset = ExecutionCache.objects.all()
    serializer_class = ExecutionCacheSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'delete']

    def get_queryset(self):
        """Filter cache entries to accessible workflow scope when possible."""
        queryset = ExecutionCache.objects.all()
        
        # Filter by node type
        node_type = self.request.query_params.get('node_type')
        if node_type:
            queryset = queryset.filter(node_type=node_type)
        
        # Filter by validity
        is_valid = self.request.query_params.get('is_valid')
        if is_valid is not None:
            queryset = queryset.filter(is_valid=is_valid.lower() == 'true')
        
        # Filter by expiration
        include_expired = self.request.query_params.get('include_expired')
        if include_expired is None:
            queryset = queryset.filter(is_valid=True)
        
        return queryset.order_by('-last_accessed')

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get cache statistics."""
        service = ExecutionCacheService()
        stats = service.get_stats()
        return Response(stats)

    @action(detail=False, methods=['post'])
    def cleanup(self, request):
        """Clean up expired cache entries."""
        service = ExecutionCacheService()
        count = service.cleanup_expired()
        return Response({'cleaned': count})

    @action(detail=False, methods=['delete'])
    def invalidate_all(self, request):
        """Clear all cache entries or by node type."""
        node_type = request.query_params.get('node_type')
        service = ExecutionCacheService()
        count = service.invalidate(node_type=node_type)
        return Response({'invalidated': count})

    @action(detail=True, methods=['delete'])
    def invalidate(self, request, pk=None):
        """Invalidate a specific cache entry."""
        cache_entry = self.get_object()
        cache_entry.invalidate()
        return Response({'status': 'invalidated'})


class ExecutionCacheConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for managing cache configuration."""

    queryset = ExecutionCacheConfig.objects.all()
    serializer_class = ExecutionCacheConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']
    lookup_field = 'node_type'

    def perform_create(self, serializer):
        """Create or update cache config."""
        serializer.save()

    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """Get default cache configuration values."""
        return Response({
            'enabled': True,
            'ttl_hours': 24,
            'max_size_mb': 100,
        })

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update cache configurations."""
        configs = request.data.get('configs', [])
        updated = 0
        created = 0
        
        for config_data in configs:
            obj, was_created = ExecutionCacheConfig.objects.update_or_create(
                node_type=config_data['node_type'],
                defaults={
                    'enabled': config_data.get('enabled', True),
                    'ttl_hours': config_data.get('ttl_hours', 24),
                    'max_size_mb': config_data.get('max_size_mb', 100),
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1
        
        return Response({
            'created': created,
            'updated': updated,
        })
