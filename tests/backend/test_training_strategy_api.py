"""Training strategy API coverage."""

from unittest.mock import patch

import pytest
from rest_framework import status

from training.models import TrainingJob


pytestmark = pytest.mark.django_db


class TestTrainingStrategyApi:
    def test_training_options_include_required_strategies(self, authenticated_client):
        response = authenticated_client.get('/api/v1/training/training-jobs/options/')

        assert response.status_code == status.HTTP_200_OK
        strategy_ids = {item['id'] for item in response.data['strategies']}
        assert {'yolo', 'clip', 'transformer'}.issubset(strategy_ids)

        yolo = next(item for item in response.data['strategies'] if item['id'] == 'yolo')
        weight_ids = {item['id'] for item in yolo['base_weights']}
        assert {'yolov8n.pt', 'yolo11x.pt'}.issubset(weight_ids)

    def test_analyze_dataset_reads_yolo_yaml_classes(self, authenticated_client):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory(prefix='flowly-yolo-') as tmp_dir:
            dataset_yaml = Path(tmp_dir) / 'dataset.yaml'
            dataset_yaml.write_text('names:\n  0: helmet\n  1: vest\n', encoding='utf-8')

            response = authenticated_client.post(
                '/api/v1/training/training-jobs/analyze-dataset/',
                {'training_kind': 'yolo', 'dataset_yaml_path': str(dataset_yaml)},
                format='json',
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['class_count'] == 2
        assert [item['name'] for item in response.data['classes']] == ['helmet', 'vest']
        assert response.data['suggested_task_type'] == 'detection'

    @patch('training.views.run_training_task.delay')
    def test_create_yolo_training_job_with_base_weight(self, delay_mock, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/training/training-jobs/',
            {
                'name': 'helmet-yolo',
                'training_kind': 'yolo',
                'dataset_yaml_path': 'E:/datasets/helmet/dataset.yaml',
                'class_names': ['helmet', 'vest'],
                'yolo_version': 'v11',
                'model_variant': 'x',
                'base_weight_uri': 'yolo11x.pt',
                'total_epochs': 20,
            },
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        job = TrainingJob.objects.get(id=response.data['id'])
        assert job.training_kind == 'yolo'
        assert job.framework == 'ultralytics'
        assert job.model_type == 'detection'
        assert job.yolo_version == 'v11'
        assert job.model_variant == 'x'
        assert job.config['base_weight_uri'] == 'yolo11x.pt'
        delay_mock.assert_called_once()

    @patch('training.views.run_training_task.delay')
    @pytest.mark.parametrize(
        'payload, expected_kind, expected_framework',
        [
            ({'training_kind': 'clip', 'model_type': 'retrieval', 'base_weight_uri': 'ViT-B-32/openai'}, 'clip_ret', 'pytorch'),
            ({'training_kind': 'transformer', 'model_type': 'classification', 'base_weight_uri': 'bert-base-uncased'}, 'transformer', 'transformers'),
        ],
    )
    def test_create_clip_and_transformer_training_jobs(self, delay_mock, authenticated_client, payload, expected_kind, expected_framework):
        response = authenticated_client.post(
            '/api/v1/training/training-jobs/',
            {'name': f'{expected_kind}-job', 'total_epochs': 3, **payload},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        job = TrainingJob.objects.get(id=response.data['id'])
        assert job.training_kind == expected_kind
        assert job.framework == expected_framework
        assert job.config['base_weight_uri'] == payload['base_weight_uri']
        delay_mock.assert_called_once()
