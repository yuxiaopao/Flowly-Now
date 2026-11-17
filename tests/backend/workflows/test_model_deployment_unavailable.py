"""Unimplemented deployment never becomes a real workflow or release success."""
import copy

import pytest

from applications.models import ApplicationRequest, ApplicationRelease
from workflows.models import Workflow, Node, Edge, WorkflowExecution
from workflows.services.langchain_service import LangChainService


@pytest.mark.parametrize('platform', ['local', 'sagemaker', 'lambdagpu', 'triton'])
def test_each_saved_deployment_platform_fails_explicitly_without_mutating_configuration(platform):
    configuration = {'platform': platform, 'modelPath': 'registered-model.pt', 'endpointType': 'realtime',
        'autoscaling': True, 'minInstances': 2, 'maxInstances': 4}
    original = copy.deepcopy(configuration)
    result = LangChainService().run_model_deployment_node(configuration, {'model_path': 'upstream-model.pt'})
    assert result['success'] is False
    assert result['error_type'] == 'deployment_not_configured'
    assert result['error'] and 'output' not in result
    assert configuration == original


@pytest.mark.parametrize('platform', ['unknown-provider', '', None, [], {}])
def test_unknown_or_malformed_platform_is_not_a_deployment(platform):
    result = LangChainService().run_model_deployment_node({'platform': platform}, {})
    assert result['success'] is False and result['error_type'] == 'unsupported_platform'
    assert 'output' not in result


def test_default_local_platform_is_also_unconfigured():
    result = LangChainService().run_model_deployment_node({}, {})
    assert result['success'] is False and result['error_type'] == 'deployment_not_configured'


@pytest.mark.django_db
@pytest.mark.parametrize('platform', ['local', 'sagemaker', 'lambdagpu', 'triton'])
def test_real_http_preflight_readiness_and_application_test_reject_deployment(user, authenticated_client, platform):
    workflow = Workflow.objects.create(owner=user, name=f'Unconfigured deployment {platform}')
    first = Node.objects.create(workflow=workflow, node_type='start', name='Start')
    deployment = Node.objects.create(workflow=workflow, node_type='model_deployment', name='Deploy model',
        config={'platform': platform, 'modelPath': 'registered-model.pt', 'autoscaling': True, 'minInstances': 2, 'maxInstances': 4})
    final = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=first, target_node=deployment)
    Edge.objects.create(workflow=workflow, source_node=deployment, target_node=final)
    original = copy.deepcopy(deployment.config)
    advertised = authenticated_client.get('/api/v1/workflows/nodes/available_types/')
    assert advertised.status_code == 200
    assert any(row['type'] == 'model_deployment' and row['supported'] is False for row in advertised.data)
    workflow_url = f'/api/v1/workflows/{workflow.pk}/'
    validation = authenticated_client.post(workflow_url+'validate/', {}, format='json')
    assert validation.status_code == 200
    assert validation.data['valid'] is False
    assert any(row['node_id'] == str(deployment.pk) and row['code'] == 'unsupported_integration'
               for row in validation.data['node_issues'])
    rejected = authenticated_client.post(workflow_url+'execute/', {'input_data': {}, 'is_async': False}, format='json')
    assert rejected.status_code == 400 and rejected.data['code'] == 'workflow_validation'
    assert not WorkflowExecution.objects.exists()

    created = authenticated_client.post('/api/v1/applications/', {'name': 'Preserved deployment configuration',
        'kind': 'workflow', 'draft': {'workflow_id': str(workflow.pk)}}, format='json')
    assert created.status_code == 201, created.content.decode()
    app_id = created.json()['data']['id']
    base = f'/api/v1/applications/{app_id}/'
    readiness = authenticated_client.get(base+'readiness/')
    assert readiness.status_code == 200
    prepared = readiness.json()['data']['draft']
    assert prepared['configuration_ready'] is False
    assert any(row['status'] == 'blocked' for row in prepared['checks'])
    attempted = authenticated_client.post(base+'test/', {'input_data': {}}, format='json')
    assert attempted.status_code == 422, attempted.content.decode()
    request = ApplicationRequest.objects.get(application_id=app_id)
    assert request.status == 'failed' and request.error_code == 'workflow_validation'
    assert request.workflow_execution_id is None and request.output_data is None
    assert authenticated_client.post(base+'publish/', {}, format='json').status_code == 409
    assert not ApplicationRelease.objects.filter(application_id=app_id).exists()
    deployment.refresh_from_db()
    assert deployment.config == original
