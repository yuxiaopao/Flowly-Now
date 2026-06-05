"""
Monitoring services for execution logging, alerting, and metrics.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum, Q, F
from django.db.models.functions import TruncHour, TruncDay
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class ExecutionLoggingService:
    """Service for logging workflow execution events."""

    @staticmethod
    def log_execution(
        execution_id: int,
        node_id: str = '',
        node_name: str = '',
        level: str = 'info',
        message: str = '',
        details: Optional[Dict] = None
    ) -> 'ExecutionLog':
        """Log an execution event."""
        from monitoring.models import ExecutionLog

        return ExecutionLog.objects.create(
            workflow_execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            level=level,
            message=message,
            details=details or {}
        )

    @staticmethod
    def get_execution_logs(
        execution_id: int,
        level: Optional[str] = None,
        node_id: Optional[str] = None,
        limit: int = 100
    ) -> List['ExecutionLog']:
        """Get logs for a specific execution."""
        from monitoring.models import ExecutionLog

        queryset = ExecutionLog.objects.filter(workflow_execution_id=execution_id)

        if level:
            queryset = queryset.filter(level=level)
        if node_id:
            queryset = queryset.filter(node_id=node_id)

        return list(queryset[:limit])

    @staticmethod
    def get_execution_timeline(execution_id: int) -> List[Dict]:
        """Get a timeline of execution events."""
        from monitoring.models import ExecutionLog

        logs = ExecutionLog.objects.filter(
            workflow_execution_id=execution_id
        ).order_by('timestamp')

        timeline = []
        for log in logs:
            timeline.append({
                'timestamp': log.timestamp.isoformat(),
                'level': log.level,
                'node': log.node_name or log.node_id,
                'message': log.message,
                'details': log.details
            })

        return timeline


class AlertService:
    """Service for managing and triggering alerts."""

    def __init__(self):
        self._notification_channels = {}

    def check_execution_failure(
        self,
        workflow_id: int,
        execution_id: int,
        error_message: str
    ) -> List['Alert']:
        """Check if any alert rules are triggered by execution failure."""
        from monitoring.models import AlertRule, Alert

        triggered_alerts = []

        rules = AlertRule.objects.filter(
            condition='execution_failed',
            is_active=True
        )

        for rule in rules:
            if self._should_trigger_rule(rule, workflow_id, execution_id):
                alert = self._create_alert_from_rule(
                    rule,
                    title=f'工作流执行失败: {workflow_id}',
                    message=error_message,
                    triggered_by_type='workflow',
                    triggered_by_id=str(workflow_id)
                )
                triggered_alerts.append(alert)

        return triggered_alerts

    def check_execution_timeout(
        self,
        workflow_id: int,
        execution_id: int,
        duration_seconds: int
    ) -> List['Alert']:
        """Check if execution timeout threshold is exceeded."""
        from monitoring.models import AlertRule, Alert

        triggered_alerts = []

        rules = AlertRule.objects.filter(
            condition='execution_timeout',
            is_active=True
        )

        for rule in rules:
            if duration_seconds > rule.threshold:
                alert = self._create_alert_from_rule(
                    rule,
                    title=f'工作流执行超时: {workflow_id}',
                    message=f'执行耗时 {duration_seconds}s 超过阈值 {rule.threshold}s',
                    triggered_by_type='workflow',
                    triggered_by_id=str(workflow_id)
                )
                triggered_alerts.append(alert)

        return triggered_alerts

    def check_error_rate(
        self,
        user_id: Optional[int] = None,
        time_window_minutes: int = 5
    ) -> List['Alert']:
        """Check if error rate exceeds threshold in time window."""
        from monitoring.models import AlertRule, Alert, ExecutionLog
        from workflows.models import WorkflowExecution

        triggered_alerts = []
        cutoff_time = timezone.now() - timedelta(minutes=time_window_minutes)

        rules = AlertRule.objects.filter(
            condition='error_rate_high',
            is_active=True
        )

        for rule in rules:
            # Count executions in time window
            executions_qs = WorkflowExecution.objects.filter(
                started_at__gte=cutoff_time
            )

            if user_id:
                executions_qs = executions_qs.filter(workflow__owner_id=user_id)

            total_executions = executions_qs.count()
            if total_executions == 0:
                continue

            # Count failures
            failed_executions = executions_qs.filter(
                status='failed'
            ).count()

            error_rate = failed_executions / total_executions

            if error_rate > (rule.threshold / 100):
                alert = self._create_alert_from_rule(
                    rule,
                    title=f'错误率过高',
                    message=f'错误率 {error_rate*100:.1f}% 超过阈值 {rule.threshold}%',
                    triggered_by_type='user' if user_id else 'system',
                    triggered_by_id=str(user_id) if user_id else 'global'
                )
                triggered_alerts.append(alert)

        return triggered_alerts

    def check_duration_threshold(
        self,
        workflow_id: int,
        execution_id: int,
        duration_ms: int
    ) -> List['Alert']:
        """Check if average execution duration exceeds threshold."""
        from monitoring.models import AlertRule, Alert
        from workflows.models import WorkflowExecution

        triggered_alerts = []

        rules = AlertRule.objects.filter(
            condition='execution_duration_high',
            is_active=True
        )

        # Calculate average duration for this workflow
        avg_result = WorkflowExecution.objects.filter(
            workflow_id=workflow_id,
            status='completed',
            completed_at__isnull=False
        ).aggregate(avg_duration=Avg('completed_at') - Avg('started_at'))

        avg_duration = 0
        if avg_result['avg_duration']:
            avg_duration = avg_result['avg_duration'].total_seconds() * 1000

        for rule in rules:
            if avg_duration > rule.threshold:
                alert = self._create_alert_from_rule(
                    rule,
                    title=f'执行时间过长: {workflow_id}',
                    message=f'平均执行时间 {avg_duration:.0f}ms 超过阈值 {rule.threshold}ms',
                    triggered_by_type='workflow',
                    triggered_by_id=str(workflow_id)
                )
                triggered_alerts.append(alert)

        return triggered_alerts

    def check_api_quota(self, user_id: int) -> List['Alert']:
        """Check if API quota is exceeded."""
        from monitoring.models import AlertRule, Alert
        from tenants.models import TenantMembership

        triggered_alerts = []

        # Get user's tenant
        try:
            membership = TenantMembership.objects.select_related('tenant').get(
                user_id=user_id
            )
            tenant = membership.tenant
        except TenantMembership.DoesNotExist:
            return triggered_alerts

        rules = AlertRule.objects.filter(
            condition='api_quota_exceeded',
            is_active=True
        )

        # Get usage statistics
        usage = self.get_usage_stats(user_id)
        monthly_executions = usage.get('monthly_executions', 0)
        limit = tenant.max_executions_per_month

        for rule in rules:
            if limit > 0 and monthly_executions >= limit * (rule.threshold / 100):
                alert = self._create_alert_from_rule(
                    rule,
                    title=f'API配额即将用尽',
                    message=f'本月执行 {monthly_executions}/{limit} ({rule.threshold}%)',
                    triggered_by_type='user',
                    triggered_by_id=str(user_id)
                )
                triggered_alerts.append(alert)

        return triggered_alerts

    def _should_trigger_rule(
        self,
        rule: 'AlertRule',
        workflow_id: int,
        execution_id: int
    ) -> bool:
        """Check if rule should be triggered based on cooldown."""
        cache_key = f'alert_rule_{rule.id}_workflow_{workflow_id}'
        if cache.get(cache_key):
            return False
        return True

    def _create_alert_from_rule(
        self,
        rule: 'AlertRule',
        title: str,
        message: str,
        triggered_by_type: str,
        triggered_by_id: str
    ) -> 'Alert':
        """Create an alert instance from a rule."""
        from monitoring.models import Alert

        alert = Alert.objects.create(
            rule=rule,
            severity=rule.severity,
            title=title,
            message=message,
            triggered_by_type=triggered_by_type,
            triggered_by_id=triggered_by_id
        )

        # Send notifications
        self._send_notifications(alert, rule)

        # Set cooldown
        cache_key = f'alert_rule_{rule.id}_{triggered_by_type}_{triggered_by_id}'
        cache.set(cache_key, True, rule.cooldown_minutes * 60)

        return alert

    def _send_notifications(self, alert: 'Alert', rule: 'AlertRule'):
        """Send notifications for an alert."""
        if rule.notify_email:
            self._send_email_notification(alert)

        if rule.notify_webhook and rule.webhook_url:
            self._send_webhook_notification(alert, rule.webhook_url)

    def _send_email_notification(self, alert: 'Alert'):
        """Send email notification for alert."""
        # Implementation would integrate with email service
        logger.info(f'[Email Notification] Alert triggered: {alert.title}')

    def _send_webhook_notification(self, alert: 'Alert', webhook_url: str):
        """Send webhook notification for alert."""
        import httpx
        import asyncio

        payload = {
            'alert_id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity,
            'created_at': alert.created_at.isoformat()
        }

        try:
            asyncio.create_task(
                httpx.AsyncClient().post(webhook_url, json=payload, timeout=10)
            )
        except Exception as e:
            logger.error(f'Failed to send webhook notification: {e}')

    @staticmethod
    def get_usage_stats(user_id: int) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        from workflows.models import WorkflowExecution
        from gateway.models import APICallLog

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Execution stats
        executions = WorkflowExecution.objects.filter(
            workflow__owner_id=user_id
        )

        monthly_executions = executions.filter(
            started_at__gte=month_start
        ).count()

        total_executions = executions.count()

        failed_executions = executions.filter(status='failed').count()
        success_rate = ((total_executions - failed_executions) / total_executions * 100) if total_executions > 0 else 0

        # API call stats
        api_calls = APICallLog.objects.filter(user_id=user_id)

        monthly_tokens = api_calls.filter(
            created_at__gte=month_start
        ).aggregate(Sum('tokens_used'))['tokens_used__sum'] or 0

        monthly_cost = api_calls.filter(
            created_at__gte=month_start
        ).aggregate(Sum('cost'))['cost__sum'] or Decimal('0')

        return {
            'monthly_executions': monthly_executions,
            'total_executions': total_executions,
            'success_rate': round(success_rate, 2),
            'monthly_tokens': monthly_tokens,
            'monthly_cost': float(monthly_cost),
            'total_api_calls': api_calls.count()
        }


class MetricsService:
    """Service for collecting and aggregating metrics."""

    @staticmethod
    def record_execution(execution: 'WorkflowExecution'):
        """Record metrics for a workflow execution."""
        from monitoring.models import Metric

        duration_ms = 0
        if execution.started_at and execution.completed_at:
            duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )

        # Record execution count
        Metric.objects.create(
            metric_type='execution_count',
            value=1,
            user=execution.workflow.owner,
            workflow=execution.workflow,
            tags={'status': execution.status}
        )

        # Record execution duration if completed
        if duration_ms > 0:
            Metric.objects.create(
                metric_type='execution_duration',
                value=duration_ms,
                unit='ms',
                user=execution.workflow.owner,
                workflow=execution.workflow
            )

        # Record success/failure
        if execution.status == 'completed':
            Metric.objects.create(
                metric_type='execution_success_rate',
                value=1,
                user=execution.workflow.owner,
                workflow=execution.workflow
            )
        elif execution.status == 'failed':
            Metric.objects.create(
                metric_type='execution_success_rate',
                value=0,
                user=execution.workflow.owner,
                workflow=execution.workflow
            )

    @staticmethod
    def record_api_call(api_call_log: 'APICallLog'):
        """Record metrics for an API call."""
        from monitoring.models import Metric

        # Record token usage
        if api_call_log.tokens_used:
            Metric.objects.create(
                metric_type='token_usage',
                value=api_call_log.tokens_used,
                user=api_call_log.user,
                tags={
                    'model': api_call_log.model,
                    'provider': api_call_log.provider
                }
            )

        # Record cost
        if api_call_log.cost:
            Metric.objects.create(
                metric_type='api_call_cost',
                value=float(api_call_log.cost),
                unit='USD',
                user=api_call_log.user
            )

    @staticmethod
    def get_execution_trend(
        user_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict]:
        """Get execution trend over time."""
        from monitoring.models import Metric
        from workflows.models import WorkflowExecution
        from django.db.models.functions import TruncDate

        start_date = timezone.now() - timedelta(days=days)

        queryset = WorkflowExecution.objects.filter(
            started_at__gte=start_date
        )

        if user_id:
            queryset = queryset.filter(workflow__owner_id=user_id)

        daily_stats = queryset.annotate(
            date=TruncDate('started_at')
        ).values('date').annotate(
            total=Count('id'),
            success=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed'))
        ).order_by('date')

        return list(daily_stats)

    @staticmethod
    def get_hourly_stats(
        user_id: Optional[int] = None,
        hours: int = 24
    ) -> List[Dict]:
        """Get hourly execution statistics."""
        from workflows.models import WorkflowExecution
        from django.db.models import Count, Q

        start_time = timezone.now() - timedelta(hours=hours)

        queryset = WorkflowExecution.objects.filter(
            started_at__gte=start_time
        )

        if user_id:
            queryset = queryset.filter(workflow__owner_id=user_id)

        hourly_stats = queryset.annotate(
            hour=TruncHour('started_at')
        ).values('hour').annotate(
            total=Count('id'),
            success=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed'))
        ).order_by('hour')

        return list(hourly_stats)

    @staticmethod
    def get_model_usage_stats(user_id: Optional[int] = None) -> List[Dict]:
        """Get usage statistics grouped by model."""
        from monitoring.models import Metric

        queryset = Metric.objects.filter(metric_type='token_usage')

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        stats = queryset.values('tags__model').annotate(
            total_tokens=Sum('value'),
            call_count=Count('id')
        ).order_by('-total_tokens')

        result = []
        for stat in stats:
            result.append({
                'model': stat['tags__model'] or 'unknown',
                'total_tokens': stat['total_tokens'] or 0,
                'call_count': stat['call_count'] or 0
            })

        return result

    @staticmethod
    def get_aggregated_metrics(
        user_id: Optional[int] = None,
        metric_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregated metrics."""
        from monitoring.models import Metric

        queryset = Metric.objects.all()

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        stats = queryset.aggregate(
            total_count=Count('id'),
            total_value=Sum('value'),
            avg_value=Avg('value')
        )

        return {
            'count': stats['total_count'] or 0,
            'total': float(stats['total_value'] or 0),
            'average': float(stats['avg_value'] or 0)
        }


class PerformanceMonitoringService:
    """Service for performance monitoring and profiling."""

    @staticmethod
    def record_node_execution(
        execution_id: int,
        node_id: str,
        node_name: str,
        duration_ms: int,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Record node execution performance."""
        from monitoring.models import ExecutionLog

        ExecutionLog.objects.create(
            workflow_execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            level='info' if success else 'error',
            message=f"Node {'completed' if success else 'failed'} in {duration_ms}ms" if success else f"Node failed: {error}",
            details={
                'duration_ms': duration_ms,
                'success': success,
                'error': error
            }
        )

    @staticmethod
    def get_slowest_nodes(
        workflow_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """Get the slowest nodes for a workflow."""
        from monitoring.models import ExecutionLog

        logs = ExecutionLog.objects.filter(
            workflow_execution__workflow_id=workflow_id,
            details__has_key='duration_ms'
        ).values(
            'node_id', 'node_name'
        ).annotate(
            avg_duration=Avg('details__duration_ms'),
            total_calls=Count('id'),
            failure_count=Count('id', filter=Q(level='error'))
        ).order_by('-avg_duration')[:limit]

        return list(logs)

    @staticmethod
    def get_workflow_health_score(workflow_id: int) -> Dict[str, Any]:
        """Calculate a health score for a workflow (0-100)."""
        from workflows.models import WorkflowExecution

        recent_executions = WorkflowExecution.objects.filter(
            workflow_id=workflow_id,
            started_at__gte=timezone.now() - timedelta(days=7)
        )

        total = recent_executions.count()
        if total == 0:
            return {'score': 100, 'status': 'no_data'}

        success = recent_executions.filter(status='completed').count()
        failed = recent_executions.filter(status='failed').count()

        success_rate = success / total
        failure_rate = failed / total

        # Calculate health score
        score = (success_rate * 70) + (min(failure_rate, 0.1) / 0.1 * 30)

        if score >= 90:
            status = 'healthy'
        elif score >= 70:
            status = 'warning'
        else:
            status = 'critical'

        return {
            'score': round(score, 1),
            'status': status,
            'total_executions': total,
            'success_count': success,
            'failure_count': failed
        }


# Singleton instances
execution_logging_service = ExecutionLoggingService()
alert_service = AlertService()
metrics_service = MetricsService()
performance_monitoring_service = PerformanceMonitoringService()
