"""
Monitoring app configuration.
"""

import os

from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    verbose_name = 'Monitoring & Analytics'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import monitoring.signals  # noqa
