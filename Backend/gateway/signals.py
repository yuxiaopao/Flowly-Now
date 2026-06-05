"""
Django signals for gateway app.
Handles API call logging and model usage tracking.
"""

import logging
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save


logger = logging.getLogger(__name__)

# Custom signals
api_call_completed = Signal()
model_called = Signal()
api_key_used = Signal()


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='gateway.APICallLog')
def on_api_call_logged(sender, instance, created, **kwargs):
    """Handle API call log creation."""
    if created:
        logger.debug(f"API call logged: {instance.id} - {instance.endpoint}")

        api_key_used.send(
            sender=sender,
            user_id=instance.user_id,
            provider=instance.provider,
            model=instance.model,
            total_tokens=instance.total_tokens,
        )

        model_called.send(
            sender=sender,
            model=instance.model,
            provider=instance.provider,
            total_tokens=instance.total_tokens,
            cost=instance.cost,
        )

        api_call_completed.send(
            sender=sender,
            log_id=instance.id,
            endpoint=instance.endpoint,
            status_code=instance.status_code,
            latency_ms=instance.latency_ms
        )


@receiver(post_save, sender='gateway.AIModel')
def on_model_status_changed(sender, instance, **kwargs):
    """Handle AI model status changes."""
    tracker = getattr(instance, 'tracker', None)
    if tracker is None or tracker.has_changed('is_active'):
        if instance.is_active:
            logger.info(f"Model activated: {instance.id} - {instance.name}")
        else:
            logger.info(f"Model deactivated: {instance.id} - {instance.name}")

        broadcast_to_monitoring({
            'event': 'model_status_changed',
            'model_id': instance.id,
            'model_name': instance.name,
            'is_active': instance.is_active
        })




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
