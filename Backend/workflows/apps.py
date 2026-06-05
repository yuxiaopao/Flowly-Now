import os

"""Workflows app configuration."""

from django.apps import AppConfig


class WorkflowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workflows'
    verbose_name = '工作流'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        """Connect Django signals."""
        import workflows.signals  # noqa: F401
