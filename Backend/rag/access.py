"""One visibility boundary for HTTP, workflow and Agent retrieval."""
from django.db.models import Q
from tenants.access import get_accessible_tenant_ids, is_tenant_admin
from .models import DocumentCollection


def accessible_collections(user):
    if not user or not user.is_authenticated:
        return DocumentCollection.objects.none()
    return DocumentCollection.objects.filter(
        Q(owner=user) | Q(tenant_id__in=get_accessible_tenant_ids(user))
    ).distinct()


def can_manage_collection(user, collection):
    return bool(user and user.is_authenticated and (
        user.is_superuser or collection.owner_id == user.id or
        (collection.tenant_id and is_tenant_admin(user, collection.tenant_id))
    ))
