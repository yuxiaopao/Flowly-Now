"""Only durable run identities cross the queue; never replay external effects on failure."""
import logging
from celery import shared_task
from .evaluation_constants import MESSAGES

logger = logging.getLogger(__name__)


@shared_task(name='applications.execute_evaluation', acks_late=False, max_retries=0)
def execute_application_evaluation(run_id):
    from .evaluation_service import execute_run, stop_run
    try:
        execute_run(run_id)
    except Exception as exc:
        logger.warning('Application evaluation %s stopped (%s)', run_id, type(exc).__name__)
        stop_run(run_id, failed=True, code='runner_failed', message=MESSAGES['execution'])
