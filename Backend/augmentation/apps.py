"""
Augmentation app configuration.
"""

import os

from django.apps import AppConfig


class AugmentationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'augmentation'
    verbose_name = '数据增强'
    path = os.path.dirname(os.path.abspath(__file__))
