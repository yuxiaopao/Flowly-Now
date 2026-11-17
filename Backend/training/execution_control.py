"""Persist training control across workers and protect terminal task results."""
import logging
import subprocess
import threading

import psutil
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import close_old_connections, connections, transaction
from django.utils import timezone

from .models import TrainingJob

logger = logging.getLogger(__name__)

CANCEL_REQUEST_KEY = '_cancel_requested_at'
CLAIMABLE_STATUSES = ('queued', 'provisioning', 'preparing')
ACTIVE_STATUSES = (*CLAIMABLE_STATUSES, 'running', 'validating', 'packaging')
TERMINAL_STATUSES = ('completed', 'failed', 'cancelled', 'timeout')
DEFAULT_CANCEL_POLL_SECONDS = 1.0
DEFAULT_TERMINATE_GRACE_SECONDS = 10.0
DESKTOP_CANCEL_UNAVAILABLE_MESSAGE = '取消请求已保存，但未能发送至桌面设备，请重试'


class TrainingStopped(Exception):
    """A persisted cancellation or terminal result supersedes this worker."""


@transaction.atomic
def claim_training_run(job_id, task_id):
    job = TrainingJob.objects.select_for_update().get(pk=job_id)
    if job.status not in CLAIMABLE_STATUSES:
        return job, False
    # A new queued attempt may reuse the previous attempt's config through retry.
    job.config = dict(job.config or {})
    job.config.pop(CANCEL_REQUEST_KEY, None)
    job.status = 'running'
    job.job_id = task_id or ''
    job.started_at = timezone.now()
    job.completed_at = None
    job.save(update_fields=['status', 'job_id', 'started_at', 'completed_at', 'config', 'updated_at'])
    return job, True


@transaction.atomic
def save_training_update(job, *, update_fields):
    """Serialize progress/completion against cancellation and other terminal writes."""
    current = TrainingJob.objects.select_for_update().get(pk=job.pk)
    if (current.job_id, current.started_at) != (job.job_id, job.started_at):
        raise TrainingStopped('Training attempt replaced')
    if current.status in TERMINAL_STATUSES or (current.config or {}).get(CANCEL_REQUEST_KEY):
        raise TrainingStopped(current.status)
    job.save(update_fields=update_fields)


@transaction.atomic
def request_training_cancel(job_id):
    job = TrainingJob.objects.select_for_update().get(pk=job_id)
    if job.status not in ACTIVE_STATUSES:
        return job, job.status
    record_id, agent_id = _desktop_assignment(job.config or {})
    if job.status in CLAIMABLE_STATUSES and not (record_id or agent_id):
        job.status = 'cancelled'
        job.completed_at = timezone.now()
        job.error_message = 'Cancelled before execution'
        job.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
        return job, 'cancelled'
    config = dict(job.config or {})
    config.setdefault(CANCEL_REQUEST_KEY, timezone.now().isoformat())
    job.config = config
    job.save(update_fields=['config', 'updated_at'])
    return job, 'cancelling'


def _desktop_assignment(config):
    from agents.desktop_jobs import DESKTOP_AGENT_CONFIG_KEY, DESKTOP_AGENT_RECORD_CONFIG_KEY

    return config.get(DESKTOP_AGENT_RECORD_CONFIG_KEY), config.get(DESKTOP_AGENT_CONFIG_KEY)


def dispatch_desktop_training_cancel(job):
    """Deliver a durable cancellation to the assigned desktop without a worker slot."""
    from agents.desktop_jobs import desktop_agent_group
    from agents.models_desktop import DesktopAgent

    record_id, agent_id = _desktop_assignment(job.config or {})
    if not record_id and not agent_id:
        return False
    agents = DesktopAgent.objects.filter(owner_id=job.created_by_id)
    agent = agents.filter(pk=record_id).first() if record_id else agents.filter(agent_id=agent_id).first()
    if agent is None:
        raise RuntimeError('Assigned desktop no longer exists')
    channel_layer = get_channel_layer()
    if channel_layer is None:
        raise RuntimeError('Desktop command channel unavailable')
    async_to_sync(channel_layer.group_send)(desktop_agent_group(agent.pk), {
        'type': 'training_command', 'command': 'stop',
        'job_id': str(job.pk), 'jobId': job.job_id or str(job.pk),
    })
    return True


def cancellation_requested(job_id, *, owner=None):
    current = TrainingJob.objects.filter(pk=job_id).values('status', 'config', 'job_id', 'started_at').first()
    if current is not None and owner is not None and (
        current['job_id'], current['started_at']
    ) != (owner.job_id, owner.started_at):
        return True
    return current is None or current['status'] in TERMINAL_STATUSES or bool(
        (current['config'] or {}).get(CANCEL_REQUEST_KEY)
    )


@transaction.atomic
def finish_training_cancel(job_id, *, owner=None):
    """Only the process owner acknowledges cancellation after stopping its child."""
    job = TrainingJob.objects.select_for_update().get(pk=job_id)
    if owner is not None and (job.job_id, job.started_at) != (owner.job_id, owner.started_at):
        return job
    if job.status not in TERMINAL_STATUSES:
        job.status = 'cancelled'
        job.completed_at = timezone.now()
        job.error_message = 'Cancelled by user'
        job.config = dict(job.config or {})
        job.config.pop(CANCEL_REQUEST_KEY, None)
        job.save(update_fields=['status', 'completed_at', 'error_message', 'config', 'updated_at'])
    return job


def terminate_training_process(process):
    """Stop the owned child and its data-loader children with a bounded grace period."""
    if process is None or process.poll() is not None:
        return
    grace = max(0.0, float(getattr(
        settings, 'TRAINING_TERMINATE_GRACE_SECONDS', DEFAULT_TERMINATE_GRACE_SECONDS,
    )))
    try:
        children = psutil.Process(process.pid).children(recursive=True)
    except (psutil.Error, OSError):
        children = []
    for child in children:
        try:
            child.terminate()
        except psutil.Error:
            pass
    try:
        process.terminate()
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=grace)
    except ProcessLookupError:
        pass
    _, alive = psutil.wait_procs(children, timeout=grace)
    for child in alive:
        try:
            child.kill()
        except psutil.Error:
            pass


class TrainingCancellationMonitor:
    """Poll durable control while the owner may be blocked reading a quiet child."""

    def __init__(self, job, process):
        self.job = job
        self.job_id = job.pk
        self.process = process
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._poll, name=f'training-control-{job.pk}', daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._done.set()
        self._thread.join()

    def _poll(self):
        interval = max(0.01, float(getattr(
            settings, 'TRAINING_CANCEL_POLL_SECONDS', DEFAULT_CANCEL_POLL_SECONDS,
        )))
        close_old_connections()
        try:
            while not self._done.wait(interval):
                if self.process.poll() is not None:
                    return
                try:
                    if cancellation_requested(self.job_id, owner=self.job):
                        terminate_training_process(self.process)
                        return
                except Exception:
                    logger.exception('Training cancellation poll failed for %s', self.job_id)
                    close_old_connections()
        finally:
            connections.close_all()
