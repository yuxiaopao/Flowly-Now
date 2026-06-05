"""
Django signals for monitoring app.
Handles alert lifecycle and metric collection.
"""

import logging
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django.utils import timezone

logger = logging.getLogger(__name__)

# Custom signals
alert_triggered = Signal()
alert_resolved = Signal()
alert_acknowledged = Signal()
metric_collected = Signal()


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='monitoring.Alert')
def on_alert_created(sender, instance, created, **kwargs):
    """Handle new alert creation."""
    if created:
        logger.info(f"Alert triggered: {instance.id} - {instance.title}")

        alert_triggered.send(
            sender=sender,
            alert_id=instance.id,
            rule_id=instance.rule_id,
            severity=instance.severity
        )

        # Notify user if notification channel is configured
        if instance.rule and instance.rule.notification_channels:
            send_alert_notification(instance)


@receiver(post_save, sender='monitoring.Alert')
def on_alert_status_changed(sender, instance, **kwargs):
    """Handle alert status changes."""
    if instance.tracker.has_changed('status'):
        old_status = instance.tracker.previous('status')
        new_status = instance.status

        logger.info(f"Alert status changed: {instance.id} from {old_status} to {new_status}")

        if new_status == 'acknowledged':
            alert_acknowledged.send(
                sender=sender,
                alert_id=instance.id,
                acknowledged_by=instance.acknowledged_by_id
            )

        elif new_status == 'resolved':
            alert_resolved.send(
                sender=sender,
                alert_id=instance.id,
                resolved_by=instance.resolved_by_id
            )


@receiver(post_save, sender='monitoring.AlertRule')
def on_alert_rule_created(sender, instance, created, **kwargs):
    """Handle alert rule creation."""
    if created:
        logger.info(f"Alert rule created: {instance.id} - {instance.name}")

        broadcast_to_monitoring({
            'event': 'alert_rule_created',
            'rule_id': instance.id,
            'name': instance.name,
            'severity': instance.severity
        })


@receiver(post_save, sender='monitoring.AlertRule')
def on_alert_rule_updated(sender, instance, **kwargs):
    """Handle alert rule updates."""
    logger.debug(f"Alert rule updated: {instance.id}")


@receiver(post_save, sender='monitoring.Metric')
def on_metric_collected(sender, instance, created, **kwargs):
    """Handle new metric collection."""
    if created:
        metric_collected.send(
            sender=sender,
            metric_type=instance.metric_type,
            value=instance.value,
            tags=instance.tags
        )


def send_alert_notification(alert):
    """Send alert notification through configured channels."""
    notification_data = {
        'alert_id': alert.id,
        'title': alert.title,
        'message': alert.message,
        'severity': alert.severity,
        'status': alert.status,
        'created_at': alert.created_at.isoformat() if alert.created_at else None
    }

    # Send through WebSocket
    channel_layer = get_channel_layer_safe()
    if channel_layer and alert.rule and alert.rule.created_by_id:
        try:
            from asgiref.sync import async_to_sync
            async_to_sync(channel_layer.group_send)(
                f'notifications_{alert.rule.created_by_id}',
                {
                    'type': 'alert_notification',
                    'data': notification_data
                }
            )
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")


def broadcast_to_monitoring(data):
    """Broadcast event to monitoring channel."""
    channel_layer = get_channel_layer_safe()
    if channel_layer:
        try:
            from asgiref.sync import async_to_sync
            async_to_sync(channel_layer.group_send)(
                'monitoring',
                {
                    'type': 'metric_update',
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"Failed to broadcast to monitoring: {e}")
