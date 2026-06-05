"""
Datasets app configuration.
"""

import os

from django.apps import AppConfig


class DatasetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'datasets'
    verbose_name = '数据集管理'
    path = os.path.dirname(os.path.abspath(__file__))
