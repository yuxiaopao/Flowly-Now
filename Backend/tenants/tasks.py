"""
Celery tasks for tenants app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_tenant_usage():
    """Update usage statistics for all tenants."""
    from .models import Tenant, TenantUsage
    from workflows.models import WorkflowExecution
    
    tenants = Tenant.objects.filter(status='active')
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    for tenant in tenants:
        # Count workflows
        workflow_count = tenant.workflows.count()
        
        # Count executions this month
        executions = WorkflowExecution.objects.filter(
            workflow__tenant=tenant,
            started_at__gte=month_start
        )
        execution_count = executions.count()
        
        # Count users
        user_count = tenant.memberships.filter(is_active=True).count()
        
        # Update or create usage record
        usage, _ = TenantUsage.objects.get_or_create(tenant=tenant)
        usage.current_month_workflows = workflow_count
        usage.current_month_executions = execution_count
        usage.current_month_users = user_count
        usage.save()
    
    return tenants.count()


@shared_task
def check_tenant_limits():
    """Check if tenants are exceeding their limits."""
    from .models import Tenant, TenantUsage
    from django.core.mail import send_mail
    from django.conf import settings
    
    tenants = Tenant.objects.filter(status='active')
    
    for tenant in tenants:
        try:
            usage = TenantUsage.objects.get(tenant=tenant)
        except TenantUsage.DoesNotExist:
            continue
        
        alerts = []
        
        # Check user limit
        if usage.current_month_users >= tenant.max_users:
            alerts.append(f"用户数已达到上限 ({tenant.max_users})")
        
        # Check workflow limit
        if usage.current_month_workflows >= tenant.max_workflows:
            alerts.append(f"工作流数已达到上限 ({tenant.max_workflows})")
        
        # Check execution limit
        if usage.current_month_executions >= tenant.max_executions_per_month:
            alerts.append(f"执行次数已达到上限 ({tenant.max_executions_per_month})")
        
        if alerts and tenant.owner.email:
            send_mail(
                subject=f'[Flowly] {tenant.name} 接近使用限制',
                message=f'''您好 {tenant.owner.username},

您的租户 "{tenant.name}" 已接近以下限制：

{chr(10).join(f"- {alert}" for alert in alerts)}

请升级您的套餐或清理未使用的资源。

谢谢！
Flowly 团队
''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[tenant.owner.email],
                fail_silently=True
            )
    
    return len(tenants)


@shared_task
def process_pending_invitations():
    """Process and clean up expired invitations."""
    from .models import TenantInvitation, TenantMembership
    
    # Find expired invitations
    expired = TenantInvitation.objects.filter(
        status='pending',
        expires_at__lt=timezone.now()
    )
    
    count = expired.update(status='expired')
    logger.info(f"Expired {count} invitations")
    
    return count


@shared_task
def cleanup_suspended_tenants(days=90):
    """Clean up data for long-suspended tenants."""
    from .models import Tenant
    
    cutoff = timezone.now() - timedelta(days=days)
    old_suspended = Tenant.objects.filter(
        status='suspended',
        updated_at__lt=cutoff
    )
    
    count = old_suspended.count()
    logger.info(f"Found {count} long-suspended tenants")
    
    # Don't delete, just log
    return count


@shared_task
def reset_monthly_stats():
    """Reset monthly statistics for all tenants."""
    from .models import TenantUsage
    
    TenantUsage.objects.all().update(
        current_month_workflows=0,
        current_month_executions=0,
        current_month_users=0,
        last_reset_at=timezone.now()
    )
    
    logger.info("Reset monthly stats for all tenants")
    return TenantUsage.objects.count()
