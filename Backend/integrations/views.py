"""
Integration API views.
"""

import hmac
import hashlib
import json
import time
import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Webhook, WebhookDelivery, Integration, IntegrationTemplate
from .serializers import (
    WebhookSerializer,
    WebhookDeliverySerializer,
    IntegrationSerializer,
    IntegrationTemplateSerializer,
)


class WebhookViewSet(viewsets.ModelViewSet):
    """ViewSet for webhooks."""

    serializer_class = WebhookSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Webhook.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Send a test webhook."""
        webhook = self.get_object()

        # Create test payload
        payload = {
            'event': 'test',
            'timestamp': time.time(),
            'data': {
                'message': 'This is a test webhook',
                'webhook_id': webhook.id,
                'webhook_name': webhook.name
            }
        }

        # Send webhook (in production, this would use Celery)
        delivery = self._send_webhook(webhook, 'test', payload)

        if delivery.status == 'success':
            return Response({'status': 'Test webhook sent successfully'})
        else:
            return Response(
                {'error': delivery.error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def deliveries(self, request, pk=None):
        """Get webhook delivery history."""
        webhook = self.get_object()
        limit = int(request.query_params.get('limit', 50))
        deliveries = WebhookDelivery.objects.filter(webhook=webhook)[:limit]
        return Response(WebhookDeliverySerializer(deliveries, many=True).data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get webhook statistics."""
        webhook = self.get_object()
        return Response({
            'total': webhook.total_deliveries,
            'successful': webhook.successful_deliveries,
            'failed': webhook.failed_deliveries,
            'success_rate': webhook.success_rate
        })

    def _send_webhook(self, webhook, event, payload):
        """Send webhook and create delivery record."""
        import httpx
        from django.utils import timezone

        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event=event,
            event_id=payload.get('id', str(time.time())),
            payload=payload,
            url=webhook.url,
            headers={
                'Content-Type': webhook.content_type,
                'X-Webhook-Event': event,
                'X-Webhook-ID': str(webhook.id)
            }
        )

        start_time = time.time()

        try:
            # Add signature if secret is configured
            headers = dict(delivery.headers)
            if webhook.secret:
                signature = hmac.new(
                    webhook.secret.encode(),
                    json.dumps(payload).encode(),
                    hashlib.sha256
                ).hexdigest()
                headers['X-Webhook-Signature'] = signature

            # Send request
            response = httpx.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=webhook.timeout_seconds
            )

            delivery.status_code = response.status_code
            delivery.response_body = response.text[:1000]
            delivery.status = 'success' if response.is_success else 'failed'
            delivery.sent_at = timezone.now()

        except Exception as e:
            delivery.status = 'failed'
            delivery.error_message = str(e)

        delivery.duration_ms = int((time.time() - start_time) * 1000)
        delivery.completed_at = timezone.now()
        delivery.save()

        webhook.increment_stats(delivery.status == 'success')

        return delivery


@csrf_exempt
@require_http_methods(['POST'])
@permission_classes([AllowAny])
def webhook_receiver(request):
    """Receive incoming webhooks (for integrations)."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)

    signature = request.headers.get('X-Webhook-Signature')
    if signature:
        secret = os.getenv('WEBHOOK_SECRET', '')
        if secret:
            expected = hmac.new(
                secret.encode(),
                request.body,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return HttpResponse('Invalid signature', status=401)

    event = request.headers.get('X-Webhook-Event', 'unknown')
    webhook_id = request.headers.get('X-Webhook-ID')

    if event == 'workflow.trigger':
        pass

    return HttpResponse('OK', status=200)


class IntegrationViewSet(viewsets.ModelViewSet):
    """ViewSet for integrations."""

    serializer_class = IntegrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Integration.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def connect(self, request, pk=None):
        """Connect an integration."""
        integration = self.get_object()
        # In production, this would initiate OAuth flow or API connection
        integration.is_connected = True
        integration.save()
        return Response({'status': 'Connected'})

    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """Disconnect an integration."""
        integration = self.get_object()
        integration.is_connected = False
        integration.save()
        return Response({'status': 'Disconnected'})

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Trigger sync for an integration."""
        integration = self.get_object()
        # In production, this would trigger async sync task
        return Response({'status': 'Sync started'})

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available integration templates."""
        templates = IntegrationTemplate.objects.filter(is_active=True)
        return Response(IntegrationTemplateSerializer(templates, many=True).data)


class IntegrationTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for integration templates."""

    queryset = IntegrationTemplate.objects.filter(is_active=True)
    serializer_class = IntegrationTemplateSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get templates by category."""
        templates = self.get_queryset()
        categories = {}

        for template in templates:
            cat = template.category or 'other'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(IntegrationTemplateSerializer(template).data)

        return Response(categories)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured templates."""
        templates = self.get_queryset().filter(is_featured=True)[:10]
        return Response(IntegrationTemplateSerializer(templates, many=True).data)
