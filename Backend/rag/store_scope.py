"""Writable collection spaces and owner/tenant-scoped store defaults."""
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied, ValidationError
from tenants.access import TENANT_MEMBER_ROLES
from tenants.models import Tenant, TenantMembership

from .constants import ACTIVE_TEAM_STATUSES, DEFAULT_STORE_NAME, DEFAULT_STORE_TYPE
from .models import VectorStore


def writable_space(user, tenant):
    if not get_user_model().objects.filter(pk=user.pk, is_active=True).exists():
        raise PermissionDenied('当前账号无法编辑知识库资源。')
    if tenant is None:
        return None
    current = Tenant.objects.filter(pk=tenant.pk, status__in=ACTIVE_TEAM_STATUSES).first()
    if current is None:
        raise PermissionDenied('所属团队已停用，无法编辑知识库资源。')
    role = 'owner' if user.is_superuser or current.owner_id == user.pk else TenantMembership.objects.filter(
        user=user, tenant=current, is_active=True).values_list('role', flat=True).first()
    if role not in TENANT_MEMBER_ROLES:
        raise PermissionDenied('需要当前团队的所有者、管理员或成员编辑权限。')
    return current


def default_stores(owner_id, tenant):
    return VectorStore.objects.filter(owner_id=owner_id, tenant_id=tenant.pk if tenant else None)


def lock_store_owner(owner_id):
    # One existing row serializes default selection even when a space has no store yet.
    get_user_model().objects.select_for_update().get(pk=owner_id)


def clear_other_defaults(owner_id, tenant, *, except_id=None):
    selected = default_stores(owner_id, tenant)
    if except_id is not None:
        selected = selected.exclude(pk=except_id)
    selected.filter(is_default=True).update(is_default=False)


def choose_default_store(user, tenant):
    lock_store_owner(user.pk)
    selected = default_stores(user.pk, tenant)
    store = selected.filter(is_default=True).first()
    if store is None:
        store = selected.filter(store_type=DEFAULT_STORE_TYPE, name=DEFAULT_STORE_NAME).first()
        if store is None:
            store = VectorStore.objects.create(owner=user, tenant=tenant, store_type=DEFAULT_STORE_TYPE,
                name=DEFAULT_STORE_NAME, is_default=True)
        elif not store.is_default:
            VectorStore.objects.filter(pk=store.pk).update(is_default=True)
            store.is_default = True
    return store


def validate_collection_store(user, tenant, store, owner_id):
    tenant = writable_space(user, tenant)
    if store is None:
        return tenant
    current = VectorStore.objects.filter(pk=store.pk).first()
    if current is None or current.tenant_id != (tenant.pk if tenant else None):
        raise ValidationError({'vector_store': '向量存储必须与知识库处于同一个个人或团队空间。'})
    if tenant is None and current.owner_id != owner_id:
        raise ValidationError({'vector_store': '个人知识库必须使用其所有者的个人向量存储。'})
    return tenant
