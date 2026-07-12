import os, sys
import django
sys.path.insert(0, r'e:\Flowly-now\Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from training.models import TrainingJob
import uuid

try:
    job = TrainingJob.objects.create(
        name='Test YOLO Job',
        framework='ultralytics',
        model_type='detection',
        status='queued',
        config={'epochs': 5},
        dataset_yaml_path=r'E:\Flowly-now\Backend\media\yolo_datasets\flowly_test\dataset.yaml',
        total_epochs=5,
    )
    print(f'SUCCESS: Created TrainingJob id={job.id} framework={job.framework}')
except Exception as e:
    print(f'FAILED: {type(e).__name__}: {e}')
