"""Local readiness reflects actual stored content and never fabricates connectivity."""
import json
from unittest.mock import patch
import pytest
from django.test import override_settings
from applications.models import Application
from rag.models import DocumentCollection, VectorStore, Document, Chunk
from rag.pipeline import index_signature
from workflows.models import Workflow, Node, Edge

pytestmark = pytest.mark.django_db


def endpoint(app):
    return f'/api/v1/applications/{app.pk}/readiness/'


@pytest.fixture
def knowledge(user):
    store = VectorStore.objects.create(owner=user, name='Readiness store', store_type='memory')
    collection = DocumentCollection.objects.create(owner=user, name='Readiness collection', vector_store=store, retrieval_mode='keyword')
    app = Application.objects.create(owner=user, name='Readiness app', kind='knowledge',
        draft={'collection_id': str(collection.pk), 'system_prompt': 'Use evidence', 'top_k': 5, 'min_similarity': 0})
    return app, collection


def data(response):
    assert response.status_code == 200, response.content.decode()
    return response.json()['data']


def test_empty_knowledge_and_absent_chat_are_blocked_without_network(authenticated_client, knowledge):
    app, _ = knowledge
    with override_settings(RAG_CHAT_MODEL='gpt-fixture', RAG_CHAT_API_KEY='', OPENAI_API_KEY=''), patch('httpx.Client.send', side_effect=AssertionError('Unexpected network request')) as network:
        result = data(authenticated_client.get(endpoint(app)))
    network.assert_not_called()
    assert result['draft']['configuration_ready'] is False
    assert {row['code'] for row in result['draft']['checks'] if row['status'] == 'blocked'} == {'content', 'chat'}
    assert result['draft']['connection_verified'] is False and result['active_release'] is None


def test_keyword_needs_no_embedding_and_uses_real_completed_chunks(authenticated_client, knowledge):
    app, collection = knowledge
    document = Document.objects.create(collection=collection, title='Real content', content='Evidence', status='completed')
    Chunk.objects.create(document=document, content='Evidence', vector_id='one')
    Document.objects.create(collection=collection, title='Still processing', content='More', status='processing')
    with override_settings(RAG_CHAT_MODEL='gpt-fixture', RAG_CHAT_API_KEY='private-fixture-secret', RAG_EMBEDDING_API_KEY='', OPENAI_API_KEY=''):
        result = data(authenticated_client.get(endpoint(app)))
    draft = result['draft']
    assert draft['configuration_ready'] is True and draft['knowledge']['available_chunks'] == 1
    assert draft['knowledge']['processing_documents'] == 1
    assert 'embedding' not in draft and draft['chat']['connection_verified'] is False
    assert 'private-fixture-secret' not in json.dumps(result)
    assert any(row['code'] == 'partial_content' and row['status'] == 'warning' for row in draft['checks'])


def test_stale_semantic_index_reports_reprocessing(authenticated_client, knowledge):
    app, collection = knowledge
    collection.retrieval_mode, collection.embedding_model = 'semantic', 'openai:fixture-embedding'
    collection.save()
    document = Document.objects.create(collection=collection, title='Semantic', content='Evidence', status='completed')
    chunk = Chunk.objects.create(document=document, content='Evidence', vector_id='semantic', embedding=[1, 0], metadata={})
    with override_settings(RAG_CHAT_MODEL='gpt-fixture', RAG_CHAT_API_KEY='fixture', RAG_EMBEDDING_API_KEY='embedding-fixture'):
        result = data(authenticated_client.get(endpoint(app)))['draft']
        assert any(row['code'] == 'index' and row['status'] == 'blocked' for row in result['checks'])
        chunk.metadata = {'index_signature': index_signature(collection)}
        chunk.save(update_fields=['metadata'])
        result = data(authenticated_client.get(endpoint(app)))['draft']
    assert result['configuration_ready'] is True and result['embedding']['connection_verified'] is False


def test_default_ollama_url_is_configuration_not_proof_of_running_server(authenticated_client, knowledge):
    app, collection = knowledge
    doc = Document.objects.create(collection=collection, title='Ready', content='Evidence', status='completed')
    Chunk.objects.create(document=doc, content='Evidence')
    with override_settings(RAG_CHAT_MODEL='ollama:fixture-model', RAG_CHAT_API_KEY='', OPENAI_API_KEY='', RAG_CHAT_BASE_URL=''):
        result = data(authenticated_client.get(endpoint(app)))['draft']
    assert result['configuration_ready'] is True
    assert result['chat']['provider'] == 'ollama' and result['connection_verified'] is False
    assert any(row['code'] == 'upstream' and row['status'] == 'not_checked' for row in result['checks'])


def test_workflow_required_inputs_are_described_without_false_blocker(authenticated_client, user):
    workflow = Workflow.objects.create(owner=user, name='Required input')
    first = Node.objects.create(workflow=workflow, node_type='start', name='Start')
    required = Node.objects.create(workflow=workflow, node_type='input', name='Customer', config={'variable_name': 'Customer_ID', 'required': True})
    last = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=first, target_node=required)
    Edge.objects.create(workflow=workflow, source_node=required, target_node=last)
    app = Application.objects.create(owner=user, name='Input app', kind='workflow', draft={'workflow_id': str(workflow.pk)})
    result = data(authenticated_client.get(endpoint(app)))['draft']
    assert result['configuration_ready'] is True and result['inputs'][0] == {'name': 'Customer_ID', 'required': True, 'has_default': False}
    required.node_type = 'unknown_node'
    required.save(update_fields=['node_type'])
    result = data(authenticated_client.get(endpoint(app)))['draft']
    assert result['configuration_ready'] is False


def test_foreign_collection_and_foreign_store_are_not_exposed(authenticated_client, knowledge, admin_user):
    app, collection = knowledge
    collection.vector_store.owner = admin_user
    collection.vector_store.save(update_fields=['owner'])
    result = data(authenticated_client.get(endpoint(app)))['draft']
    assert result['configuration_ready'] is False and 'source' not in result
    assert result['checks'][0]['status'] == 'blocked'
    collection.owner = admin_user
    collection.save(update_fields=['owner'])
    result = data(authenticated_client.get(endpoint(app)))['draft']
    assert 'Readiness collection' not in json.dumps(result)


def test_unauthenticated_or_foreign_application_readiness_rejected(api_client, authenticated_client, knowledge, admin_user):
    app, _ = knowledge
    assert api_client.get(endpoint(app)).status_code == 401
    app.owner = admin_user
    app.save(update_fields=['owner'])
    assert authenticated_client.get(endpoint(app)).status_code == 404


def test_queued_default_execution_still_runs(user):
    from workflows.models import WorkflowExecution
    from workflows.services.workflow_executor import WorkflowExecutor
    workflow = Workflow.objects.create(owner=user, name='Legacy direct execution')
    start = Node.objects.create(workflow=workflow, node_type='start', name='Start')
    end = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=start, target_node=end)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user)
    assert execution.status == 'queued'
    assert WorkflowExecutor(workflow, execution).execute().status == 'completed'


def test_published_snapshot_readiness_rechecks_owner_permission(authenticated_client, user, admin_user):
    from rest_framework.test import APIClient
    workflow = Workflow.objects.create(owner=user, name='Published workflow')
    start = Node.objects.create(workflow=workflow, node_type='start', name='Start')
    end = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=start, target_node=end)
    app = Application.objects.create(owner=user, name='Published readiness', kind='workflow', draft={'workflow_id': str(workflow.pk)})
    base = f'/api/v1/applications/{app.pk}/'
    assert authenticated_client.post(base+'test/', {'input_data': {}}, format='json').status_code == 200
    assert authenticated_client.post(base+'publish/', {}, format='json').status_code == 201
    user.is_active = False
    user.save(update_fields=['is_active'])
    administrator = APIClient(); administrator.force_authenticate(admin_user)
    result = data(administrator.get(endpoint(app)))
    assert result['draft']['configuration_ready'] is False
    assert result['active_release']['configuration_ready'] is False
    assert result['active_release']['checks'][0]['status'] == 'blocked'
