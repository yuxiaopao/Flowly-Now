"""
Celery tasks for integrations app.
Handles webhook delivery retries and integration sync tasks.
"""

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone


@shared_task(bind=True, max_retries=5)
def retry_webhook_delivery(self, delivery_id: int):
    """
    Retry a failed webhook delivery.

    Args:
        delivery_id: ID of the webhook delivery to retry
    """
    try:
        from .models import WebhookDelivery, Webhook

        delivery = WebhookDelivery.objects.select_related('webhook').get(id=delivery_id)

        if delivery.status == 'success':
            return {'status': 'already_succeeded', 'delivery_id': delivery_id}

        # Reset status
        delivery.status = 'pending'
        delivery.attempts = 0
        delivery.last_attempt_at = None
        delivery.error_message = None
        delivery.save()

        # Execute delivery
        return execute_webhook_delivery_task.delay(delivery_id)

    except WebhookDelivery.DoesNotExist:
        return {'error': f'Delivery {delivery_id} not found'}
    except Exception as e:
        try:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        except MaxRetriesExceededError:
            return {'error': f'Max retries exceeded for delivery {delivery_id}'}


@shared_task(bind=True, max_retries=3)
def execute_webhook_delivery(self, delivery_id: int):
    """
    Execute webhook delivery.

    Args:
        delivery_id: ID of the webhook delivery
    """
    try:
        import httpx
        from .models import WebhookDelivery, Webhook

        delivery = WebhookDelivery.objects.select_related('webhook').get(id=delivery_id)
        webhook = delivery.webhook

        if not webhook.is_active:
            delivery.status = 'failed'
            delivery.error_message = 'Webhook is inactive'
            delivery.save()
            return {'status': 'webhook_inactive', 'delivery_id': delivery_id}

        # Prepare request
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Flowly-Webhook/1.0',
            'X-Webhook-ID': str(webhook.id),
            'X-Delivery-ID': str(delivery.id)
        }

        # Add signature if configured
        if webhook.auth_type == 'hmac' and webhook.auth_config:
            import hmac
            import hashlib
            secret = webhook.auth_config.get('secret', '')
            signature = hmac.new(
                secret.encode(),
                delivery.payload.encode(),
                hashlib.sha256
            ).hexdigest()
            headers['X-Webhook-Signature'] = f'sha256={signature}'

        # Execute request
        delivery.attempts += 1
        delivery.last_attempt_at = timezone.now()

        try:
            response = httpx.post(
                webhook.url,
                content=delivery.payload,
                headers=headers,
                timeout=webhook.timeout_seconds or 30
            )

            delivery.status_code = response.status_code
            delivery.response_body = response.text[:1000] if response.text else ''

            if 200 <= response.status_code < 300:
                delivery.status = 'success'
            else:
                delivery.status = 'failed'
                delivery.error_message = f'HTTP {response.status_code}'

        except httpx.TimeoutException:
            delivery.status = 'failed'
            delivery.error_message = 'Request timeout'

        except httpx.RequestError as e:
            delivery.status = 'failed'
            delivery.error_message = str(e)

        delivery.save()

        # Update webhook stats
        webhook = delivery.webhook
        if delivery.status == 'success':
            webhook.successful_deliveries += 1
        else:
            webhook.failed_deliveries += 1
        webhook.save()

        return {
            'delivery_id': delivery_id,
            'status': delivery.status,
            'status_code': delivery.status_code
        }

    except WebhookDelivery.DoesNotExist:
        return {'error': f'Delivery {delivery_id} not found'}
    except Exception as e:
        try:
            raise self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            return {'error': f'Max retries exceeded for delivery {delivery_id}'}


@shared_task
def cleanup_old_deliveries(days: int = 30):
    """
    Clean up old webhook delivery records.

    Args:
        days: Number of days to keep
    """
    from datetime import timedelta

    from .models import WebhookDelivery

    cutoff = timezone.now() - timedelta(days=days)

    deleted_count, _ = WebhookDelivery.objects.filter(
        created_at__lt=cutoff,
        status__in=['success', 'failed']
    ).delete()

    return {'deliveries_deleted': deleted_count}


@shared_task
def sync_integration(id: int):
    """Run the same real adapter used by the API; never report a simulated sync."""
    from .models import Integration
    from .catalog import CONNECTORS
    from .services import run_check, deliver
    integration = Integration.objects.filter(pk=id, is_active=True, is_connected=True).first()
    if not integration:
        return {'success': False, 'message': '集成不存在或尚未连接。'}
    connector = CONNECTORS.get(integration.integration_type)
    if not connector:
        return {'success': False, 'message': '不支持的集成类型。'}
    if connector['mode'] == 'api':
        return run_check(integration, read=True)
    delivery = deliver(integration)
    return {'success': delivery.status == 'success', 'message': delivery.message}


@shared_task
def deliver_integration_event(delivery_id):
    """Deliver an outbox item once, keeping the result visible to the owner."""
    from .models import IntegrationDelivery
    from .services import deliver
    delivery = IntegrationDelivery.objects.select_related('integration').filter(pk=delivery_id).first()
    if not delivery:
        return {'status': 'missing'}
    integration = delivery.integration
    if not integration.is_active or not integration.is_connected or delivery.event not in integration.config.get('events', []):
        IntegrationDelivery.objects.filter(pk=delivery_id, status='pending').update(
            status='cancelled', message='连接已断开、未验证或事件已取消订阅。', completed_at=timezone.now())
        return {'status': 'cancelled'}
    result = deliver(integration, payload=delivery.payload, event_key=delivery.event_key)
    return {'status': result.status, 'delivery_id': result.pk}


@shared_task
def send_integration_health_check():
    """Return dated evidence. Scheduled health reporting must not send test messages."""
    from .models import Integration
    return {'integrations': [{
        'id': item.pk, 'name': item.name, 'type': item.integration_type,
        'healthy': item.is_connected and item.verification_status == 'success',
        'message': item.last_error or '状态来自最近一次验证，不代表实时在线。',
        'last_checked_at': item.last_checked_at.isoformat() if item.last_checked_at else None,
    } for item in Integration.objects.filter(is_active=True)]}
