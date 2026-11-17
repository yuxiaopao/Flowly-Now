"""The API and worker must use paths present in both the checkout and /app image."""
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from training.models import TrainingJob
from training.tasks import run_training_task


@pytest.mark.django_db
def test_worker_resolves_training_script_and_working_directory_from_base_dir(tmp_path):
    application = tmp_path / 'isolated-app'
    script = application / 'scripts' / 'train_model.py'
    script.parent.mkdir(parents=True)
    script.write_text('# deployed script path fixture\n', encoding='utf-8')
    job = TrainingJob.objects.create(framework='pytorch', model_type='classifier')
    process = Mock(stdout=io.StringIO('{"type":"training_complete","model_path":"result.pt"}\n'),
                   stderr=io.StringIO(''))
    process.poll.return_value = 0
    process.wait.return_value = 0
    run_training_task.push_request(id='deployed-training', retries=0)
    try:
        with override_settings(BASE_DIR=application), patch('training.tasks.subprocess.Popen', return_value=process) as launch:
            result = run_training_task.run(str(job.pk), str(application / 'data' / 'config.json'))
    finally:
        run_training_task.pop_request()
    command = launch.call_args.args[0]
    assert Path(command[1]) == script
    assert Path(command[1]).is_file()
    assert Path(launch.call_args.kwargs['cwd']) == application
    assert '--streaming' in command
    assert result['status'] == 'completed'


def test_packaged_canonical_training_script_exposes_worker_cli_without_training():
    backend = Path(__file__).resolve().parents[3] / 'Backend'
    result = subprocess.run([sys.executable, str(backend / 'scripts' / 'train_model.py'), '--help'],
                            cwd=backend, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    for argument in ('--config', '--job-id', '--streaming', '--output-dir'):
        assert argument in result.stdout


@pytest.mark.django_db
@pytest.mark.parametrize('kind,route', [('generic', 'training-jobs'), ('yolo', 'yolo-runs')])
def test_create_api_persists_config_under_shared_application_data(user, tmp_path, kind, route):
    client = APIClient()
    client.force_authenticate(user)
    body = {'name': 'Runtime path', 'training_kind': kind, 'config': {}}
    if kind == 'yolo':
        body.update(dataset_yaml_path='/datasets/data.yaml', yolo_version='v8', model_variant='n')
    with override_settings(BASE_DIR=tmp_path), patch.object(run_training_task, 'delay') as dispatch:
        response = client.post(f'/api/v1/training/{route}/', body, format='json')
    assert response.status_code == 201, response.content
    dispatch.assert_called_once()
    identifier, config_path, output_dir = dispatch.call_args.args
    expected = tmp_path / 'data' / 'training_configs' / f'{identifier}.json'
    assert Path(config_path) == expected
    assert expected.is_file()
    assert Path(output_dir) == tmp_path / 'data' / 'training_outputs' / identifier
    saved = json.loads(expected.read_text(encoding='utf-8'))
    assert saved['job_id'] == identifier
    assert saved['training_kind'] == kind


@pytest.mark.django_db
@pytest.mark.parametrize('kind,route', [('generic', 'training-jobs'), ('yolo', 'yolo-runs')])
def test_retry_api_uses_the_same_shared_data_root(user, tmp_path, kind, route):
    job = TrainingJob.objects.create(created_by=user, status='failed', training_kind=kind,
                                     framework='ultralytics' if kind == 'yolo' else 'pytorch',
                                     model_type='detection' if kind == 'yolo' else 'classifier')
    client = APIClient()
    client.force_authenticate(user)
    with override_settings(BASE_DIR=tmp_path), patch.object(run_training_task, 'delay') as dispatch:
        response = client.post(f'/api/v1/training/{route}/{job.pk}/retry/', {}, format='json')
    assert response.status_code == 200, response.content
    dispatch.assert_called_once()
    identifier, config_path, output_dir = dispatch.call_args.args
    assert Path(config_path) == tmp_path / 'data' / 'training_configs' / f'{identifier}.json'
    assert Path(config_path).is_file()
    assert Path(output_dir) == tmp_path / 'data' / 'training_outputs' / identifier


@pytest.mark.django_db
def test_explicit_training_output_directory_is_preserved(user, tmp_path):
    client = APIClient()
    client.force_authenticate(user)
    output = str(tmp_path / 'custom-output')
    with override_settings(BASE_DIR=tmp_path), patch.object(run_training_task, 'delay') as dispatch:
        response = client.post('/api/v1/training/yolo-runs/', {
            'dataset_yaml_path': '/datasets/data.yaml', 'yolo_version': 'v8', 'model_variant': 'n',
            'config': {'output_dir': output},
        }, format='json')
    assert response.status_code == 201
    assert dispatch.call_args.args[2] == output
