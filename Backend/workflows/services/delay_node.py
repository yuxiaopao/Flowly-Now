"""Normalize both published delay formats and execute the configured schedule."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as datetime_timezone
import math
import random
import re
import time

from django.utils import timezone

from .execution_budget import remaining_seconds
from .execution_errors import WorkflowExecutionError

DEFAULT_SECONDS = 1.0
LEGACY_MAX_SECONDS = 3600.0
MIN_UI_DURATION = 1.0
MAX_UI_DURATION = 3600.0
CONTROL_POLL_SECONDS = .2
DEFAULT_RANDOM_MAX = 10.0
UNIT_SECONDS = {'ms': .001, 'seconds': 1.0, 'minutes': 60.0, 'hours': 3600.0}
WINDOW_STRATEGIES = frozenset(('wait', 'skip', 'execute'))
TIME_PATTERN = re.compile(r'(?:[01]\d|2[0-3]):[0-5]\d')


@dataclass(frozen=True)
class DelayPlan:
    seconds: float
    delay_type: str
    maximum_seconds: float = None
    window_start: object = None
    window_end: object = None
    outside_strategy: str = 'wait'

    def window_wait_seconds(self, now):
        if self.window_start is None:
            return 0.0
        current = now.time().replace(tzinfo=None)
        inside = (self.window_start <= current < self.window_end if self.window_start < self.window_end
                  else current >= self.window_start or current < self.window_end)
        if inside:
            return 0.0
        date = now.date() if current < self.window_start else now.date() + timedelta(days=1)
        next_start = timezone.make_aware(datetime.combine(date, self.window_start), now.tzinfo)
        return (next_start.astimezone(datetime_timezone.utc) - now.astimezone(datetime_timezone.utc)).total_seconds()


class DelayWaitStopped(WorkflowExecutionError):
    """A paused/cancelled wait is control flow, never node failure or success."""
    def __init__(self, state):
        super().__init__('延迟等待已暂停或取消。', 'execution_control')
        self.state = state
        self.resume_node_ids = set()


def _duration(config, field, default):
    value = config.get(field, default)
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f'{field} 必须是 {MIN_UI_DURATION:g} 至 {MAX_UI_DURATION:g} 的有限数值。')
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f'{field} 必须是有效数值。') from None
    if not math.isfinite(value) or not MIN_UI_DURATION <= value <= MAX_UI_DURATION:
        raise ValueError(f'{field} 必须是 {MIN_UI_DURATION:g} 至 {MAX_UI_DURATION:g} 的有限数值。')
    return value


def normalize_delay(config):
    """Legacy seconds keep their original priority, fallback and one-hour cap."""
    maximum_seconds = None
    if 'seconds' in config or 'delay_seconds' in config:
        try:
            seconds = float(config.get('seconds', config.get('delay_seconds', DEFAULT_SECONDS)))
        except (ValueError, TypeError, OverflowError):
            seconds = DEFAULT_SECONDS
        if math.isnan(seconds):
            raise ValueError('seconds 必须是有效数值。')
        seconds = DEFAULT_SECONDS if seconds <= 0 else min(seconds, LEGACY_MAX_SECONDS)
        delay_type = 'fixed'
    else:
        unit = config.get('unit', 'seconds')
        if not isinstance(unit, str) or unit not in UNIT_SECONDS:
            raise ValueError('延迟单位必须是 ms、seconds、minutes 或 hours。')
        delay_type = config.get('delayType', 'fixed')
        if delay_type == 'fixed':
            seconds = _duration(config, 'duration', DEFAULT_SECONDS) * UNIT_SECONDS[unit]
        elif delay_type == 'random':
            low = _duration(config, 'minDelay', MIN_UI_DURATION)
            high = _duration(config, 'maxDelay', DEFAULT_RANDOM_MAX)
            if low > high:
                raise ValueError('最小延迟不能大于最大延迟。')
            seconds, maximum_seconds = low * UNIT_SECONDS[unit], high * UNIT_SECONDS[unit]
        else:
            raise ValueError('延迟类型必须是 fixed 或 random。')
    window_enabled = config.get('hasTimeWindow', False)
    if not isinstance(window_enabled, bool):
        raise ValueError('hasTimeWindow 必须是布尔值。')
    start = end = None
    strategy = config.get('outsideWindowStrategy', 'wait')
    if window_enabled:
        for field in ('windowStart', 'windowEnd'):
            value = config.get(field)
            if not isinstance(value, str) or not TIME_PATTERN.fullmatch(value):
                raise ValueError(f'{field} 必须是 HH:mm 格式的有效时间。')
        start = datetime.strptime(config['windowStart'], '%H:%M').time()
        end = datetime.strptime(config['windowEnd'], '%H:%M').time()
        if start == end:
            raise ValueError('执行窗口开始和结束时间不能相同。')
        if not isinstance(strategy, str) or strategy not in WINDOW_STRATEGIES:
            raise ValueError('窗口外策略必须是 wait、skip 或 execute。')
    return DelayPlan(seconds, delay_type, maximum_seconds, start, end, strategy)


def execute_delay(config, *, control=None, resume=None):
    plan = normalize_delay(config)
    if isinstance(resume, dict) and resume.get('phase') in ('window', 'delay'):
        seconds = float(resume['seconds'])
    else:
        seconds = random.uniform(plan.seconds, plan.maximum_seconds) if plan.maximum_seconds is not None else plan.seconds
    window_wait = plan.window_wait_seconds(timezone.localtime())
    if isinstance(resume, dict) and resume.get('phase') == 'delay':
        window_wait = 0.0
    if window_wait and plan.outside_strategy == 'skip':
        return {'success': True, 'output': {'delayed': False, 'seconds': 0.0,
            'reason': config.get('reason', 'Workflow delay'), 'window_skipped': True,
            'resumed_at': timezone.localtime().isoformat()}}
    if plan.outside_strategy == 'execute':
        window_wait = 0.0
    deadline = config.get('_execution_deadline_at')

    def wait(duration, phase):
        remaining = duration
        while remaining > 0:
            if control and control():
                raise DelayWaitStopped({'phase': phase, 'seconds': seconds, 'remaining_seconds': remaining})
            interval = min(remaining, CONTROL_POLL_SECONDS) if control else remaining
            if deadline:
                interval = min(interval, remaining_seconds(deadline))
            time.sleep(interval)
            remaining = max(0.0, remaining - interval)
            if deadline:
                remaining_seconds(deadline)
    wait(window_wait, 'window')
    remaining_delay = resume['remaining_seconds'] if isinstance(resume, dict) and resume.get('phase') == 'delay' else seconds
    wait(remaining_delay, 'delay')
    return {'success': True, 'output': {'delayed': True, 'seconds': seconds,
        'reason': config.get('reason', 'Workflow delay'), 'window_wait_seconds': window_wait,
        'resumed_at': timezone.localtime().isoformat()}}
