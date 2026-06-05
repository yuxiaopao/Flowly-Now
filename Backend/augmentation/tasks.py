"""
Celery tasks for augmentation operations.
"""

import os
import logging
from pathlib import Path
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_augmentation_task(self, job_id: str):
    """
    Celery task to run augmentation job asynchronously.
    
    Args:
        job_id: UUID of the AugmentationJob
    """
    run_augmentation_task_sync(job_id)


def run_augmentation_task_sync(job_id: str):
    """
    Synchronous version of augmentation task for non-Celery environments.
    
    Args:
        job_id: UUID of the AugmentationJob
    """
    from .models import AugmentationJob
    from .augmentors import get_augmentor, detect_data_type
    from datasets.models import Dataset

    try:
        job = AugmentationJob.objects.get(id=job_id)
    except AugmentationJob.DoesNotExist:
        logger.error(f"AugmentationJob {job_id} not found")
        return

    job.mark_running()
    job.progress = 10
    job.save(update_fields=['status', 'started_at', 'progress'])

    try:
        dataset = job.input_dataset
        data_type = detect_data_type(dataset)
        job.progress = 20
        job.save(update_fields=['progress'])

        file_path = dataset.get_absolute_file_path()
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        output_dir_base = Path(settings.MEDIA_ROOT) / 'augmented'
        output_dir = output_dir_base / str(job.id)
        output_dir.mkdir(parents=True, exist_ok=True)

        job.output_dir = str(output_dir)
        job.save(update_fields=['output_dir'])

        job.progress = 30
        job.save(update_fields=['progress'])

        augmentor = get_augmentor(
            data_type=data_type,
            strategy=job.strategy,
            ratio=job.ratio,
            transformations=job.transformations
        )

        job.progress = 40
        job.save(update_fields=['progress'])

        if data_type == 'image':
            result = augmentor.augment_dataset(
                input_path=file_path,
                output_dir=str(output_dir)
            )
        elif data_type == 'text':
            result = augmentor.augment_dataset(
                input_path=file_path,
                output_dir=str(output_dir)
            )
        elif data_type == 'tabular':
            result = augmentor.augment_csv(
                input_path=file_path,
                output_dir=str(output_dir)
            )
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        job.progress = 70
        job.save(update_fields=['progress'])

        output_dataset = _create_output_dataset(
            job=job,
            result=result,
            data_type=data_type,
            output_mode=job.output_mode
        )

        job.progress = 90
        job.save(update_fields=['progress'])

        job.mark_completed(
            augmented_count=result.get('augmented_count', 0),
            output_dataset=output_dataset
        )

        logger.info(f"Augmentation job {job_id} completed successfully")

    except Exception as e:
        logger.exception(f"Augmentation job {job_id} failed: {e}")
        job.mark_failed(str(e))
        raise


def _create_output_dataset(job, result, data_type, output_mode):
    """
    Create output dataset after augmentation.
    
    Args:
        job: AugmentationJob instance
        result: Augmentation result dict
        data_type: Detected data type
        output_mode: Output mode ('create_new' or 'overwrite')
        
    Returns:
        Created Dataset instance
    """
    from datasets.models import Dataset

    output_name = job.output_name or f"{job.input_dataset.name}_augmented"
    output_dir = Path(job.output_dir)

    if output_mode == 'overwrite':
        output_dataset = job.input_dataset
        output_dataset.name = output_name
    else:
        output_dataset = Dataset(
            name=output_name,
            description=f"增强后的数据集，基于 {job.input_dataset.name} 创建",
            source='upload',
            status='ready',
            created_by=job.created_by,
            tenant=job.tenant
        )

    if data_type == 'image':
        output_files = list(output_dir.glob('*.jpg')) + list(output_dir.glob('*.png'))
        output_dataset.size_bytes = sum(f.stat().st_size for f in output_files)
        output_dataset.row_count = len(output_files)
        output_dataset.format = 'image'
    elif data_type == 'text':
        output_file = list(output_dir.glob('*.txt')) + list(output_dir.glob('*.json'))
        if output_file:
            output_file = output_file[0]
            output_dataset.size_bytes = output_file.stat().st_size
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                output_dataset.row_count = len(lines)
        output_dataset.format = 'txt'
    elif data_type == 'tabular':
        output_file = list(output_dir.glob('*.csv'))
        if output_file:
            output_file = output_file[0]
            output_dataset.size_bytes = output_file.stat().st_size
            import pandas as pd
            df = pd.read_csv(output_file)
            output_dataset.row_count = len(df)
            output_dataset.column_count = len(df.columns)
            output_dataset.columns = [
                {'name': col, 'type': str(dtype)} 
                for col, dtype in df.dtypes.items()
            ]
        output_dataset.format = 'csv'

    output_dataset.metadata = {
        'augmentation_job_id': str(job.id),
        'original_dataset_id': str(job.input_dataset.id),
        'strategy': job.strategy,
        'ratio': job.ratio,
        'original_count': job.original_count,
        'augmented_count': result.get('augmented_count', 0),
        'data_type': data_type,
    }

    output_dataset.save()

    job.output_dataset = output_dataset
    job.save(update_fields=['output_dataset'])

    return output_dataset


from django.conf import settings
