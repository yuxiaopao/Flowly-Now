"""
Celery tasks for model training.
Provides async training execution with progress streaming via WebSocket.
"""
import json
import subprocess
import signal
import os
import sys
import time
from datetime import timedelta
from pathlib import Path
from celery import shared_task, Task
from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def _utc_timestamp():
    return timezone.now().isoformat()


def _format_eta(seconds: int) -> str:
    if seconds <= 0:
        return '约 0 分钟'
    hours, remainder = divmod(int(seconds), 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0:
        return f'约 {hours} 小时 {minutes} 分钟'
    return f'约 {minutes} 分钟'


def _build_ws_event(event: str, data: dict) -> dict:
    return {
        'event': event,
        'version': '1.0',
        'timestamp': _utc_timestamp(),
        'data': data,
    }


def _extract_yolo_metrics(data: dict) -> dict:
    metrics = data.get('metrics', {}) or {}
    loss = data.get('loss', {}) or {}
    gpu = data.get('gpu', {}) or {}
    timing = data.get('timing', {}) or {}
    return {
        'loss_box': data.get('loss_box', loss.get('box')),
        'loss_cls': data.get('loss_cls', loss.get('cls')),
        'loss_dfl': data.get('loss_dfl', loss.get('dfl')),
        'precision': data.get('precision', metrics.get('precision')),
        'recall': data.get('recall', metrics.get('recall')),
        'map50': data.get('mAP50', metrics.get('mAP50')),
        'map50_95': data.get('mAP50_95', metrics.get('mAP50_95')),
        'fitness': data.get('fitness', metrics.get('fitness')),
        'learning_rate': data.get('learning_rate', data.get('lr')),
        'gpu': gpu,
        'timing': timing,
        'preview_samples': data.get('preview_samples', []),
        'best_epoch': data.get('best_epoch', 0),
    }


def _append_if_number(target: list, value):
    if isinstance(value, (int, float)):
        target.append(value)


class TrainingTask(Task):
    """Base task for model training with graceful termination."""
    
    # Class-level registry of running training processes (for cancellation)
    _running_jobs = {}
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            job_id = kwargs.get('job_id') or (args[0] if args else None)
            if job_id:
                try:
                    from training.models import TrainingJob
                    job = TrainingJob.objects.get(job_id=job_id)
                    job.mark_failed(str(exc))
                    _broadcast_training_event(job_id, 'training_error', {
                        'job_id': str(job_id),
                        'error': str(exc),
                        'traceback': str(einfo)
                    })
                except Exception as model_error:
                    logger.error(f"Failed to update TrainingJob on failure: {model_error}")
        except Exception as e:
            logger.error(f"Failed to handle training failure: {e}")

    def on_terminal(self, task_id, args, kwargs, retval):
        """Called when task succeeds or fails after all retries."""
        try:
            job_id = kwargs.get('job_id') or (args[0] if args else None)
            if job_id:
                try:
                    from training.models import TrainingJob
                    job = TrainingJob.objects.get(job_id=job_id)
                    if job.status == 'running':
                        job.status = 'failed'
                        job.error_message = 'Training terminated unexpectedly'
                        job.completed_at = timezone.now()
                        job.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed in on_terminal: {e}")


@shared_task(
    bind=True,
    base=TrainingTask,
    soft_time_limit=7200,   # 2 hours soft limit
    time_limit=10800,       # 3 hours hard limit
    max_retries=2,
    default_retry_delay=300
)
def run_training_task(self, training_job_id: str, config_path: str = None, output_dir: str = None):
    """
    Run model training in a subprocess with progress streaming.
    
    Args:
        training_job_id: UUID primary key of the TrainingJob record
        config_path: Path to the training config JSON file
        output_dir: Directory to save model files (optional override)
    """
    from training.models import TrainingJob
    job_id = training_job_id  # Local alias for compatibility

    try:
        job = TrainingJob.objects.get(id=training_job_id)
    except (TrainingJob.DoesNotExist, ValueError):
        logger.error(f"TrainingJob {training_job_id} not found")
        return {'error': f'TrainingJob {training_job_id} not found'}

    # Mark as running
    job.status = 'running'
    job.started_at = timezone.now()
    job.save(update_fields=['status', 'started_at', 'updated_at'])
    
    # Mark as running
    job.status = 'running'
    job.job_id = self.request.id
    job.started_at = timezone.now()
    job.save(update_fields=['status', 'job_id', 'started_at', 'updated_at'])
    
    _broadcast_training_event(job_id, 'training_started', _build_ws_event('training_started', {
        'training_run_id': str(job_id),
        'status': 'running',
        'gpu': job.gpu_info or {},
        'config_summary': {
            'yolo_version': job.yolo_version,
            'model_variant': job.model_variant,
            'epochs': job.total_epochs,
            'batch_size': (job.config or {}).get('batch_size') or (job.config or {}).get('batchSize'),
            'image_size': (job.config or {}).get('image_size') or (job.config or {}).get('imageSize'),
        },
        'message': 'Training started'
    }))
    
    # Build command
    script_path = Path(__file__).parent.parent.parent / 'scripts' / 'train_model.py'
    cmd = [
        sys.executable,
        str(script_path),
        '--config', str(config_path),
        '--job-id', str(job_id),
        '--streaming',
    ]
    if output_dir:
        cmd.extend(['--output-dir', output_dir])
    
    process = None
    all_metrics = []
    
    try:
        # Set up environment for unbuffered output
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
            cwd=str(script_path.parent.parent.parent)
        )
        
        # Track the process so we can terminate it
        TrainingTask._running_jobs[job_id] = process
        
        logger.info(f"Started training process for job {job_id}, PID: {process.pid}")
        
        # Read stdout line by line
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            # Skip non-JSON lines (info messages)
            if not line.startswith('{'):
                logger.info(f"Training [{job_id}]: {line}")
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from training process: {line}")
                continue
            
            event_type = data.get('type', 'unknown')
            
            if event_type == 'epoch_start':
                epoch = data.get('epoch', 0)
                total = data.get('total_epochs', 0)
                progress = data.get('progress', 0)

                job.current_epoch = epoch
                job.total_epochs = total
                job.progress = progress
                if total > 0 and job.started_at and epoch > 0:
                    elapsed_seconds = int((timezone.now() - job.started_at).total_seconds())
                    estimated_total = int(elapsed_seconds / epoch * total)
                    job.estimated_duration_seconds = estimated_total
                    job.eta_seconds = max(estimated_total - elapsed_seconds, 0)
                job.save(update_fields=['current_epoch', 'total_epochs', 'progress', 'estimated_duration_seconds', 'eta_seconds', 'updated_at'])

                _broadcast_training_event(job_id, 'epoch_start', _build_ws_event('epoch_start', {
                    'training_run_id': str(job_id),
                    'epoch': epoch,
                    'total_epochs': total,
                    'progress_percent': progress,
                }))

            elif event_type == 'epoch_complete':
                epoch = data.get('epoch', 0)
                total = data.get('total_epochs', 0)
                progress = data.get('progress', 0)

                if job.training_kind == 'yolo':
                    yolo_metrics = _extract_yolo_metrics(data)
                    elapsed_seconds = int((timezone.now() - job.started_at).total_seconds()) if job.started_at else 0
                    estimated_total = job.estimated_duration_seconds
                    eta_seconds = job.eta_seconds
                    if total > 0 and epoch > 0 and elapsed_seconds > 0:
                        estimated_total = int(elapsed_seconds / epoch * total)
                        eta_seconds = max(estimated_total - elapsed_seconds, 0)

                    metrics = {
                        'precision': yolo_metrics['precision'],
                        'recall': yolo_metrics['recall'],
                        'mAP50': yolo_metrics['map50'],
                        'mAP50_95': yolo_metrics['map50_95'],
                        'fitness': yolo_metrics['fitness'],
                    }

                    job.current_epoch = epoch
                    job.total_epochs = total
                    job.progress = progress
                    job.current_loss = yolo_metrics['loss_box'] or 0.0
                    job.current_metric = yolo_metrics['map50'] or 0.0
                    job.learning_rate = yolo_metrics['learning_rate'] or 0.0
                    job.metrics = metrics
                    job.estimated_duration_seconds = estimated_total
                    job.eta_seconds = eta_seconds
                    job.preview_samples = yolo_metrics['preview_samples'] or []
                    job.best_epoch = yolo_metrics['best_epoch'] or job.best_epoch
                    job.best_fitness = yolo_metrics['fitness'] or job.best_fitness
                    _append_if_number(job.loss_box_history, yolo_metrics['loss_box'])
                    _append_if_number(job.loss_cls_history, yolo_metrics['loss_cls'])
                    _append_if_number(job.loss_dfl_history, yolo_metrics['loss_dfl'])
                    _append_if_number(job.precision_history, yolo_metrics['precision'])
                    _append_if_number(job.recall_history, yolo_metrics['recall'])
                    _append_if_number(job.map50_history, yolo_metrics['map50'])
                    _append_if_number(job.map50_95_history, yolo_metrics['map50_95'])
                    if yolo_metrics['gpu']:
                        job.gpu_info = {**(job.gpu_info or {}), **yolo_metrics['gpu']}
                    job.metrics_history.append({
                        'epoch': epoch,
                        'loss': {
                            'box': yolo_metrics['loss_box'],
                            'cls': yolo_metrics['loss_cls'],
                            'dfl': yolo_metrics['loss_dfl'],
                        },
                        'metrics': metrics,
                        'learning_rate': yolo_metrics['learning_rate'],
                        'timing': {
                            'elapsed_seconds': elapsed_seconds,
                            'eta_seconds': eta_seconds,
                            'eta_formatted': _format_eta(eta_seconds),
                            'estimated_completion_at': (timezone.now() + timedelta(seconds=eta_seconds)).isoformat() if eta_seconds else timezone.now().isoformat(),
                        },
                        'gpu': yolo_metrics['gpu'],
                        'preview_samples': yolo_metrics['preview_samples'],
                        'timestamp': _utc_timestamp(),
                    })
                    job.save(update_fields=[
                        'current_epoch', 'total_epochs', 'progress', 'current_loss', 'current_metric',
                        'learning_rate', 'metrics', 'estimated_duration_seconds', 'eta_seconds',
                        'preview_samples', 'best_epoch', 'best_fitness', 'gpu_info', 'metrics_history',
                        'loss_box_history', 'loss_cls_history', 'loss_dfl_history', 'precision_history',
                        'recall_history', 'map50_history', 'map50_95_history', 'updated_at'
                    ])

                    _broadcast_training_event(job_id, 'training_progress', _build_ws_event('training_progress', {
                        'training_run_id': str(job_id),
                        'status': 'running',
                        'epoch': epoch,
                        'total_epochs': total,
                        'progress_percent': progress,
                        'loss': {
                            'box': yolo_metrics['loss_box'],
                            'cls': yolo_metrics['loss_cls'],
                            'dfl': yolo_metrics['loss_dfl'],
                        },
                        'metrics': metrics,
                        'learning_rate': yolo_metrics['learning_rate'],
                        'gpu': job.gpu_info or {},
                        'timing': {
                            'elapsed_seconds': elapsed_seconds,
                            'eta_seconds': eta_seconds,
                            'eta_formatted': _format_eta(eta_seconds),
                            'estimated_completion_at': (timezone.now() + timedelta(seconds=eta_seconds)).isoformat() if eta_seconds else timezone.now().isoformat(),
                        },
                        'best': {
                            'epoch': job.best_epoch,
                            'fitness': job.best_fitness,
                        },
                        'preview_samples': job.preview_samples or [],
                    }))

                    _broadcast_training_event(job_id, 'epoch_complete', _build_ws_event('epoch_complete', {
                        'training_run_id': str(job_id),
                        'epoch': epoch,
                        'total_epochs': total,
                        'saved_checkpoint': False,
                        'checkpoint_path': '',
                    }))
                else:
                    train_loss = data.get('train_loss')
                    train_acc = data.get('train_acc')
                    val_loss = data.get('val_loss')
                    val_acc = data.get('val_acc')

                    metrics = {
                        'train_loss': train_loss,
                        'train_acc': train_acc,
                        'val_loss': val_loss,
                        'val_acc': val_acc,
                    }
                    all_metrics.append(metrics)

                    job.current_epoch = epoch
                    job.total_epochs = total
                    job.progress = progress
                    job.current_loss = train_loss
                    job.current_metric = val_acc
                    job.metrics = metrics
                    job.save(update_fields=[
                        'current_epoch', 'total_epochs', 'progress',
                        'current_loss', 'current_metric', 'metrics', 'updated_at'
                    ])

                    job.add_metrics_entry(epoch, loss=train_loss, metric=val_acc)

                    _broadcast_training_event(job_id, 'epoch_complete', {
                        'job_id': str(job_id),
                        'epoch': epoch,
                        'total_epochs': total,
                        'metrics': metrics,
                        'progress': progress,
                    })
            
            elif event_type == 'training_complete':
                if job.training_kind == 'yolo':
                    best_weight_path = data.get('best_weight_path') or data.get('model_path', '')
                    last_weight_path = data.get('last_weight_path', '')
                    exported_artifacts = data.get('exported_artifacts', {}) or {}
                    final_metrics = data.get('final_metrics', {}) or {}
                    duration_seconds = data.get('total_time') or data.get('duration_seconds', 0)

                    job.model_path = best_weight_path
                    job.best_weight_path = best_weight_path
                    job.last_weight_path = last_weight_path
                    job.exported_artifacts = exported_artifacts
                    job.status = 'completed'
                    job.completed_at = timezone.now()
                    job.duration_seconds = duration_seconds or (int((job.completed_at - job.started_at).total_seconds()) if job.started_at else 0)
                    job.progress = 100
                    job.current_metric = final_metrics.get('mAP50', job.current_metric)
                    job.best_fitness = final_metrics.get('fitness', job.best_fitness)
                    job.metrics = final_metrics
                    job.save(update_fields=[
                        'model_path', 'best_weight_path', 'last_weight_path', 'exported_artifacts',
                        'status', 'completed_at', 'duration_seconds', 'progress',
                        'current_metric', 'best_fitness', 'metrics', 'updated_at'
                    ])

                    _broadcast_training_event(job_id, 'training_complete', _build_ws_event('training_complete', {
                        'training_run_id': str(job_id),
                        'status': 'completed',
                        'artifacts': {
                            'best_weight_path': best_weight_path,
                            'last_weight_path': last_weight_path,
                            'exported_artifacts': exported_artifacts,
                        },
                        'final_metrics': final_metrics,
                        'duration_seconds': job.duration_seconds,
                        'next_actions': {
                            'can_download': True,
                            'can_generate_site': True,
                            'recommended_project_name': job.name or 'YOLO Detection System',
                        }
                    }))

                    logger.info(f"YOLO training job {job_id} completed successfully. Model: {best_weight_path}")
                    return {
                        'job_id': str(job_id),
                        'status': 'completed',
                        'model_path': best_weight_path,
                        'duration_seconds': job.duration_seconds,
                        'final_metrics': final_metrics,
                    }

                model_path = data.get('model_path', '')
                total_time = data.get('total_time', 0)
                best_val_acc = data.get('best_val_acc', 0)
                training_history = data.get('training_history', [])

                job.model_path = model_path
                job.status = 'completed'
                job.completed_at = timezone.now()
                if job.started_at:
                    job.duration_seconds = int((job.completed_at - job.started_at).total_seconds())
                job.progress = 100
                job.current_metric = best_val_acc
                job.metrics_history = training_history
                job.save(update_fields=[
                    'model_path', 'status', 'completed_at', 'duration_seconds',
                    'progress', 'current_metric', 'metrics_history', 'updated_at'
                ])

                _broadcast_training_event(job_id, 'training_complete', {
                    'job_id': str(job_id),
                    'model_path': model_path,
                    'total_time': total_time,
                    'best_val_acc': best_val_acc,
                    'training_history': training_history,
                })

                logger.info(f"Training job {job_id} completed successfully. Model: {model_path}")
                return {
                    'job_id': str(job_id),
                    'status': 'completed',
                    'model_path': model_path,
                    'total_time': total_time,
                    'best_val_acc': best_val_acc
                }
            
            elif event_type == 'error':
                error_msg = data.get('message', 'Unknown error')
                job.status = 'failed'
                job.error_message = error_msg
                job.completed_at = timezone.now()
                job.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
                
                _broadcast_training_event(job_id, 'training_error', {
                    'job_id': str(job_id),
                    'error': error_msg,
                })
            
            elif event_type == 'info':
                logger.info(f"Training [{job_id}]: {data.get('message', '')}")
            
            elif event_type == 'cancelled':
                job.status = 'cancelled'
                job.completed_at = timezone.now()
                job.error_message = data.get('message', 'Cancelled by signal')
                job.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
                
                _broadcast_training_event(job_id, 'training_cancelled', {
                    'job_id': str(job_id),
                    'message': job.error_message
                })
        
        # Wait for process to finish
        process.stdout.close()
        stderr = process.stderr.read()
        process.stderr.close()
        return_code = process.wait()
        
        if return_code != 0 and job.status == 'running':
            error_msg = stderr.strip() or f'Process exited with code {return_code}'
            job.status = 'failed'
            job.error_message = error_msg
            job.completed_at = timezone.now()
            job.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
            
            _broadcast_training_event(job_id, 'training_error', {
                'job_id': str(job_id),
                'error': error_msg,
                'return_code': return_code,
            })
    
    except SoftTimeLimitExceeded:
        if process:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        job.status = 'failed'
        job.error_message = 'Training exceeded time limit (2 hours)'
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
        
        _broadcast_training_event(job_id, 'training_error', {
            'job_id': str(job_id),
            'error': 'Training exceeded time limit (2 hours)',
        })
        raise
    
    except Exception as e:
        logger.exception(f"Training task {job_id} failed: {e}")
        if process:
            process.terminate()
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
        
        _broadcast_training_event(job_id, 'training_error', {
            'job_id': str(job_id),
            'error': str(e),
        })
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying training task {job_id}, attempt {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=300)
        return {'error': str(e)}
    
    finally:
        if process:
            TrainingTask._running_jobs.pop(job_id, None)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


@shared_task
def cancel_training_task(training_job_id: str):
    """
    Cancel a running training job by sending SIGTERM to the subprocess.

    Args:
        training_job_id: UUID primary key of the TrainingJob record

    Returns:
        dict with cancellation status
    """
    from training.models import TrainingJob
    job_id = training_job_id

    try:
        job = TrainingJob.objects.get(id=training_job_id)
        
        if job.status not in ['queued', 'running', 'preparing']:
            return {
                'job_id': str(job_id),
                'status': job.status,
                'message': 'Job is not in a cancellable state'
            }
        
        # If queued or preparing, just mark as cancelled directly
        if job.status in ['queued', 'preparing']:
            job.status = 'cancelled'
            job.completed_at = timezone.now()
            job.error_message = 'Cancelled before execution'
            job.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
            
            _broadcast_training_event(job_id, 'training_cancelled', {
                'job_id': str(job_id),
                'message': 'Cancelled before execution'
            })
            return {'job_id': str(job_id), 'status': 'cancelled'}
        
        # If running, terminate the subprocess
        if job_id in TrainingTask._running_jobs:
            process = TrainingTask._running_jobs[job_id]
            logger.info(f"Terminating training process for job {job_id}, PID: {process.pid}")
            
            # Send SIGTERM for graceful shutdown
            process.terminate()
            
            try:
                # Wait for graceful termination (10 seconds)
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination fails
                logger.warning(f"Graceful termination failed for job {job_id}, killing process")
                process.kill()
                process.wait()
            
            job.status = 'cancelled'
            job.completed_at = timezone.now()
            job.error_message = 'Cancelled by user'
            job.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
            
            _broadcast_training_event(job_id, 'training_cancelled', {
                'job_id': str(job_id),
                'message': 'Cancelled by user'
            })
            
            return {'job_id': str(job_id), 'status': 'cancelled'}
        
        # If process not found in registry but still running
        if job.status == 'running':
            job.status = 'cancelled'
            job.completed_at = timezone.now()
            job.error_message = 'Process not found (may have already completed)'
            job.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
            
            return {'job_id': str(job_id), 'status': 'cancelled', 'message': 'Job marked as cancelled'}
        
        return {'job_id': str(job_id), 'status': job.status, 'message': 'No action taken'}
    
    except (TrainingJob.DoesNotExist, ValueError):
        return {'error': f'TrainingJob {training_job_id} not found'}


def _broadcast_training_event(job_id: str, event_type: str, data: dict):
    """
    Broadcast a training event to WebSocket consumers.
    
    Args:
        job_id: Public job ID
        event_type: Type of event (e.g., 'training_started', 'epoch_complete')
        data: Event data payload
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'training_{job_id}',
                {
                    'type': f'training_{event_type}',
                    'data': data
                }
            )
    except Exception as e:
        # Don't let broadcast failures affect training
        logging.getLogger(__name__).warning(
            f"Failed to broadcast training event {event_type} for {job_id}: {e}"
        )


def get_training_job_status(training_job_id: str) -> dict:
    """
    Get current status of a training job.

    Args:
        training_job_id: UUID primary key of the TrainingJob record

    Returns:
        dict with job status information
    """
    from training.models import TrainingJob

    try:
        job = TrainingJob.objects.get(id=training_job_id)
        return {
            'id': str(job.id),
            'name': job.name,
            'status': job.status,
            'framework': job.framework,
            'progress': job.progress,
            'current_epoch': job.current_epoch,
            'total_epochs': job.total_epochs,
            'current_loss': job.current_loss,
            'current_metric': job.current_metric,
            'model_path': job.model_path,
            'error_message': job.error_message,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'duration_seconds': job.duration_seconds,
            'metrics_history': job.metrics_history,
        }
    except (TrainingJob.DoesNotExist, ValueError):
        return {'error': f'TrainingJob {training_job_id} not found'}


def list_training_jobs(framework: str = None, status: str = None, limit: int = 50) -> list:
    """
    List training jobs with optional filters.
    
    Args:
        framework: Filter by training framework
        status: Filter by job status
        limit: Maximum number of jobs to return
    
    Returns:
        list of job status dicts
    """
    from training.models import TrainingJob
    
    queryset = TrainingJob.objects.all()
    
    if framework:
        queryset = queryset.filter(framework=framework)
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset[:limit]

    results = []
    for job in queryset.only('id', 'name', 'status', 'framework', 'progress', 'created_at'):
        results.append({
            'id': str(job.id),
            'name': job.name,
            'status': job.status,
            'framework': job.framework,
            'progress': job.progress,
            'created_at': job.created_at.isoformat(),
        })
    return results
