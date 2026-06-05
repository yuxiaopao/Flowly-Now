"""
Django signals for users app.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender='users.User')
def user_created(sender, instance, created, **kwargs):
    """Handle user creation."""
    if created:
        # Update last_login_at for new users
        pass


@receiver(post_save, sender='users.User')
def update_timestamps(sender, instance, **kwargs):
    """Update user timestamps."""
    if instance.last_login and not instance.last_login_at:
        User = instance.__class__
        User.objects.filter(pk=instance.pk).update(last_login_at=instance.last_login)


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


def send_to_user(user_id, event_type, data):
    """Send event to user's notification channel."""
    channel_layer = get_channel_layer_safe()
    if channel_layer:
        from asgiref.sync import async_to_sync
        try:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                {
                    'type': 'notification',
                    'data': data
                }
            )
        except Exception:
            pass
