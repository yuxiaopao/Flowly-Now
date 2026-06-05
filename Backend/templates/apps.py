"""
Templates app configuration.
"""

import os

from django.apps import AppConfig


class TemplatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'templates'
    verbose_name = 'Workflow Templates'
    path = os.path.dirname(os.path.abspath(__file__))
