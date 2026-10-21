"""Website generator contract coverage."""

import py_compile
from unittest.mock import patch
import tempfile
from pathlib import Path

import pytest
from rest_framework import status

from training.models import TrainingJob
from website_generator.generators import get_generator
from website_generator.models import GeneratedSite


pytestmark = pytest.mark.django_db


@patch('threading.Thread')
def test_generate_site_accepts_training_manifest_contract(thread_mock, authenticated_client):
    thread_mock.return_value.start.return_value = None
    with tempfile.TemporaryDirectory(prefix='flowly-site-contract-') as temp_dir:
        temp_path = Path(temp_dir)
        job = TrainingJob.objects.create(
            name='helmet-yolo',
            status='completed',
            training_kind='yolo',
            framework='ultralytics',
            model_type='detection',
            class_names=['helmet', 'vest'],
            best_weight_path=str(temp_path / 'best.pt'),
            config={'base_weight_uri': 'yolo11x.pt'},
            total_epochs=1,
            created_by=None,
        )

        output_dir = temp_path / 'site-output'
        response = authenticated_client.post(
            '/api/v1/website-generator/generate/',
            {
                'name': 'Helmet Safety Site',
                'training_job_id': str(job.id),
                'output_dir': str(output_dir),
                'site_brief': {'scenario': 'Safety helmet recognition'},
                'theme_profile': {'primaryColor': '#06b6d4', 'uiTone': 'industrial_warning'},
                'environment_config': {'outputDir': str(output_dir)},
                'required_features': ['imageRecognition'],
            },
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        site = GeneratedSite.objects.get(id=response.data['id'])
    assert site.frontend_framework == 'vue'
    assert site.backend_framework == 'flask'
    assert site.environment_config['dbEngine'] == 'mysql'
    assert site.model_artifact_manifest['trainingKind'] == 'yolo'
    assert site.model_artifact_manifest['baseModel'] == 'yolo11x.pt'
    assert site.required_features == [
        'imageRecognition', 'videoRecognition', 'factRecognition', 'historyRecords'
    ]
    assert site.labels == ['helmet', 'vest']


def test_detection_generator_outputs_full_recognition_site_contract():
    with tempfile.TemporaryDirectory(prefix='flowly-detection-site-') as temp_dir:
        temp_path = Path(temp_dir)
        model_path = temp_path / 'best.pt'
        model_path.write_bytes(b'fake weights for contract test')
        output_dir = temp_path / 'site-output'

        generator = get_generator('detection', {
            'output_dir': str(output_dir),
            'model_path': str(model_path),
            'model_type': 'detection',
            'labels': ['helmet', 'vest'],
            'framework': 'ultralytics',
            'website_type': 'detection',
            'frontend_framework': 'vue',
            'backend_framework': 'flask',
            'port': 5017,
            'name': 'Helmet Safety Site',
            'description': 'Safety helmet recognition',
            'dbEngine': 'mysql',
            'required_features': [
                'imageRecognition', 'videoRecognition', 'factRecognition', 'historyRecords'
            ],
            'model_artifact_manifest': {
                'trainingKind': 'yolo',
                'baseModel': 'yolo11x.pt',
                'bestWeightPath': str(model_path),
                'labels': ['helmet', 'vest'],
            },
            'wizard': {
                'siteName': 'Helmet Safety Site',
                'usageDescription': 'Safety helmet recognition',
                'primaryColor': '#06b6d4',
            },
        })

        result = generator.generate()

        assert result['success'] is True
        index_html = (output_dir / 'frontend' / 'index.html').read_text(encoding='utf-8')
        app_py = (output_dir / 'backend' / 'app.py').read_text(encoding='utf-8')
        config = (output_dir / 'backend' / 'config.json').read_text(encoding='utf-8')
        schema_sql = (output_dir / 'backend' / 'db' / 'schema.sql').read_text(encoding='utf-8')
        init_db_py = (output_dir / 'backend' / 'db' / 'init_db.py').read_text(encoding='utf-8')
        py_compile.compile(str(output_dir / 'backend' / 'app.py'), doraise=True)
        py_compile.compile(str(output_dir / 'backend' / 'db' / 'init_db.py'), doraise=True)

    assert '图片识别' in index_html
    assert '视频识别' in index_html
    assert '实时识别' in index_html
    assert '事实识别' in index_html
    assert '历史记录' in index_html
    assert 'LABELS = ["helmet", "vest"]' in index_html
    assert all(token not in index_html for token in ('?/p>', '?/span>', '?/div>'))

    assert "@app.route('/predict', methods=['POST'])" in app_py
    assert "@app.route('/predict/video', methods=['POST'])" in app_py
    assert "@app.route('/api/history', methods=['GET'])" in app_py
    assert "@app.route('/api/fact-check', methods=['POST'])" in app_py
    assert "@app.route('/api/fact-checks', methods=['GET'])" in app_py
    assert 'list_inference_history' in app_py
    assert 'log_fact_check' in app_py

    assert '"db_engine": "mysql"' in config
    assert '"trainingKind": "yolo"' in config
    assert '"baseModel": "yolo11x.pt"' in config
    assert '"videoRecognition"' in config
    assert '"factRecognition"' in config
    assert '"historyRecords"' in config

    assert 'CREATE TABLE IF NOT EXISTS inference_logs' in schema_sql
    assert 'CREATE TABLE IF NOT EXISTS fact_checks' in schema_sql
    assert 'mode VARCHAR(32)' in schema_sql
    assert 'detections_json TEXT' in schema_sql
    assert "DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()" in init_db_py
    assert 'def list_inference_history' in init_db_py
    assert 'def log_fact_check' in init_db_py
