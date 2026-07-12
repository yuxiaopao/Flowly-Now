"""
Django signals for tenants app.
"""

from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


@receiver(post_save, sender='tenants.TenantMembership')
def membership_created(sender, instance, created, **kwargs):
    """Handle new membership creation."""
    if created:
        # Send notification to new member
        if instance.user and instance.user.email:
            from django.core.mail import send_mail
            from django.conf import settings
            
            try:
                send_mail(
                    subject=f'您已被邀请加入 {instance.tenant.name}',
                    message=f'''您好 {instance.user.username},

您已被邀请加入团队 "{instance.tenant.name}"，角色为 {instance.get_role_display()}。

请登录 Flowly 查看邀请。

谢谢！
Flowly 团队
''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.user.email],
                    fail_silently=True
                )
            except Exception:
                pass


@receiver(post_delete, sender='tenants.TenantMembership')
def membership_deleted(sender, instance, **kwargs):
    """Handle membership deletion — notify removed member and team."""
    user = instance.user
    tenant = instance.tenant
    if user and user.email:
        from django.conf import settings
        from core.email_delivery import send_email_with_fallback

        try:
            send_email_with_fallback(
                subject=f'您已离开团队 {tenant.name}',
                message=(
                    f'您好 {user.username},\n\n'
                    f'您已不再属于团队 "{tenant.name}"。\n\n'
                    f'如有疑问请联系团队管理员。\n\n'
                    f'Flowly 团队'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
        except Exception:
            pass

    notify_tenant(
        tenant.id,
        'membership_removed',
        {
            'user_id': str(user.id) if user else None,
            'username': getattr(user, 'username', ''),
            'role': instance.role,
        },
    )


def notify_tenant(tenant_id, event_type, data):
    """Send notification to all tenant members."""
    from .models import TenantMembership
    
    channel_layer = get_channel_layer_safe()
    if not channel_layer:
        return
    
    from asgiref.sync import async_to_sync
    
    members = TenantMembership.objects.filter(
        tenant_id=tenant_id,
        is_active=True
    ).select_related('user')
    
    for membership in members:
        if membership.user:
            try:
                async_to_sync(channel_layer.group_send)(
                    f'notifications_{membership.user_id}',
                    {
                        'type': 'notification',
                        'data': {
                            'event': event_type,
                            'tenant_id': tenant_id,
                            **data
                        }
                    }
                )
            except Exception:
                pass
