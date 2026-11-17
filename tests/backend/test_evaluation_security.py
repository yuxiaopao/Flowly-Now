"""Real model artifacts, owned data, routed HTTP and persistent evaluation state."""
from pathlib import Path
import uuid

import pytest
from django.core.files.base import ContentFile

pytestmark = pytest.mark.django_db(transaction=True)
BASE = '/api/v1/evaluations/'


@pytest.fixture
def evaluation_assets(user, settings, tmp_path):
    import torch
    from datasets.models import Dataset
    from training.models import TrainingJob
    from workflows.models import Workflow, WorkflowExecution, Node, NodeExecution

    settings.BASE_DIR = tmp_path
    settings.MEDIA_ROOT = tmp_path / 'media'
    workflow = Workflow.objects.create(owner=user, name='Actual training source')
    node = Node.objects.create(workflow=workflow, name='Training', node_type='model_training')
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user, status='completed')
    job = TrainingJob.objects.create(created_by=user, workflow=workflow, node=node, execution=execution,
        name='Tiny classifier', status='completed', framework='pytorch', model_type='classifier',
        training_kind='generic', class_names=['negative', 'positive'])
    output = tmp_path / 'data' / 'training_outputs' / str(job.pk)
    output.mkdir(parents=True)
    filename = output / 'model.pt'
    model = torch.nn.Sequential(torch.nn.Linear(2, 2))
    with torch.no_grad():
        model[0].weight.copy_(torch.tensor([[-1., 0.], [1., 0.]]))
        model[0].bias.zero_()
    torch.save({'model_state_dict': model.state_dict(), 'config': {'input_dim': 2, 'hidden_dims': [],
        'output_dim': 2, 'dropout': 0}}, filename)
    job.model_path = str(filename)
    job.save(update_fields=['model_path'])
    NodeExecution.objects.create(execution=execution, node=node, node_version=1, status='completed',
        output_data={'training_run_id': str(job.pk), 'model_path': str(filename)})
    dataset = Dataset.objects.create(created_by=user, name='Actual held-out CSV', source='upload', format='csv', status='ready')
    dataset.file.save('heldout.csv', ContentFile(b'x1,x2,label\n-2,0,negative\n-1,1,negative\n1,0,positive\n2,1,positive\n'))
    return job, dataset, filename


def payload(assets):
    training, dataset, _ = assets
    return {'name': 'Real classifier check', 'training_job_id': str(training.pk), 'dataset_id': str(dataset.pk)}


def test_real_owned_state_dict_and_csv_produce_measured_metrics(authenticated_client, user, evaluation_assets):
    from evaluation.models import EvaluationJob
    response = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    assert response.status_code == 201, response.data
    job_id = response.data['job_id']
    job = EvaluationJob.objects.get(job_id=job_id)
    assert job.created_by_id == user.pk and job.status == 'pending'
    result = authenticated_client.post(f'{BASE}{job_id}/run/', {}, format='json')
    assert result.status_code == 200, result.data
    assert result.data['status'] == 'completed'
    assert result.data['metrics']['accuracy'] == result.data['metrics']['f1'] == 1.0
    assert result.data['metrics']['sample_count'] == 4
    job.refresh_from_db()
    assert job.status == 'completed' and job.completed_at and job.started_at
    assert authenticated_client.post(f'{BASE}{job_id}/run/', {}, format='json').status_code == 409
    dataset = evaluation_assets[1]
    original_id = str(dataset.pk)
    assert authenticated_client.delete(f'/api/v1/datasets/{dataset.pk}/').status_code == 204
    job.refresh_from_db()
    assert job.dataset_id is None and job.status == 'completed'
    assert job.artifact_snapshot['dataset_id'] == original_id
    assert authenticated_client.get(f'{BASE}{job_id}/').data['verification_status'] == 'verified_source_removed'


def test_private_and_legacy_ownerless_jobs_are_not_exposed(user, admin_user, authenticated_client, api_client):
    from evaluation.models import EvaluationJob
    foreign = EvaluationJob.objects.create(job_id='foreign', name='Private', created_by=admin_user, model_path='/private/model.pt')
    orphan = EvaluationJob.objects.create(job_id='orphan', name='Legacy unknown owner', model_path='/old/model.pt')
    assert api_client.get(BASE).status_code == 401
    response = authenticated_client.get(BASE)
    assert response.status_code == 200 and response.data['data']['count'] == 0
    for record in (foreign, orphan):
        url = f'{BASE}{record.job_id}/'
        assert authenticated_client.get(url).status_code == 404
        assert authenticated_client.patch(url, {'name': 'taken'}, format='json').status_code == 404
        assert authenticated_client.delete(url).status_code == 404
        assert authenticated_client.post(url + 'run/', {}, format='json').status_code == 404
    foreign.refresh_from_db()
    assert foreign.name == 'Private'


def test_create_edit_delete_and_old_path_aliases_use_registered_owned_sources(user, authenticated_client, evaluation_assets):
    from evaluation.models import EvaluationJob
    training, dataset, filename = evaluation_assets
    result = authenticated_client.post(BASE, {'name': 'Legacy aliases', 'model_path': str(filename),
        'test_dataset_path': dataset.file.path}, format='json')
    assert result.status_code == 201, result.data
    job = EvaluationJob.objects.get(job_id=result.data['job_id'])
    assert job.training_job_id == training.pk and job.dataset_id == dataset.pk
    url = f'{BASE}{job.job_id}/'
    updated = authenticated_client.patch(url, {'name': 'Renamed'}, format='json')
    assert updated.status_code == 200 and updated.data['name'] == 'Renamed'
    assert authenticated_client.delete(url).status_code == 204
    assert not EvaluationJob.objects.filter(pk=job.pk).exists()


def test_forged_missing_and_cross_owner_artifact_or_data_is_rejected(user, admin_user, authenticated_client, evaluation_assets, tmp_path):
    from evaluation.models import EvaluationJob
    training, dataset, filename = evaluation_assets
    outside = tmp_path / 'outside.pt'
    outside.write_bytes(filename.read_bytes())
    training.model_path = str(outside)
    training.save(update_fields=['model_path'])
    result = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    assert result.status_code == 422 and result.data['error_code'] == 'unmanaged_path'
    training.model_path = str(filename.parent.parent / str(uuid.uuid4()) / 'model.pt')
    Path(training.model_path).parent.mkdir()
    Path(training.model_path).write_bytes(filename.read_bytes())
    training.save(update_fields=['model_path'])
    result = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    assert result.status_code == 422 and result.data['error_code'] == 'untrusted_artifact'
    training.model_path = str(filename)
    training.created_by = admin_user
    training.save(update_fields=['model_path', 'created_by'])
    assert authenticated_client.post(BASE, payload(evaluation_assets), format='json').status_code == 403
    training.created_by = user
    training.save(update_fields=['created_by'])
    dataset.created_by = admin_user
    dataset.save(update_fields=['created_by'])
    assert authenticated_client.post(BASE, payload(evaluation_assets), format='json').status_code == 403
    assert not EvaluationJob.objects.exists()


@pytest.mark.parametrize('content', [b'a,b,label\n', b'a,b,label\n1,,positive\n', b'a,b,label\nNaN,1,positive\n',
    b'a,a,label\n1,2,positive\n', b'a,b,label\n1,2,positive,extra\n'])
def test_malformed_or_empty_samples_fail_persistently_without_fake_metrics(content, authenticated_client, evaluation_assets):
    from evaluation.models import EvaluationJob
    _, dataset, _ = evaluation_assets
    with open(dataset.file.path, 'wb') as output:
        output.write(content)
    created = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    assert created.status_code == 201
    result = authenticated_client.post(f'{BASE}{created.data["job_id"]}/run/', {}, format='json')
    assert result.status_code == 422, result.data
    job = EvaluationJob.objects.get(job_id=created.data['job_id'])
    assert job.status == 'failed' and job.metrics == {} and job.error_code == 'invalid_dataset'
    assert job.started_at and job.completed_at and not job.lease_expires_at


def test_running_claim_conflicts_and_stale_rows_are_explicit_failures(user, authenticated_client, evaluation_assets):
    from datetime import timedelta
    from django.utils import timezone
    from evaluation.models import EvaluationJob
    from evaluation.services import claim
    created = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    job = EvaluationJob.objects.get(job_id=created.data['job_id'])
    claimed = claim(job.pk, user)
    url = f'{BASE}{job.job_id}/'
    assert authenticated_client.post(url + 'run/', {}, format='json').status_code == 409
    assert authenticated_client.patch(url, {'name': 'during run'}, format='json').status_code == 409
    assert authenticated_client.delete(url).status_code == 409
    EvaluationJob.objects.filter(pk=job.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    stale = authenticated_client.get(url)
    assert stale.status_code == 200
    assert stale.data['status'] == 'failed' and stale.data['error_code'] == 'lease_expired'
    assert stale.data['metrics'] == {}
    job.refresh_from_db()
    assert job.claim_token is None and job.completed_at


def test_team_viewer_cannot_create_run_edit_or_delete_and_revocation_is_fresh(user, admin_user, authenticated_client, evaluation_assets):
    from tenants.models import Tenant, TenantMembership
    from evaluation.models import EvaluationJob
    training, dataset, _ = evaluation_assets
    tenant = Tenant.objects.create(owner=admin_user, name='Evaluation team', slug='evaluation-team', status='active')
    membership = TenantMembership.objects.create(tenant=tenant, user=user, role='member', is_active=True)
    training.tenant = dataset.tenant = tenant
    training.save(update_fields=['tenant'])
    dataset.save(update_fields=['tenant'])
    training.workflow.tenant = tenant
    training.workflow.save(update_fields=['tenant'])
    training.execution.tenant = tenant
    training.execution.save(update_fields=['tenant'])
    created = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    assert created.status_code == 201 and created.data['tenant_id'] == tenant.pk
    job = EvaluationJob.objects.get(job_id=created.data['job_id'])
    url = f'{BASE}{job.job_id}/'
    membership.role = 'viewer'
    membership.save(update_fields=['role'])
    assert authenticated_client.get(url).status_code == 200
    assert authenticated_client.post(BASE, payload(evaluation_assets), format='json').status_code == 403
    assert authenticated_client.post(url + 'run/', {}, format='json').status_code == 403
    assert authenticated_client.patch(url, {'name': 'viewer edit'}, format='json').status_code == 403
    assert authenticated_client.delete(url).status_code == 403
    membership.is_active = False
    membership.save(update_fields=['is_active'])
    assert authenticated_client.get(url).status_code == 404


def test_symlink_or_directory_junction_cannot_supply_an_artifact(authenticated_client, evaluation_assets, tmp_path):
    import os
    import subprocess
    training, _, original = evaluation_assets
    outside = tmp_path / 'outside-artifacts'
    outside.mkdir()
    (outside / 'model.pt').write_bytes(original.read_bytes())
    link = original.parent / 'linked'
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        assert os.name == 'nt'
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)], capture_output=True)
        assert result.returncode == 0
    training.model_path = str(link / 'model.pt')
    training.save(update_fields=['model_path'])
    response = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    assert response.status_code == 422 and response.data['error_code'] == 'symlink_forbidden'


def test_child_environment_does_not_inherit_cloud_credentials(monkeypatch, tmp_path):
    from evaluation.services import _child_environment
    monkeypatch.setenv('OPENAI_API_KEY', 'fixture-secret')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'fixture-secret')
    monkeypatch.setenv('DATABASE_URL', 'fixture-secret')
    environment = _child_environment(tmp_path)
    assert 'OPENAI_API_KEY' not in environment and 'AWS_SECRET_ACCESS_KEY' not in environment and 'DATABASE_URL' not in environment
    assert environment['CUDA_VISIBLE_DEVICES'] == '' and environment['OMP_NUM_THREADS'] == '1'


def test_real_metric_definitions_cover_misclassification_auc_ties_and_undefined_auc():
    from evaluation.evaluators import classification_metrics
    metrics = classification_metrics([0, 0, 1, 1], [0, 1, 1, 1],
        [[.9, .1], [.4, .6], [.3, .7], [.2, .8]], ['negative', 'positive'])
    assert metrics['sample_count'] == 4 and metrics['confusion_matrix'] == [[1, 1], [0, 2]]
    assert metrics['accuracy'] == .75
    assert metrics['precision'] == pytest.approx(5 / 6)
    assert metrics['recall'] == .75
    assert metrics['f1'] == pytest.approx(11 / 15)
    assert metrics['auc'] == 1
    tied = classification_metrics([0, 1], [0, 0], [[.5, .5], [.5, .5]], ['a', 'b'])
    assert tied['auc'] == .5
    single = classification_metrics([0], [0], [[1., 0.]], ['a', 'b'])
    assert single['auc'] is None
    with pytest.raises(ValueError, match='实际可评分样本'):
        classification_metrics([], [], [], ['a', 'b'])


def test_workflow_dispatcher_records_only_actual_execution_actor_and_tenant(user, authenticated_client, evaluation_assets):
    from evaluation.models import EvaluationJob
    from workflows.models import Workflow, WorkflowExecution, Node, Edge
    from workflows.services.workflow_executor import WorkflowExecutor
    training, dataset, _ = evaluation_assets
    workflow = Workflow.objects.create(owner=user, name='Actual evaluation dispatcher')
    first = Node.objects.create(workflow=workflow, node_type='start', name='Start')
    evaluate = Node.objects.create(workflow=workflow, node_type='model_evaluation', name='Evaluate', config={
        'trainingJobId': str(training.pk), 'testDataset': str(dataset.pk),
        'metrics': 'accuracy, precision, recall, f1', 'created_by': 'forged', 'tenant_id': 999,
        'features': [], 'labelColumn': '', 'imageSize': 224})
    last = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=first, target_node=evaluate)
    Edge.objects.create(workflow=workflow, source_node=evaluate, target_node=last)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user,
        input_data={'metadata': {'execution_id': 'business-value'}})
    WorkflowExecutor(workflow, execution).execute()
    execution.refresh_from_db()
    assert execution.status == 'completed', execution.error_message
    job = EvaluationJob.objects.get(execution=execution)
    assert job.status == 'completed' and job.created_by_id == user.pk and job.tenant_id is None
    assert job.workflow_id == workflow.pk and job.node_id == evaluate.pk
    assert job.metrics['accuracy'] == 1 and job.metrics['sample_count'] == 4
    assert execution.input_data['metadata']['execution_id'] == 'business-value'


def test_foreign_or_forged_workflow_metadata_never_creates_an_evaluation(user, admin_user, evaluation_assets):
    from evaluation.models import EvaluationJob
    from workflows.models import Workflow, WorkflowExecution, Node, NodeExecution
    from workflows.services.langchain_service import LangChainService
    workflow = Workflow.objects.create(owner=admin_user, name='Foreign source')
    node = Node.objects.create(workflow=workflow, node_type='model_evaluation', name='Foreign evaluation')
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=admin_user, status='running')
    NodeExecution.objects.create(execution=execution, node=node, node_version=1, status='running')
    service = LangChainService(user_id=user.pk)
    training, dataset, _ = evaluation_assets
    result = service.execute_node('model_evaluation', {'trainingJobId': str(training.pk), 'testDataset': str(dataset.pk)},
        {'metadata': {'workflow_id': str(workflow.pk), 'node_id': str(node.pk), 'execution_id': str(execution.pk)}})
    assert result['success'] is False and result['error_type'] == 'untrusted_execution'
    assert not EvaluationJob.objects.exists()


def test_malicious_pickle_is_rejected_without_executing_it(authenticated_client, evaluation_assets, tmp_path):
    import torch
    marker = tmp_path / 'pickle-must-not-run.txt'

    class ExecutableObject:
        def __reduce__(self):
            return eval, (f"__import__('pathlib').Path({str(marker)!r}).write_text('unsafe')",)

    _, _, filename = evaluation_assets
    torch.save({'model': ExecutableObject()}, filename)
    created = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    result = authenticated_client.post(f'{BASE}{created.data["job_id"]}/run/', {}, format='json')
    assert result.status_code == 422 and result.data['status'] == 'failed'
    assert result.data['metrics'] == {} and not marker.exists()
    assert 'Python' in result.data['error_message']


@pytest.mark.parametrize('training_kind', ['clip_cls', 'yolo'])
def test_real_clip_torchscript_classifies_labeled_images_on_cpu(user, authenticated_client, evaluation_assets, settings, training_kind):
    import json
    import torch
    from PIL import Image
    from datasets.models import Dataset
    training, _, filename = evaluation_assets

    class ColorClassifier(torch.nn.Module):
        def forward(self, images):
            averages = images.mean(dim=(2, 3))
            return torch.stack((averages[:, 0], averages[:, 2]), dim=1)

    scripted = filename.with_suffix('.torchscript')
    model = torch.jit.trace(ColorClassifier(), torch.zeros(1, 3, 16, 16))
    torch.jit.save(model, str(scripted), _extra_files={'config.txt': json.dumps({
        'stride': 16, 'names': {'0': 'red', '1': 'blue'}, 'task': 'classify', 'batch': 1, 'imgsz': [16, 16]})})
    training.model_path, training.training_kind, training.class_names = str(scripted), training_kind, ['red', 'blue']
    training.model_type = 'classification'
    training.save(update_fields=['model_path', 'training_kind', 'class_names', 'model_type'])
    root = Path(settings.MEDIA_ROOT) / 'datasets' / uuid.uuid4().hex
    for name, color in [('red', 'red'), ('blue', 'blue')]:
        (root / 'test' / name).mkdir(parents=True)
        Image.new('RGB', (16, 16), color=color).save(root / 'test' / name / 'sample.png')
    dataset = Dataset.objects.create(created_by=user, name='Actual labeled images', file_path=str(root),
        source='upload', format='classification_folders', status='ready')
    request = {'name': 'CLIP exported classifier', 'training_job_id': str(training.pk), 'dataset_id': str(dataset.pk),
        'parameters': {'image_size': 16}}
    created = authenticated_client.post(BASE, request, format='json')
    assert created.status_code == 201, created.data
    result = authenticated_client.post(f'{BASE}{created.data["job_id"]}/run/', {}, format='json')
    assert result.status_code == 200, result.data.get('error_message', result.data)
    assert result.data['metrics']['accuracy'] == result.data['metrics']['f1'] == 1
    assert result.data['metrics']['sample_count'] == 2


def test_cancel_between_copy_and_dispatch_does_not_start_or_accept_a_worker(user, authenticated_client, evaluation_assets, monkeypatch):
    from evaluation import services
    original = services.copy_resource
    created = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    url = f'{BASE}{created.data["job_id"]}/'
    copies = []

    def copy_and_cancel(*args, **kwargs):
        result = original(*args, **kwargs)
        copies.append(result)
        if len(copies) == 2:
            cancelled = authenticated_client.post(url + 'cancel/', {}, format='json')
            assert cancelled.status_code == 200 and cancelled.data['status'] == 'cancelled'
        return result

    monkeypatch.setattr(services, 'copy_resource', copy_and_cancel)
    monkeypatch.setattr(services.subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('Cancelled evaluation started external work'))
    result = authenticated_client.post(url + 'run/', {}, format='json')
    assert result.status_code == 409 and result.data['status'] == 'cancelled'
    assert result.data['metrics'] == {} and result.data['error_code'] == 'cancelled'


def test_real_yolo_torchscript_scores_actual_boxes_on_cpu(user, authenticated_client, evaluation_assets, settings):
    import json
    import torch
    from PIL import Image
    from datasets.models import Dataset
    training, _, filename = evaluation_assets

    class BoxDetector(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.register_buffer('boxes', torch.tensor([32., 32., 32., 32., .99, .01]).view(1, 6, 1))

        def forward(self, images):
            return self.boxes.expand(images.size(0), -1, -1)

    scripted = filename.with_suffix('.torchscript')
    detector = torch.jit.trace(BoxDetector(), torch.zeros(1, 3, 64, 64))
    torch.jit.save(detector, str(scripted), _extra_files={'config.txt': json.dumps({
        'stride': 32, 'names': {'0': 'target', '1': 'other'}, 'task': 'detect', 'batch': 1,
        'imgsz': [64, 64], 'shape': [1, 3, 64, 64]})})
    training.model_path, training.training_kind, training.class_names = str(scripted), 'yolo', ['target', 'other']
    training.framework, training.model_type = 'ultralytics', 'detection'
    training.save(update_fields=['model_path', 'training_kind', 'class_names', 'framework', 'model_type'])
    root = Path(settings.MEDIA_ROOT) / 'datasets' / uuid.uuid4().hex
    (root / 'images' / 'test').mkdir(parents=True)
    (root / 'labels' / 'test').mkdir(parents=True)
    Image.new('RGB', (64, 64), color='white').save(root / 'images' / 'test' / 'sample.jpg')
    (root / 'labels' / 'test' / 'sample.txt').write_text('0 .5 .5 .5 .5\n')
    (root / 'data.yaml').write_text('names: [target, other]\ntrain: images/test\nval: images/test\ntest: images/test\n')
    dataset = Dataset.objects.create(created_by=user, name='Actual YOLO boxes', file_path=str(root),
        source='upload', format='yolo', status='ready')
    created = authenticated_client.post(BASE, {'name': 'CPU detection', 'training_job_id': str(training.pk),
        'dataset_id': str(dataset.pk), 'parameters': {'image_size': 64}}, format='json')
    assert created.status_code == 201, created.data
    result = authenticated_client.post(f'{BASE}{created.data["job_id"]}/run/', {}, format='json')
    assert result.status_code == 200, result.data.get('error_message', result.data)
    assert result.data['metrics']['sample_count'] == 1
    assert result.data['metrics']['precision'] > .99 and result.data['metrics']['recall'] > .99
    assert result.data['metrics']['mAP50'] > .99


def test_dataset_parent_directory_cannot_relabel_other_users_uploads(user, admin_user, authenticated_client, evaluation_assets, settings):
    from datasets.models import Dataset
    _, _, _ = evaluation_assets
    foreign = Dataset.objects.create(created_by=admin_user, name='Foreign rows', source='upload', format='csv', status='ready')
    foreign.file.save('private.csv', ContentFile(b'x,label\n1,private\n'))
    parent = Dataset.objects.create(created_by=user, name='Forged parent', file_path=str(Path(settings.MEDIA_ROOT) / 'datasets'),
        format='classification_folders', source='upload', status='ready')
    values = payload(evaluation_assets)
    values['dataset_id'] = str(parent.pk)
    result = authenticated_client.post(BASE, values, format='json')
    assert result.status_code == 403 and result.data['error_code'] == 'dataset_alias_forbidden'


@pytest.mark.parametrize('terminal', ['cancelled', 'failed'])
def test_late_actual_model_result_cannot_overwrite_cancel_or_stale_failure(terminal, authenticated_client, evaluation_assets, monkeypatch):
    from django.utils import timezone
    from evaluation import services
    from evaluation.models import EvaluationJob
    created = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    url = f'{BASE}{created.data["job_id"]}/'
    original = services._child_result

    def finish_after_control(job, actor, directory):
        metrics = original(job, actor, directory)
        assert metrics['accuracy'] == 1 and metrics['sample_count'] == 4
        if terminal == 'cancelled':
            assert authenticated_client.post(url + 'cancel/', {}, format='json').status_code == 200
        else:
            EvaluationJob.objects.filter(pk=job.pk).update(lease_expires_at=timezone.now())
            assert authenticated_client.get(url).data['error_code'] == 'lease_expired'
        return metrics

    monkeypatch.setattr(services, '_child_result', finish_after_control)
    result = authenticated_client.post(url + 'run/', {}, format='json')
    assert result.status_code == 409 and result.data['status'] == terminal
    assert result.data['metrics'] == {}


def test_legacy_completed_metrics_are_visible_as_unverified_not_new_proof(user, authenticated_client):
    from evaluation.models import EvaluationJob
    job = EvaluationJob.objects.create(created_by=user, job_id='old-completed', name='Unknown old metrics',
        model_path='/old/model.pt', status='completed', metrics={'accuracy': .99})
    response = authenticated_client.get(f'{BASE}{job.job_id}/')
    assert response.status_code == 200 and response.data['metrics'] == {'accuracy': .99}
    assert response.data['verification_status'] == 'legacy_unverified'


def test_team_deactivation_after_copy_is_rechecked_before_worker_start(user, admin_user, authenticated_client, evaluation_assets, monkeypatch):
    from tenants.models import Tenant, TenantMembership
    from evaluation import services
    from evaluation.models import EvaluationJob
    training, dataset, _ = evaluation_assets
    tenant = Tenant.objects.create(owner=admin_user, name='Deactivate evaluation', slug='deactivate-evaluation', status='active')
    TenantMembership.objects.create(tenant=tenant, user=user, role='member', is_active=True)
    training.tenant = dataset.tenant = tenant
    training.save(update_fields=['tenant'])
    dataset.save(update_fields=['tenant'])
    training.workflow.tenant = tenant
    training.workflow.save(update_fields=['tenant'])
    original = services.copy_resource
    copies = []

    def revoke_after_copy(*args, **kwargs):
        value = original(*args, **kwargs)
        copies.append(value)
        if len(copies) == 2:
            Tenant.objects.filter(pk=tenant.pk).update(status='cancelled')
        return value

    created = authenticated_client.post(BASE, payload(evaluation_assets), format='json')
    assert created.status_code == 201
    monkeypatch.setattr(services, 'copy_resource', revoke_after_copy)
    monkeypatch.setattr(services.subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('Revoked team started model inference'))
    result = authenticated_client.post(f'{BASE}{created.data["job_id"]}/run/', {}, format='json')
    assert result.status_code == 403
    job = EvaluationJob.objects.get(job_id=created.data['job_id'])
    assert job.status == 'failed' and job.metrics == {}
