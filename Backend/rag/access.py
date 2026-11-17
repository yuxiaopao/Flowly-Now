"""One visibility boundary for HTTP, workflow and Agent retrieval."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from tenants.access import TENANT_VIEWER_ROLES
from tenants.models import Tenant, TenantMembership
from .constants import ACTIVE_TEAM_STATUSES
from .models import Chunk, Document, DocumentCollection, RAGPipeline, VectorStore


def active_actor(user):
    if not user or not user.is_authenticated:
        return None
    return get_user_model().objects.filter(pk=user.pk, is_active=True).only('id', 'is_superuser').first()


def team_role(user, tenant_id):
    tenant = Tenant.objects.filter(pk=tenant_id, status__in=ACTIVE_TEAM_STATUSES).only('id', 'owner_id').first()
    if tenant is None:
        return None
    if tenant.owner_id == user.pk:
        return 'owner'
    return TenantMembership.objects.filter(user=user, tenant=tenant, is_active=True,
        role__in=TENANT_VIEWER_ROLES).values_list('role', flat=True).first()


def resource_scope(user, *, public_stores=False):
    actor = active_actor(user)
    if actor is None:
        return Q(pk__in=[])
    personal = Q(owner_id=actor.pk, tenant__isnull=True)
    if public_stores:
        personal |= Q(owner__isnull=True, tenant__isnull=True)
    if actor.is_superuser:
        return personal | Q(tenant__isnull=False)
    teams = Tenant.objects.filter(status__in=ACTIVE_TEAM_STATUSES).filter(
        Q(owner=actor) | Q(memberships__user=actor, memberships__is_active=True, memberships__role__in=TENANT_VIEWER_ROLES))
    return personal | Q(tenant_id__in=teams.values('pk'))


def accessible_collections(user):
    return DocumentCollection.objects.filter(resource_scope(user)).distinct()


def accessible_stores(user):
    return VectorStore.objects.filter(resource_scope(user, public_stores=True)).distinct()


def _can_manage(user, owner_id, tenant_id):
    actor = active_actor(user)
    if actor is None:
        return False
    if actor.is_superuser:
        return True
    if tenant_id is None:
        return owner_id == actor.pk
    role = team_role(actor, tenant_id)
    return role in ('owner', 'admin') or role == 'member' and owner_id == actor.pk


def can_manage_collection(user, collection):
    current = DocumentCollection.objects.filter(pk=collection.pk).values('owner_id', 'tenant_id').first()
    return bool(current and _can_manage(user, current['owner_id'], current['tenant_id']))


def can_manage_store(user, store):
    current = VectorStore.objects.filter(pk=store.pk).values('owner_id', 'tenant_id').first()
    return bool(current and _can_manage(user, current['owner_id'], current['tenant_id']))


def can_manage_resource(user, resource):
    if isinstance(resource, DocumentCollection):
        return can_manage_collection(user, resource)
    if isinstance(resource, VectorStore):
        return can_manage_store(user, resource)
    if isinstance(resource, RAGPipeline):
        current = RAGPipeline.objects.filter(pk=resource.pk).values('owner_id', 'collection__tenant_id').first()
        return bool(current and _can_manage(user, current['owner_id'], current['collection__tenant_id']))
    if isinstance(resource, Document):
        return can_manage_collection(user, resource.collection)
    if isinstance(resource, Chunk):
        return can_manage_collection(user, resource.document.collection)
    return False
