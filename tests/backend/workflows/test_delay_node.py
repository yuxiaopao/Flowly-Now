"""Delay configurations are tested through the real node dispatcher and API."""
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from workflows.services.langchain_service import LangChainService


def test_registry_milliseconds_are_honored_by_the_real_dispatcher(monkeypatch):
    sleeps = []
    monkeypatch.setattr('time.sleep', sleeps.append)
    result = LangChainService().execute_node('delay', {'delayType': 'fixed', 'duration': 200, 'unit': 'ms'}, {})
    assert result['success'] is True
    assert sum(sleeps) == pytest.approx(.2)
    assert result['output']['seconds'] == pytest.approx(.2)


@pytest.mark.parametrize(('config', 'seconds'), [
    ({}, 1), ({'duration': 1, 'unit': 'seconds'}, 1),
    ({'duration': 2, 'unit': 'minutes'}, 120), ({'duration': 2, 'unit': 'hours'}, 7200),
    ({'duration': 1000, 'unit': 'ms'}, 1), ({'seconds': .25}, .25), ({'delay_seconds': '2.5'}, 2.5),
    ({'seconds': .5, 'delay_seconds': 90, 'duration': 30, 'unit': 'hours'}, .5),
    ({'seconds': 0}, 1), ({'seconds': -2}, 1), ({'seconds': 'invalid'}, 1),
    ({'seconds': None, 'delay_seconds': 2}, 1), ({'seconds': 7200}, 3600),
])
def test_fixed_units_and_legacy_seconds_keep_their_own_meaning(config, seconds, monkeypatch):
    sleeps = []
    monkeypatch.setattr('time.sleep', sleeps.append)
    result = LangChainService().execute_node('delay', config, {})
    assert result['success'] is True
    assert sum(sleeps) == pytest.approx(seconds)
    assert result['output']['seconds'] == pytest.approx(seconds)


@pytest.mark.parametrize('invalid', [
    {'duration': 0}, {'duration': -1}, {'duration': 3601}, {'duration': True}, {'duration': None},
    {'duration': 'abc'}, {'duration': 'NaN'}, {'duration': 'inf'}, {'duration': []},
    {'unit': 'days'}, {'unit': []}, {'delayType': 'unimplemented'},
    {'delayType': 'random', 'minDelay': 4, 'maxDelay': 2},
    {'delayType': 'random', 'minDelay': False}, {'delayType': 'random', 'maxDelay': float('inf')},
    {'hasTimeWindow': 'false'},
    {'hasTimeWindow': True, 'windowStart': '', 'windowEnd': '17:00'},
    {'hasTimeWindow': True, 'windowStart': '25:00', 'windowEnd': '17:00'},
    {'hasTimeWindow': True, 'windowStart': '9:00', 'windowEnd': '17:00'},
    {'hasTimeWindow': True, 'windowStart': '09:00', 'windowEnd': '09:00'},
    {'hasTimeWindow': True, 'windowStart': '09:00', 'windowEnd': '17:00', 'outsideWindowStrategy': 'other'},
])
def test_invalid_delay_never_sleeps_or_reports_success(invalid, monkeypatch):
    sleeps = []
    monkeypatch.setattr('time.sleep', sleeps.append)
    result = LangChainService().execute_node('delay', invalid, {})
    assert result['success'] is False and result['error']
    assert sleeps == []


def test_random_range_is_sampled_at_execution_and_respects_the_unit(monkeypatch):
    sleeps, bounds = [], []
    monkeypatch.setattr('time.sleep', sleeps.append)

    def draw(low, high):
        bounds.append((low, high))
        return 120

    monkeypatch.setattr('workflows.services.delay_node.random.uniform', draw)
    result = LangChainService().execute_node('delay', {'delayType': 'random', 'minDelay': 1,
        'maxDelay': 3, 'unit': 'minutes'}, {})
    assert result['success'] is True
    assert bounds == [(60, 180)] and sleeps == [120]
    assert result['output']['seconds'] == 120


@pytest.mark.parametrize(('now', 'start', 'end', 'strategy', 'expected'), [
    ('2026-10-31T08:30:00+08:00', '09:00', '17:00', 'wait', [1800, 2]),
    ('2026-10-31T17:00:00+08:00', '09:00', '17:00', 'wait', [57600, 2]),
    ('2026-10-31T09:00:00+08:00', '09:00', '17:00', 'wait', [2]),
    ('2026-10-31T08:30:00+08:00', '09:00', '17:00', 'skip', []),
    ('2026-10-31T08:30:00+08:00', '09:00', '17:00', 'execute', [2]),
    ('2026-10-31T23:00:00+08:00', '22:00', '06:00', 'wait', [2]),
    ('2026-11-01T01:00:00+08:00', '22:00', '06:00', 'wait', [2]),
    ('2026-11-01T06:00:00+08:00', '22:00', '06:00', 'wait', [57600, 2]),
])
def test_local_time_window_boundaries_and_every_outside_strategy(now, start, end, strategy, expected, monkeypatch):
    sleeps = []
    monkeypatch.setattr('time.sleep', sleeps.append)
    monkeypatch.setattr('workflows.services.delay_node.timezone.localtime', lambda: datetime.fromisoformat(now))
    result = LangChainService().execute_node('delay', {'duration': 2, 'unit': 'seconds', 'hasTimeWindow': True,
        'windowStart': start, 'windowEnd': end, 'outsideWindowStrategy': strategy}, {})
    assert result['success'] is True
    assert sleeps == expected
    assert result['output']['delayed'] == bool(expected)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('streaming', [False, True])
@pytest.mark.parametrize('control_status', ['paused', 'cancelled'])
def test_real_execution_wait_stops_and_pause_resumes_only_its_remaining_time(user, monkeypatch, streaming, control_status):
    from workflows.models import Workflow, Node, Edge, WorkflowExecution, NodeExecution
    from workflows.services.workflow_executor import WorkflowExecutor

    workflow = Workflow.objects.create(owner=user, name='Delay controls')
    start = Node.objects.create(workflow=workflow, node_type='start', name='Start')
    delay = Node.objects.create(workflow=workflow, node_type='delay', name='Wait', config={
        'duration': 1000, 'unit': 'ms', '_delay_control': 'forged', '_delay_resume': {'phase': 'delay', 'remaining_seconds': 0}})
    end = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=start, target_node=delay)
    Edge.objects.create(workflow=workflow, source_node=delay, target_node=end)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user)
    sleeps = []

    def control_after_one_quantum(seconds):
        sleeps.append(seconds)
        WorkflowExecution.objects.filter(pk=execution.pk).update(status=control_status)

    monkeypatch.setattr('time.sleep', control_after_one_quantum)
    executor = WorkflowExecutor(workflow, execution)
    events = list(executor.stream_execute()) if streaming else None
    if not streaming:
        executor.execute()
    execution.refresh_from_db()
    node = NodeExecution.objects.get(execution=execution, node=delay)
    assert sleeps == [.2]
    assert execution.status == control_status and node.status == 'pending' and node.completed_at is None
    assert node.output_data['_delay_state']['remaining_seconds'] == pytest.approx(.8)
    assert str(delay.pk) not in execution.context_snapshot['visited']
    assert str(delay.pk) in execution.context_snapshot['queue_node_ids']
    assert not NodeExecution.objects.filter(execution=execution, node=end).exists()
    if streaming:
        assert events[-1]['type'] == f'execution_{control_status}'
        assert not any(event['type'] == 'execution_complete' for event in events)
    if control_status == 'paused':
        resumed_sleeps = []
        monkeypatch.setattr('time.sleep', resumed_sleeps.append)
        WorkflowExecutor(workflow, execution).execute(resume=True)
        execution.refresh_from_db()
        node.refresh_from_db()
        assert execution.status == node.status == 'completed'
        assert sum(resumed_sleeps) == pytest.approx(.8)
        assert NodeExecution.objects.filter(execution=execution, node=end, status='completed').exists()


def test_total_deadline_caps_wait_and_does_not_report_a_shortened_success(monkeypatch):
    now = [datetime(2026, 10, 31, 12, tzinfo=ZoneInfo('Asia/Shanghai'))]
    sleeps = []
    monkeypatch.setattr('workflows.services.delay_node.timezone.now', lambda: now[0])

    def advance(seconds):
        sleeps.append(seconds)
        now[0] += timedelta(seconds=seconds)

    monkeypatch.setattr('time.sleep', advance)
    result = LangChainService().execute_node('delay', {'duration': 5, 'unit': 'seconds',
        '_execution_deadline_at': (now[0] + timedelta(seconds=.1)).isoformat()}, {})
    assert sleeps == [.1]
    assert result['success'] is False and '超时' in result['error']


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('streaming', [False, True])
def test_loop_delay_pause_resumes_current_item_without_repeating_prior_body_nodes(user, monkeypatch, streaming):
    from django.db.models.signals import post_save
    from workflows.models import Workflow, Node, Edge, WorkflowExecution, NodeExecution
    from workflows.services.workflow_executor import WorkflowExecutor

    workflow = Workflow.objects.create(owner=user, name='Loop delay resume')
    specs = [('start', {}), ('loop', {'items_source': 'config', 'items': ['first', 'second'], 'continue_on_error': True}),
        ('input', {'variable_name': 'input', 'required': False}), ('delay', {'duration': 1, 'unit': 'seconds'}),
        ('input', {'variable_name': 'input', 'required': False}), ('merge', {}), ('end', {})]
    nodes = [Node.objects.create(workflow=workflow, node_type=kind, name=f'{kind}-{index}', config=config)
        for index, (kind, config) in enumerate(specs)]
    for source, target in zip(nodes, nodes[1:]):
        Edge.objects.create(workflow=workflow, source_node=source, target_node=target)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user)
    completions = []

    def record_completed(sender, instance, **kwargs):
        if instance.execution_id == execution.pk and instance.status == 'completed':
            completions.append(instance.node_id)

    def pause(seconds):
        WorkflowExecution.objects.filter(pk=execution.pk).update(status='paused')

    post_save.connect(record_completed, sender=NodeExecution, weak=False)
    try:
        monkeypatch.setattr('time.sleep', pause)
        executor = WorkflowExecutor(workflow, execution)
        if streaming:
            assert list(executor.stream_execute())[-1]['type'] == 'execution_paused'
        else:
            executor.execute()
        execution.refresh_from_db()
        assert execution.status == 'paused'
        assert completions.count(nodes[2].pk) == 1
        assert completions.count(nodes[4].pk) == 0
        assert str(nodes[1].pk) not in execution.context_snapshot['visited']
        assert str(nodes[1].pk) in execution.context_snapshot['queue_node_ids']
        waits = []
        monkeypatch.setattr('time.sleep', waits.append)
        WorkflowExecutor(workflow, execution).execute(resume=True)
        execution.refresh_from_db()
        assert execution.status == 'completed', execution.error_message
        assert completions.count(nodes[2].pk) == completions.count(nodes[4].pk) == 2
        assert sum(waits) == pytest.approx(1.8)
        loop_output = NodeExecution.objects.get(execution=execution, node=nodes[1]).output_data
        assert loop_output['iterations'] == 2
        assert [item['item'] for item in loop_output['results']] == ['first', 'second']
    finally:
        post_save.disconnect(record_completed, sender=NodeExecution)


@pytest.mark.django_db(transaction=True)
def test_window_pause_rechecks_wall_clock_on_resume_instead_of_waiting_old_window_remainder(user, monkeypatch):
    from workflows.models import Workflow, Node, Edge, WorkflowExecution, NodeExecution
    from workflows.services.workflow_executor import WorkflowExecutor

    workflow = Workflow.objects.create(owner=user, name='Window control')
    delay = Node.objects.create(workflow=workflow, node_type='delay', name='Wait for opening', config={
        'duration': 1, 'unit': 'seconds', 'hasTimeWindow': True, 'windowStart': '09:00',
        'windowEnd': '17:00', 'outsideWindowStrategy': 'wait'})
    end = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=delay, target_node=end)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user)
    now = [datetime(2026, 10, 31, 8, 30, tzinfo=ZoneInfo('Asia/Shanghai'))]
    monkeypatch.setattr('workflows.services.delay_node.timezone.localtime', lambda: now[0])
    monkeypatch.setattr('time.sleep', lambda seconds: WorkflowExecution.objects.filter(pk=execution.pk).update(status='paused'))
    WorkflowExecutor(workflow, execution).execute()
    execution.refresh_from_db()
    delay_execution = NodeExecution.objects.get(execution=execution, node=delay)
    assert execution.status == 'paused'
    assert delay_execution.output_data['_delay_state']['phase'] == 'window'
    assert delay_execution.output_data['_delay_state']['remaining_seconds'] == pytest.approx(1799.8)
    now[0] += timedelta(minutes=31)
    waits = []
    monkeypatch.setattr('time.sleep', waits.append)
    WorkflowExecutor(workflow, execution).execute(resume=True)
    execution.refresh_from_db()
    assert execution.status == 'completed'
    assert sum(waits) == pytest.approx(1)


@pytest.mark.django_db(transaction=True)
def test_real_workflow_timeout_during_delay_stays_timeout_without_running_the_end(user, monkeypatch):
    from workflows.models import Workflow, Node, Edge, WorkflowExecution
    from workflows.services.workflow_executor import WorkflowExecutor

    workflow = Workflow.objects.create(owner=user, name='Bounded delay')
    delay = Node.objects.create(workflow=workflow, node_type='delay', name='Delay', config={'duration': 10, 'unit': 'seconds'})
    end = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=delay, target_node=end)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user)
    now = [datetime(2026, 10, 31, 12, tzinfo=ZoneInfo('Asia/Shanghai'))]
    monkeypatch.setattr('workflows.services.delay_node.timezone.now', lambda: now[0])
    waits = []

    def advance(seconds):
        waits.append(seconds)
        now[0] += timedelta(seconds=seconds)

    monkeypatch.setattr('time.sleep', advance)
    WorkflowExecutor(workflow, execution, deadline_at=now[0] + timedelta(seconds=.3)).execute()
    execution.refresh_from_db()
    assert sum(waits) == pytest.approx(.3)
    assert execution.status == 'timeout' and '超时' in execution.error_message
    assert not execution.node_executions.filter(node=end).exists()


@pytest.mark.django_db(transaction=True)
def test_routed_sse_observes_real_two_hundred_millisecond_delay_and_invalid_preflight(user, authenticated_client):
    import json
    import time
    from asgiref.sync import async_to_sync
    from workflows.models import Workflow, Node, Edge, WorkflowExecution

    workflow = Workflow.objects.create(owner=user, name='Actual 200ms')
    delay = Node.objects.create(workflow=workflow, node_type='delay', name='Actual wait', config={
        'delayType': 'fixed', 'duration': 200, 'unit': 'ms'})
    end = Node.objects.create(workflow=workflow, node_type='end', name='End')
    Edge.objects.create(workflow=workflow, source_node=delay, target_node=end)
    url = f'/api/v1/workflows/{workflow.pk}/stream_execute/'
    response = authenticated_client.post(url, {'input_data': {}}, format='json')
    assert response.status_code == 200

    async def read():
        received = []
        async for frame in response.streaming_content:
            received.append((time.monotonic(), json.loads(frame.decode().removeprefix('data: ').strip())))
        return received

    frames = async_to_sync(read)()
    assert .15 <= frames[-1][0] - frames[0][0] < 5
    assert frames[0][1]['type'] == 'execution_start'
    assert frames[-1][1]['type'] == 'execution_complete'
    result = next(event for _, event in frames if event['type'] == 'node_complete' and event['node_id'] == str(delay.pk))
    assert result['output']['seconds'] == .2
    assert WorkflowExecution.objects.get(workflow=workflow).status == 'completed'
    delay.config = {'duration': 0, 'unit': 'invalid'}
    delay.save(update_fields=['config'])
    invalid = authenticated_client.post(url, {'input_data': {}}, format='json')
    assert invalid.status_code == 400 and invalid.data['code'] == 'workflow_validation'
    assert invalid.data['node_issues'][0]['code'] == 'delay_configuration'
    assert WorkflowExecution.objects.filter(workflow=workflow).count() == 1


@pytest.mark.django_db(transaction=True)
def test_parallel_delay_pause_preserves_completed_sibling_and_resumes_unfinished_wait(user, monkeypatch):
    from django.db import connection
    if connection.vendor == 'sqlite':
        pytest.skip('并行暂停/恢复依赖服务端数据库的行级锁语义；SQLite 单写者限制会导致 table locked')
    import threading
    from django.db.models.signals import post_save
    from workflows.models import Workflow, Node, Edge, WorkflowExecution, NodeExecution
    from workflows.services.workflow_executor import WorkflowExecutor

    workflow = Workflow.objects.create(owner=user, name='Parallel delay pause')
    start = Node.objects.create(workflow=workflow, node_type='start', name='Start')
    delay = Node.objects.create(workflow=workflow, node_type='delay', name='Wait', config={'duration': 1})
    sibling = Node.objects.create(workflow=workflow, node_type='input', name='Sibling', config={'required': False})
    end = Node.objects.create(workflow=workflow, node_type='end', name='End')
    for source, target in ((start, delay), (start, sibling), (delay, end), (sibling, end)):
        Edge.objects.create(workflow=workflow, source_node=source, target_node=target)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user)
    sibling_done = threading.Event()
    sibling_completions = []

    def completed(sender, instance, **kwargs):
        if instance.execution_id == execution.pk and instance.node_id == sibling.pk and instance.status == 'completed':
            sibling_completions.append(instance.pk)
            sibling_done.set()

    def pause(seconds):
        assert sibling_done.wait(5)
        WorkflowExecution.objects.filter(pk=execution.pk).update(status='paused')

    post_save.connect(completed, sender=NodeExecution, weak=False)
    try:
        monkeypatch.setattr('time.sleep', pause)
        WorkflowExecutor(workflow, execution, parallel_enabled=True).execute()
        execution.refresh_from_db()
        assert execution.status == 'paused'
        assert NodeExecution.objects.get(execution=execution, node=delay).status == 'pending'
        assert str(delay.pk) not in execution.context_snapshot['visited']
        assert str(sibling.pk) in execution.context_snapshot['visited']
        resumed = []
        monkeypatch.setattr('time.sleep', resumed.append)
        WorkflowExecutor(workflow, execution, parallel_enabled=True).execute(resume=True)
        execution.refresh_from_db()
        assert execution.status == 'completed', execution.error_message
        assert sum(resumed) == pytest.approx(.8)
        assert len(sibling_completions) == 1
    finally:
        post_save.disconnect(completed, sender=NodeExecution)
