"""Celery autodiscovery entry for application delivery tasks."""
from .evaluation_tasks import execute_application_evaluation

__all__ = ['execute_application_evaluation']
