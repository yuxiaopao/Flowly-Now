import os

from django.apps import AppConfig


class BrandingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'branding'
    verbose_name = '品牌定制'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import branding.signals  # noqa
