import os

"""Prompts app configuration."""

from django.apps import AppConfig


class PromptsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prompts'
    verbose_name = '提示词模板'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import prompts.signals  # noqa
