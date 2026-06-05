"""
Webhook delivery service for workflows.
Handles sending webhooks and tracking delivery status.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

import httpx
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class DeliveryStatus(Enum):
    """Webhook delivery status."""
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRYING = 'retrying'


@dataclass
class WebhookDelivery:
    """Result of a webhook delivery attempt."""
    success: bool
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: int = 0


class WebhookDeliveryService:
    """Service for delivering webhooks with retry logic."""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    def generate_signature(
        self,
        payload: str,
        secret: str,
        timestamp: int = None
    ) -> str:
        """Generate HMAC-SHA256 signature for webhook payload."""
        if timestamp is None:
            timestamp = int(time.time())
        
        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"t={timestamp},v1={signature}"

    def verify_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook signature."""
        try:
            parts = dict(p.split('=', 1) for p in signature.split(','))
            timestamp = parts.get('t')
            received_sig = parts.get('v1')
            
            if not timestamp or not received_sig:
                return False
            
            expected_sig = self.generate_signature(payload, secret, int(timestamp))
            return hmac.compare_digest(received_sig, expected_sig.split('=')[1])
        except Exception:
            return False

    async def deliver(
        self,
        url: str,
        payload: Dict[str, Any],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = 'POST'
    ) -> WebhookDelivery:
        """Deliver webhook with automatic retries."""
        start_time = time.time()
        
        # Prepare headers
        request_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Flowly-Webhook/1.0',
            'X-Webhook-Event': 'workflow.execution',
            'X-Webhook-Timestamp': str(int(time.time())),
        }
        
        if headers:
            request_headers.update(headers)
        
        # Add signature if secret provided
        if secret:
            payload_str = json.dumps(payload, sort_keys=True)
            request_headers['X-Webhook-Signature'] = self.generate_signature(
                payload_str, secret
            )
        
        # Prepare request body
        request_body = {
            'event': 'workflow.execution.completed',
            'timestamp': timezone.now().isoformat(),
            'data': payload
        }
        
        # Try delivery with retries
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == 'POST':
                        response = await client.post(url, json=request_body, headers=request_headers)
                    elif method.upper() == 'PUT':
                        response = await client.put(url, json=request_body, headers=request_headers)
                    elif method.upper() == 'PATCH':
                        response = await client.patch(url, json=request_body, headers=request_headers)
                    else:
                        response = await client.get(url, headers=request_headers)
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Success if 2xx status code
                    if 200 <= response.status_code < 300:
                        return WebhookDelivery(
                            success=True,
                            status_code=response.status_code,
                            response_body=response.text[:1000] if response.text else None,
                            duration_ms=duration_ms
                        )
                    
                    # Non-retryable status codes
                    if response.status_code in (400, 401, 403, 404, 422):
                        return WebhookDelivery(
                            success=False,
                            status_code=response.status_code,
                            response_body=response.text[:1000] if response.text else None,
                            error_message=f"HTTP {response.status_code}",
                            duration_ms=duration_ms
                        )
                    
                    # Retry server errors
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    
            except httpx.TimeoutException:
                error_msg = "Request timeout"
                duration_ms = int((time.time() - start_time) * 1000)
                
            except httpx.RequestError as e:
                error_msg = f"Request error: {str(e)}"
                duration_ms = int((time.time() - start_time) * 1000)
            
            # Retry on failure
            if attempt < self.max_retries:
                logger.warning(f"Webhook delivery failed (attempt {attempt + 1}), retrying: {error_msg}")
                await self._delay(self.retry_delay * (2 ** attempt))
            else:
                return WebhookDelivery(
                    success=False,
                    error_message=error_msg,
                    duration_ms=duration_ms
                )
        
        return WebhookDelivery(success=False, error_message="Max retries exceeded")

    async def _delay(self, seconds: float):
        """Async delay."""
        import asyncio
        await asyncio.sleep(seconds)


class WorkflowWebhookHandler:
    """Handler for workflow execution webhooks."""

    def __init__(self):
        self.delivery_service = WebhookDeliveryService()

    async def on_execution_complete(
        self,
        execution,
        webhook_urls: List[str],
        secrets: Optional[Dict[str, str]] = None
    ) -> Dict[str, WebhookDelivery]:
        """Send webhook notifications when execution completes."""
        results = {}
        
        # Build payload
        payload = {
            'execution_id': execution.id,
            'workflow_id': execution.workflow_id,
            'workflow_name': execution.workflow.name,
            'status': execution.status,
            'input_data': execution.input_data,
            'output_data': execution.output_data,
            'error_message': execution.error_message,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'duration_ms': int(execution.duration * 1000) if execution.duration else None,
            'triggered_by': execution.triggered_by.username if execution.triggered_by else None,
            'trigger_type': execution.trigger_type,
        }
        
        # Send to all webhooks
        for url in webhook_urls:
            secret = secrets.get(url) if secrets else None
            result = await self.delivery_service.deliver(url, payload, secret)
            results[url] = result
            
            # Log delivery result
            self._log_delivery(execution, url, result)
        
        return results

    def _log_delivery(self, execution, url: str, result: WebhookDelivery):
        """Log webhook delivery attempt."""
        from .models import WebhookDeliveryLog

        try:
            WebhookDeliveryLog.objects.create(
                webhook_url=url,
                execution=execution,
                status=result.status_code if result.success else 'failed',
                request_payload=json.dumps({
                    'event': 'workflow.execution.completed',
                    'execution_id': execution.id
                }),
                response_status_code=result.status_code,
                response_body=result.response_body,
                error_message=result.error_message,
                duration_ms=result.duration_ms,
                success=result.success
            )
        except Exception as e:
            logger.error(f"Failed to log webhook delivery: {e}")


class WebhookSignatureVerifier:
    """Verify incoming webhook signatures."""

    def __init__(self, secret: str):
        self.secret = secret
        self.delivery_service = WebhookDeliveryService()

    def verify(self, payload: str, signature: str) -> bool:
        """Verify incoming webhook signature."""
        return self.delivery_service.verify_signature(payload, signature, self.secret)


# Global webhook handler instance
webhook_handler = WorkflowWebhookHandler()


# Synchronous delivery for Celery tasks
def deliver_webhook_sync(
    url: str,
    payload: Dict[str, Any],
    secret: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None
) -> WebhookDelivery:
    """Synchronous webhook delivery for Celery tasks."""
    import requests
    
    start_time = time.time()
    
    # Prepare headers
    request_headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Flowly-Webhook/1.0',
        'X-Webhook-Event': 'workflow.execution',
        'X-Webhook-Timestamp': str(int(time.time())),
    }
    
    if headers:
        request_headers.update(headers)
    
    if secret:
        payload_str = json.dumps(payload, sort_keys=True)
        delivery_service = WebhookDeliveryService()
        request_headers['X-Webhook-Signature'] = delivery_service.generate_signature(
            payload_str, secret
        )
    
    request_body = {
        'event': 'workflow.execution.completed',
        'timestamp': timezone.now().isoformat(),
        'data': payload
    }
    
    try:
        response = requests.post(url, json=request_body, headers=request_headers, timeout=30)
        duration_ms = int((time.time() - start_time) * 1000)
        
        return WebhookDelivery(
            success=200 <= response.status_code < 300,
            status_code=response.status_code,
            response_body=response.text[:1000] if response.text else None,
            error_message=None if 200 <= response.status_code < 300 else f"HTTP {response.status_code}",
            duration_ms=duration_ms
        )
    except requests.Timeout:
        duration_ms = int((time.time() - start_time) * 1000)
        return WebhookDelivery(
            success=False,
            error_message="Request timeout",
            duration_ms=duration_ms
        )
    except requests.RequestException as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return WebhookDelivery(
            success=False,
            error_message=str(e),
            duration_ms=duration_ms
        )
