"""
Django signals for nl_to_workflow app.
Handles NL session lifecycle and workflow generation events.
"""

import logging
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django.utils import timezone

logger = logging.getLogger(__name__)

# Custom signals
session_created = Signal()
session_completed = Signal()
workflow_generated = Signal()


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='nl_to_workflow.NLSession')
def on_session_created(sender, instance, created, **kwargs):
    """Handle NL session creation."""
    if created:
        logger.info(f"NL session created: {instance.id} - {instance.name}")

        session_created.send(
            sender=sender,
            session_id=instance.id,
            user_id=instance.user_id
        )

        broadcast_to_monitoring({
            'event': 'nl_session_created',
            'session_id': instance.id,
            'user_id': instance.user_id
        })


@receiver(post_save, sender='nl_to_workflow.NLSession')
def on_session_status_changed(sender, instance, **kwargs):
    """Handle NL session status changes."""
    # Django has no built-in tracker; use a sentinel on the instance set by the view layer.
    # If no old status is available, skip broadcasting for the initial creation.
    if not hasattr(instance, '_previous_status'):
        return

    old_status = instance._previous_status
    new_status = instance.status

    if old_status != new_status:
        logger.info(f"NL session status changed: {instance.id} from {old_status} to {new_status}")

        if new_status == 'completed':
            session_completed.send(
                sender=sender,
                session_id=instance.id,
                user_id=instance.user_id,
                workflow_id=instance.workflow_id
            )

            broadcast_to_monitoring({
                'event': 'nl_session_completed',
                'session_id': instance.id,
                'workflow_generated': instance.workflow_id is not None
            })

        elif new_status == 'failed':
            broadcast_to_monitoring({
                'event': 'nl_session_failed',
                'session_id': instance.id,
                'error': getattr(instance, 'error_message', None)
            })


@receiver(post_save, sender='nl_to_workflow.NLSession')
def on_workflow_generated(sender, instance, **kwargs):
    """Handle workflow generation."""
    workflow_changed = (
        getattr(instance, '_workflow_changed', False) or
        getattr(instance, '_previous_workflow_id', None) is not None
    )

    if instance.workflow_id and workflow_changed:
        logger.info(f"Workflow generated from NL session: {instance.id} -> {instance.workflow_id}")

        workflow_generated.send(
            sender=sender,
            session_id=instance.id,
            workflow_id=instance.workflow_id,
            user_id=instance.user_id
        )

        broadcast_to_monitoring({
            'event': 'workflow_generated_from_nl',
            'session_id': instance.id,
            'workflow_id': instance.workflow_id
        })


def send_to_user(user_id, event_type, data):
    """Send event to user's notification channel."""
    channel_layer = get_channel_layer_safe()
    if channel_layer:
        try:
            from asgiref.sync import async_to_sync
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                {
                    'type': event_type,
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"Failed to send user notification: {e}")


from monitoring.broadcasts import broadcast_to_monitoring
