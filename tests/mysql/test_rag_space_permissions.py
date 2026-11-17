"""Actual InnoDB default-store selection and fresh RAG membership boundaries."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import connection, connections
from rest_framework.test import APIClient
from rag.models import DocumentCollection, VectorStore
from tenants.models import Tenant, TenantMembership
from users.models import User

pytestmark = pytest.mark.django_db(transaction=True)


def api(user):
    client = APIClient(); client.force_authenticate(user)
    return client


def team(user):
    value = Tenant.objects.create(owner=user, name='MySQL RAG scope', slug='mysql-rag-scope', status='active')
    TenantMembership.objects.create(tenant=value, user=user, role='owner', is_active=True)
    return value


def test_two_real_collection_posts_share_one_owned_team_default(user):
    assert connection.vendor == 'mysql'
    tenant = team(user)
    barrier = Barrier(2)
    def create(index):
        try:
            actor = User.objects.get(pk=user.pk)
            barrier.wait(timeout=10)
            return api(actor).post('/api/v1/rag/collections/', {'name': f'Concurrent knowledge {index}',
                'tenant': tenant.pk, 'retrieval_mode': 'keyword'}, format='json')
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = [future.result(timeout=30) for future in [pool.submit(create, index) for index in range(2)]]
    assert [response.status_code for response in responses] == [201, 201], [response.content for response in responses]
    rows = list(DocumentCollection.objects.filter(tenant=tenant))
    assert len(rows) == 2 and len({row.vector_store_id for row in rows}) == 1
    store = VectorStore.objects.get(pk=rows[0].vector_store_id)
    assert store.owner_id == user.pk and store.tenant_id == tenant.pk and store.is_default
    assert VectorStore.objects.filter(owner=user, tenant=tenant, is_default=True).count() == 1


def test_removed_resource_owner_cannot_read_or_delete_the_team_collection(user, admin_user):
    assert connection.vendor == 'mysql'
    tenant = team(admin_user)
    membership = TenantMembership.objects.create(tenant=tenant, user=user, role='member', is_active=True)
    client = api(user)
    response = client.post('/api/v1/rag/collections/', {'name': 'Owned inside team', 'tenant': tenant.pk,
        'retrieval_mode': 'keyword'}, format='json')
    assert response.status_code == 201, response.content
    identity = (response.data.get('data') or response.data)['id']
    membership.is_active = False; membership.save(update_fields=['is_active'])
    url = f'/api/v1/rag/collections/{identity}/'
    assert client.get(url).status_code in (403, 404)
    assert client.delete(url).status_code in (403, 404)
    assert DocumentCollection.objects.filter(pk=identity, tenant=tenant).exists()
