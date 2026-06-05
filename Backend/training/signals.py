"""
Training Job Signals
Django signals for automatic job status updates.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TrainingJob


@receiver(post_save, sender=TrainingJob)
def training_job_saved(sender, instance, created, **kwargs):
    """
    Handle TrainingJob save events.
    Can be used for additional processing like notifications.
    """
    if created:
        pass
