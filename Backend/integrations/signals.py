"""
Django signals for integrations app.
Handles webhook delivery tracking and integration status updates.
"""

import logging
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

logger = logging.getLogger(__name__)

# Custom signals
webhook_delivery_succeeded = Signal()
webhook_delivery_failed = Signal()
integration_connected = Signal()
integration_disconnected = Signal()


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='integrations.Webhook')
def on_webhook_created(sender, instance, created, **kwargs):
    """Handle webhook creation."""
    if created:
        logger.info(f"Webhook created: {instance.id} - {instance.name}")

        broadcast_to_monitoring({
            'event': 'webhook_created',
            'webhook_id': instance.id,
            'tenant_id': instance.tenant_id
        })


@receiver(post_save, sender='integrations.WebhookDelivery')
def on_webhook_delivery_completed(sender, instance, **kwargs):
    """Handle webhook delivery completion."""
    if instance.status in ('success', 'failed', 'retrying'):
        logger.info(f"Webhook delivery completed: {instance.id} - status={instance.status}")

        # Update webhook stats
        from .models import Webhook
        webhook = instance.webhook

        if instance.status == 'success':
            Webhook.objects.filter(id=webhook.id).update(
                successful_deliveries=webhook.successful_deliveries + 1,
                last_called_at=timezone.now(),
                updated_at=timezone.now()
            )

            webhook_delivery_succeeded.send(
                sender=sender,
                delivery_id=instance.id,
                webhook_id=webhook.id
            )
        else:
            Webhook.objects.filter(id=webhook.id).update(
                failed_deliveries=webhook.failed_deliveries + 1,
                last_called_at=timezone.now(),
                updated_at=timezone.now()
            )

            webhook_delivery_failed.send(
                sender=sender,
                delivery_id=instance.id,
                webhook_id=webhook.id,
                error=instance.error_message
            )

        broadcast_to_monitoring({
            'event': 'webhook_delivery',
            'delivery_id': instance.id,
            'webhook_id': webhook.id,
            'status': instance.status
        })


@receiver(post_save, sender='integrations.Integration')
def on_integration_status_changed(sender, instance, **kwargs):
    """Handle integration status changes."""
    if instance.tracker.has_changed('is_connected'):
        if instance.is_connected:
            logger.info(f"Integration connected: {instance.id} - {instance.name}")

            integration_connected.send(
                sender=sender,
                integration_id=instance.id,
                tenant_id=instance.tenant_id
            )
        else:
            logger.info(f"Integration disconnected: {instance.id} - {instance.name}")

            integration_disconnected.send(
                sender=sender,
                integration_id=instance.id,
                tenant_id=instance.tenant_id
            )


@receiver(post_save, sender='integrations.Integration')
def on_integration_updated(sender, instance, **kwargs):
    """Handle integration updates."""
    logger.debug(f"Integration updated: {instance.id}")


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
