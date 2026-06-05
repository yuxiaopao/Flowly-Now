"""
Website Generator app configuration.
"""

import os

from django.apps import AppConfig


class WebsiteGeneratorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'website_generator'
    verbose_name = '网站生成器'
    path = os.path.dirname(os.path.abspath(__file__))
