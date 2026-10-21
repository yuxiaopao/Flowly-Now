"""
Celery tasks for workflow execution and other background jobs.
"""

import json
import traceback as tb_module
import logging
import signal
import asyncio
from celery import shared_task, Task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .models import WorkflowExecution, Workflow
from .services.workflow_executor import WorkflowExecutor
from .services.context import ExecutionContext
from .execution_control import (
    claim_execution_for_run,
    recover_stale_running_executions,
    check_concurrency_allowed,
    has_resumable_snapshot,
)
from django.db.models import Q

logger = logging.getLogger(__name__)


class WorkflowTask(Task):
    """Base task class for workflow execution with timeout and retry support."""

    # Do NOT autoretry SoftTimeLimit / cooperative stops — handled explicitly below.
    autoretry_for = ()
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        try:
            execution_id = args[0] if args else kwargs.get('execution_id')
            if execution_id:
                execution = WorkflowExecution.objects.get(id=execution_id)
                # Interrupted/paused are intentional control states — do not mark failed
                if execution.status in ('paused', 'interrupted', 'cancelled', 'completed'):
                    return
                execution.mark_failed(
                    error_message=str(exc),
                    error_stack=str(einfo)
                )
                _broadcast_execution_event(execution_id, 'execution_error', {
                    'execution_id': execution_id,
                    'error': str(exc)
                })
        except Exception as e:
            logger.error(f"Failed to handle task failure: {e}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task retries."""
        try:
            execution_id = args[0] if args else kwargs.get('execution_id')
            if execution_id:
                execution = WorkflowExecution.objects.get(id=execution_id)
                _broadcast_execution_event(execution_id, 'execution_retry', {
                    'execution_id': execution_id,
                    'error': str(exc),
                    'retry_count': self.request.retries
                })
        except Exception as e:
            logger.error(f"Failed to handle task retry: {e}")


def _finalize_task_result(execution_id, execution):
    """Broadcast completion only for terminal success/failure (not pause/interrupt)."""
    status = execution.status
    if status in ('paused', 'interrupted'):
        _broadcast_execution_event(execution_id, f'execution_{status}', {
            'execution_id': execution_id,
            'status': status,
            'progress': execution.progress,
            'message': 'Checkpoint saved — call resume to continue',
        })
        return {
            'execution_id': execution_id,
            'status': status,
            'resumable': True,
            'progress': execution.progress,
        }

    _broadcast_execution_event(execution_id, 'execution_complete', {
        'execution_id': execution_id,
        'status': status,
        'output_data': execution.output_data,
        'duration': execution.duration,
        'progress': execution.progress
    })
    return {
        'execution_id': execution_id,
        'status': status,
        'output': execution.output_data
    }


@shared_task(
    bind=True,
    base=WorkflowTask,
    soft_time_limit=1800,
    time_limit=3600,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def execute_workflow_task(self, execution_id: int, parallel_enabled: bool = True):
    """
    Celery task for asynchronous workflow execution with timeout and retry support.

    Concurrent executions are isolated (separate WorkflowExecutor + LangChainService).
    Use worker concurrency > 1 (not solo) so multiple workflows can run in parallel.

    Args:
        execution_id: ID of the WorkflowExecution to run
        parallel_enabled: Enable parallel node execution
    """
    try:
        execution = WorkflowExecution.objects.select_related('workflow').get(id=execution_id)
        workflow = execution.workflow

        # Resume path: paused / interrupted continue from checkpoint
        if execution.status in ('paused', 'interrupted'):
            logger.info(f"Execution {execution_id} is {execution.status}, resuming...")
            return resume_workflow_task.run(execution_id, parallel_enabled=parallel_enabled)

        if execution.status == 'running' and has_resumable_snapshot(execution):
            from .execution_control import get_heartbeat_at, stale_running_minutes
            from datetime import timedelta
            hb = get_heartbeat_at(execution)
            ref = hb or execution.started_at
            stale = False
            if ref:
                if timezone.is_naive(ref):
                    ref = timezone.make_aware(ref, timezone.get_current_timezone())
                stale = ref < timezone.now() - timedelta(minutes=min(5, stale_running_minutes()))
            if stale:
                logger.info(
                    f"Execution {execution_id} redelivered stale running — resume from snapshot"
                )
                return resume_workflow_task.run(execution_id, parallel_enabled=parallel_enabled)
            logger.warning(
                f"Execution {execution_id} still looks alive (heartbeat); skip duplicate task"
            )
            return {
                'execution_id': execution_id,
                'status': 'running',
                'message': 'Execution already running on another worker',
            }

        if execution.status not in ['queued', 'pending']:
            logger.warning(f"Execution {execution_id} has status {execution.status}, skipping")
            return {
                'execution_id': execution_id,
                'status': execution.status,
                'message': 'Execution is not in queued/pending status'
            }

        ok_limit, limit_msg = check_concurrency_allowed(
            execution.workflow_id, exclude_execution_id=execution.id
        )
        if not ok_limit:
            # Stay queued — beat/recover or next schedule can pick up; avoid failing hard
            logger.warning('Concurrency limit for %s: %s', execution_id, limit_msg)
            execution.status = 'queued'
            execution.error_message = limit_msg
            execution.save(update_fields=['status', 'error_message'])
            raise self.retry(countdown=30, max_retries=20)

        ok, execution, claim_msg = claim_execution_for_run(
            execution_id,
            allowed_statuses=('queued', 'pending'),
            task_id=self.request.id,
        )
        if not ok:
            return {
                'execution_id': execution_id,
                'status': getattr(execution, 'status', None),
                'message': claim_msg,
            }

        workflow = execution.workflow

        _broadcast_execution_event(execution_id, 'execution_start', {
            'execution_id': execution_id,
            'workflow_id': workflow.id,
            'workflow_name': workflow.name,
            'status': 'running'
        })

        executor = WorkflowExecutor(workflow, execution, parallel_enabled=parallel_enabled)

        try:
            result = executor.execute(resume=False)
        except SoftTimeLimitExceeded:
            logger.error(f"Execution {execution_id} exceeded soft time limit — interrupting with checkpoint")
            try:
                executor.interrupt('Soft time limit exceeded — resume to continue')
            except Exception:
                execution.refresh_from_db()
                execution.mark_interrupted(
                    error_message='Soft time limit exceeded — resume to continue',
                    context_snapshot=execution.context_snapshot or {},
                )
            execution.refresh_from_db()
            return _finalize_task_result(execution_id, execution)

        execution.refresh_from_db()
        return _finalize_task_result(execution_id, execution)

    except WorkflowExecution.DoesNotExist:
        logger.error(f"Execution {execution_id} not found")
        return {
            'error': f'Execution {execution_id} not found'
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Soft time limit exceeded for execution {execution_id}")
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
            if execution.status not in ('paused', 'interrupted', 'cancelled', 'completed'):
                execution.mark_interrupted(
                    error_message='Execution exceeded soft time limit — resumable',
                    context_snapshot=execution.context_snapshot or {},
                )
            return _finalize_task_result(execution_id, execution)
        except Exception:
            pass
        return {'execution_id': execution_id, 'status': 'interrupted', 'resumable': True}

    except Exception as e:
        logger.exception(f"Execution {execution_id} failed: {e}")
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
            if execution.status in ('paused', 'interrupted', 'cancelled', 'completed'):
                return _finalize_task_result(execution_id, execution)

            execution.mark_failed(
                error_message=str(e),
                error_stack=tb_module.format_exc()
            )

            _broadcast_execution_event(execution_id, 'execution_error', {
                'execution_id': execution_id,
                'error': str(e)
            })

        except Exception as inner:
            logger.error(f"Failed to handle execution error for {execution_id}: {inner}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        return {
            'error': f'Execution {execution_id} failed after max retries',
            'exception': str(e)
        }


@shared_task(
    bind=True,
    base=WorkflowTask,
    soft_time_limit=3600,
    time_limit=7200
)
def execute_workflow_stream_task(self, execution_id: int, parallel_enabled: bool = True):
    """
    Execute workflow with streaming events.

    Args:
        execution_id: ID of the WorkflowExecution to run
        parallel_enabled: Enable parallel node execution
    """
    try:
        execution = WorkflowExecution.objects.select_related('workflow').get(id=execution_id)
        workflow = execution.workflow

        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.task_id = self.request.id
        execution.save()

        executor = WorkflowExecutor(workflow, execution, parallel_enabled=parallel_enabled)

        for event in executor.stream_execute():
            event_type = event.get('type', 'unknown')
            _broadcast_execution_event(execution_id, event_type, event)

        execution.refresh_from_db()

        return {
            'execution_id': execution_id,
            'status': execution.status,
            'output': execution.output_data
        }

    except WorkflowExecution.DoesNotExist:
        return {'error': f'Execution {execution_id} not found'}

    except SoftTimeLimitExceeded:
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
            execution.mark_interrupted(
                error_message='Execution exceeded soft time limit — resumable',
                context_snapshot=execution.context_snapshot or {},
            )
            _broadcast_execution_event(execution_id, 'execution_interrupted', {
                'execution_id': execution_id,
                'error': 'Soft time limit exceeded',
                'resumable': True,
            })
        except Exception:
            pass
        return {'execution_id': execution_id, 'status': 'interrupted', 'resumable': True}

    except Exception as e:
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
            execution.mark_failed(error_message=str(e))
            _broadcast_execution_event(execution_id, 'execution_error', {
                'execution_id': execution_id,
                'error': str(e)
            })
        except Exception as inner:
            logger.error(f"Failed to mark execution {execution_id} as failed: {inner}")
        return {'error': str(e)}


@shared_task(bind=True)
def pause_workflow_task(self, execution_id: int):
    """
    Request pause via DB. The running executor polls status and checkpoints out.
    """
    try:
        execution = WorkflowExecution.objects.get(id=execution_id)

        if execution.status != 'running':
            return {
                'execution_id': execution_id,
                'status': execution.status,
                'message': 'Execution is not running'
            }

        # Do not wipe context_snapshot — worker will write a real checkpoint
        execution.pause()

        _broadcast_execution_event(execution_id, 'execution_pause_requested', {
            'execution_id': execution_id,
            'status': 'paused',
            'paused_at': execution.paused_at.isoformat() if execution.paused_at else None,
        })

        return {
            'execution_id': execution_id,
            'status': 'paused',
            'message': 'Pause requested — worker will checkpoint and stop',
        }

    except WorkflowExecution.DoesNotExist:
        return {'error': f'Execution {execution_id} not found'}


@shared_task(
    bind=True,
    base=WorkflowTask,
    soft_time_limit=1800,
    time_limit=3600,
    acks_late=True,
    reject_on_worker_lost=True,
)
def resume_workflow_task(self, execution_id: int, parallel_enabled: bool = True):
    """
    Resume a paused or interrupted workflow execution from context_snapshot.
    """
    try:
        execution = WorkflowExecution.objects.select_related('workflow').get(id=execution_id)

        if execution.status not in ('paused', 'interrupted', 'running'):
            return {
                'execution_id': execution_id,
                'status': execution.status,
                'message': 'Execution is not resumable'
            }

        # running only allowed when continuing from snapshot after stale/redelivery
        if execution.status == 'running' and not has_resumable_snapshot(execution):
            return {
                'execution_id': execution_id,
                'status': execution.status,
                'message': 'Running execution has no resume snapshot'
            }

        allowed = ('paused', 'interrupted')
        if execution.status == 'running':
            allowed = ('running',)

        ok, execution, claim_msg = claim_execution_for_run(
            execution_id,
            allowed_statuses=allowed,
            task_id=getattr(self.request, 'id', None),
            require_snapshot=True,
        )
        if not ok:
            return {
                'execution_id': execution_id,
                'status': getattr(execution, 'status', None),
                'message': claim_msg,
            }

        workflow = execution.workflow

        _broadcast_execution_event(execution_id, 'execution_resume', {
            'execution_id': execution_id,
            'status': 'running'
        })

        executor = WorkflowExecutor(workflow, execution, parallel_enabled=parallel_enabled)

        try:
            executor.execute(resume=True)
        except SoftTimeLimitExceeded:
            logger.error(f"Resume of {execution_id} hit soft time limit — interrupting")
            try:
                executor.interrupt('Soft time limit during resume — checkpoint saved')
            except Exception:
                execution.mark_interrupted(
                    error_message='Soft time limit during resume',
                    context_snapshot=execution.context_snapshot or {},
                )
            execution.refresh_from_db()
            return _finalize_task_result(execution_id, execution)

        execution.refresh_from_db()
        return _finalize_task_result(execution_id, execution)

    except WorkflowExecution.DoesNotExist:
        return {'error': f'Execution {execution_id} not found'}
    except SoftTimeLimitExceeded:
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
            execution.mark_interrupted(
                error_message='Soft time limit during resume',
                context_snapshot=execution.context_snapshot or {},
            )
            return _finalize_task_result(execution_id, execution)
        except Exception:
            return {'execution_id': execution_id, 'status': 'interrupted', 'resumable': True}
    except Exception as e:
        logger.exception(f"Failed to resume execution {execution_id}: {e}")
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
            if execution.status not in ('paused', 'interrupted', 'cancelled', 'completed'):
                execution.mark_failed(error_message=str(e))
        except Exception:
            pass
        return {'error': str(e)}


@shared_task(bind=True)
def cancel_workflow_task(self, execution_id: int):
    """
    Cancel a running workflow execution (cooperative + soft revoke).
    """
    try:
        execution = WorkflowExecution.objects.get(id=execution_id)

        if execution.status in ('running', 'paused', 'interrupted', 'pending', 'queued'):
            execution.cancel()

            if execution.task_id:
                try:
                    from celery.result import AsyncResult
                    AsyncResult(execution.task_id).revoke(terminate=False)
                except Exception as revoke_err:
                    logger.warning(f"Failed to soft-revoke Celery task {execution.task_id}: {revoke_err}")

            _broadcast_execution_event(execution_id, 'execution_cancelled', {
                'execution_id': execution_id,
                'status': 'cancelled',
            })

            return {
                'execution_id': execution_id,
                'status': 'cancelled',
                'message': 'Cancel requested — worker stops on next control poll',
            }

        return {
            'execution_id': execution_id,
            'status': execution.status,
            'message': 'Execution is not running or paused'
        }

    except WorkflowExecution.DoesNotExist:
        return {
            'error': f'Execution {execution_id} not found'
        }


@shared_task(bind=True)
def recover_stale_executions_task(self, minutes: int = None):
    """
    Periodic: mark silent 'running' executions as interrupted (resumable).
    Schedule via Celery Beat every 5–10 minutes.
    """
    result = recover_stale_running_executions(minutes=minutes)
    logger.info(
        'Stale execution recovery: scanned=%s recovered=%s',
        result.get('scanned'), result.get('recovered_count'),
    )
    return result


@shared_task(bind=True)
def cleanup_old_executions(self, days: int = 30):
    """
    Clean up old execution records.

    Args:
        days: Number of days to keep execution records
    """
    cutoff_date = timezone.now() - timedelta(days=days)

    # Delete old completed/failed/cancelled executions
    deleted_count, _ = WorkflowExecution.objects.filter(
        status__in=['completed', 'failed', 'cancelled'],
        completed_at__lt=cutoff_date
    ).delete()

    return {'deleted_count': deleted_count}


@shared_task(bind=True)
def send_execution_notification(self, execution_id: int, notification_type: str):
    """
    Send notification about workflow execution.

    Args:
        execution_id: ID of the execution
        notification_type: Type of notification (email, webhook, etc.)
    """
    try:
        execution = WorkflowExecution.objects.select_related(
            'workflow', 'triggered_by'
        ).get(id=execution_id)

        notification_sent = False

        if notification_type == 'email' and execution.triggered_by:
            notification_sent = _send_email_notification(execution)

        elif notification_type == 'webhook':
            notification_sent = _send_webhook_notification(execution)

        elif notification_type == 'push':
            notification_sent = _send_push_notification(execution)

        return {
            'execution_id': execution_id,
            'notification_type': notification_type,
            'sent': notification_sent
        }

    except WorkflowExecution.DoesNotExist:
        return {
            'error': f'Execution {execution_id} not found'
        }


def _send_email_notification(execution):
    """Send email notification for execution."""
    try:
        from django.core.mail import send_mail

        subject = f"Workflow Execution {execution.status.title()}: {execution.workflow.name}"
        message = f"""
Workflow: {execution.workflow.name}
Status: {execution.status}
Started: {execution.started_at}
Completed: {execution.completed_at}
Duration: {execution.duration}s

{f'Error: {execution.error_message}' if execution.error_message else ''}
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[execution.triggered_by.email],
            fail_silently=False
        )

        return True
    except Exception:
        return False


def _send_webhook_notification(execution):
    """Send webhook notification for execution."""
    try:
        import httpx

        webhook_url = getattr(settings, 'EXECUTION_WEBHOOK_URL', None)
        if not webhook_url:
            return False

        payload = {
            'execution_id': execution.id,
            'workflow_name': execution.workflow.name,
            'status': execution.status,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'duration': execution.duration,
            'error': execution.error_message
        }

        response = httpx.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 200

    except Exception:
        return False


def _send_push_notification(execution):
    """Send push notification for execution via Firebase Cloud Messaging or configured provider."""
    try:
        push_config = getattr(settings, 'PUSH_NOTIFICATION_CONFIG', None)
        if not push_config:
            logger.debug("Push notification not configured, skipping")
            return False

        provider = push_config.get('provider', 'fcm').lower()

        if provider == 'fcm':
            return _send_fcm_notification(execution, push_config)
        elif provider == 'apns':
            return _send_apns_notification(execution, push_config)
        elif provider == 'webpush':
            return _send_webpush_notification(execution, push_config)
        else:
            logger.warning(f"Unknown push provider: {provider}")
            return False

    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False


def _send_fcm_notification(execution, config):
    """Send push notification via Firebase Cloud Messaging."""
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            cred = credentials.Certificate(config.get('credentials_file'))
            firebase_admin.initialize_app(cred)

        user = execution.triggered_by
        if not user or not getattr(user, 'fcm_token', None):
            return False

        status_emoji = {
            'completed': '\u2705',
            'failed': '\u274c',
            'cancelled': '\u23f8',
        }.get(execution.status, '\u23f3')

        message = messaging.Message(
            notification=messaging.Notification(
                title=f"{status_emoji} Workflow: {execution.workflow.name}",
                body=f"Status: {execution.status.title()} - {execution.duration or 0:.1f}s"
            ),
            data={
                'execution_id': str(execution.id),
                'workflow_id': str(execution.workflow.id),
                'status': execution.status,
                'type': 'execution_update'
            },
            token=user.fcm_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='workflow_icon',
                    color='#4F46E5'
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(badge=1)
                )
            )
        )
        response = messaging.send(message)
        logger.info(f"FCM notification sent: {response}")
        return True

    except ImportError:
        logger.warning("firebase-admin not installed, FCM push disabled")
        return False
    except Exception as e:
        logger.error(f"FCM notification failed: {e}")
        return False


def _send_apns_notification(execution, config):
    """Send push notification via Apple Push Notification Service."""
    try:
        from hyper import HTTPConnection

        user = execution.triggered_by
        if not user or not getattr(user, 'apns_token', None):
            return False

        payload = {
            'aps': {
                'alert': {
                    'title': f'Workflow: {execution.workflow.name}',
                    'body': f'Status: {execution.status.title()}'
                },
                'badge': 1,
                'sound': 'default'
            },
            'execution_id': str(execution.id),
            'workflow_id': str(execution.workflow.id),
            'status': execution.status
        }

        headers = {
            'content-type': 'application/json',
            'apns-topic': config.get('topic', 'com.flowly.app')
        }
        path = f"/3/device/{user.apns_token}"

        host = config.get('host', 'api.push.apple.com')
        conn = HTTPConnection(host)
        conn.request('POST', path, json.dumps(payload), headers)
        response = conn.getresponse()

        if response.status == 200:
            logger.info(f"APNS notification sent for execution {execution.id}")
            return True
        else:
            logger.warning(f"APNS returned {response.status}: {response.read()}")
            return False

    except ImportError:
        logger.warning("hyper not installed, APNS push disabled")
        return False
    except Exception as e:
        logger.error(f"APNS notification failed: {e}")
        return False


def _send_webpush_notification(execution, config):
    """Send Web Push notification via VAPID."""
    try:
        from py_vapid import Vapid
        from py_webpush import webpush

        user = execution.triggered_by
        if not user or not getattr(user, 'webpush_subscription', None):
            return False

        subscription = user.webpush_subscription
        payload = {
            'execution_id': str(execution.id),
            'workflow_id': str(execution.workflow.id),
            'status': execution.status,
            'workflow_name': execution.workflow.name
        }

        vapid_claims = {
            'sub': config.get('vapid_subject', 'mailto:admin@flowly.com'),
            'aud': config.get('vapid_audience')
        }

        vapid = Vapid()
        vapid.public_key = config.get('vapid_public_key')
        vapid.private_key = config.get('vapid_private_key')

        token = vapid.sign(vapid_claims)

        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=vapid.private_key,
            vapid_claims=vapid_claims,
            timeout=10
        )
        logger.info(f"WebPush notification sent for execution {execution.id}")
        return True

    except ImportError:
        logger.warning("py-webpush not installed, WebPush disabled")
        return False
    except Exception as e:
        logger.error(f"WebPush notification failed: {e}")
        return False


def _broadcast_execution_event(execution_id, event_type, data):
    """Broadcast execution event to WebSocket group."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'execution_{execution_id}',
                {
                    'type': f'execution_{event_type.replace("_", "_")}',
                    'data': data
                }
            )
    except Exception as e:
        logger.warning(f"Failed to broadcast event {event_type} for execution {execution_id}: {e}")


@shared_task
def execute_scheduled_workflow(workflow_id: int):
    """
    Execute a scheduled workflow.

    Args:
        workflow_id: ID of the workflow to execute
    """
    try:
        workflow = Workflow.objects.get(id=workflow_id, is_scheduled=True)

        # Create execution
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            trigger_type='scheduled',
            status='pending'
        )

        # Queue execution
        execute_workflow_task.delay(execution.id)

        return {
            'execution_id': execution.id,
            'workflow_id': workflow_id
        }

    except Workflow.DoesNotExist:
        return {
            'error': f'Workflow {workflow_id} not found or not scheduled'
        }


@shared_task
def check_workflow_schedules():
    """
    Check and trigger scheduled workflows.
    This should be run periodically (e.g., every minute).
    """
    from datetime import datetime

    now = timezone.now()

    # Find workflows that should run now
    workflows = Workflow.objects.filter(
        is_scheduled=True,
        schedule_type='interval',
        is_active=True
    )

    triggered = []

    for workflow in workflows:
        # Simple interval check (should be enhanced with proper scheduling)
        if workflow.next_run_at and workflow.next_run_at <= now:
            execute_scheduled_workflow.delay(workflow.id)
            triggered.append(workflow.id)

            # Update next run time
            if workflow.schedule_interval:
                workflow.next_run_at = now + timedelta(minutes=workflow.schedule_interval)
                workflow.save()

    return {'triggered_workflows': triggered}


@shared_task
def generate_execution_report(days: int = 7):
    """
    Generate execution statistics report.

    Args:
        days: Number of days to include in report
    """
    from django.db.models import Count, Avg, Sum

    cutoff = timezone.now() - timedelta(days=days)

    stats = WorkflowExecution.objects.filter(
        started_at__gte=cutoff
    ).aggregate(
        total=Count('id'),
        successful=Count('id', filter=Q(status='completed')),
        failed=Count('id', filter=Q(status='failed')),
        avg_duration=Avg('duration')
    )

    # By workflow
    by_workflow = WorkflowExecution.objects.filter(
        started_at__gte=cutoff
    ).values(
        'workflow__name'
    ).annotate(
        executions=Count('id'),
        successful=Count('id', filter=Q(status='completed')),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('-executions')

    return {
        'period_days': days,
        'stats': stats,
        'by_workflow': list(by_workflow),
        'generated_at': timezone.now().isoformat()
    }


@shared_task
def export_workflow_executions(workflow_id: int, format: str = 'json'):
    """
    Export workflow executions to file.

    Args:
        workflow_id: ID of the workflow
        format: Export format (json, csv)
    """
    try:
        from django.db.models import Q

        workflow = Workflow.objects.get(id=workflow_id)
        executions = WorkflowExecution.objects.filter(
            workflow=workflow
        ).order_by('-started_at')

        if format == 'json':
            data = [
                {
                    'id': e.id,
                    'status': e.status,
                    'trigger_type': e.trigger_type,
                    'started_at': e.started_at.isoformat() if e.started_at else None,
                    'completed_at': e.completed_at.isoformat() if e.completed_at else None,
                    'duration': e.duration,
                    'error': e.error_message
                }
                for e in executions
            ]
            return {'data': data, 'format': 'json'}

        elif format == 'csv':
            # Return CSV data
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Status', 'Trigger', 'Started', 'Completed', 'Duration', 'Error'])

            for e in executions:
                writer.writerow([
                    e.id,
                    e.status,
                    e.trigger_type,
                    e.started_at,
                    e.completed_at,
                    e.duration,
                    e.error_message or ''
                ])

            return {'data': output.getvalue(), 'format': 'csv'}

        return {'error': 'Unsupported format'}

    except Workflow.DoesNotExist:
        return {'error': f'Workflow {workflow_id} not found'}
