"""
Annotations app configuration.
"""

import os

from django.apps import AppConfig


class AnnotationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'annotations'
    verbose_name = '数据标注'
    path = os.path.dirname(os.path.abspath(__file__))
