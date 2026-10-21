"""Status broadcasts and delivery outbox for subscribed execution transitions."""
import logging
from functools import partial

from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver, Signal

from monitoring.broadcasts import broadcast_to_monitoring
from .catalog import CONNECTORS, EXECUTION_EVENTS
from .models import Integration, IntegrationDelivery

logger = logging.getLogger(__name__)
webhook_delivery_succeeded = Signal()
webhook_delivery_failed = Signal()
integration_connected = Signal()
integration_disconnected = Signal()


@receiver(post_save, sender='integrations.Webhook')
def on_webhook_created(sender, instance, created, **kwargs):
    if created:
        broadcast_to_monitoring({'event': 'webhook_created', 'webhook_id': instance.id, 'user_id': instance.user_id})


@receiver(pre_save, sender='integrations.WebhookDelivery')
@receiver(pre_save, sender='integrations.Integration')
@receiver(pre_save, sender='workflows.WorkflowExecution')
def remember_status(sender, instance, raw=False, **kwargs):
    if raw:
        return
    field = 'is_connected' if sender is Integration else 'status'
    instance._integration_previous_status = sender.objects.filter(pk=instance.pk).values_list(field, flat=True).first() if instance.pk else None


@receiver(post_save, sender='integrations.WebhookDelivery')
def on_webhook_delivery_completed(sender, instance, raw=False, **kwargs):
    if raw or instance.status == getattr(instance, '_integration_previous_status', None):
        return
    if instance.status not in ('success', 'failed'):
        return
    # The sender owns counters, avoiding double increments on log updates.
    signal = webhook_delivery_succeeded if instance.status == 'success' else webhook_delivery_failed
    signal.send(sender=sender, delivery_id=instance.id, webhook_id=instance.webhook_id)
    broadcast_to_monitoring({'event': 'webhook_delivery', 'delivery_id': instance.id,
                             'webhook_id': instance.webhook_id, 'status': instance.status})


@receiver(post_save, sender=Integration)
def on_integration_status_changed(sender, instance, raw=False, **kwargs):
    if raw or instance.is_connected == getattr(instance, '_integration_previous_status', None):
        return
    signal = integration_connected if instance.is_connected else integration_disconnected
    signal.send(sender=sender, integration_id=instance.id, user_id=instance.user_id)


def enqueue_delivery(delivery_id):
    from .tasks import deliver_integration_event
    try:
        deliver_integration_event.delay(delivery_id)
    except Exception:
        logger.exception('Could not queue integration delivery %s', delivery_id)
        IntegrationDelivery.objects.filter(pk=delivery_id, status='pending').update(
            status='failed', message='投递任务未入队，请检查任务队列后重新测试连接。')


@receiver(post_save, sender='workflows.WorkflowExecution')
def on_execution_transition(sender, instance, raw=False, **kwargs):
    if raw or instance.status == getattr(instance, '_integration_previous_status', None):
        return
    event = EXECUTION_EVENTS.get(instance.status)
    if not event:
        return
    # Only the workflow owner can subscribe to its execution metadata.
    owner_id = instance.workflow.owner_id
    candidates = Integration.objects.filter(user_id=owner_id, is_active=True, is_connected=True)
    payload = {'event': event, 'execution_id': str(instance.pk), 'workflow_id': str(instance.workflow_id),
               'workflow_name': instance.workflow.name, 'status': instance.status}
    for integration in candidates:
        connector = CONNECTORS.get(integration.integration_type)
        if not connector or connector['mode'] == 'api' or event not in integration.config.get('events', []):
            continue
        delivery, created = IntegrationDelivery.objects.get_or_create(
            integration=integration, event_key=f'{instance.pk}:{event}',
            defaults={'event': event, 'payload': payload})
        if created:
            transaction.on_commit(partial(enqueue_delivery, delivery.pk))
