"""
Shared tenant access helpers.
"""

from django.db.models import Q

from tenants.models import Tenant, TenantMembership
from workflows.models import Workflow

TENANT_ADMIN_ROLES = ('owner', 'admin')
TENANT_MEMBER_ROLES = ('owner', 'admin', 'member')
TENANT_VIEWER_ROLES = ('owner', 'admin', 'member', 'viewer')


def get_accessible_tenant_ids(user):
    """Return active tenant ids the user belongs to."""
    if not user or not user.is_authenticated:
        return []

    if user.is_superuser:
        return list(Tenant.objects.values_list('id', flat=True))

    return list(
        TenantMembership.objects.filter(user=user, is_active=True)
        .values_list('tenant_id', flat=True)
        .distinct()
    )


def get_tenant_role(user, tenant_id):
    """Return the caller role in the target tenant, if any."""
    if not user or not user.is_authenticated:
        return None

    if user.is_superuser:
        return 'owner'

    membership = TenantMembership.objects.filter(
        user=user,
        tenant_id=tenant_id,
        is_active=True,
    ).values_list('role', flat=True).first()
    return membership



def is_tenant_admin(user, tenant_id):
    """Whether the caller can administer resources in the tenant."""
    return get_tenant_role(user, tenant_id) in TENANT_ADMIN_ROLES



def is_tenant_member(user, tenant_id):
    """Whether the caller is an active tenant member."""
    return get_tenant_role(user, tenant_id) in TENANT_MEMBER_ROLES



def is_tenant_viewer(user, tenant_id):
    """Whether the caller has any active tenant role."""
    return get_tenant_role(user, tenant_id) in TENANT_VIEWER_ROLES



def get_accessible_workflow_queryset(user):
    """Return workflows visible to the current user with tenant boundary enforced."""
    queryset = Workflow.objects.filter(is_deleted=False)

    if not user or not user.is_authenticated:
        return queryset.filter(is_public=True, tenant__isnull=True)

    if user.is_superuser:
        return queryset

    tenant_ids = get_accessible_tenant_ids(user)
    return queryset.filter(
        Q(owner=user)
        | Q(tenant_id__in=tenant_ids)
        | Q(is_public=True, tenant__isnull=True)
    ).distinct()



def can_view_resource(user, resource):
    """Generic visibility guard for tenant-owned resources."""
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    owner_id = getattr(resource, 'owner_id', None) or getattr(resource, 'created_by_id', None)
    if owner_id == user.id:
        return True

    tenant_id = getattr(resource, 'tenant_id', None)
    if tenant_id and tenant_id in set(get_accessible_tenant_ids(user)):
        return True

    return False



def can_execute_workflow(user, workflow):
    """Execution permission baseline before dependency-specific checks."""
    return workflow in get_accessible_workflow_queryset(user)


def can_edit_workflow(user, workflow):
    """Whether the caller may modify workflow definition (save nodes/edges)."""
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if getattr(workflow, 'owner_id', None) == user.id:
        return True

    tenant_id = getattr(workflow, 'tenant_id', None)
    if tenant_id and is_tenant_admin(user, tenant_id):
        return True

    return False
