"""
Admin app configuration.
"""

import os

from django.apps import AppConfig


class AdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin'
    label = 'flowly_admin'
    verbose_name = '系统管理'
    path = os.path.dirname(os.path.abspath(__file__))
