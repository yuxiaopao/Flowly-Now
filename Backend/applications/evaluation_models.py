"""Persistent cases and frozen regression evidence, independent of model benchmarking."""
import uuid
from django.conf import settings
from django.db import models


class ApplicationTestSuite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey('applications.Application', on_delete=models.PROTECT, related_name='test_suites')
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    revision = models.PositiveIntegerField(default=1)
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', 'id']


class ApplicationTestCase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    suite = models.ForeignKey(ApplicationTestSuite, on_delete=models.CASCADE, related_name='cases')
    name = models.CharField(max_length=160)
    input_data = models.JSONField(default=dict)
    assertions = models.JSONField(default=list)
    enabled = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', 'created_at', 'id']


class ApplicationEvaluationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey('applications.Application', on_delete=models.PROTECT, related_name='evaluation_runs')
    suite = models.ForeignKey(ApplicationTestSuite, on_delete=models.PROTECT, related_name='runs')
    suite_revision = models.PositiveIntegerField()
    suite_name = models.CharField(max_length=160)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    target = models.CharField(max_length=10, choices=[('draft', '当前草稿'), ('release', '发布版本')])
    release = models.ForeignKey('applications.ApplicationRelease', null=True, blank=True, on_delete=models.PROTECT, related_name='evaluation_runs')
    fingerprint = models.CharField(max_length=64)
    configuration = models.JSONField(default=dict)
    workflow_snapshot = models.ForeignKey('workflows.Workflow', null=True, blank=True, on_delete=models.PROTECT, related_name='evaluation_targets')
    workflow_manifest = models.JSONField(default=dict)
    corpus_signature = models.CharField(max_length=64, blank=True)
    final_corpus_signature = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=15, default='queued', db_index=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    total = models.PositiveIntegerField(default=0)
    passed = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    errors = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    idempotency_hash = models.CharField(max_length=64, null=True, blank=True)
    parameters_hash = models.CharField(max_length=64)
    runner_mode = models.CharField(max_length=10, default='celery')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    deadline_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at', 'id']
        constraints = [models.UniqueConstraint(fields=['application', 'idempotency_hash'], name='app_eval_idempotency_unique')]


class ApplicationEvaluationResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ApplicationEvaluationRun, on_delete=models.CASCADE, related_name='results')
    case = models.ForeignKey(ApplicationTestCase, null=True, blank=True, on_delete=models.SET_NULL, related_name='evaluation_results')
    case_id_snapshot = models.UUIDField()
    case_name = models.CharField(max_length=160)
    case_hash = models.CharField(max_length=64)
    position = models.PositiveIntegerField()
    input_data = models.JSONField(default=dict)
    assertions = models.JSONField(default=list)
    status = models.CharField(max_length=15, default='pending')
    request = models.ForeignKey('applications.ApplicationRequest', null=True, blank=True, on_delete=models.PROTECT, related_name='evaluation_results')
    assertion_results = models.JSONField(default=list)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['position', 'id']
        constraints = [models.UniqueConstraint(fields=['run', 'case_id_snapshot'], name='app_eval_case_unique')]
