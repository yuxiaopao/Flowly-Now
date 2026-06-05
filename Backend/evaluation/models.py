"""
Models for evaluation app.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class EvaluationJob(models.Model):
    """Records a model evaluation job."""

    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_id = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255)

    model_path = models.CharField(max_length=500)
    test_dataset_path = models.CharField(max_length=500, blank=True)

    metrics = models.JSONField(default=dict)
    metrics_history = models.JSONField(default=list)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='evaluation_jobs')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['job_id']), models.Index(fields=['status'])]
