"""
Celery tasks for monitoring and alerting.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_alert_rules(self):
    """Check all active alert rules and trigger alerts if needed."""
    from .models import AlertRule, Alert
    from workflows.models import WorkflowExecution

    rules = AlertRule.objects.filter(is_active=True)
    now = timezone.now()

    for rule in rules:
        try:
            triggered = False
            triggered_by_id = None
            message = ""

            time_window = timedelta(minutes=rule.time_window_minutes)
            cutoff = now - time_window

            if rule.condition == 'execution_failed':
                failed_count = WorkflowExecution.objects.filter(
                    workflow__owner=rule.owner,
                    status='failed',
                    started_at__gte=cutoff
                ).count()
                if failed_count >= rule.threshold:
                    triggered = True
                    message = f"在过去 {rule.time_window_minutes} 分钟内执行失败 {failed_count} 次"

            elif rule.condition == 'execution_timeout':
                timeout_count = WorkflowExecution.objects.filter(
                    workflow__owner=rule.owner,
                    status='timeout',
                    started_at__gte=cutoff
                ).count()
                if timeout_count >= rule.threshold:
                    triggered = True
                    message = f"在过去 {rule.time_window_minutes} 分钟内超时 {timeout_count} 次"

            elif rule.condition == 'error_rate_high':
                total = WorkflowExecution.objects.filter(
                    workflow__owner=rule.owner,
                    started_at__gte=cutoff
                ).count()
                failed = WorkflowExecution.objects.filter(
                    workflow__owner=rule.owner,
                    status='failed',
                    started_at__gte=cutoff
                ).count()
                if total > 0:
                    error_rate = (failed / total) * 100
                    if error_rate >= rule.threshold:
                        triggered = True
                        message = f"错误率 {error_rate:.1f}% 超过阈值 {rule.threshold}%"

            if triggered:
                # Check if similar alert already exists
                existing = Alert.objects.filter(
                    rule=rule,
                    status__in=['active', 'acknowledged'],
                    created_at__gte=cutoff
                ).exists()

                if not existing:
                    Alert.objects.create(
                        rule=rule,
                        severity=rule.severity,
                        title=f"{rule.name} 告警",
                        message=message,
                        triggered_by_type='workflow',
                        triggered_by_id=triggered_by_id
                    )

                    # Send notifications
                    send_alert_notifications.delay(rule.id, message)

        except Exception as e:
            logger.error(f"Error checking alert rule {rule.id}: {e}")
            self.retry(exc=e, countdown=60)


@shared_task
def send_alert_notifications(rule_id, message):
    """Send notifications for an alert rule."""
    from .models import AlertRule

    try:
        rule = AlertRule.objects.get(id=rule_id)

        if rule.notify_email and rule.owner:
            send_email_notification(rule.owner.email, rule.name, message)

        if rule.notify_webhook and rule.webhook_url:
            send_webhook_notification(rule.webhook_url, rule.name, message)

    except Exception as e:
        logger.error(f"Error sending alert notifications: {e}")


def send_email_notification(email, subject, message):
    """Send email notification."""
    from django.conf import settings
    from django.core.mail import send_mail

    if hasattr(settings, 'EMAIL_HOST'):
        try:
            send_mail(
                subject=f"[Flowly] {subject}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Error sending email to {email}: {e}")


def send_webhook_notification(webhook_url, subject, message):
    """Send webhook notification."""
    import requests
    import json

    try:
        payload = {
            "event": "alert",
            "subject": subject,
            "message": message,
            "timestamp": timezone.now().isoformat()
        }
        requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
    except Exception as e:
        logger.error(f"Error sending webhook to {webhook_url}: {e}")


@shared_task
def cleanup_old_logs(days=30):
    """Clean up execution logs older than specified days."""
    from .models import ExecutionLog

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = ExecutionLog.objects.filter(timestamp__lt=cutoff).delete()
    logger.info(f"Cleaned up {deleted} old execution logs")


@shared_task
def record_metrics():
    """Record periodic metrics."""
    from .models import Metric
    from workflows.models import Workflow, WorkflowExecution
    from django.contrib.auth import get_user_model

    User = get_user_model()
    now = timezone.now()

    # Record total users
    user_count = User.objects.count()
    Metric.objects.create(
        metric_type='user_count',
        value=user_count,
        unit='users'
    )

    # Record total workflows
    workflow_count = Workflow.objects.count()
    Metric.objects.create(
        metric_type='workflow_count',
        value=workflow_count,
        unit='workflows'
    )

    # Record executions today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    executions_today = WorkflowExecution.objects.filter(
        started_at__gte=today_start
    ).count()
    Metric.objects.create(
        metric_type='execution_count',
        value=executions_today,
        unit='executions'
    )

    # Record success rate (last 24h)
    day_ago = now - timedelta(days=1)
    total = WorkflowExecution.objects.filter(started_at__gte=day_ago).count()
    successful = WorkflowExecution.objects.filter(
        started_at__gte=day_ago,
        status='completed'
    ).count()
    success_rate = (successful / total * 100) if total > 0 else 0
    Metric.objects.create(
        metric_type='execution_success_rate',
        value=success_rate,
        unit='%'
    )


@shared_task
def aggregate_hourly_metrics():
    """Aggregate hourly metrics from finer-grained data."""
    from .models import Metric
    from django.db.models import Avg, Count
    from django.db.models.functions import TruncHour

    now = timezone.now()
    hour_ago = now - timedelta(hours=1)
    hour_start = hour_ago.replace(minute=0, second=0, microsecond=0)

    # Get all raw metrics from the last hour
    raw_metrics = Metric.objects.filter(
        timestamp__gte=hour_start,
        timestamp__lt=hour_start + timedelta(hours=1)
    )

    # Aggregate by type
    aggregated = raw_metrics.values('metric_type').annotate(
        avg_value=Avg('value'),
        count=Count('id')
    )

    # Store aggregated values
    for agg in aggregated:
        Metric.objects.create(
            metric_type=f"{agg['metric_type']}_hourly",
            value=agg['avg_value'] or 0,
            unit='aggregated',
            tags={'hour': hour_start.isoformat()}
        )
