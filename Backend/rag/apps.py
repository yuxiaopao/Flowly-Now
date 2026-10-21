"""
RAG app configuration.
"""

import os

from django.apps import AppConfig


class RagConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rag'
    verbose_name = 'RAG'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        from . import signals  # noqa: F401
