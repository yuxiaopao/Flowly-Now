"""
Core application for shared models and utilities.
"""

import os

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = '核心模块'
    path = os.path.dirname(os.path.abspath(__file__))
