"""
Marketplace app configuration.
"""

import os

from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'
    verbose_name = '模板市场'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import marketplace.signals  # noqa
