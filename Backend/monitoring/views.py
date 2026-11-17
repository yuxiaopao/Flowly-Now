"""
Views for monitoring app.
"""

import logging
from datetime import timedelta
from django.db.models import Count, Avg, Sum, F, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from tenants.access import can_view_resource, get_accessible_workflow_queryset

logger = logging.getLogger(__name__)

from .models import ExecutionLog, AlertRule, Alert, Metric, NotificationChannel, Notification
from .constants import DEFAULT_LOOKBACK_HOURS
from .serializers import (
    ExecutionLogSerializer, AlertRuleSerializer, AlertRuleCreateSerializer,
    AlertSerializer, AlertCreateSerializer,
    MetricSerializer, MetricAggregateSerializer, MetricQuerySerializer,
    NotificationChannelSerializer, NotificationChannelCreateSerializer,
    NotificationSerializer
)
from workflows.models import Workflow, WorkflowExecution
from gateway.models import APICallLog


class ExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ExecutionLog."""

    serializer_class = ExecutionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get logs for user's workflows."""
        return ExecutionLog.objects.filter(
            workflow_execution__workflow__in=get_accessible_workflow_queryset(self.request.user)
        ).select_related('workflow_execution')


class AlertRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for AlertRule."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get user's alert rules."""
        return AlertRule.objects.filter(
            Q(owner=self.request.user) | Q(owner__isnull=True)
        ).distinct()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return AlertRuleCreateSerializer
        return AlertRuleSerializer

    def perform_create(self, serializer):
        """Set owner on create."""
        serializer.save(owner=self.request.user)


class AlertViewSet(viewsets.ModelViewSet):
    """ViewSet for Alert."""

    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get alerts for user's workflows."""
        queryset = Alert.objects.filter(
            Q(rule__owner=self.request.user) |
            Q(rule__owner__isnull=True)
        ).distinct()

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by severity
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)

        return queryset.select_related('rule', 'resolved_by')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create']:
            return AlertCreateSerializer
        return AlertSerializer

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert."""
        alert = self.get_object()
        alert.status = 'acknowledged'
        alert.save()
        return Response({'status': 'acknowledged'})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert."""
        alert = self.get_object()
        note = request.data.get('note', '')

        alert.resolve(request.user, note)
        return Response({
            'status': 'resolved',
            'resolved_at': alert.resolved_at
        })

    @action(detail=True, methods=['post'])
    def mute(self, request, pk=None):
        """Mute an alert."""
        alert = self.get_object()
        alert.status = 'muted'
        alert.save()
        return Response({'status': 'muted'})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get alert summary."""
        queryset = self.get_queryset()

        summary = {
            'total': queryset.count(),
            'active': queryset.filter(status='active').count(),
            'acknowledged': queryset.filter(status='acknowledged').count(),
            'resolved': queryset.filter(status='resolved').count(),
            'muted': queryset.filter(status='muted').count(),
            'by_severity': {},
            'recent': AlertSerializer(
                queryset.order_by('-created_at')[:5],
                many=True
            ).data
        }

        # Count by severity
        for severity, _ in Alert.SEVERITY_CHOICES:
            count = queryset.filter(severity=severity, status='active').count()
            summary['by_severity'][severity] = count

        return Response(summary)


class MetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Metric."""

    serializer_class = MetricSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get metrics for user's resources."""
        queryset = Metric.objects.filter(
            Q(user=self.request.user) |
            Q(workflow__owner=self.request.user) |
            Q(user__isnull=True, workflow__isnull=True)
        ).distinct()

        # Filter by type
        metric_type = self.request.query_params.get('type')
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)

        # Filter by time range
        query = MetricQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        hours = query.validated_data.get('hours')
        if hours is not None:
            cutoff = timezone.now() - timedelta(hours=hours)
            queryset = queryset.filter(timestamp__gte=cutoff)

        return queryset.order_by('-timestamp')

    @action(detail=False, methods=['get'])
    def aggregate(self, request):
        """Get aggregated metrics."""
        metric_type = request.query_params.get('type')
        period = request.query_params.get('period', 'hour')

        queryset = self.get_queryset()
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)

        query = MetricQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        hours = query.validated_data.get('hours', DEFAULT_LOOKBACK_HOURS)
        cutoff = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(timestamp__gte=cutoff)

        # Aggregate by period
        from django.db.models.functions import TruncHour, TruncDay

        if period == 'hour':
            queryset = queryset.annotate(period=TruncHour('timestamp'))
        elif period == 'day':
            queryset = queryset.annotate(period=TruncDay('timestamp'))
        else:
            queryset = queryset.annotate(period=TruncHour('timestamp'))

        aggregated = queryset.values('metric_type', 'period').annotate(
            value=Avg('value'),
            count=Count('id')
        ).order_by('period')

        return Response(aggregated)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export metrics as CSV."""
        import csv
        from django.http import HttpResponse

        metric_type = request.query_params.get('type')
        hours = int(request.query_params.get('hours', 168))  # Default 7 days
        cutoff = timezone.now() - timedelta(hours=hours)

        queryset = self.get_queryset()
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)
        queryset = queryset.filter(timestamp__gte=cutoff).order_by('-timestamp')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="metrics_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Type', 'Value', 'Unit', 'Tags', 'Workflow', 'User'])

        for metric in queryset:
            writer.writerow([
                metric.timestamp.isoformat(),
                metric.metric_type,
                metric.value,
                metric.unit,
                ','.join(f"{k}={v}" for k, v in (metric.tags or {}).items()),
                metric.workflow_id if metric.workflow else '',
                metric.user_id if metric.user else ''
            ])

        return response

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard metrics."""
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Execution stats
        from workflows.models import WorkflowExecution

        total_executions = WorkflowExecution.objects.filter(
            workflow__owner=request.user
        ).count()

        executions_this_month = WorkflowExecution.objects.filter(
            workflow__owner=request.user,
            started_at__gte=month_ago
        ).count()

        successful_executions = WorkflowExecution.objects.filter(
            workflow__owner=request.user,
            status='completed'
        ).count()

        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0

        # Active alerts
        active_alerts = Alert.objects.filter(
            rule__owner=request.user,
            status__in=['active', 'acknowledged']
        ).count()

        # Workflow count
        from workflows.models import Workflow
        workflow_count = Workflow.objects.filter(owner=request.user).count()

        return Response({
            'total_executions': total_executions,
            'executions_this_month': executions_this_month,
            'successful_executions': successful_executions,
            'success_rate': round(success_rate, 2),
            'active_alerts': active_alerts,
            'workflow_count': workflow_count
        })


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications."""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'updated': updated})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a specific notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'success': True})

    @action(detail=False, methods=['delete'])
    def clear_read(self, request):
        """Delete all read notifications."""
        deleted, _ = self.get_queryset().filter(is_read=True).delete()
        return Response({'deleted': deleted})


class NotificationChannelViewSet(viewsets.ModelViewSet):
    """ViewSet for NotificationChannel."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get user's notification channels."""
        return NotificationChannel.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return NotificationChannelCreateSerializer
        return NotificationChannelSerializer

    def perform_create(self, serializer):
        """Set owner on create."""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test notification channel."""
        channel = self.get_object()
        test_message = request.data.get('message', '这是一条测试通知')

        try:
            if channel.channel_type == 'email':
                from django.core.mail import send_mail
                from django.conf import settings as django_settings
                recipient = channel.config.get('email')
                if not recipient:
                    return Response(
                        {'error': '未配置邮箱地址'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                send_mail(
                    subject='Flowly 通知测试',
                    message=test_message,
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )

            elif channel.channel_type == 'webhook':
                import httpx
                webhook_url = channel.config.get('url')
                if not webhook_url:
                    return Response(
                        {'error': '未配置 Webhook URL'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                payload = {
                    'type': 'test',
                    'message': test_message,
                    'channel_id': str(channel.id),
                }
                httpx.post(webhook_url, json=payload, timeout=10)

            elif channel.channel_type == 'slack':
                import httpx
                webhook_url = channel.config.get('slack_webhook_url')
                if not webhook_url:
                    return Response(
                        {'error': '未配置 Slack Webhook URL'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                payload = {'text': f"[测试] {test_message}"}
                httpx.post(webhook_url, json=payload, timeout=10)

            else:
                logger.debug(f"Test not implemented for channel type: {channel.channel_type}")

        except Exception as e:
            logger.error(f"Failed to send test notification via channel {channel.id}: {e}")
            return Response(
                {'error': f'发送测试通知失败: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({'message': '测试通知已发送'})


class AnalyticsViewSet(viewsets.ViewSet):
    """All related analytics share an owner boundary and validated time window."""
    permission_classes = [IsAuthenticated]

    def executions(self, request):
        from .analytics_queries import analytics_window
        start, end = analytics_window(request.query_params)
        return WorkflowExecution.objects.filter(workflow__owner=request.user, started_at__gte=start, started_at__lte=end), start, end

    @action(detail=False, methods=['get'])
    def overview(self, request):
        executions, start, end = self.executions(request)
        total = executions.count()
        successful = executions.filter(status='completed').count()
        logs = APICallLog.objects.filter(user=request.user, timestamp__gte=start, timestamp__lte=end)
        usage = logs.aggregate(total_tokens=Sum('total_tokens'), total_cost=Sum('cost'), avg_latency=Avg('latency_ms'))
        workflows = Workflow.objects.filter(owner=request.user, is_deleted=False, created_at__lte=end)
        previous_workflows = workflows.filter(created_at__lt=start).count()
        previous_executions = WorkflowExecution.objects.filter(workflow__owner=request.user,
            started_at__gte=start - (end - start), started_at__lt=start).count()
        return Response({
            'total_workflows': workflows.count(),
            'workflows_trend': round((workflows.count() - previous_workflows) / previous_workflows * 100, 1) if previous_workflows else None,
            'total_executions': total,
            'executions_trend': round((total - previous_executions) / previous_executions * 100, 1) if previous_executions else None,
            'total_tokens': usage['total_tokens'],
            'total_cost': float(usage['total_cost']) if usage['total_cost'] is not None else None,
            'avg_latency': usage['avg_latency'],
            'success_rate': round(successful / total * 100, 1) if total else None,
            'cost_provenance': 'gateway_log', 'cost_currency': None,
            'start_date': start, 'end_date': end,
        })

    @action(detail=False, methods=['get'])
    def top_workflows(self, request):
        from .analytics_queries import analytics_limit, analytics_window
        start, end = analytics_window(request.query_params)
        limit = analytics_limit(request.query_params, 10)
        selected = Q(executions__started_at__gte=start, executions__started_at__lte=end)
        workflows = Workflow.objects.filter(owner=request.user, is_deleted=False).annotate(
            analytics_execution_count=Count('executions', filter=selected),
            successful_count=Count('executions', filter=selected & Q(executions__status='completed')),
            mean_duration=Avg('executions__duration_ms', filter=selected & Q(executions__status='completed')),
        ).filter(analytics_execution_count__gt=0).order_by('-analytics_execution_count', 'id')[:limit]
        return Response([{'id': workflow.id, 'name': workflow.name,
            'execution_count': workflow.analytics_execution_count, 'success_rate': round(workflow.successful_count / workflow.analytics_execution_count * 100, 2),
            'avg_duration': round(workflow.mean_duration / 1000, 2) if workflow.mean_duration is not None else None,
        } for workflow in workflows])

    @action(detail=False, methods=['get'])
    def recent_executions(self, request):
        from .analytics_queries import analytics_limit
        executions, _, _ = self.executions(request)
        executions = executions.select_related('workflow').order_by('-started_at')[:analytics_limit(request.query_params, 20)]
        return Response([{'id': execution.id, 'workflow_id': execution.workflow_id, 'workflow_name': execution.workflow.name,
            'status': execution.status, 'duration': execution.duration, 'trigger_type': execution.trigger_type,
            'started_at': execution.started_at, 'completed_at': execution.completed_at,
        } for execution in executions])

    @action(detail=False, methods=['get'])
    def api_usage(self, request):
        from .analytics_queries import analytics_window
        start, end = analytics_window(request.query_params)
        usage = APICallLog.objects.filter(user=request.user, timestamp__gte=start, timestamp__lte=end).values('model', 'provider').annotate(
            call_count=Count('id'), input_tokens=Sum('input_tokens'), output_tokens=Sum('output_tokens'), total_tokens=Sum('total_tokens'), cost=Sum('cost'),
        ).order_by('-call_count', 'provider', 'model')
        return Response(list(usage))

    @action(detail=False, methods=['get'])
    def execution_trend(self, request):
        from django.db.models.functions import TruncDate
        executions, start, end = self.executions(request)
        by_date = executions.annotate(date=TruncDate('started_at')).values('date').annotate(
            executions=Count('id'), successful=Count('id', filter=Q(status='completed')),
        )
        logs = APICallLog.objects.filter(user=request.user, timestamp__gte=start, timestamp__lte=end).annotate(date=TruncDate('timestamp')).values('date').annotate(cost=Sum('cost'))
        counts = {row['date']: row for row in by_date}
        costs = {row['date']: row['cost'] for row in logs}
        return Response([{'date': date.isoformat(), 'executions': counts.get(date, {}).get('executions', 0),
            'success_rate': counts[date]['successful'] / counts[date]['executions'] * 100 if date in counts else None,
            'cost': float(costs[date]) if date in costs and costs[date] is not None else None,
        } for date in sorted(set(counts) | set(costs)) if date is not None])


class ExecutionStatsViewSet(viewsets.ViewSet):
    """ViewSet for execution statistics."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get execution statistics summary."""
        now = timezone.now()
        days = int(request.query_params.get('days', 7))
        start_date = now - timedelta(days=days)

        from workflows.models import WorkflowExecution

        queryset = WorkflowExecution.objects.filter(
            workflow__owner=request.user
        )

        total = queryset.count()
        period_total = queryset.filter(started_at__gte=start_date).count()
        completed = queryset.filter(status='completed').count()
        failed = queryset.filter(status='failed').count()
        running = queryset.filter(status='running').count()

        period_completed = queryset.filter(
            status='completed', started_at__gte=start_date
        ).count()
        period_failed = queryset.filter(
            status='failed', started_at__gte=start_date
        ).count()

        success_rate = (completed / total * 100) if total > 0 else 0
        period_success_rate = (period_completed / period_total * 100) if period_total > 0 else 0

        avg_duration_qs = queryset.filter(
            status='completed', duration_ms__isnull=False
        )
        avg_duration_seconds = avg_duration_qs.aggregate(
            avg=Avg(F('duration_ms') / 1000.0)
        )['avg'] or 0

        # Calculate success trend (compare with previous period)
        prev_start = start_date - timedelta(days=days)
        prev_completed = queryset.filter(
            status='completed', started_at__gte=prev_start, started_at__lt=start_date
        ).count()
        prev_total = queryset.filter(started_at__gte=prev_start, started_at__lt=start_date).count()
        prev_success_rate = (prev_completed / prev_total * 100) if prev_total > 0 else 0
        success_trend = round(period_success_rate - prev_success_rate, 2)

        return Response({
            'totalExecutions': total,
            'executionsInPeriod': period_total,
            'completed': completed,
            'failed': failed,
            'running': running,
            'successRate': round(success_rate, 2),
            'periodSuccessRate': round(period_success_rate, 2),
            'successTrend': success_trend,
            'avgDuration': round(float(avg_duration_seconds or 0) * 1000, 2),
            'avgDurationMs': round(float(avg_duration_seconds or 0) * 1000, 2),
            'avgDurationSeconds': round(float(avg_duration_seconds or 0), 2),
            'period': days,
            'periodCompleted': period_completed,
            'periodFailed': period_failed,
            'activeWorkflows': running,
        })

    @action(detail=False, methods=['get'])
    def trend(self, request):
        """Get execution trend data."""
        period = request.query_params.get('period', '7d')
        days = int(period.rstrip('d')) if period.endswith('d') else 7
        start_date = timezone.now() - timedelta(days=days)

        from django.db.models.functions import TruncDate
        from workflows.models import WorkflowExecution

        executions_by_date = WorkflowExecution.objects.filter(
            workflow__owner=request.user,
            started_at__gte=start_date
        ).annotate(
            date=TruncDate('started_at')
        ).values('date').annotate(
            executions=Count('id'),
            successful=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed')),
            avg_duration=Avg(F('duration_ms') / 1000.0)
        ).order_by('date')

        trend_data = []
        for item in executions_by_date:
            executions = item['executions']
            successful = item['successful']
            trend_data.append({
                'date': item['date'].isoformat() if item['date'] else None,
                'executions': executions,
                'success': successful,
                'failed': item['failed'],
                'success_rate': round((successful / executions * 100) if executions > 0 else 0, 2),
                'avg_duration': round(float(item['avg_duration'] or 0), 2),
            })

        return Response(trend_data)


class ActiveExecutionsViewSet(viewsets.ViewSet):
    """ViewSet for active/running executions."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get active (running) executions."""
        from workflows.models import WorkflowExecution

        executions = WorkflowExecution.objects.filter(
            workflow__owner=request.user,
            status__in=['running', 'pending', 'queued']
        ).select_related('workflow').order_by('-started_at')

        data = []
        for e in executions:
            # Calculate progress from executed_nodes / total_nodes
            progress = 0
            if e.total_nodes and e.total_nodes > 0:
                progress = min(100, round((e.executed_nodes or 0) / e.total_nodes * 100))

            # Get current node from node_status (last running node)
            current_node = ''
            node_status = e.node_status or {}
            for node_id, status in node_status.items():
                if status == 'running':
                    current_node = node_id
                    break

            data.append({
                'id': e.id,
                'workflowId': e.workflow_id,
                'workflow_name': e.workflow.name if e.workflow else None,
                'workflowName': e.workflow.name if e.workflow else None,
                'status': e.status,
                'triggerType': e.trigger_type,
                'startedAt': e.started_at,
                'duration': (timezone.now() - e.started_at).total_seconds() if e.started_at else 0,
                'durationSeconds': (timezone.now() - e.started_at).total_seconds() if e.started_at else 0,
                'progress': progress,
                'currentNode': current_node,
                'currentNodeId': current_node,
            })

        return Response(data)


class HealthCheckViewSet(viewsets.ViewSet):
    """ViewSet for system health checks."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get overall system health."""
        workflow_id = request.query_params.get('workflow_id')

        from workflows.models import WorkflowExecution

        base_qs = WorkflowExecution.objects.filter(
            workflow__owner=request.user
        ).order_by('-started_at')

        recent_executions = base_qs[:10]
        total_recent = recent_executions.count()
        recent_failed = sum(1 for execution in recent_executions if execution.status == 'failed')
        recent_completed = sum(1 for execution in recent_executions if execution.status == 'completed')

        overall_status = 'healthy'
        if total_recent > 0:
            failure_rate = recent_failed / total_recent
            if failure_rate > 0.5:
                overall_status = 'critical'
            elif failure_rate > 0.2:
                overall_status = 'degraded'

        return Response({
            'status': overall_status,
            'recent_total': total_recent,
            'recent_completed': recent_completed,
            'recent_failed': recent_failed,
            'recent_success_rate': round((recent_completed / total_recent * 100) if total_recent > 0 else 100, 2),
        })

    @action(detail=True, methods=['get'])
    def execution(self, request, pk=None):
        """Get health status for a specific execution."""
        from workflows.models import WorkflowExecution

        try:
            execution = WorkflowExecution.objects.select_related('workflow').get(
                id=pk, workflow__owner=request.user
            )
        except WorkflowExecution.DoesNotExist:
            return Response(
                {'error': 'Execution not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'id': execution.id,
            'workflow_id': execution.workflow_id,
            'workflow_name': execution.workflow.name if execution.workflow else None,
            'status': execution.status,
            'started_at': execution.started_at,
            'completed_at': execution.completed_at,
            'duration': execution.duration,
            'error': execution.error_message if execution.status == 'failed' else None,
            'retry_count': execution.config.get('retry_count', 0) if execution.config else 0,
        })


class ResourceUsageViewSet(viewsets.ViewSet):
    """ViewSet for system resource usage."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get current resource usage and workflow health."""
        now = timezone.now()
        hour_ago = now - timedelta(hours=1)

        from workflows.models import Workflow, WorkflowExecution
        from monitoring.models import Metric

        cpu_metric = Metric.objects.filter(
            metric_type='cpu_usage',
            timestamp__gte=hour_ago
        ).order_by('-timestamp').first()

        memory_metric = Metric.objects.filter(
            metric_type='memory_usage',
            timestamp__gte=hour_ago
        ).order_by('-timestamp').first()

        # Get workflow health data (for loadWorkflowHealth which calls this endpoint)
        workflows = []
        for workflow in Workflow.objects.filter(owner=request.user)[:20]:
            # Get recent executions WITHOUT slicing, use Python for limit
            all_recent = list(WorkflowExecution.objects.filter(
                workflow=workflow
            ).order_by('-started_at')[:5])

            total = len(all_recent)
            successful = sum(1 for e in all_recent if e.status == 'completed')

            # Use duration_ms field (milliseconds), convert to seconds
            completed_durations = [e.duration_ms for e in all_recent if e.status == 'completed' and e.duration_ms is not None]
            avg_duration_seconds = sum(completed_durations) / len(completed_durations) / 1000.0 if completed_durations else 0.0

            if total > 0:
                success_rate = (successful / total) * 100
                health_score = min(100, round(success_rate * 1.0))
                workflows.append({
                    'id': workflow.id,
                    'name': workflow.name,
                    'healthScore': health_score,
                    'successRate': round(success_rate, 1),
                    'avgDuration': round(avg_duration_seconds * 1000, 0) if completed_durations else 0,
                    'avgDurationMs': round(avg_duration_seconds * 1000, 0) if completed_durations else 0,
                })

        workflows.sort(key=lambda x: x['healthScore'])

        return Response({
            'cpu': {
                'value': float(cpu_metric.value) if cpu_metric else 0,
                'unit': '%',
                'timestamp': cpu_metric.timestamp.isoformat() if cpu_metric else None,
            },
            'memory': {
                'value': float(memory_metric.value) if memory_metric else 0,
                'unit': '%',
                'timestamp': memory_metric.timestamp.isoformat() if memory_metric else None,
            },
            'disk': {
                'value': 0,
                'unit': '%',
                'timestamp': None,
            },
            'activeConnections': 0,
            'workflows': workflows,
        })

    @action(detail=False, methods=['get'])
    def timeseries(self, request):
        """Get resource usage timeseries."""
        hours = int(request.query_params.get('hours', 24))
        start_date = timezone.now() - timedelta(hours=hours)

        from workflows.models import Metric

        metrics = Metric.objects.filter(
            metric_type__in=['cpu_usage', 'memory_usage'],
            timestamp__gte=start_date
        ).order_by('timestamp')

        cpu_data = []
        memory_data = []

        for m in metrics:
            entry = {
                'timestamp': m.timestamp.isoformat(),
                'value': m.value,
            }
            if m.metric_type == 'cpu_usage':
                cpu_data.append(entry)
            elif m.metric_type == 'memory_usage':
                memory_data.append(entry)

        return Response({
            'cpu': cpu_data,
            'memory': memory_data,
        })


class ExecutionTrendViewSet(viewsets.ViewSet):
    """ViewSet for execution trend data (standalone endpoint)."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get execution trend data."""
        period = request.query_params.get('period', '7d')
        days = int(period.rstrip('d')) if period.endswith('d') else 7
        start_date = timezone.now() - timedelta(days=days)

        from django.db.models.functions import TruncDate
        from workflows.models import WorkflowExecution

        executions_by_date = WorkflowExecution.objects.filter(
            workflow__owner=request.user,
            started_at__gte=start_date
        ).annotate(
            date=TruncDate('started_at')
        ).values('date').annotate(
            executions=Count('id'),
            successful=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed')),
            avg_duration=Avg(F('duration_ms') / 1000.0)
        ).order_by('date')

        trend_data = []
        for item in executions_by_date:
            executions = item['executions']
            successful = item['successful']
            trend_data.append({
                'date': item['date'].isoformat() if item['date'] else None,
                'executions': executions,
                'success': successful,
                'failed': item['failed'],
                'successRate': round((successful / executions * 100) if executions > 0 else 0, 2),
                'avgDuration': round(float(item['avg_duration'] or 0), 2),
            })

        # Return as dict with separate arrays (matching frontend expectations)
        dates = [item['date'] for item in trend_data]
        counts = [item['executions'] for item in trend_data]
        success_rates = [item['successRate'] for item in trend_data]
        durations = [item['avgDuration'] for item in trend_data]

        return Response({
            'dates': dates,
            'counts': counts,
            'successRates': success_rates,
            'durations': durations,
            'data': trend_data  # Also include raw data for flexibility
        })

