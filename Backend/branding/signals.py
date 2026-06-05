"""
Django signals for branding app.
Handles branding config changes and domain verification events.
"""

import logging
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

logger = logging.getLogger(__name__)

# Custom signals
branding_updated = Signal()
domain_verified = Signal()
domain_failed = Signal()
email_template_updated = Signal()


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='branding.BrandingConfig')
def on_branding_updated(sender, instance, **kwargs):
    """Handle branding config updates."""
    logger.info(f"Branding config updated for tenant: {instance.tenant_id}")

    branding_updated.send(
        sender=sender,
        tenant_id=instance.tenant_id,
        config_keys=list(instance.config.keys()) if instance.config else []
    )

    # Invalidate CDN cache
    invalidate_branding_cache(instance.tenant_id)


@receiver(post_save, sender='branding.CustomDomain')
def on_domain_status_changed(sender, instance, **kwargs):
    """Handle custom domain status changes."""
    if instance.tracker.has_changed('is_verified'):
        if instance.is_verified:
            logger.info(f"Custom domain verified: {instance.id} - {instance.domain}")

            domain_verified.send(
                sender=sender,
                domain_id=instance.id,
                tenant_id=instance.tenant_id,
                domain=instance.domain
            )
        else:
            logger.warning(f"Custom domain verification failed: {instance.id}")

            domain_failed.send(
                sender=sender,
                domain_id=instance.id,
                tenant_id=instance.tenant_id,
                domain=instance.domain
            )


@receiver(post_save, sender='branding.EmailTemplate')
def on_email_template_updated(sender, instance, **kwargs):
    """Handle email template updates."""
    logger.info(f"Email template updated: {instance.id}")

    email_template_updated.send(
        sender=sender,
        template_id=instance.id,
        tenant_id=instance.tenant_id,
        template_type=instance.template_type
    )


@receiver(post_delete, sender='branding.CustomDomain')
def on_domain_deleted(sender, instance, **kwargs):
    """Handle custom domain deletion."""
    logger.info(f"Custom domain deleted: {instance.domain}")


def invalidate_branding_cache(tenant_id):
    """Invalidate CDN cache for branding assets."""
    logger.info(f"Invalidating branding cache for tenant: {tenant_id}")

    # Could integrate with CDN provider API here
    # For now, just log the event
    broadcast_to_monitoring({
        'event': 'branding_cache_invalidated',
        'tenant_id': str(tenant_id) if tenant_id else None
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
