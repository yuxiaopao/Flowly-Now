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
        ('cancelled', '已取消'),
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
    tenant = models.ForeignKey('tenants.Tenant', null=True, blank=True, on_delete=models.PROTECT, related_name='evaluation_jobs')
    training_job = models.ForeignKey('training.TrainingJob', null=True, blank=True, on_delete=models.SET_NULL, related_name='evaluations')
    dataset = models.ForeignKey('datasets.Dataset', null=True, blank=True, on_delete=models.SET_NULL, related_name='evaluations')
    training_dataset = models.ForeignKey('training.Dataset', null=True, blank=True, on_delete=models.SET_NULL, related_name='evaluations')
    workflow = models.ForeignKey('workflows.Workflow', null=True, blank=True, on_delete=models.SET_NULL, related_name='evaluation_jobs')
    node = models.ForeignKey('workflows.Node', null=True, blank=True, on_delete=models.SET_NULL, related_name='evaluation_jobs')
    execution = models.ForeignKey('workflows.WorkflowExecution', null=True, blank=True, on_delete=models.SET_NULL, related_name='evaluation_jobs')
    parameters = models.JSONField(default=dict, blank=True)
    artifact_snapshot = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    claim_token = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['job_id']), models.Index(fields=['status'])]
