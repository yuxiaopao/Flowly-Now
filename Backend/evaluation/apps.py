"""
Evaluation app configuration.
"""

from django.apps import AppConfig


class EvaluationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'evaluation'
    verbose_name = '模型评估'
