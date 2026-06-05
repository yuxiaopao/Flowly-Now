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
from pathlib import Path
from celery import shared_task, Task
from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


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
    
    _broadcast_training_event(job_id, 'training_started', {
        'job_id': str(job_id),
        'status': 'running',
        'message': 'Training started'
    })
    
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
                job.save(update_fields=['current_epoch', 'total_epochs', 'progress', 'updated_at'])
                
                _broadcast_training_event(job_id, 'epoch_start', {
                    'job_id': str(job_id),
                    'epoch': epoch,
                    'total_epochs': total,
                    'progress': progress,
                })
            
            elif event_type == 'epoch_complete':
                epoch = data.get('epoch', 0)
                total = data.get('total_epochs', 0)
                train_loss = data.get('train_loss')
                train_acc = data.get('train_acc')
                val_loss = data.get('val_loss')
                val_acc = data.get('val_acc')
                progress = data.get('progress', 0)
                
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
                
                # Add to metrics history
                job.add_metrics_entry(epoch, loss=train_loss, metric=val_acc)
                
                _broadcast_training_event(job_id, 'epoch_complete', {
                    'job_id': str(job_id),
                    'epoch': epoch,
                    'total_epochs': total,
                    'metrics': metrics,
                    'progress': progress,
                })
            
            elif event_type == 'training_complete':
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

    for job in queryset.only('id', 'name', 'status', 'framework', 'progress', 'created_at'):
        result.append({
            'id': str(job.id),
            'name': job.name,
            'status': job.status,
            'framework': job.framework,
            'progress': job.progress,
            'created_at': job.created_at.isoformat(),
        })
    return result
