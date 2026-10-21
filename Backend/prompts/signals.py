"""
Django signals for prompts app.
Handles template usage tracking and analytics updates.
"""

import logging
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

logger = logging.getLogger(__name__)

# Custom signals
template_usage = Signal()
template_rated = Signal()
template_shared = Signal()


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='prompts.PromptTemplate')
def on_template_created(sender, instance, created, **kwargs):
    """Handle template creation."""
    if created:
        logger.info(f"New template created: {instance.id} - {instance.name}")

        # Broadcast to monitoring
        broadcast_to_monitoring({
            'event': 'template_created',
            'template_id': instance.id,
            'name': instance.name,
            'created_by': instance.created_by_id
        })


@receiver(post_save, sender='prompts.PromptTemplate')
def on_template_updated(sender, instance, **kwargs):
    """Handle template updates."""
    logger.debug(f"Template updated: {instance.id}")

    broadcast_to_monitoring({
        'event': 'template_updated',
        'template_id': instance.id,
        'updated_by': getattr(instance, 'updated_by_id', None)
    })


@receiver(post_save, sender='prompts.PromptUsage')
def on_template_usage_recorded(sender, instance, **kwargs):
    """Handle template usage recording."""
    # Update usage count on template
    from .models import PromptTemplate
    PromptTemplate.objects.filter(id=instance.template_id).update(
        usage_count=instance.template.usage_count + 1,
        updated_at=timezone.now()
    )

    logger.info(f"Template usage recorded: template={instance.template_id}, "
                f"execution={instance.execution_id}")

    broadcast_to_monitoring({
        'event': 'template_used',
        'template_id': instance.template_id,
        'execution_id': instance.execution_id,
        'success': instance.success
    })


@receiver(post_save, sender='prompts.PromptRating')
def on_template_rated(sender, instance, **kwargs):
    """Handle template rating."""
    # Recalculate average rating
    from .models import PromptTemplate
    template = instance.template
    ratings = template.ratings.all()
    if ratings.exists():
        avg_rating = sum(r.value for r in ratings) / ratings.count()
        PromptTemplate.objects.filter(id=template.id).update(
            avg_rating=round(avg_rating, 2),
            rating_count=ratings.count()
        )

    logger.info(f"Template rated: template={instance.template_id}, rating={instance.value}")

    # Send signal
    template_rated.send(
        sender=sender,
        template_id=instance.template_id,
        rating=instance.value,
        user_id=instance.user_id
    )


@receiver(template_usage)
def on_template_usage(sender, template_id, execution_id, success, **kwargs):
    """Handle template usage signal."""
    broadcast_to_monitoring({
        'event': 'template_usage',
        'template_id': template_id,
        'execution_id': execution_id,
        'success': success
    })


from monitoring.broadcasts import broadcast_to_monitoring
