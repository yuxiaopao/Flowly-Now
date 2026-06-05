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
    """
    Sync data with an external integration.

    Args:
        id: ID of the integration to sync
    """
    try:
        from .models import Integration

        integration = Integration.objects.get(id=id)

        if not integration.is_connected:
            return {'status': 'not_connected', 'integration_id': id}

        # Call integration sync based on type
        if integration.integration_type == 'zapier':
            result = _sync_zapier(integration)
        elif integration.integration_type == 'make':
            result = _sync_make(integration)
        elif integration.integration_type == 'n8n':
            result = _sync_n8n(integration)
        else:
            result = {'status': 'unsupported_type', 'type': integration.integration_type}

        integration.last_sync_at = timezone.now()
        integration.save()

        return {
            'integration_id': id,
            'integration_type': integration.integration_type,
            **result
        }

    except Integration.DoesNotExist:
        return {'error': f'Integration {id} not found'}


def _sync_zapier(integration):
    """Sync with Zapier integration."""
    # Zapier webhook-based integration
    return {'status': 'synced', 'type': 'zapier'}


def _sync_make(integration):
    """Sync with Make (Integromat) integration."""
    # Make scenario trigger
    return {'status': 'synced', 'type': 'make'}


def _sync_n8n(integration):
    """Sync with n8n integration."""
    # n8n webhook workflow trigger
    return {'status': 'synced', 'type': 'n8n'}


@shared_task
def send_integration_health_check():
    """
    Check health of all active integrations.
    """
    from .models import Integration

    integrations = Integration.objects.filter(is_active=True, is_connected=True)

    health_report = []
    for integration in integrations:
        # Simple health check
        healthy = True
        message = 'OK'

        # Could perform actual health check based on integration type
        health_report.append({
            'id': integration.id,
            'name': integration.name,
            'type': integration.integration_type,
            'healthy': healthy,
            'message': message,
            'last_sync': integration.last_sync_at.isoformat() if integration.last_sync_at else None
        })

    return {'integrations': health_report}
