"""Shared absolute deadlines; stopping result acceptance cannot undo external effects."""
from config.application_messages import MESSAGES
from datetime import datetime
from django.utils import timezone


class ExecutionDeadlineExceeded(TimeoutError):
    pass


def remaining_seconds(deadline):
    if isinstance(deadline, str):
        deadline = datetime.fromisoformat(deadline)
    seconds = (deadline - timezone.now()).total_seconds()
    if seconds <= 0:
        raise ExecutionDeadlineExceeded(MESSAGES['deadline'])
    return seconds
