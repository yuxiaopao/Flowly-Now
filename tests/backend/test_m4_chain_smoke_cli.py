"""The manual smoke CLI uses real owner/execution records; generation is external."""
import importlib.util
import os
import subprocess
import sys
import threading
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'Backend' / 'scripts' / 'm4_chain_smoke_test.py'


def load_script():
    spec = importlib.util.spec_from_file_location('m4_chain_smoke_cli', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_help_requires_an_explicit_actor_without_initializing_django():
    environment = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'deliberately_missing_settings'}
    result = subprocess.run([sys.executable, str(SCRIPT), '--help'], env=environment, capture_output=True, text=True)
    assert result.returncode == 0
    assert '--user-id' in result.stdout and '--user-email' in result.stdout
    result = subprocess.run([sys.executable, str(SCRIPT)], env=environment, capture_output=True, text=True)
    assert result.returncode == 2
    assert 'required' in result.stderr and 'ModuleNotFoundError' not in result.stderr


@pytest.fixture
def external_generation(monkeypatch):
    from workflows.services.langchain_service import LangChainService
    import website_generator.generators
    import website_generator.views

    class FakeGenerator:
        def generate(self):
            return {'success': True, 'generated_files': ['fixture.html']}

    original_start = threading.Thread.start

    def start_generation_inline(thread):
        target = getattr(thread, '_target', None)
        if target and target.__name__ == 'run_gen':
            thread.run()
        else:
            original_start(thread)

    monkeypatch.setattr(threading.Thread, 'start', start_generation_inline)
    monkeypatch.setattr(LangChainService, '_detect_gpu', lambda self: {'available': False})
    monkeypatch.setattr(website_generator.generators, 'get_generator', lambda *args, **kwargs: FakeGenerator())
    monkeypatch.setattr(website_generator.views, 'register_site_codegraph', lambda site: None)


def test_external_generation_boundary_preserves_the_standard_thread_type(external_generation):
    # Torch and other libraries use Thread in isinstance during lazy imports.
    assert isinstance(threading.current_thread(), threading.Thread)


@pytest.mark.django_db
def test_ordinary_user_smoke_records_trusted_training_and_site_sources(user, tmp_path, external_generation):
    from training.models import TrainingJob
    from website_generator.models import GeneratedSite
    result = load_script().run_smoke(user, tmp_path)
    assert result['passed'], [name for name, passed in result['checks'].items() if not passed]
    job = TrainingJob.objects.get(pk=result['training_run_id'])
    site = GeneratedSite.objects.get(pk=result['site_id'])
    assert not user.is_superuser
    assert job.created_by_id == site.created_by_id == user.pk
    assert str(job.execution_id) == result['execution_id']
    assert str(job.workflow_id) == result['workflow_id']
    assert job.node.node_type == 'clip_retrieval'
    assert site.source_execution_id == job.execution_id


@pytest.mark.django_db
@pytest.mark.parametrize('team', [False, True])
def test_real_classification_dispatcher_inherits_actor_space_and_site_source(user, admin_user, tmp_path, monkeypatch, external_generation, team):
    from tenants.models import Tenant, TenantMembership
    from training.models import TrainingJob
    from website_generator.models import GeneratedSite
    from workflows.models import Workflow, WorkflowExecution, Node, Edge
    from workflows.services.workflow_executor import WorkflowExecutor
    import training.clip_service

    calls = []

    def classify(dataset, names, output, **kwargs):
        calls.append((dataset, names))
        return {'success': True, 'model_path': str(tmp_path / 'model.json'), 'class_names': names,
                'metrics': {'accuracy': .9}}

    monkeypatch.setattr(training.clip_service, 'run_zero_shot_classification', classify)
    tenant = Tenant.objects.create(owner=admin_user, name='CLIP team', slug='clip-team', status='active') if team else None
    if tenant:
        TenantMembership.objects.create(tenant=tenant, user=user, role='member', is_active=True)
    workflow = Workflow.objects.create(owner=admin_user if team else user, tenant=tenant, name='Classification source')
    previous, nodes = None, {}
    for kind, config in (('start', {}), ('clip_classification', {'classNames': ['cat', 'dog'],
        'mode': 'zero_shot', 'datasetPath': str(tmp_path), 'outputDir': str(tmp_path / 'classification'),
        'created_by': admin_user.pk, 'tenant_id': 'forged'}), ('website_generator', {
        'outputDir': str(tmp_path / 'site'), 'waitForCompletion': False}), ('end', {})):
        node = Node.objects.create(workflow=workflow, node_type=kind, name=kind, config=config)
        nodes[kind] = node
        if previous:
            Edge.objects.create(workflow=workflow, source_node=previous, target_node=node)
        previous = node
    execution = WorkflowExecution.objects.create(workflow=workflow, tenant=tenant, version=workflow.version,
        triggered_by=user, input_data={'metadata': {'execution_id': 'business-data', 'node_id': 'opaque'}}, trigger_type='manual')
    WorkflowExecutor(workflow, execution).execute()
    execution.refresh_from_db()
    assert execution.status == 'completed', execution.error_message
    assert calls == [(str(tmp_path), ['cat', 'dog'])]
    job = TrainingJob.objects.get(execution=execution)
    site = GeneratedSite.objects.get(source_execution=execution)
    assert not user.is_superuser
    assert job.created_by_id == site.created_by_id == user.pk
    assert job.tenant_id == site.tenant_id == workflow.tenant_id
    assert job.workflow_id == site.source_workflow_id == workflow.pk
    assert job.node_id == nodes['clip_classification'].pk
    assert site.source_node_id == nodes['website_generator'].pk


@pytest.mark.django_db
@pytest.mark.parametrize('kind', ['clip_classification', 'clip_retrieval'])
def test_foreign_execution_rejected_before_clip_job_or_provider(user, admin_user, monkeypatch, kind):
    from rest_framework.exceptions import PermissionDenied
    from training.models import TrainingJob
    from workflows.models import Workflow, WorkflowExecution, Node, NodeExecution
    from workflows.services.langchain_service import LangChainService

    workflow = Workflow.objects.create(owner=admin_user, name='Foreign CLIP workflow')
    node = Node.objects.create(workflow=workflow, node_type=kind, name=kind)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=admin_user, status='running')
    NodeExecution.objects.create(execution=execution, node=node, node_version=1, status='running')
    service = object.__new__(LangChainService)
    service.user_id = user.pk
    monkeypatch.setattr(service, '_detect_gpu', lambda: pytest.fail('An unauthorized source reached the provider boundary'))
    with pytest.raises(PermissionDenied, match='当前正在执行'):
        getattr(service, f'run_{kind}_node')({'created_by': user.pk}, {'_execution': {'metadata': {
            'workflow_id': str(workflow.pk), 'execution_id': str(execution.pk), 'node_id': str(node.pk)}}})
    assert not TrainingJob.objects.exists()


@pytest.mark.django_db
def test_ordinary_website_dispatcher_prioritizes_internal_source_over_business_metadata(user, tmp_path, external_generation):
    from website_generator.models import GeneratedSite
    from workflows.models import Workflow, WorkflowExecution, Node, Edge
    from workflows.services.workflow_executor import WorkflowExecutor

    workflow = Workflow.objects.create(owner=user, name='Direct site dispatcher')
    start = Node.objects.create(workflow=workflow, node_type='start', name='Start')
    site_node = Node.objects.create(workflow=workflow, node_type='website_generator', name='Site', config={
        'modelPath': '/fixture/model.pt', 'outputDir': str(tmp_path / 'site'), 'waitForCompletion': False})
    end = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=start, target_node=site_node)
    Edge.objects.create(workflow=workflow, source_node=site_node, target_node=end)
    opaque = {'execution_id': 'customer-value', 'workflow_id': 'customer-value', 'node_id': 'customer-value'}
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user, input_data={'metadata': opaque})
    WorkflowExecutor(workflow, execution).execute()
    execution.refresh_from_db()
    assert execution.status == 'completed', execution.error_message
    site = GeneratedSite.objects.get(source_execution=execution)
    assert site.created_by_id == user.pk and site.source_node_id == site_node.pk
    assert execution.input_data['metadata'] == opaque
