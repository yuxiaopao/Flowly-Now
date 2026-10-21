"""
Django signals for marketplace app.
Handles template install tracking and marketplace analytics.
"""

import logging
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from .models import WorkflowTemplate

logger = logging.getLogger(__name__)

template_installed = Signal()
template_rated = Signal()
template_published = Signal()


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='marketplace.WorkflowTemplate')
def on_template_created(sender, instance, created, **kwargs):
    """Handle template creation."""
    if created:
        logger.info(f"Template created in marketplace: {instance.id} - {instance.name}")

        broadcast_to_monitoring({
            'event': 'marketplace_template_created',
            'template_id': instance.id,
            'creator_id': instance.created_by_id
        })


@receiver(post_save, sender='marketplace.TemplateInstall')
def on_template_installed(sender, instance, created, **kwargs):
    """Handle template installation."""
    if not created:
        return

    logger.info(f"Template installed: template={instance.template_id}, user={instance.user_id}")

    WorkflowTemplate.objects.filter(id=instance.template_id).update(
        install_count=instance.template.installs.count(),
        updated_at=timezone.now(),
    )

    template_installed.send(
        sender=sender,
        template_id=instance.template_id,
        install_id=instance.id,
        user_id=instance.user_id
    )

    broadcast_to_monitoring({
        'event': 'template_installed',
        'template_id': instance.template_id,
        'install_id': instance.id,
        'installed_by': instance.user_id
    })


@receiver(post_save, sender='marketplace.TemplateRating')
def on_template_rated(sender, instance, created, **kwargs):
    """Handle template rating."""
    logger.info(f"Template rated: {instance.template_id} - {instance.rating} stars")

    template = instance.template
    ratings = template.ratings.all()
    if ratings.exists():
        average_rating = sum(r.rating for r in ratings) / ratings.count()
        WorkflowTemplate.objects.filter(id=template.id).update(
            avg_rating=round(average_rating, 2)
        )

    template_rated.send(
        sender=sender,
        template_id=instance.template_id,
        rating=instance.rating,
        user_id=instance.user_id
    )


@receiver(post_delete, sender='marketplace.TemplateInstall')
def on_template_uninstalled(sender, instance, **kwargs):
    """Handle template uninstallation."""
    logger.info(f"Template uninstalled: template={instance.template_id}")

    WorkflowTemplate.objects.filter(id=instance.template_id).update(
        install_count=max(0, instance.template.installs.count() - 1),
        updated_at=timezone.now(),
    )


from monitoring.broadcasts import broadcast_to_monitoring
