"""语创（FlowSpeak）应用配置 — 对话生成工作流。"""

import os

from django.apps import AppConfig


class NlToWorkflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nl_to_workflow'
    verbose_name = '语创'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import nl_to_workflow.signals  # noqa
