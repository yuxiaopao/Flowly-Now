"""
Django signals for billing app.
Handles subscription lifecycle and usage tracking.
"""

import logging
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from .models import SubscriptionStatus

logger = logging.getLogger(__name__)

# Custom signals
subscription_created = Signal()
subscription_cancelled = Signal()
subscription_renewed = Signal()
usage_threshold_reached = Signal()


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='billing.Subscription')
def on_subscription_created(sender, instance, created, **kwargs):
    """Handle subscription creation."""
    if not created:
        return
    try:
        logger.info(f"New subscription created: {instance.id} for user {instance.user_id}")

        tier = instance.get_price_tier()
        max_executions = None
        if tier:
            max_executions = tier.max_executions_per_month
        else:
            limits = instance.get_usage_limits() or {}
            max_executions = limits.get('max_executions_per_month')

        if instance.user and max_executions:
            from users.models import User
            User.objects.filter(id=instance.user_id).update(
                execution_limit=max_executions,
                updated_at=timezone.now()
            )

        subscription_created.send(
            sender=sender,
            subscription_id=instance.id,
            user_id=instance.user_id,
            plan=instance.plan_type,
        )
    except Exception as exc:
        logger.exception("Subscription create signal failed: %s", exc)


@receiver(post_save, sender='billing.Subscription')
def on_subscription_status_changed(sender, instance, created, **kwargs):
    """Handle subscription status changes."""
    if created:
        return

    tracker = getattr(instance, 'tracker', None)
    if tracker is None or not hasattr(tracker, 'has_changed'):
        return
    if not tracker.has_changed('status'):
        return

    try:
        old_status = tracker.previous('status')
        new_status = instance.status

        logger.info(f"Subscription status changed: {instance.id} from {old_status} to {new_status}")

        if new_status == SubscriptionStatus.CANCELED:
            subscription_cancelled.send(
                sender=sender,
                subscription_id=instance.id,
                user_id=instance.user_id
            )
        elif new_status == SubscriptionStatus.ACTIVE and old_status == SubscriptionStatus.PAST_DUE:
            subscription_renewed.send(
                sender=sender,
                subscription_id=instance.id,
                user_id=instance.user_id
            )
    except Exception as exc:
        logger.exception("Subscription status signal failed: %s", exc)


@receiver(post_save, sender='billing.UsageRecord')
def on_usage_recorded(sender, instance, created, **kwargs):
    """Handle usage record creation."""
    if created:
        logger.info(f"Usage recorded for tenant {instance.tenant_id}: "
                    f"executions={instance.execution_count}")

        # Check usage thresholds
        tier = None
        if getattr(instance, 'subscription', None):
            tier = instance.subscription.get_price_tier()
        max_executions = tier.max_executions_per_month if tier else None
        if max_executions:
            usage_percentage = (instance.execution_count / max_executions) * 100

            if usage_percentage >= 100:
                usage_threshold_reached.send(
                    sender=sender,
                    tenant_id=instance.tenant_id,
                    usage_type='executions',
                    percentage=usage_percentage,
                    threshold=100
                )
            elif usage_percentage >= 80:
                usage_threshold_reached.send(
                    sender=sender,
                    tenant_id=instance.tenant_id,
                    usage_type='executions',
                    percentage=usage_percentage,
                    threshold=80
                )


@receiver(post_save, sender='billing.Payment')
def on_payment_received(sender, instance, created, **kwargs):
    """Handle payment received."""
    if created and instance.status == 'completed':
        logger.info(f"Payment received: {instance.id} - ${instance.amount}")

        # Update subscription period
        if instance.subscription:
            from .models import Subscription
            Subscription.objects.filter(id=instance.subscription_id).update(
                current_period_start=instance.paid_at,
                current_period_end=instance.subscription.get_next_period_start(),
                status='active',
                updated_at=timezone.now()
            )

        broadcast_to_monitoring({
            'event': 'payment_received',
            'payment_id': instance.id,
            'amount': float(instance.amount),
            'currency': instance.currency
        })


@receiver(post_save, sender='billing.Invoice')
def on_invoice_created(sender, instance, created, **kwargs):
    """Handle invoice creation."""
    if created:
        logger.info(f"Invoice created: {instance.id} - ${instance.total}")

        broadcast_to_monitoring({
            'event': 'invoice_created',
            'invoice_id': instance.id,
            'amount': float(instance.total),
            'currency': instance.currency,
            'tenant_id': instance.tenant_id
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
