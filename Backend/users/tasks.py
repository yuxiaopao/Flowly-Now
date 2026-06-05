"""
Celery tasks for users app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def reset_monthly_executions():
    """Reset monthly execution counters for all users."""
    from .models import User
    
    users = User.objects.filter(monthly_executions__gt=0)
    count = users.update(monthly_executions=0)
    logger.info(f"Reset monthly executions for {count} users")
    return count


@shared_task
def cleanup_inactive_users(days=90):
    """Send reminder emails to inactive users."""
    from django.core.mail import send_mail
    from django.conf import settings
    
    cutoff = timezone.now() - timedelta(days=days)
    inactive_users = User.objects.filter(
        last_login_at__lt=cutoff,
        is_active=True
    )
    
    for user in inactive_users:
        try:
            send_mail(
                subject='[Flowly] 您的账户已有一段时间未使用',
                message=f'''您好 {user.username},

我们注意到您已经有一段时间没有使用 Flowly 了。

如果您有任何问题，可以查看我们的帮助文档或联系支持团队。

谢谢！
Flowly 团队
''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Failed to send reminder to {user.email}: {e}")
    
    return inactive_users.count()


@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new users."""
    from django.core.mail import send_mail
    from django.conf import settings
    
    try:
        from .models import User
        user = User.objects.get(id=user_id)
        
        send_mail(
            subject='欢迎使用 Flowly',
            message=f'''您好 {user.username},

感谢您注册 Flowly！

开始使用：
1. 创建一个工作流
2. 添加 AI 节点
3. 执行并查看结果

如有疑问，请查看我们的文档或联系支持。

祝您使用愉快！
Flowly 团队
''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True
        )
        logger.info(f"Sent welcome email to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")


@shared_task
def update_user_stats():
    """Update user statistics."""
    from .models import User
    from workflows.models import WorkflowExecution
    
    users = User.objects.filter(is_active=True)
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    for user in users:
        # Count executions this month
        executions = WorkflowExecution.objects.filter(
            triggered_by=user,
            started_at__gte=month_start
        ).count()
        
        User.objects.filter(id=user.id).update(monthly_executions=executions)
    
    return users.count()


@shared_task
def export_user_data(user_id):
    """Export user data for GDPR requests."""
    import json
    from django.conf import settings
    import os
    
    try:
        from .models import User
        user = User.objects.get(id=user_id)
        
        data = {
            'user': {
                'username': user.username,
                'email': user.email,
                'date_joined': user.date_joined.isoformat(),
                'role': user.role,
            },
            'workflows': [],
            'executions': [],
            'agents': [],
        }
        
        # Add workflows
        for wf in user.workflows.all():
            data['workflows'].append({
                'name': wf.name,
                'created_at': wf.created_at.isoformat(),
            })
        
        # Add executions
        for ex in user.triggered_executions.all()[:1000]:
            data['executions'].append({
                'workflow_name': ex.workflow.name,
                'status': ex.status,
                'started_at': ex.started_at.isoformat(),
            })
        
        # Save to file
        export_dir = getattr(settings, 'USER_DATA_EXPORT_DIR', '/tmp/exports')
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f"user_{user_id}_export_{now.strftime('%Y%m%d')}.json"
        filepath = os.path.join(export_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported user data for {user_id} to {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Failed to export user data: {e}")
        raise
