"""Real source ownership and authorized, atomic project reconstruction."""
from unittest.mock import patch
import pytest
from website_generator.models import GeneratedSite
from workflows.models import Workflow, WorkflowExecution, Node, NodeExecution, Edge

pytestmark = pytest.mark.django_db


def site_for(user, **overrides):
    values = dict(name='安全识别', created_by=user, website_type='detection', model_path='/weights/best.pt',
        best_weight_path='/weights/best.pt', labels=['helmet'], output_dir='/old/site', status='completed',
        site_brief={'wizard': {'siteName': '安全识别', 'usageDescription': '识别安全帽', 'mysqlPassword': 'do-not-copy'}},
        theme_profile={'primaryColor': '#06b6d4'}, required_features=['imageRecognition', 'historyRecords'],
        environment_config={'dbEngine': 'mysql', 'databasePassword': 'do-not-copy', 'outputDir': '/old/site'})
    values.update(overrides)
    return GeneratedSite.objects.create(**values)


def running_source(user):
    workflow = Workflow.objects.create(owner=user, name='Actual site workflow')
    node = Node.objects.create(workflow=workflow, name='建站', node_type='website_generator', config={})
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user, status='running')
    NodeExecution.objects.create(execution=execution, node=node, node_version=1, status='running')
    return workflow, node, execution


def test_generator_records_only_the_current_server_execution_source(user, authenticated_client, settings, tmp_path):
    from workflows.services.langchain_service import LangChainService
    workflow, node, execution = running_source(user)
    service = object.__new__(LangChainService)
    service.user_id = user.pk
    settings.WEBSITE_GENERATOR_OUTPUT_ROOT = str(tmp_path)
    with patch('threading.Thread'):
        result = service.run_website_generator_node({'modelPath': '/weights/best.pt', 'waitForCompletion': False,
            'source_workflow_id': 'forged', 'source_node_id': 'forged'}, {'metadata': {
            'workflow_id': str(workflow.pk), 'execution_id': str(execution.pk), 'node_id': str(node.pk)}})
    assert result['success'] is True
    site = GeneratedSite.objects.get(pk=result['output']['site_id'])
    assert (site.created_by_id, site.tenant_id) == (user.pk, workflow.tenant_id)
    assert (site.source_workflow_id, site.source_node_id, site.source_execution_id) == (workflow.pk, node.pk, execution.pk)
    response = authenticated_client.get(f'/api/v1/website-generator/{site.pk}/')
    assert response.status_code == 200
    assert response.data['source']['workflow_id'] == str(workflow.pk)
    assert response.data['source']['can_edit'] is True


def test_forged_or_stopped_execution_cannot_claim_a_site_source(user):
    from website_generator.provenance import trusted_site_source
    workflow, node, execution = running_source(user)
    execution.status = 'completed'
    execution.save(update_fields=['status'])
    with pytest.raises(Exception, match='当前正在执行'):
        trusted_site_source(user.pk, {'metadata': {'workflow_id': str(workflow.pk), 'execution_id': str(execution.pk), 'node_id': str(node.pk)}})
    assert GeneratedSite.objects.count() == 0


def test_source_identifiers_are_hidden_when_the_workflow_is_not_visible(user, authenticated_client, admin_user):
    foreign = Workflow.objects.create(owner=admin_user, name='Private foreign graph')
    site = site_for(user, source_workflow=foreign)
    response = authenticated_client.get(f'/api/v1/website-generator/{site.pk}/')
    assert response.status_code == 200
    assert response.data['source']['status'] == 'unavailable'
    assert 'workflow_id' not in response.data['source']
    assert str(foreign.pk) not in str(response.data['source'])


def test_historical_site_rebuild_creates_real_weight_bound_graph_and_is_idempotent(user, authenticated_client):
    site = site_for(user)
    before = Workflow.objects.count()
    url = f'/api/v1/website-generator/{site.pk}/rebuild-workflow/'
    first = authenticated_client.post(url, {}, format='json', HTTP_IDEMPOTENCY_KEY='site-copy-1')
    assert first.status_code == 201
    workflow = Workflow.objects.get(pk=first.data['workflow_id'])
    assert workflow.owner_id == user.pk and workflow.tenant_id == site.tenant_id
    assert workflow.config['source_site_id'] == str(site.pk)
    config = workflow.nodes.get(node_type='website_generator').config
    assert config['modelPath'] == '/weights/best.pt'
    assert config['labels'] == ['helmet']
    assert config['wizard']['siteName'] == '安全识别'
    assert config['requiredFeatures'] == site.required_features
    assert config['sourceSiteId'] == str(site.pk)
    assert 'do-not-copy' not in str(config)
    assert '/old/site' not in str(config)
    assert workflow.nodes.count() == 4 and workflow.edges.count() == 3
    second = authenticated_client.post(url, {}, format='json', HTTP_IDEMPOTENCY_KEY='site-copy-1')
    assert second.status_code == 200 and second.data['workflow_id'] == first.data['workflow_id']
    assert Workflow.objects.count() == before + 1


def test_foreign_site_rebuild_is_denied_without_creating_a_graph(user, authenticated_client, admin_user):
    site = site_for(admin_user)
    before = Workflow.objects.count()
    result = authenticated_client.post(f'/api/v1/website-generator/{site.pk}/rebuild-workflow/', {}, format='json', HTTP_IDEMPOTENCY_KEY='foreign')
    assert result.status_code == 404
    assert Workflow.objects.count() == before


def test_rebuild_rolls_back_all_nodes_on_graph_creation_failure(user, authenticated_client):
    site = site_for(user)
    before = (Workflow.objects.count(), Node.objects.count(), Edge.objects.count())
    from website_generator.provenance import rebuild_site_workflow
    with patch.object(Node.objects, 'create', side_effect=RuntimeError('injected graph failure')):
        with pytest.raises(RuntimeError, match='injected graph failure'):
            rebuild_site_workflow(site, user, 'failed-copy')
    assert (Workflow.objects.count(), Node.objects.count(), Edge.objects.count()) == before


def test_clients_cannot_write_trusted_source_fields(authenticated_client, workflow):
    response = authenticated_client.post('/api/v1/website-generator/', {'name': 'forged', 'model_path': '/model.pt',
        'source_workflow_id': str(workflow.pk)}, format='json')
    assert response.status_code == 400
    assert GeneratedSite.objects.count() == 0


def test_visible_team_viewer_cannot_rebuild_or_mutate_site(user, authenticated_client, admin_user):
    from tenants.models import Tenant, TenantMembership
    tenant = Tenant.objects.create(owner=admin_user, name='Delivery team', slug='delivery-team', status='active')
    TenantMembership.objects.create(tenant=tenant, user=user, role='viewer', is_active=True)
    site = site_for(admin_user, tenant=tenant)
    url = f'/api/v1/website-generator/{site.pk}/'
    assert authenticated_client.get(url).status_code == 200
    assert authenticated_client.post(url + 'rebuild-workflow/', {}, format='json', HTTP_IDEMPOTENCY_KEY='viewer').status_code == 403
    assert authenticated_client.patch(url, {'name': 'changed'}, format='json').status_code == 403


def test_team_admin_rebuild_preserves_the_actual_site_space(user, authenticated_client, admin_user):
    from tenants.models import Tenant, TenantMembership
    tenant = Tenant.objects.create(owner=admin_user, name='Team copy', slug='team-copy', status='active')
    TenantMembership.objects.create(tenant=tenant, user=user, role='admin', is_active=True)
    site = site_for(admin_user, tenant=tenant)
    response = authenticated_client.post(f'/api/v1/website-generator/{site.pk}/rebuild-workflow/', {}, format='json', HTTP_IDEMPOTENCY_KEY='team-copy')
    assert response.status_code == 201
    workflow = Workflow.objects.get(pk=response.data['workflow_id'])
    assert workflow.tenant_id == tenant.pk and workflow.owner_id == user.pk


def test_hard_deleted_source_is_reported_as_unavailable_not_never_recorded(user, authenticated_client):
    workflow = Workflow.objects.create(owner=user, name='Deleted original')
    site = site_for(user, source_workflow=workflow, source_recorded=True)
    workflow.delete()
    response = authenticated_client.get(f'/api/v1/website-generator/{site.pk}/')
    assert response.status_code == 200
    assert response.data['source']['status'] == 'unavailable'
    assert 'workflow_id' not in response.data['source']


def test_foreign_training_manifest_cannot_be_imported_through_site_generation(user, authenticated_client, admin_user):
    from training.models import TrainingJob
    job = TrainingJob.objects.create(name='foreign weights', created_by=admin_user, training_kind='yolo', status='completed')
    response = authenticated_client.post('/api/v1/website-generator/generate/', {'name': 'foreign', 'training_run_id': str(job.pk),
        'model_artifact_manifest': {'trainingJobId': str(job.pk), 'bestWeightPath': '/foreign/best.pt'}}, format='json')
    assert response.status_code == 403
    assert GeneratedSite.objects.count() == 0


def test_retrieval_rebuild_preserves_public_artifacts_and_custom_site_configuration(user, authenticated_client):
    site = site_for(user, website_type='clip_retrieval', model_path='', best_weight_path='',
        model_artifact_manifest={'trainingKind': 'clip_ret', 'exportedArtifacts': {'index_dir': '/qa/index'},
            'metricHistory': [{'epoch': 1, 'recall': .9}], 'siteHints': {'displayMode': 'retrieval_gallery'}},
        site_brief={'scenario': '产品检索', 'custom_config': {'Customer_ID': 'keep', 'api_key': 'do-not-copy'},
            'wizard': {'siteName': '检索站', 'exampleQueries': '相似产品'}},
        theme_profile={'primaryColor': '#06b6d4', 'customTypography': 'compact'})
    response = authenticated_client.post(f'/api/v1/website-generator/{site.pk}/rebuild-workflow/', {}, format='json', HTTP_IDEMPOTENCY_KEY='retrieval-copy')
    assert response.status_code == 201
    config = Workflow.objects.get(pk=response.data['workflow_id']).nodes.get(node_type='website_generator').config
    assert config['indexDir'] == '/qa/index'
    assert config['modelArtifactManifest']['metricHistory'] == [{'epoch': 1, 'recall': .9}]
    assert config['siteBrief']['scenario'] == '产品检索'
    assert config['siteBrief']['custom_config'] == {'Customer_ID': 'keep'}
    assert config['themeProfile']['customTypography'] == 'compact'
