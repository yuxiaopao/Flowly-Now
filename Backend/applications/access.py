"""Fail closed on inactive accounts, inactive teams and revoked memberships."""
from django.db.models import Q
from tenants.models import TenantMembership
from .constants import ACTIVE_TENANT_STATUSES
from .models import Application


def team_role(user, tenant):
    if not user or not user.is_authenticated or not user.is_active:
        return None
    if tenant.status not in ACTIVE_TENANT_STATUSES:
        return None
    if user.is_superuser or tenant.owner_id == user.pk:
        return 'owner'
    return TenantMembership.objects.filter(tenant=tenant, user=user, is_active=True).values_list('role', flat=True).first()


def visible_applications(user):
    qs = Application.objects.filter(is_deleted=False)
    if not user or not user.is_authenticated or not user.is_active:
        return qs.none()
    if user.is_superuser:
        return qs.filter(Q(tenant__isnull=True) | Q(tenant__status__in=ACTIVE_TENANT_STATUSES))
    teams = TenantMembership.objects.filter(user=user, is_active=True, tenant__status__in=ACTIVE_TENANT_STATUSES).values('tenant_id')
    return qs.filter(Q(owner=user, tenant__isnull=True) | Q(tenant_id__in=teams) |
                     Q(tenant__owner=user, tenant__status__in=ACTIVE_TENANT_STATUSES)).distinct()


def can_edit(user, application):
    if not user or not user.is_active:
        return False
    if application.tenant_id:
        return team_role(user, application.tenant) in ('owner', 'admin', 'member')
    return user.is_superuser or application.owner_id == user.pk


def can_publish(user, application):
    if not can_edit(user, application):
        return False
    return (application.owner_id == user.pk or not application.tenant_id or
            team_role(user, application.tenant) in ('owner', 'admin'))


def request_authorized(record):
    from django.contrib.auth import get_user_model
    from .models import ApplicationAPIKey
    if record.status not in ('running', 'completed'):
        return False
    application = Application.objects.select_related('owner', 'tenant').filter(pk=record.application_id, is_deleted=False).first()
    if not application or not can_edit(application.owner, application):
        return False
    caller = get_user_model().objects.filter(pk=record.caller_id, is_active=True).first() if record.caller_id else None
    if not caller or not visible_applications(caller).filter(pk=application.pk).exists() or not can_edit(caller, application):
        return False
    if not record.api_key_id:
        return True
    key = ApplicationAPIKey.objects.select_related('created_by').filter(pk=record.api_key_id).first()
    return bool(key and key.is_active and can_publish(key.created_by, application))
