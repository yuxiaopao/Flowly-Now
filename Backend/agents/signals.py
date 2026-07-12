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
                    'conversation_id': str(instance.id),
                    'message_count': instance.message_count
                }
            }
        )
    except Exception:
        pass


@receiver(post_save, sender='agents.AgentExecution')
def execution_completed(sender, instance, **kwargs):
    """Handle execution completion — update agent stats and notify subscribers."""
    if instance.status not in ('completed', 'failed'):
        return

    from django.utils import timezone

    agent = instance.agent
    settings_data = dict(agent.settings or {})
    stats = dict(settings_data.get('execution_stats') or {})
    stats['total'] = int(stats.get('total') or 0) + 1
    if instance.status == 'completed':
        stats['completed'] = int(stats.get('completed') or 0) + 1
    else:
        stats['failed'] = int(stats.get('failed') or 0) + 1
    settings_data['execution_stats'] = stats
    settings_data['last_execution'] = {
        'id': str(instance.id),
        'status': instance.status,
        'completed_at': (instance.completed_at or timezone.now()).isoformat(),
    }
    agent.settings = settings_data
    agent.save(update_fields=['settings', 'updated_at'])

    channel_layer = get_channel_layer_safe()
    if not channel_layer:
        return

    from asgiref.sync import async_to_sync

    try:
        async_to_sync(channel_layer.group_send)(
            f'agent_{agent.id}',
            {
                'type': 'agent_execution_update',
                'data': {
                    'agent_id': str(agent.id),
                    'execution_id': str(instance.id),
                    'status': instance.status,
                    'stats': stats,
                },
            },
        )
    except Exception:
        pass
