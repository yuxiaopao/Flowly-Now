"""
Django signals for billing app.
Handles subscription lifecycle and usage tracking.
"""

import logging
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

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
    if created:
        logger.info(f"New subscription created: {instance.id} for user {instance.user_id}")

        # Update user execution limits
        if instance.user:
            from users.models import User
            User.objects.filter(id=instance.user_id).update(
                execution_limit=instance.plan.max_executions_per_month,
                updated_at=timezone.now()
            )

        subscription_created.send(
            sender=sender,
            subscription_id=instance.id,
            user_id=instance.user_id,
            plan=instance.plan.plan_type if instance.plan else 'free'
        )


@receiver(post_save, sender='billing.Subscription')
def on_subscription_status_changed(sender, instance, **kwargs):
    """Handle subscription status changes."""
    if instance.tracker.has_changed('status'):
        old_status = instance.tracker.previous('status')
        new_status = instance.status

        logger.info(f"Subscription status changed: {instance.id} from {old_status} to {new_status}")

        if new_status == 'cancelled':
            subscription_cancelled.send(
                sender=sender,
                subscription_id=instance.id,
                user_id=instance.user_id
            )
        elif new_status == 'active' and old_status == 'past_due':
            subscription_renewed.send(
                sender=sender,
                subscription_id=instance.id,
                user_id=instance.user_id
            )


@receiver(post_save, sender='billing.UsageRecord')
def on_usage_recorded(sender, instance, created, **kwargs):
    """Handle usage record creation."""
    if created:
        logger.info(f"Usage recorded for tenant {instance.tenant_id}: "
                    f"executions={instance.execution_count}")

        # Check usage thresholds
        if instance.subscription and instance.subscription.plan:
            plan = instance.subscription.plan
            if plan.max_executions_per_month:
                usage_percentage = (instance.execution_count / plan.max_executions_per_month) * 100

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
