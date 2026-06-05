import os

from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'
    verbose_name = '计费和订阅'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import billing.signals  # noqa
