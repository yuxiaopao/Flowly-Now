import os

from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'integrations'
    verbose_name = '集成和Webhook'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import integrations.signals  # noqa
