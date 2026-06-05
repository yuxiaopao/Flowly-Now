"""
Celery tasks for billing app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_monthly_invoices():
    """Generate monthly invoices for all active subscriptions."""
    from .models import Subscription, Invoice, SubscriptionStatus, PaymentStatus
    from tenants.models import TenantUsage
    
    now = timezone.now()
    
    # Find subscriptions that need invoicing
    subscriptions = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        current_period_end__lte=now
    )
    
    invoices = []
    for sub in subscriptions:
        try:
            # Calculate usage
            usage = TenantUsage.objects.get(tenant=sub.tenant)
            
            # Calculate cost
            price_tier = sub.plan.price
            base_cost = price_tier.price
            
            # Add usage costs if applicable
            additional_costs = 0
            if usage.current_month_executions > sub.plan.workflow_limit:
                additional_costs = (
                    usage.current_month_executions - sub.plan.workflow_limit
                ) * sub.plan.execution_overage_price
            
            total = base_cost + additional_costs
            
            # Create invoice
            invoice = Invoice.objects.create(
                subscription=sub,
                amount=total,
                currency='CNY',
                status=PaymentStatus.PENDING,
                due_date=now + timedelta(days=30),
                period_start=sub.current_period_start,
                period_end=sub.current_period_end,
                line_items=[{
                    'description': f'{sub.get_plan_display()} - {now.strftime("%Y年%m月")}',
                    'amount': base_cost
                }] + ([{
                    'description': '超出执行次数费用',
                    'amount': additional_costs
                }] if additional_costs > 0 else [])
            )
            invoices.append(invoice)
            
        except Exception as e:
            logger.error(f"Failed to process invoice for subscription {sub.id}: {e}")
    
    return len(invoices)


@shared_task
def check_subscription_status():
    """Check and update subscription statuses."""
    from .models import Subscription, SubscriptionStatus
    
    now = timezone.now()
    
    # Check for expired trials
    Trial_expired = Subscription.objects.filter(
        status=SubscriptionStatus.TRIALING,
        trial_end__lt=now
    )
    Trial_expired.update(status=SubscriptionStatus.INACTIVE)
    
    # Check for expired subscriptions
    expired = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        current_period_end__lt=now
    )
    expired.update(status=SubscriptionStatus.PAST_DUE)
    
    return {
        'trial_expired': Trial_expired.count(),
        'subscription_expired': expired.count()
    }


@shared_task
def send_billing_reminders():
    """Send billing reminder emails."""
    from .models import Subscription, Invoice, SubscriptionStatus, PaymentStatus
    from django.core.mail import send_mail
    from django.conf import settings
    
    # Find invoices due in 3 days
    three_days = timezone.now() + timedelta(days=3)
    
    invoices = Invoice.objects.filter(
        status=PaymentStatus.PENDING,
        due_date__lte=three_days
    ).select_related('subscription', 'subscription__tenant')
    
    for invoice in invoices:
        try:
            tenant = invoice.subscription.tenant
            if tenant.owner.email:
                send_mail(
                    subject=f'[Flowly] 账单提醒 - {invoice.invoice_number}',
                    message=f'''您好 {tenant.owner.username},

您的账单即将到期：

账单编号: {invoice.invoice_number}
金额: ¥{invoice.amount}
到期日: {invoice.due_date.strftime("%Y年%m月%d日")}

请及时支付以避免服务中断。

谢谢！
Flowly 团队
''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tenant.owner.email],
                    fail_silently=True
                )
        except Exception as e:
            logger.error(f"Failed to send billing reminder: {e}")
    
    return invoices.count()


@shared_task
def record_usage_batch():
    """Record usage for all active subscriptions."""
    from .models import Subscription, UsageRecord, SubscriptionStatus
    from tenants.models import TenantUsage
    
    subscriptions = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE
    ).select_related('tenant')
    
    records = []
    for sub in subscriptions:
        try:
            usage = TenantUsage.objects.get(tenant=sub.tenant)
            
            # Record executions
            if usage.current_month_executions > 0:
                records.append(UsageRecord(
                    tenant=sub.tenant,
                    record_type='executions',
                    quantity=usage.current_month_executions,
                    cost=usage.current_month_executions * sub.plan.execution_overage_price
                ))
            
            # Record workflows
            if usage.current_month_workflows > 0:
                records.append(UsageRecord(
                    tenant=sub.tenant,
                    record_type='workflows',
                    quantity=usage.current_month_workflows
                ))
                
        except Exception as e:
            logger.error(f"Failed to record usage for tenant {sub.tenant_id}: {e}")
    
    UsageRecord.objects.bulk_create(records)
    return len(records)


@shared_task
def cleanup_old_invoices(days=365):
    """Archive old paid invoices."""
    from .models import Invoice, PaymentStatus
    
    cutoff = timezone.now() - timedelta(days=days)
    old_invoices = Invoice.objects.filter(
        status=PaymentStatus.PAID,
        paid_at__lt=cutoff
    )
    
    count = old_invoices.count()
    logger.info(f"Would archive {count} old invoices")
    
    # For now, just log - implement archival logic if needed
    return count
