"""
Users app configuration.
"""

import os

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'User Management'
    path = os.path.dirname(os.path.abspath(__file__))
