"""Training task cancellation must work across worker processes and terminal races."""
import io
import json
import threading
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, Mock, patch

import pytest
from celery.exceptions import Retry
from django.db import close_old_connections
from django.test import override_settings
from rest_framework.test import APIClient

from training.models import TrainingJob
from training.tasks import TrainingTask, cancel_training_task, run_training_task


@pytest.fixture
def job(db):
    return TrainingJob.objects.create(name='reliability', framework='pytorch', model_type='classifier')


def invoke_training(job_id):
    run_training_task.push_request(id='training-task', retries=0)
    try:
        return run_training_task.run(str(job_id), 'test-config.json')
    finally:
        run_training_task.pop_request()


class Process:
    def __init__(self, stdout=None):
        self.stdout = stdout or io.StringIO(json.dumps({'type': 'training_complete', 'model_path': 'model.pt'}) + '\n')
        self.stderr = io.StringIO('')
        self.returncode = None
        self.pid = 99999999
        self.terminated = threading.Event()

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = -15
        self.terminated.set()

    def kill(self):
        self.terminate()

    def wait(self, timeout=None):
        self.returncode = self.returncode or 0
        return self.returncode


@pytest.mark.django_db
def test_cancelled_delivery_does_not_launch_training(job):
    job.mark_cancelled()
    with patch('training.tasks.subprocess.Popen', return_value=Process()) as launch:
        result = invoke_training(job.pk)
    assert result['status'] == 'cancelled'
    launch.assert_not_called()


@pytest.mark.django_db
def test_duplicate_running_delivery_does_not_start_second_gpu_process(job):
    job.mark_running()
    with patch('training.tasks.subprocess.Popen', return_value=Process()) as launch:
        result = invoke_training(job.pk)
    assert result['status'] == 'running'
    launch.assert_not_called()


@pytest.mark.django_db
def test_cancel_on_another_worker_persists_request_until_owner_stops(job):
    job.mark_running()
    with patch.object(TrainingTask, '_running_jobs', {}):
        result = cancel_training_task.run(str(job.pk))
    job.refresh_from_db()
    assert result['status'] == 'cancelling'
    assert job.status == 'running'
    assert job.config.get('_cancel_requested_at')


@pytest.mark.django_db
@pytest.mark.parametrize('kind', ['generic', 'yolo'])
def test_completion_arriving_after_cancel_does_not_overwrite_cancellation(job, kind):
    job.training_kind = kind
    job.save(update_fields=['training_kind'])

    class CancellingOutput(io.StringIO):
        def readline(self, *args):
            with patch.object(TrainingTask, '_running_jobs', {}):
                cancel_training_task.run(str(job.pk))
            return super().readline(*args)

    process = Process(CancellingOutput(json.dumps({'type': 'training_complete', 'model_path': 'late.pt'}) + '\n'))
    with patch('training.tasks.subprocess.Popen', return_value=process):
        result = invoke_training(job.pk)
    job.refresh_from_db()
    assert result['status'] == 'cancelled'
    assert job.status == 'cancelled'
    assert job.model_path == ''
    assert process.terminated.is_set()


@pytest.mark.django_db
def test_normal_training_completion_is_preserved(job):
    with patch('training.tasks.subprocess.Popen', return_value=Process()):
        result = invoke_training(job.pk)
    job.refresh_from_db()
    assert result['status'] == 'completed'
    assert job.status == 'completed'
    assert job.model_path == 'model.pt'


@pytest.mark.django_db
def test_training_retry_stays_claimable_and_redelivery_can_finish(job):
    with patch('training.tasks.subprocess.Popen', side_effect=[OSError('temporary spawn error'), Process()]), \
            patch.object(run_training_task, 'retry', side_effect=Retry('retry')) as retry:
        with pytest.raises(Retry):
            invoke_training(job.pk)
        job.refresh_from_db()
        assert job.status == 'queued'
        assert job.completed_at is None
        assert invoke_training(job.pk)['status'] == 'completed'
    retry.assert_called_once()


@pytest.mark.django_db
def test_duplicate_task_completion_callback_does_not_fail_active_owner(job):
    job.mark_running()
    run_training_task.after_return('SUCCESS', {'job_id': str(job.pk), 'status': 'running'}, 'duplicate', [str(job.pk)], {}, None)
    job.refresh_from_db()
    assert job.status == 'running'


@pytest.mark.django_db
@pytest.mark.parametrize('status', ['completed', 'cancelled'])
def test_failure_callback_preserves_terminal_training_result(job, status):
    job.status = status
    job.save(update_fields=['status'])
    run_training_task.on_failure(RuntimeError('late failure'), 'task', [], {'training_job_id': str(job.pk)}, None)
    job.refresh_from_db()
    assert job.status == status


@pytest.mark.django_db
def test_failure_callback_uses_training_primary_key(job):
    job.mark_running()
    run_training_task.on_failure(RuntimeError('worker error'), 'task', [], {'training_job_id': str(job.pk)}, None)
    job.refresh_from_db()
    assert job.status == 'failed'
    assert job.error_message == 'worker error'


@pytest.mark.django_db
def test_clean_child_exit_without_completion_event_is_failed(job):
    with patch('training.tasks.subprocess.Popen', return_value=Process(io.StringIO('info only\n'))):
        invoke_training(job.pk)
    job.refresh_from_db()
    assert job.status == 'failed'
    assert 'without a completion event' in job.error_message


@pytest.mark.django_db
def test_explicit_retry_clears_previous_attempt_cancellation(job):
    job.mark_running()
    with patch.object(TrainingTask, '_running_jobs', {}):
        cancel_training_task.run(str(job.pk))
    from training.execution_control import finish_training_cancel
    finish_training_cancel(job.pk)
    # Both the existing generic retry endpoint and YOLO retry copy the stored config.
    job.refresh_from_db()
    job.status = 'queued'
    job.completed_at = None
    job.save()
    with patch('training.tasks.subprocess.Popen', return_value=Process()):
        assert invoke_training(job.pk)['status'] == 'completed'


@pytest.mark.django_db
def test_old_worker_cannot_complete_or_cancel_a_new_training_attempt(job):
    from training.execution_control import claim_training_run, finish_training_cancel

    class RetryingOutput(io.StringIO):
        def readline(self, *args):
            with patch.object(TrainingTask, '_running_jobs', {}):
                cancel_training_task.run(str(job.pk))
            finish_training_cancel(job.pk)
            TrainingJob.objects.filter(pk=job.pk).update(status='queued')
            _, claimed = claim_training_run(job.pk, 'new-worker')
            assert claimed
            return super().readline(*args)

    process = Process(RetryingOutput(json.dumps({'type': 'training_complete', 'model_path': 'old.pt'}) + '\n'))
    with patch('training.tasks.subprocess.Popen', return_value=process):
        result = invoke_training(job.pk)
    job.refresh_from_db()
    assert result['status'] == 'running'
    assert job.status == 'running'
    assert job.job_id == 'new-worker'
    assert job.model_path == ''


@pytest.mark.django_db
@pytest.mark.parametrize('kind,route', [('generic', 'training-jobs'), ('yolo', 'yolo-runs')])
@pytest.mark.parametrize('status', ['queued', 'running'])
def test_cancel_api_persists_control_without_waiting_for_a_worker_slot(job, user, kind, route, status):
    job.training_kind = kind
    job.created_by = user
    job.status = status
    job.save()
    client = APIClient()
    client.force_authenticate(user)
    with patch.object(cancel_training_task, 'delay', side_effect=AssertionError('all broker slots busy')) as enqueue:
        response = client.post(f'/api/v1/training/{route}/{job.pk}/cancel/')
    assert response.status_code == 200
    expected_status = 'cancelled' if status == 'queued' else 'cancelling'
    assert response.json()['data']['status'] == expected_status
    job.refresh_from_db()
    if status == 'running':
        assert job.config.get('_cancel_requested_at')
        assert job.status == 'running'
    else:
        assert job.status == 'cancelled'
    enqueue.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize('route', ['training-jobs', 'yolo-runs'])
def test_cancel_api_preserves_resource_ownership(job, user, route):
    job.training_kind = 'yolo'
    job.save()
    client = APIClient()
    client.force_authenticate(user)
    response = client.post(f'/api/v1/training/{route}/{job.pk}/cancel/')
    assert response.status_code == 404
    job.refresh_from_db()
    assert job.status == 'queued'


@pytest.mark.django_db
def test_cancel_api_rejects_completed_run(job, user):
    job.created_by = user
    job.status = 'completed'
    job.save()
    client = APIClient()
    client.force_authenticate(user)
    assert client.post(f'/api/v1/training/training-jobs/{job.pk}/cancel/').status_code == 400
    job.refresh_from_db()
    assert job.status == 'completed'


@pytest.mark.django_db
@pytest.mark.parametrize('route', ['training-jobs', 'yolo-runs'])
@pytest.mark.parametrize('status', ['queued', 'running'])
@pytest.mark.parametrize('use_record_id', [False, True])
def test_desktop_cancel_api_sends_stop_to_bound_device_and_waits_for_ack(job, user, route, status, use_record_id):
    from agents.desktop_jobs import desktop_agent_group
    from agents.models_desktop import DesktopAgent

    desktop = DesktopAgent.objects.create(agent_id='cancel-device', owner=user)
    job.training_kind = 'yolo'
    job.created_by = user
    job.job_id = 'manual-cancel-job'
    job.status = status
    job.config = {'desktop_agent_id': desktop.agent_id}
    if use_record_id:
        job.config['desktop_agent_record_id'] = str(desktop.pk)
    job.save()
    client = APIClient()
    client.force_authenticate(user)
    channel = Mock(group_send=AsyncMock())
    with patch('training.execution_control.get_channel_layer', return_value=channel):
        response = client.post(f'/api/v1/training/{route}/{job.pk}/cancel/')
    assert response.status_code == 200
    assert response.json()['data']['status'] == 'cancelling'
    channel.group_send.assert_awaited_once_with(desktop_agent_group(desktop.pk), {
        'type': 'training_command', 'command': 'stop',
        'job_id': str(job.pk), 'jobId': job.job_id,
    })
    job.refresh_from_db()
    assert job.status == status
    assert job.config['_cancel_requested_at']


@pytest.mark.django_db
def test_desktop_cancel_channel_failure_keeps_durable_request_for_retry(job, user):
    from agents.models_desktop import DesktopAgent

    desktop = DesktopAgent.objects.create(agent_id='cancel-failure-device', owner=user)
    job.created_by = user
    job.status = 'running'
    job.config = {'desktop_agent_record_id': str(desktop.pk)}
    job.save()
    client = APIClient()
    client.force_authenticate(user)
    channel = Mock(group_send=AsyncMock(side_effect=ConnectionError('channel offline')))
    with patch('training.execution_control.get_channel_layer', return_value=channel):
        response = client.post(f'/api/v1/training/training-jobs/{job.pk}/cancel/')
    assert response.status_code == 503
    job.refresh_from_db()
    assert job.status == 'running'
    assert job.config['_cancel_requested_at']


@pytest.mark.django_db
def test_desktop_cancel_does_not_fall_back_to_recreated_device(job, user):
    from agents.models_desktop import DesktopAgent

    deleted = DesktopAgent.objects.create(agent_id='reused-device', owner=user)
    old_pk = str(deleted.pk)
    deleted.delete()
    DesktopAgent.objects.create(agent_id='reused-device', owner=user)
    job.created_by = user
    job.status = 'running'
    job.config = {'desktop_agent_record_id': old_pk, 'desktop_agent_id': 'reused-device'}
    job.save()
    client = APIClient()
    client.force_authenticate(user)
    channel = Mock(group_send=AsyncMock())
    with patch('training.execution_control.get_channel_layer', return_value=channel):
        response = client.post(f'/api/v1/training/training-jobs/{job.pk}/cancel/')
    assert response.status_code == 503
    channel.group_send.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_desktop_cancel_reaches_socket_and_only_ack_finalizes_job(job, user):
    from agents.consumers import DesktopAgentConsumer
    from agents.models_desktop import DesktopAgent
    from training.consumers import TrainingConsumer

    desktop = DesktopAgent.objects.create(agent_id='socket-cancel-device', owner=user)
    job.created_by = user
    job.job_id = 'socket-cancel-job'
    job.status = 'running'
    job.config = {'desktop_agent_id': desktop.agent_id, 'desktop_agent_record_id': str(desktop.pk)}
    job.save()
    client = APIClient()
    client.force_authenticate(user)

    async def scenario():
        device = WebsocketCommunicator(DesktopAgentConsumer.as_asgi(), '/')
        device.scope.update(user=user, url_route={'kwargs': {'agent_id': desktop.agent_id}})
        subscriber = WebsocketCommunicator(TrainingConsumer.as_asgi(), '/')
        subscriber.scope.update(user=user, url_route={'kwargs': {'job_id': str(job.pk)}})
        assert (await device.connect())[0]
        await device.receive_json_from()
        assert (await subscriber.connect())[0]
        await subscriber.receive_json_from()
        response = await database_sync_to_async(client.post)(f'/api/v1/training/training-jobs/{job.pk}/cancel/')
        assert response.status_code == 200
        command = await device.receive_json_from()
        assert command['payload']['command'] == 'stop'
        await device.send_json_to({'type': 'training_complete', 'jobId': job.job_id, 'success': True})
        assert await subscriber.receive_nothing(timeout=0.05)
        await device.send_json_to({'type': 'training_cancelled', 'jobId': job.job_id})
        ack = await subscriber.receive_json_from()
        assert ack['type'] == 'training_cancelled'
        await subscriber.disconnect()
        await device.disconnect()

    async_to_sync(scenario)()
    job.refresh_from_db()
    assert job.status == 'cancelled'
    assert job.completed_at is not None


@pytest.mark.django_db(transaction=True)
@override_settings(TRAINING_CANCEL_POLL_SECONDS=0.01)
def test_owner_stops_silent_child_after_another_worker_requests_cancel(job):
    started = threading.Event()
    process = Process()

    class SilentOutput(io.StringIO):
        def readline(self, *args):
            started.set()
            assert process.terminated.wait(5), 'cancel never reached the process owner'
            return ''

    process.stdout = SilentOutput()

    def run_owner():
        close_old_connections()
        try:
            return invoke_training(job.pk)
        finally:
            close_old_connections()

    with patch('training.tasks.subprocess.Popen', return_value=process), ThreadPoolExecutor(max_workers=1) as pool:
        owner = pool.submit(run_owner)
        assert started.wait(5)
        with patch.object(TrainingTask, '_running_jobs', {}):
            result = cancel_training_task.run(str(job.pk))
        assert result['status'] == 'cancelling'
        assert owner.result(timeout=6)['status'] == 'cancelled'
    job.refresh_from_db()
    assert job.status == 'cancelled'
    assert process.terminated.is_set()
