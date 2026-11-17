"""Persist desktop progress for HTTP refreshes without trusting invalid telemetry."""
from copy import deepcopy

import pytest
from rest_framework.test import APIClient

from agents.consumers import DesktopAgentConsumer
from agents.desktop_jobs import (
    DESKTOP_AGENT_CONFIG_KEY, DESKTOP_AGENT_RECORD_CONFIG_KEY, apply_training_event,
)
from agents.models_desktop import DesktopAgent
from training.execution_control import CANCEL_REQUEST_KEY
from training.models import TrainingJob

pytestmark = pytest.mark.django_db


@pytest.fixture
def desktop(user):
    return DesktopAgent.objects.create(owner=user, agent_id='progress-device', status='online')


@pytest.fixture
def job(user, desktop):
    return TrainingJob.objects.create(created_by=user, status='running', progress=20,
                                      current_epoch=2, total_epochs=10, best_fitness=0.4,
                                      config={DESKTOP_AGENT_CONFIG_KEY: desktop.agent_id,
                                              DESKTOP_AGENT_RECORD_CONFIG_KEY: str(desktop.pk)})


def report(user, desktop, job, **fields):
    event = {'type': 'training_progress', 'jobId': str(job.pk), **fields}
    return apply_training_event(user, desktop.agent_id, event, agent_record_id=desktop.pk)


def test_valid_desktop_progress_is_available_after_http_refresh(user, desktop, job):
    event = {'type': 'training_progress', 'jobId': str(job.pk), 'running': True,
             'progress': 40.5, 'currentEpoch': 4, 'totalEpochs': 10, 'bestFitness': 0.8,
             'elapsedMs': 12_345, 'logs': ['raw desktop line']}
    original = deepcopy(event)
    assert apply_training_event(user, desktop.agent_id, event, agent_record_id=desktop.pk)
    job.refresh_from_db()
    assert (job.progress, job.current_epoch, job.total_epochs, job.best_fitness, job.duration_seconds) == (40, 4, 10, 0.8, 12)
    assert event == original
    client = APIClient()
    client.force_authenticate(user)
    response = client.get(f'/api/v1/training/training-jobs/{job.pk}/')
    assert response.status_code == 200
    data = response.json()['data']
    assert (data['progress'], data['current_epoch'], data['total_epochs']) == (40, 4, 10)


def test_snake_case_progress_fields_remain_supported(user, desktop, job):
    report(user, desktop, job, progress=60, current_epoch=6, total_epochs=12, best_fitness=0.9, elapsed_ms=22_000)
    job.refresh_from_db()
    assert (job.progress, job.current_epoch, job.total_epochs, job.best_fitness, job.duration_seconds) == (60, 6, 12, 0.9, 22)


@pytest.mark.parametrize('invalid', [
    pytest.param(True, id='boolean'), pytest.param('50', id='numeric-string'),
    pytest.param(float('nan'), id='nan'), pytest.param(float('inf'), id='infinity'),
    pytest.param(-1, id='negative'), pytest.param(10 ** 400, id='huge-integer'),
    pytest.param({}, id='object'), pytest.param([], id='array'),
])
def test_invalid_progress_fields_do_not_corrupt_persisted_state(user, desktop, job, invalid):
    report(user, desktop, job, progress=invalid, currentEpoch=invalid, totalEpochs=invalid,
           bestFitness=invalid, elapsedMs=invalid)
    job.refresh_from_db()
    assert (job.progress, job.current_epoch, job.total_epochs, job.best_fitness, job.duration_seconds) == (20, 2, 10, 0.4, 0)
    assert job.status == 'running'


def test_out_of_range_and_inconsistent_counters_are_rejected(user, desktop, job):
    report(user, desktop, job, progress=101, currentEpoch=11, totalEpochs=10, bestFitness=1.1)
    job.refresh_from_db()
    assert (job.progress, job.current_epoch, job.total_epochs, job.best_fitness) == (20, 2, 10, 0.4)
    report(user, desktop, job, currentEpoch=2.5, totalEpochs=0)
    job.refresh_from_db()
    assert (job.current_epoch, job.total_epochs) == (2, 10)


def test_delayed_progress_does_not_move_training_backwards(user, desktop, job):
    report(user, desktop, job, progress=50, currentEpoch=5, bestFitness=0.8, elapsedMs=5000)
    report(user, desktop, job, progress=10, currentEpoch=1, bestFitness=0.2, elapsedMs=1000)
    job.refresh_from_db()
    assert (job.progress, job.current_epoch, job.best_fitness, job.duration_seconds) == (50, 5, 0.8, 5)


@pytest.mark.parametrize('terminal', ['completed', 'failed', 'cancelled', 'timeout'])
def test_progress_cannot_change_a_terminal_training_result(user, desktop, job, terminal):
    job.status = terminal
    job.save(update_fields=['status'])
    assert report(user, desktop, job, running=True, progress=80, currentEpoch=8) is None
    job.refresh_from_db()
    assert (job.status, job.progress, job.current_epoch) == (terminal, 20, 2)


def test_progress_is_ignored_while_desktop_cancellation_awaits_ack(user, desktop, job):
    job.config[CANCEL_REQUEST_KEY] = 'requested'
    job.save(update_fields=['config'])
    assert report(user, desktop, job, running=True, progress=80, currentEpoch=8) is None
    job.refresh_from_db()
    assert (job.status, job.progress, job.current_epoch) == ('running', 20, 2)


@pytest.mark.parametrize('active', ['queued', 'running', 'validating', 'packaging'])
def test_reconnecting_desktop_keeps_busy_status(user, desktop, job, active):
    job.status = active
    job.save(update_fields=['status'])
    consumer = DesktopAgentConsumer()
    consumer.user = user
    consumer.agent_pk = desktop.pk
    consumer._update_agent_record(desktop.agent_id, 'host', 'win32', {'available': True}, ['training'])
    desktop.refresh_from_db()
    assert desktop.status == 'training'
    assert desktop.hostname == 'host'


def test_reconnecting_desktop_without_active_jobs_is_online(user, desktop, job):
    job.status = 'completed'
    job.save(update_fields=['status'])
    consumer = DesktopAgentConsumer()
    consumer.user = user
    consumer.agent_pk = desktop.pk
    consumer._update_agent_record(desktop.agent_id, 'host', 'win32', {}, [])
    desktop.refresh_from_db()
    assert desktop.status == 'online'


def test_progress_recovers_running_status_when_started_event_was_missed(user, desktop, job):
    job.status = 'queued'
    job.save(update_fields=['status'])
    report(user, desktop, job, running=True, currentEpoch=3, totalEpochs=10, progress=30)
    job.refresh_from_db()
    assert job.status == 'running'
    assert job.started_at is not None
    assert job.current_epoch == 3


def test_reconnecting_legacy_desktop_assignment_stays_busy(user, desktop, job):
    job.config.pop(DESKTOP_AGENT_RECORD_CONFIG_KEY)
    job.save(update_fields=['config'])
    consumer = DesktopAgentConsumer()
    consumer.user = user
    consumer.agent_pk = desktop.pk
    consumer._update_agent_record(desktop.agent_id, 'host', 'win32', {}, [])
    desktop.refresh_from_db()
    assert desktop.status == 'training'


def test_stale_record_assignment_does_not_occupy_recreated_device(user, desktop, job):
    from uuid import uuid4

    job.config[DESKTOP_AGENT_RECORD_CONFIG_KEY] = str(uuid4())
    job.save(update_fields=['config'])
    consumer = DesktopAgentConsumer()
    consumer.user = user
    consumer.agent_pk = desktop.pk
    consumer._update_agent_record(desktop.agent_id, 'host', 'win32', {}, [])
    desktop.refresh_from_db()
    assert desktop.status == 'online'
