"""API views for workflow triggers."""

import logging
import uuid
from datetime import timedelta

from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from tenants.access import get_accessible_workflow_queryset

from .models import WorkflowExecution

from .scheduling import WorkflowTrigger, TriggerExecution, TriggerType
from .trigger_serializers import (
    WorkflowTriggerSerializer,
    WorkflowTriggerWriteSerializer,
    TriggerExecutionSerializer,
    CronPreviewSerializer,
)
from .services.workflow_executor import WorkflowExecutor

logger = logging.getLogger(__name__)


def _get_workflow(user, workflow_id):
    return get_accessible_workflow_queryset(user).get(id=workflow_id)


def _cron_preview(expression: str, count: int = 5):
    try:
        from croniter import croniter
        base = timezone.now()
        itr = croniter(expression, base)
        return [itr.get_next(type(base)).isoformat() for _ in range(count)]
    except Exception:
        base = timezone.now()
        return [(base + timedelta(hours=i + 1)).isoformat() for i in range(count)]


class WorkflowTriggerViewSet(viewsets.ModelViewSet):
    """CRUD for workflow triggers."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_value_regex = r'\d+'

    def get_queryset(self):
        accessible = get_accessible_workflow_queryset(self.request.user)
        qs = WorkflowTrigger.objects.filter(workflow__in=accessible)
        workflow_id = self.request.query_params.get('workflow_id') or self.request.query_params.get('workflow')
        if workflow_id:
            _get_workflow(self.request.user, workflow_id)
            qs = qs.filter(workflow_id=workflow_id)
        return qs.select_related('workflow', 'created_by').order_by('-created_at')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return WorkflowTriggerWriteSerializer
        return WorkflowTriggerSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.kwargs.get('workflow_pk'):
            ctx['workflow'] = _get_workflow(self.request.user, self.kwargs['workflow_pk'])
        return ctx

    def perform_create(self, serializer):
        workflow = self.get_serializer_context().get('workflow')
        if not workflow:
            workflow_id = self.request.data.get('workflow_id') or self.request.data.get('workflow')
            workflow = _get_workflow(self.request.user, workflow_id)
        serializer.save(workflow=workflow)

    @action(detail=True, methods=['get'], url_path='executions')
    def executions(self, request, pk=None):
        trigger = self.get_object()
        qs = TriggerExecution.objects.filter(trigger=trigger).order_by('-queued_at')[:50]
        page_size = int(request.query_params.get('page_size') or 50)
        serializer = TriggerExecutionSerializer(qs[:page_size], many=True)
        return Response({'count': qs.count(), 'results': serializer.data})

    @action(detail=True, methods=['post'], url_path='test')
    def test_trigger(self, request, pk=None):
        trigger = self.get_object()
        if not trigger.can_execute:
            return Response({'success': False, 'message': '触发器当前不可执行'}, status=status.HTTP_400_BAD_REQUEST)
        return _fire_trigger(trigger, request.user, request.data or {}, source='test')

    @action(detail=True, methods=['post'], url_path='webhook')
    def webhook(self, request, pk=None):
        trigger = self.get_object()
        if trigger.trigger_type != TriggerType.WEBHOOK:
            return Response({'error': 'Not a webhook trigger'}, status=status.HTTP_400_BAD_REQUEST)
        secret = trigger.webhook_secret
        if secret:
            provided = request.headers.get('X-Webhook-Secret') or request.data.get('secret')
            if provided != secret:
                return Response({'error': 'Invalid webhook secret'}, status=status.HTTP_403_FORBIDDEN)
        if not trigger.can_execute:
            return Response({'success': False, 'message': '触发器当前不可执行'}, status=status.HTTP_400_BAD_REQUEST)
        payload = request.data if isinstance(request.data, dict) else {}
        return _fire_trigger(trigger, request.user, payload, source='webhook')


class WorkflowTriggerCreateView(APIView):
    """POST /workflows/<workflow_id>/triggers/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, workflow_pk):
        workflow = _get_workflow(request.user, workflow_pk)
        serializer = WorkflowTriggerWriteSerializer(
            data=request.data,
            context={'request': request, 'workflow': workflow},
        )
        serializer.is_valid(raise_exception=True)
        trigger = serializer.save(workflow=workflow)
        return Response(
            WorkflowTriggerSerializer(trigger, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class CronPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = CronPreviewSerializer(data={
            'expression': request.query_params.get('expression', ''),
            'count': request.query_params.get('count', 5),
        })
        serializer.is_valid(raise_exception=True)
        expression = serializer.validated_data['expression']
        count = serializer.validated_data['count']
        if not expression:
            return Response([])
        return Response(_cron_preview(expression, count))


def _fire_trigger(trigger, user, payload, source='manual'):
    execution_id = str(uuid.uuid4())
    input_data = dict(payload)
    mappings = []
    if isinstance(trigger.input_mapping, dict):
        mappings = trigger.input_mapping.get('mappings') or []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        external = mapping.get('external')
        internal = mapping.get('internal')
        if external and internal and external in input_data:
            input_data[internal] = input_data.pop(external)

    exec_log = TriggerExecution.objects.create(
        trigger=trigger,
        execution_id=execution_id,
        trigger_source=source,
        event_data=payload,
        status='running',
        started_at=timezone.now(),
    )

    try:
        execution = WorkflowExecution.objects.create(
            workflow=trigger.workflow,
            status='pending',
            input_data=input_data,
            triggered_by=user if user and user.is_authenticated else None,
            trigger_type=source,
            version=trigger.workflow.version,
            trigger_source={'trigger_id': trigger.id, 'source': source},
        )
        executor = WorkflowExecutor(trigger.workflow, execution)
        executor.execute()
        execution.refresh_from_db()
        wf_exec_id = str(execution.id)
        exec_log.workflow_execution_id = wf_exec_id
        exec_log.status = 'success' if execution.status == 'completed' else 'failed'
        if execution.status != 'completed':
            exec_log.error_message = execution.error_message or 'Execution failed'
        exec_log.completed_at = timezone.now()
        exec_log.save()
        trigger.increment_execution_count()
        return Response({
            'success': execution.status == 'completed',
            'message': '触发器已执行' if execution.status == 'completed' else (execution.error_message or '执行失败'),
            'execution_id': execution_id,
            'workflow_execution_id': wf_exec_id,
        }, status=status.HTTP_200_OK if execution.status == 'completed' else status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        logger.exception('Trigger execution failed: %s', trigger.id)
        exec_log.status = 'failed'
        exec_log.error_message = str(exc)
        exec_log.completed_at = timezone.now()
        exec_log.save()
        return Response({
            'success': False,
            'message': str(exc),
            'execution_id': execution_id,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
