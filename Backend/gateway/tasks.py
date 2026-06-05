"""
Celery tasks for gateway app.
Handles usage statistics, cost calculation, and model maintenance.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def calculate_usage_costs(days: int = 30):
    """
    Calculate API usage costs for billing.

    Args:
        days: Number of days to analyze
    """
    from datetime import timedelta

    from .models import APICallLog

    cutoff = timezone.now() - timedelta(days=days)

    stats = APICallLog.objects.filter(
        created_at__gte=cutoff
    ).values('provider', 'model').annotate(
        total_calls=Count('id'),
        total_tokens=Sum('tokens_used'),
        total_cost=Sum('cost'),
        avg_latency=Avg('latency_ms')
    ).order_by('-total_cost')

    return {
        'period_days': days,
        'period_start': cutoff.isoformat(),
        'period_end': timezone.now().isoformat(),
        'stats': list(stats)
    }


@shared_task
def aggregate_api_usage(hour: int = None):
    """
    Aggregate API usage statistics hourly.

    Args:
        hour: Hour to aggregate (0-23), defaults to current hour
    """
    from datetime import datetime

    if hour is None:
        hour = timezone.now().hour

    today = timezone.now().date()
    start_time = timezone.make_aware(datetime.combine(today, datetime.min.time().replace(hour=hour)))
    end_time = start_time + timedelta(hours=1)

    from .models import APICallLog

    stats = APICallLog.objects.filter(
        created_at__gte=start_time,
        created_at__lt=end_time
    ).aggregate(
        total_calls=Count('id'),
        successful_calls=Count('id', filter=models.Q(status_code__gte=200, status_code__lt=300)),
        failed_calls=Count('id', filter=~models.Q(status_code__gte=200, status_code__lt=300)),
        total_tokens=Sum('tokens_used'),
        total_cost=Sum('cost'),
        avg_latency=Avg('latency_ms')
    )

    return {
        'hour': hour,
        'date': today.isoformat(),
        'stats': stats
    }


@shared_task
def cleanup_old_api_logs(days: int = 90):
    """
    Clean up old API call logs.

    Args:
        days: Number of days to keep
    """
    from datetime import timedelta

    from .models import APICallLog

    cutoff = timezone.now() - timedelta(days=days)

    deleted_count, _ = APICallLog.objects.filter(
        created_at__lt=cutoff
    ).delete()

    return {'logs_deleted': deleted_count}


@shared_task
def verify_user_api_keys():
    """
    Verify status of all unified API credentials exposed through the legacy gateway API key layer.
    """
    from workflows.models import APICredential

    keys = APICredential.objects.filter(credential_type='api_key', is_active=True)

    results = []
    for key in keys:
        verified = verify_api_key_connection(key)
        if not verified:
            results.append({
                'key_id': str(key.id),
                'name': key.name,
                'verified': False
            })

    return {
        'keys_checked': keys.count(),
        'keys_failed': len(results),
        'failures': results
    }


def verify_api_key_connection(api_key):
    """
    Verify that a unified credential can connect to its provider.
    """
    try:
        from .gateway_service import GatewayService

        provider = getattr(api_key, 'service_type', None)
        decrypted_key = api_key.get_decrypted_data()

        if not provider or not decrypted_key:
            return False

        gateway = GatewayService(user=api_key.owner, api_key=decrypted_key)
        response = gateway.chat(
            messages=[{"role": "user", "content": "test"}],
            model='gpt-3.5-turbo',
            max_tokens=5,
        )
        return bool(getattr(response, 'content', None) or getattr(response, 'provider', None))
    except Exception as exc:
        logger.warning("Unified credential verification failed: %s", exc)
        return False


@shared_task
def update_model_usage_stats():
    """
    Update usage statistics for all models.
    """
    from .models import AIModel

    models = AIModel.objects.filter(is_active=True)

    updated_count = 0
    for model in models:
        stats = APICallLog.objects.filter(
            model=model.model_id,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).aggregate(
            total_calls=Count('id'),
            total_tokens=Sum('tokens_used'),
            total_cost=Sum('cost')
        )

        model.total_calls = stats['total_calls'] or 0
        model.total_tokens = stats['total_tokens'] or 0
        model.total_cost = stats['total_cost'] or 0
        model.save()
        updated_count += 1

    return {'models_updated': updated_count}


@shared_task
def send_usage_report(user_id: int, period: str = 'monthly'):
    """
    Send usage report to user.

    Args:
        user_id: ID of the user
        period: Report period ('daily', 'weekly', 'monthly')
    """
    from .models import APICallLog

    if period == 'daily':
        start_date = timezone.now().date()
    elif period == 'weekly':
        start_date = timezone.now() - timedelta(days=7)
    else:
        start_date = timezone.now() - timedelta(days=30)

    stats = APICallLog.objects.filter(
        user_id=user_id,
        created_at__gte=start_date
    ).aggregate(
        total_calls=Count('id'),
        total_tokens=Sum('tokens_used'),
        total_cost=Sum('cost')
    )

    by_provider = APICallLog.objects.filter(
        user_id=user_id,
        created_at__gte=start_date
    ).values('provider').annotate(
        calls=Count('id'),
        tokens=Sum('tokens_used'),
        cost=Sum('cost')
    )

    report = {
        'user_id': user_id,
        'period': period,
        'period_start': start_date.isoformat(),
        'period_end': timezone.now().isoformat(),
        'summary': stats,
        'by_provider': list(by_provider)
    }

    return report

