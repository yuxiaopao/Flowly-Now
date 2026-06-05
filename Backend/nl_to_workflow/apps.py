import os

"""NL to Workflow app configuration."""

from django.apps import AppConfig


class NlToWorkflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nl_to_workflow'
    verbose_name = '自然语言生成工作流'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import nl_to_workflow.signals  # noqa
