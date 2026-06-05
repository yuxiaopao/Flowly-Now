"""
Django signals for agents app.
"""

from django.dispatch import receiver
from django.db.models.signals import post_save


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='agents.AgentConversation')
def conversation_updated(sender, instance, **kwargs):
    """Handle conversation updates."""
    channel_layer = get_channel_layer_safe()
    if not channel_layer:
        return
    
    from asgiref.sync import async_to_sync
    
    # Send update to any connected clients watching this conversation
    try:
        async_to_sync(channel_layer.group_send)(
            f'conversation_{instance.id}',
            {
                'type': 'conversation_update',
                'data': {
                    'conversation_id': instance.id,
                    'message_count': len(instance.messages or [])
                }
            }
        )
    except Exception:
        pass


@receiver(post_save, sender='agents.AgentExecution')
def execution_completed(sender, instance, **kwargs):
    """Handle execution completion."""
    if instance.status in ('completed', 'failed'):
        # Update agent stats
        from .models import Agent
        Agent.objects.filter(id=instance.agent_id).update(
            updated_at=instance.started_at
        )
