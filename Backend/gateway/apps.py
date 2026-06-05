"""
Gateway app configuration.
"""

import os

from django.apps import AppConfig


class GatewayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gateway'
    verbose_name = 'AI网关'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import gateway.signals  # noqa
