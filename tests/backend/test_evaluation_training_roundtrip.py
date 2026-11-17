"""Actual CPU training and held-out evaluation share the saved preprocessing."""
from pathlib import Path
import pytest
from django.core.files.base import ContentFile

from tests.backend.test_evaluation_security import evaluation_assets, BASE

pytestmark = pytest.mark.django_db(transaction=True)


def test_actual_cpu_training_saves_schema_and_evaluates_reordered_heldout_columns(user, authenticated_client, evaluation_assets):
    import torch
    from datasets.models import Dataset
    from training.training_runner import TrainingRunner

    training, _, filename = evaluation_assets
    original = Dataset.objects.create(created_by=user, name='Actual training rows', source='upload', format='csv', status='ready')
    original.file.save('train.csv', ContentFile(b'x1,x2,label\n90,1,0\n92,0,0\n94,1,0\n96,0,0\n104,1,1\n106,0,1\n108,1,1\n110,0,1\n'))
    config = {'input_dim': 2, 'hidden_dims': [], 'output_dim': 2, 'dropout': 0,
        'epochs': 25, 'batch_size': 8, 'learning_rate': .2, 'dataset_path': original.file.path}
    torch.manual_seed(13)
    torch.set_num_threads(1)
    runner = TrainingRunner(str(training.pk), config, output_dir=str(filename.parent))
    runner._device = 'cpu'
    trained = runner.run_pytorch_training()
    assert trained['success'] is True
    saved = torch.load(trained['model_path'], map_location='cpu', weights_only=True)
    metadata = saved['preprocessing']
    assert metadata['kind'] == 'standardize'
    assert metadata['feature_names'] == ['x1', 'x2'] and metadata['label_column'] == 'label'
    assert metadata['mean'] == [100., .5]
    assert metadata['std'][0] == pytest.approx(7.348469, abs=1e-5)
    training.config, training.model_path = config, trained['model_path']
    training.dataset_id, training.dataset_path = str(original.pk), original.file.path
    training.save(update_fields=['config', 'model_path', 'dataset_id', 'dataset_path'])
    heldout = Dataset.objects.create(created_by=user, name='Distinct held-out reordered rows', source='upload', format='csv', status='ready')
    heldout.file.save('heldout.csv', ContentFile(b'x2,x1,label\n0,93,0\n1,95,0\n0,107,1\n1,109,1\n'))

    def evaluate():
        created = authenticated_client.post(BASE, {'name': 'Trained model', 'training_job_id': str(training.pk),
            'dataset_id': str(heldout.pk)}, format='json')
        assert created.status_code == 201, created.data
        return authenticated_client.post(f'{BASE}{created.data["job_id"]}/run/', {}, format='json')

    result = evaluate()
    assert result.status_code == 200, result.data.get('error_message', result.data)
    assert result.data['metrics']['accuracy'] == result.data['metrics']['f1'] == 1
    assert result.data['metrics']['preprocessing'] == 'recorded_standardization'
    assert result.data['metrics']['feature_columns'] == ['x1', 'x2']
    assert result.data['verification_status'] == 'verified'
    # A pre-metadata artifact must recover its scaler from the original data, not held-out rows.
    saved.pop('preprocessing')
    torch.save(saved, trained['model_path'])
    legacy = evaluate()
    assert legacy.status_code == 200, legacy.data.get('error_message', legacy.data)
    assert legacy.data['metrics']['accuracy'] == 1
    assert legacy.data['metrics']['preprocessing'] == 'training_dataset_standardization'
    assert legacy.data['artifact_snapshot']['training_dataset_sha256']
    # Same feature count with a missing training column must fail, never silently shift columns.
    with open(heldout.file.path, 'w', encoding='utf-8') as output:
        output.write('x2,wrong,label\n0,93,0\n1,107,1\n')
    missing = evaluate()
    assert missing.status_code == 422 and missing.data['status'] == 'failed'
    assert missing.data['metrics'] == {} and '特征' in missing.data['error_message']
