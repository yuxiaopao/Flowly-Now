import os

"""Agents app configuration."""

from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agents'
    verbose_name = 'AI Agent'
    path = os.path.dirname(os.path.abspath(__file__))
