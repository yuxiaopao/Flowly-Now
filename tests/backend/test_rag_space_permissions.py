"""Current team membership governs every HTTP and internal RAG access path."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from agents.models import Agent
from rag.models import Document, DocumentCollection, VectorStore
from tenants.models import Tenant, TenantMembership
from users.models import User
from tests.backend.test_applications import model_server

pytestmark = pytest.mark.django_db
BASE = '/api/v1/rag'


def as_user(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def shared(user, authenticated_client):
    owner = User.objects.create_user(username='rag-space-team-owner')
    tenant = Tenant.objects.create(owner=owner, name='RAG space', slug='rag-space', status='active')
    membership = TenantMembership.objects.create(user=user, tenant=tenant, role='member', is_active=True)
    created = authenticated_client.post(f'{BASE}/collections/', {'name': 'Team evidence', 'tenant': tenant.pk,
        'retrieval_mode': 'keyword'}, format='json')
    assert created.status_code == 201
    collection = DocumentCollection.objects.get(pk=created.data['id'])
    uploaded = authenticated_client.post(f'{BASE}/collections/{collection.pk}/upload_file/',
        {'file': SimpleUploadedFile('evidence.txt', b'Team workflow evidence must remain intact.')}, format='multipart')
    assert uploaded.status_code == 201
    document = Document.objects.get(pk=uploaded.data['document_id'])
    pipeline = authenticated_client.post(f'{BASE}/pipelines/', {'name': 'Team pipeline', 'collection': str(collection.pk)}, format='json')
    assert pipeline.status_code == 201
    empty_store = VectorStore.objects.create(owner=user, tenant=tenant, name='Empty team store', store_type='memory')
    return tenant, membership, collection, document, pipeline.data['id'], empty_store, owner


def revoke(shared, state):
    tenant, membership, *_ = shared
    if state == 'left':
        membership.is_active = False
        membership.save(update_fields=['is_active'])
    else:
        tenant.status = 'suspended'
        tenant.save(update_fields=['status'])


@pytest.mark.parametrize('state', ['left', 'suspended'])
@pytest.mark.parametrize('operation', ['read', 'query', 'ingest', 'delete'])
def test_original_creator_cannot_bypass_team_boundary_and_uploaded_evidence_survives(user, authenticated_client, shared, state, operation):
    _, _, collection, document, pipeline_id, _, _ = shared
    chunk_ids = set(document.chunks.values_list('pk', flat=True))
    original_metadata = document.metadata.copy()
    revoke(shared, state)
    endpoint = f'{BASE}/collections/{collection.pk}/'
    if operation == 'read':
        response = authenticated_client.get(endpoint)
    elif operation == 'query':
        response = authenticated_client.post(endpoint+'search/', {'query': 'workflow'}, format='json')
    elif operation == 'ingest':
        response = authenticated_client.post(endpoint+'add_document/', {'title': 'Forbidden new', 'content': 'Must not save'}, format='json')
    else:
        response = authenticated_client.delete(endpoint)
    assert response.status_code in (403, 404)
    document.refresh_from_db()
    assert document.source_type == 'file' and document.metadata == original_metadata
    assert document.content == 'Team workflow evidence must remain intact.'
    assert set(document.chunks.values_list('pk', flat=True)) == chunk_ids
    assert collection.documents.count() == 1
    assert authenticated_client.get(f'{BASE}/documents/{document.pk}/').status_code == 404
    assert authenticated_client.get(f'{BASE}/pipelines/{pipeline_id}/retrieve/', {'query': 'workflow'}).status_code == 404
    listing = authenticated_client.get(f'{BASE}/collections/')
    assert listing.status_code == 200 and listing.json()['data']['results'] == []


@pytest.mark.parametrize('state', ['left', 'suspended'])
def test_original_store_owner_cannot_read_patch_or_delete_team_store_after_access_loss(authenticated_client, shared, state):
    _, _, collection, _, _, empty_store, _ = shared
    revoke(shared, state)
    assert authenticated_client.get(f'{BASE}/vector-stores/{collection.vector_store_id}/').status_code == 404
    assert authenticated_client.patch(f'{BASE}/vector-stores/{empty_store.pk}/', {'name': 'Must not save'}, format='json').status_code in (403, 404)
    assert authenticated_client.delete(f'{BASE}/vector-stores/{empty_store.pk}/').status_code in (403, 404)
    empty_store.refresh_from_db()
    assert empty_store.name == 'Empty team store'


@pytest.mark.parametrize('role', ['viewer', 'member'])
def test_readers_can_query_team_content_but_cannot_ingest_or_manage_another_members_resources(shared, role):
    tenant, _, collection, document, pipeline_id, empty_store, _ = shared
    reader = User.objects.create_user(username=f'rag-space-{role}')
    TenantMembership.objects.create(user=reader, tenant=tenant, role=role, is_active=True)
    client = as_user(reader)
    endpoint = f'{BASE}/collections/{collection.pk}/'
    assert client.get(endpoint).status_code == 200
    queried = client.post(endpoint+'search/', {'query': 'workflow'}, format='json')
    assert queried.status_code == 200 and queried.data['results'][0]['metadata']['doc_id'] == str(document.pk)
    assert client.get(f'{BASE}/pipelines/{pipeline_id}/retrieve/', {'query': 'workflow'}).status_code == 200
    assert client.post(endpoint+'add_document/', {'title': 'Forbidden', 'content': 'Not mine'}, format='json').status_code == 403
    assert client.post(endpoint+'upload_file/', {'file': SimpleUploadedFile('forbidden.txt', b'Not mine')}, format='multipart').status_code == 403
    assert client.delete(endpoint).status_code == 403
    assert client.patch(f'{BASE}/vector-stores/{empty_store.pk}/', {'name': 'Forbidden'}, format='json').status_code == 403
    assert client.delete(f'{BASE}/pipelines/{pipeline_id}/').status_code == 403
    if role == 'viewer':
        assert client.post(f'{BASE}/pipelines/', {'name': 'Forbidden pipeline', 'collection': str(collection.pk)}, format='json').status_code == 403
    else:
        own = client.post(f'{BASE}/collections/', {'name': 'Member owned', 'tenant': tenant.pk,
            'vector_store': str(collection.vector_store_id)}, format='json')
        assert own.status_code == 201
        assert client.post(f'{BASE}/collections/{own.data["id"]}/add_document/',
            {'title': 'Own content', 'content': 'Own workflow evidence'}, format='json').status_code == 201


@pytest.mark.parametrize('actor_role', ['admin', 'tenant_owner', 'superuser'])
def test_team_administration_and_existing_superuser_authority_are_preserved(shared, actor_role, admin_user):
    tenant, _, collection, document, _, empty_store, owner = shared
    if actor_role == 'tenant_owner':
        actor = owner  # No membership row: the actual tenant owner still administers it.
    elif actor_role == 'superuser':
        actor = admin_user
        tenant.status = 'suspended'
        tenant.save(update_fields=['status'])
    else:
        actor = User.objects.create_user(username='rag-space-admin')
        TenantMembership.objects.create(user=actor, tenant=tenant, role='admin', is_active=True)
    client = as_user(actor)
    assert client.get(f'{BASE}/collections/{collection.pk}/').status_code == 200
    assert client.get(f'{BASE}/vector-stores/{empty_store.pk}/').status_code == 200
    assert client.delete(f'{BASE}/vector-stores/{empty_store.pk}/').status_code == 204
    assert client.delete(f'{BASE}/documents/{document.pk}/').status_code == 204
    assert client.delete(f'{BASE}/collections/{collection.pk}/').status_code == 204


def test_personal_owner_access_and_inactive_actor_rejection_are_preserved(user, authenticated_client):
    created = authenticated_client.post(f'{BASE}/collections/', {'name': 'Personal'}, format='json')
    assert created.status_code == 201
    endpoint = f'{BASE}/collections/{created.data["id"]}/'
    assert authenticated_client.post(endpoint+'add_document/', {'title': 'Own', 'content': 'Personal workflow'}, format='json').status_code == 201
    assert authenticated_client.post(endpoint+'search/', {'query': 'workflow'}, format='json').status_code == 200
    outsider = as_user(User.objects.create_user(username='rag-private-outsider'))
    assert outsider.get(endpoint).status_code == 404
    User.objects.filter(pk=user.pk).update(is_active=False)
    assert authenticated_client.get(endpoint).status_code in (403, 404)
    assert DocumentCollection.objects.filter(pk=created.data['id']).exists()


def test_internal_agent_retrieval_binding_and_detail_reuse_the_current_collection_policy(user, authenticated_client, shared):
    from agents.engine import KnowledgeBaseTool
    _, _, collection, _, _, _, _ = shared
    agent = Agent.objects.create(owner=user, name='Private agent with team evidence', knowledge_collections=[str(collection.pk)])
    tool = KnowledgeBaseTool(collection_ids=[str(collection.pk)], user_id=user.pk)
    assert tool.run('workflow')['success']
    revoke(shared, 'left')
    assert tool.run('workflow')['success'] is False
    response = authenticated_client.get(f'/api/v1/agents/{agent.pk}/')
    assert response.status_code == 200
    assert response.data['knowledge_collections'] == [str(collection.pk)]  # Keep the existing binding, do not delete it.
    assert response.data['knowledge_collections_detail'] == []
    rejected = authenticated_client.post('/api/v1/agents/', {'name': 'Cannot bind revoked knowledge',
        'knowledge_collections': [str(collection.pk)]}, format='json')
    assert rejected.status_code == 400


def test_viewer_post_ask_and_pipeline_query_keep_real_retrieval_without_write_authority(shared, model_server):
    tenant, _, collection, document, pipeline_id, _, _ = shared
    viewer = User.objects.create_user(username='rag-post-query-viewer')
    membership = TenantMembership.objects.create(user=viewer, tenant=tenant, role='viewer', is_active=True)
    client = as_user(viewer)
    asked = client.post(f'{BASE}/collections/{collection.pk}/ask/', {'query': 'workflow'}, format='json')
    assert asked.status_code == 200 and asked.data['grounded'] is True
    assert asked.data['sources'][0]['metadata']['doc_id'] == str(document.pk)
    queried = client.post(f'{BASE}/pipelines/{pipeline_id}/query/', {'query': 'workflow'}, format='json')
    assert queried.status_code == 200 and queried.data['sources'][0]['metadata']['doc_id'] == str(document.pk)
    assert len(model_server) == 2
    membership.is_active = False
    membership.save(update_fields=['is_active'])
    assert client.post(f'{BASE}/pipelines/{pipeline_id}/query/', {'query': 'workflow'}, format='json').status_code == 404
    assert len(model_server) == 2 and collection.documents.count() == 1
