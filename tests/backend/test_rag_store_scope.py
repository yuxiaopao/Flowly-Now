"""Real HTTP collection defaults and explicit stores obey the same writable space."""
import pytest
from django.contrib.auth import get_user_model

from rag.models import DocumentCollection, VectorStore
from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.django_db
BASE = '/api/v1/rag'


@pytest.fixture
def spaces(user):
    owner = get_user_model().objects.create_user(username='store-team-owner')
    first = Tenant.objects.create(owner=owner, name='Store first team', slug='store-first-team', status='active')
    second = Tenant.objects.create(owner=owner, name='Store second team', slug='store-second-team', status='active')
    for tenant in (first, second):
        TenantMembership.objects.create(tenant=tenant, user=user, role='member', is_active=True)
    return owner, first, second


def create_collection(client, *, tenant=None, store=None, name='Scope collection'):
    payload = {'name': name, 'retrieval_mode': 'keyword'}
    if tenant is not None:
        payload['tenant'] = tenant.pk
    if store is not None:
        payload['vector_store'] = str(store.pk)
    return client.post(f'{BASE}/collections/', payload, format='json')


def test_new_team_default_reaches_real_application_readiness_and_preserves_personal_default(user, authenticated_client, spaces, settings):
    _, first, second = spaces
    private = VectorStore.objects.create(owner=user, name='Personal default', store_type='memory', is_default=True)
    created = create_collection(authenticated_client, tenant=first)
    assert created.status_code == 201, created.content.decode()
    collection = DocumentCollection.objects.get(pk=created.data['id'])
    store = collection.vector_store
    assert store.owner_id == user.pk and store.tenant_id == collection.tenant_id == first.pk
    assert store.pk != private.pk and store.is_default
    again = create_collection(authenticated_client, tenant=first, name='Reuses same team default')
    assert again.status_code == 201 and str(again.data['vector_store']) == str(store.pk)
    other = create_collection(authenticated_client, tenant=second)
    assert other.status_code == 201
    other_store = DocumentCollection.objects.get(pk=other.data['id']).vector_store
    assert other_store.tenant_id == second.pk and other_store.pk not in (private.pk, store.pk)
    personal = create_collection(authenticated_client)
    assert personal.status_code == 201 and str(personal.data['vector_store']) == str(private.pk)
    private.refresh_from_db()
    assert private.is_default
    ingested = authenticated_client.post(f'{BASE}/collections/{collection.pk}/add_document/',
        {'title': 'Team guide', 'content': 'The team workflow has real searchable evidence.'}, format='json')
    assert ingested.status_code == 201
    app = authenticated_client.post('/api/v1/applications/', {'name': 'Real team knowledge app', 'kind': 'knowledge',
        'tenant_id': first.pk, 'draft': {'collection_id': str(collection.pk)}}, format='json')
    assert app.status_code == 201, app.content.decode()
    settings.RAG_CHAT_MODEL, settings.RAG_CHAT_API_KEY = 'gpt-fixture', 'fixture-only'
    ready = authenticated_client.get(f'/api/v1/applications/{app.json()["data"]["id"]}/readiness/')
    assert ready.status_code == 200
    evidence = ready.json()['data']['draft']
    assert evidence['configuration_ready'] is True and evidence['knowledge']['available_chunks'] == 1
    assert evidence['connection_verified'] is False


@pytest.mark.parametrize('destination,source', [('first', 'personal'), ('first', 'second'),
    ('personal', 'first'), ('personal', 'foreign'), ('personal', 'public')])
def test_explicit_store_cannot_cross_personal_or_team_space(user, authenticated_client, spaces, destination, source):
    owner, first, second = spaces
    stores = {
        'personal': VectorStore.objects.create(owner=user, name='Personal', store_type='memory'),
        'first': VectorStore.objects.create(owner=user, tenant=first, name='First', store_type='memory'),
        'second': VectorStore.objects.create(owner=user, tenant=second, name='Second', store_type='memory'),
        'foreign': VectorStore.objects.create(owner=owner, name='Foreign private', store_type='memory'),
        'public': VectorStore.objects.create(owner=None, name='Public store', store_type='memory'),
    }
    response = create_collection(authenticated_client, tenant=first if destination == 'first' else None, store=stores[source])
    assert response.status_code == 400, response.content.decode()
    assert not DocumentCollection.objects.exists()


def test_same_team_member_can_use_team_store_but_revocation_prevents_create_and_owner_patch(user, authenticated_client, spaces):
    owner, tenant, _ = spaces
    shared = VectorStore.objects.create(owner=owner, tenant=tenant, name='Team owner store', store_type='memory')
    created = create_collection(authenticated_client, tenant=tenant, store=shared)
    assert created.status_code == 201, created.content.decode()
    collection = DocumentCollection.objects.get(pk=created.data['id'])
    assert collection.owner_id == user.pk and collection.vector_store_id == shared.pk
    allowed = authenticated_client.patch(f'{BASE}/collections/{collection.pk}/', {'description': 'Allowed member update'}, format='json')
    assert allowed.status_code == 200
    TenantMembership.objects.filter(user=user, tenant=tenant).update(is_active=False)
    denied = create_collection(authenticated_client, tenant=tenant, store=shared)
    # An inaccessible store ID may be rejected by DRF before space validation.
    assert denied.status_code in (400, 403)
    denied = authenticated_client.patch(f'{BASE}/collections/{collection.pk}/', {'description': 'Must not save'}, format='json')
    assert denied.status_code == 404  # Revoked team resources no longer enter the visible queryset.
    collection.refresh_from_db()
    assert collection.description == 'Allowed member update'


@pytest.mark.parametrize('state', ['viewer', 'revoked', 'suspended'])
def test_viewer_or_unavailable_team_cannot_create_store_or_collection(user, authenticated_client, spaces, state):
    _, tenant, _ = spaces
    membership = TenantMembership.objects.get(user=user, tenant=tenant)
    if state == 'viewer':
        membership.role = 'viewer'
        membership.save(update_fields=['role'])
    elif state == 'revoked':
        membership.is_active = False
        membership.save(update_fields=['is_active'])
    else:
        tenant.status = 'suspended'
        tenant.save(update_fields=['status'])
    own_store = VectorStore.objects.create(owner=user, tenant=tenant, name='Old own store', store_type='memory')
    response = authenticated_client.post(f'{BASE}/vector-stores/', {'name': 'Denied team store', 'store_type': 'memory',
        'tenant': tenant.pk, 'is_default': True}, format='json')
    assert response.status_code == 403
    response = create_collection(authenticated_client, tenant=tenant, store=own_store)
    assert response.status_code == 403
    assert not DocumentCollection.objects.exists()


def test_collection_update_checks_effective_space_and_allows_explicit_empty_space_transfer(user, authenticated_client, spaces):
    _, first, second = spaces
    first_store = VectorStore.objects.create(owner=user, tenant=first, name='First store', store_type='memory')
    second_store = VectorStore.objects.create(owner=user, tenant=second, name='Second store', store_type='memory')
    created = create_collection(authenticated_client, tenant=first, store=first_store)
    assert created.status_code == 201
    collection = DocumentCollection.objects.get(pk=created.data['id'])
    endpoint = f'{BASE}/collections/{collection.pk}/'
    assert authenticated_client.patch(endpoint, {'vector_store': str(second_store.pk)}, format='json').status_code == 400
    assert authenticated_client.patch(endpoint, {'tenant': second.pk}, format='json').status_code == 400
    moved = authenticated_client.patch(endpoint, {'tenant': second.pk, 'vector_store': str(second_store.pk)}, format='json')
    assert moved.status_code == 200, moved.content.decode()
    collection.refresh_from_db()
    assert collection.tenant_id == second.pk and collection.vector_store_id == second_store.pk


def test_setting_store_default_only_clears_same_owner_and_space(user, authenticated_client, spaces):
    _, tenant, _ = spaces
    private = VectorStore.objects.create(owner=user, name='Personal default', store_type='memory', is_default=True)
    first = VectorStore.objects.create(owner=user, tenant=tenant, name='Old team default', store_type='memory', is_default=True)
    created = authenticated_client.post(f'{BASE}/vector-stores/', {'name': 'New team default', 'store_type': 'memory',
        'tenant': tenant.pk, 'is_default': True}, format='json')
    assert created.status_code == 201
    private.refresh_from_db(); first.refresh_from_db()
    assert private.is_default is True and first.is_default is False
    personal_update = authenticated_client.patch(f'{BASE}/vector-stores/{private.pk}/', {'is_default': True}, format='json')
    assert personal_update.status_code == 200
    assert VectorStore.objects.get(pk=created.data['id']).is_default is True


def test_existing_collection_store_cannot_transfer_space_behind_its_back(user, authenticated_client, spaces):
    _, first, second = spaces
    store = VectorStore.objects.create(owner=user, tenant=first, name='Bound team store', store_type='memory')
    created = create_collection(authenticated_client, tenant=first, store=store)
    assert created.status_code == 201
    changed = authenticated_client.patch(f'{BASE}/vector-stores/{store.pk}/', {'tenant': second.pk}, format='json')
    assert changed.status_code == 400
    store.refresh_from_db()
    assert store.tenant_id == first.pk


def test_personal_project_memory_does_not_take_a_team_default(user, spaces):
    from website_generator.models import GeneratedSite
    from website_generator.site_factory.project_agent import ensure_project_rag_collection, resolve_rag_status
    _, tenant, _ = spaces
    site = GeneratedSite.objects.create(created_by=user, name='Personal project', model_path='registered.pt', output_dir='unused')
    team_store = VectorStore.objects.create(owner=user, tenant=tenant, name='Team default', store_type='memory', is_default=True)
    assert ensure_project_rag_collection(str(site.pk), user) is None
    assert resolve_rag_status(site, user) == 'missing'
    personal = VectorStore.objects.create(owner=user, name='Personal fallback', store_type='memory')
    collection = ensure_project_rag_collection(str(site.pk), user)
    assert collection.tenant_id is None and collection.vector_store_id == personal.pk != team_store.pk


def test_demo_store_helper_preserves_same_named_team_store_and_team_default(user, spaces):
    from features.management.commands.seed_demo_data import Command
    _, tenant, _ = spaces
    team_store = VectorStore.objects.create(owner=user, tenant=tenant, name='演示向量存储', store_type='memory', is_default=True)
    # Exercise only this helper against isolated fixtures, never run the seed command.
    Command()._seed_vector_store(user)
    team_store.refresh_from_db()
    assert team_store.store_type == 'memory' and team_store.is_default
    assert VectorStore.objects.filter(owner=user, tenant__isnull=True, name='演示向量存储', is_default=True).exists()


def test_team_project_memory_derives_real_site_space_and_refuses_revoked_or_injected_space(user, spaces):
    from rest_framework.exceptions import PermissionDenied, ValidationError
    from website_generator.models import GeneratedSite
    from website_generator.site_factory.project_agent import ensure_project_rag_collection
    _, first, second = spaces
    private = VectorStore.objects.create(owner=user, name='Personal default', store_type='memory', is_default=True)
    site = GeneratedSite.objects.create(created_by=user, tenant=first, name='Team project', model_path='registered.pt', output_dir='unused')
    with pytest.raises(ValidationError):
        ensure_project_rag_collection(str(site.pk), user, tenant=second)
    collection = ensure_project_rag_collection(str(site.pk), user, tenant=first)
    assert collection.tenant_id == first.pk and collection.vector_store.tenant_id == first.pk
    assert collection.vector_store_id != private.pk
    assert collection.owner_id == collection.vector_store.owner_id == user.pk
    TenantMembership.objects.filter(user=user, tenant=first).update(is_active=False)
    with pytest.raises(PermissionDenied):
        ensure_project_rag_collection(str(site.pk), user, tenant=first)
    assert DocumentCollection.objects.count() == 1


@pytest.mark.parametrize('bad_binding', ['collection_space', 'store_space'])
def test_legacy_cross_space_project_memory_is_rejected_without_rebinding(user, spaces, bad_binding):
    from rest_framework.exceptions import ValidationError
    from website_generator.models import GeneratedSite
    from website_generator.site_factory.project_agent import ensure_project_rag_collection
    _, first, _ = spaces
    personal = VectorStore.objects.create(owner=user, name='Old private', store_type='memory', is_default=True)
    old = DocumentCollection.objects.create(owner=user, tenant=first if bad_binding == 'store_space' else None,
        name='Old project memory', vector_store=personal)
    site = GeneratedSite.objects.create(created_by=user, tenant=first, name='Legacy team project', model_path='registered.pt',
        output_dir='unused', rag_collection_id=old.pk)
    with pytest.raises(ValidationError, match='重建'):
        ensure_project_rag_collection(str(site.pk), user, old.pk, tenant=first)
    site.refresh_from_db(); old.refresh_from_db()
    assert site.rag_collection_id == old.pk and old.vector_store_id == personal.pk
    assert DocumentCollection.objects.count() == VectorStore.objects.count() == 1


def test_real_project_agent_http_refuses_legacy_memory_before_any_file_or_model_operation(user, authenticated_client, spaces, monkeypatch):
    from website_generator.models import GeneratedSite
    _, tenant, _ = spaces
    private = VectorStore.objects.create(owner=user, name='Private old store', store_type='memory')
    old = DocumentCollection.objects.create(owner=user, vector_store=private, name='Private old memory')
    site = GeneratedSite.objects.create(created_by=user, tenant=tenant, name='Legacy team site', model_path='registered.pt',
        output_dir='must-not-be-opened', rag_collection_id=old.pk, status='completed')
    invoked = []
    def reject_external(**kwargs):
        invoked.append(kwargs)
        raise AssertionError('Legacy memory must be rejected before project editing.')
    monkeypatch.setattr('website_generator.site_factory.project_agent.process_agent_message', reject_external)
    response = authenticated_client.post(f'/api/v1/website-generator/{site.pk}/agent/message/', {'content': 'Please edit'}, format='json')
    assert response.status_code == 400, response.content.decode()
    assert response.data['error_type'] == 'project_memory_scope' and '重建' in response.data['error']
    assert invoked == []
    site.refresh_from_db()
    assert site.status == 'completed' and site.rag_collection_id == old.pk
    assert old.documents.count() == 0 and DocumentCollection.objects.count() == 1


def test_real_team_project_bridge_appends_only_to_its_team_memory(user, spaces, monkeypatch, tmp_path):
    from website_generator.models import GeneratedSite
    from website_generator.site_factory.project_agent import run_agent_for_site
    _, tenant, _ = spaces
    site = GeneratedSite.objects.create(created_by=user, tenant=tenant, name='Team memory bridge', model_path='registered.pt',
        output_dir=str(tmp_path / 'project'), status='completed')
    monkeypatch.setattr('website_generator.site_factory.project_agent.process_agent_message',
        lambda **kwargs: {'success': True, 'reply': 'Workflow evidence remains in the team.', 'files_changed': [], 'qa_triggered': False})
    result = run_agent_for_site(site, 'Remember the workflow.', user=user, sync_system_agent=False)
    assert result['success'] and result['rag_status'] == 'synced'
    site.refresh_from_db()
    collection = DocumentCollection.objects.get(pk=site.rag_collection_id)
    assert collection.tenant_id == collection.vector_store.tenant_id == tenant.pk
    assert collection.documents.get().status == 'completed'
    assert 'Remember the workflow.' in collection.documents.get().content
