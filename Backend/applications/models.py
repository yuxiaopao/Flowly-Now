"""Application configuration, immutable releases and attributable request records."""
from config.application_messages import MESSAGES
import hashlib
import secrets
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .constants import KEY_PREFIX


class Application(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='applications')
    tenant = models.ForeignKey('tenants.Tenant', null=True, blank=True, on_delete=models.PROTECT, related_name='applications')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=[('knowledge', '知识问答'), ('workflow', '工作流应用')])
    draft = models.JSONField(default=dict)
    active_release = models.ForeignKey('ApplicationRelease', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    required_evaluation_suite = models.ForeignKey('ApplicationTestSuite', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    tested_fingerprint = models.CharField(max_length=64, blank=True)
    last_test_status = models.CharField(max_length=20, blank=True)
    last_test_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class ApplicationRelease(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name='releases')
    version = models.PositiveIntegerField()
    fingerprint = models.CharField(max_length=64)
    configuration = models.JSONField()
    workflow_manifest = models.JSONField(default=dict)
    validated_by_request = models.ForeignKey('ApplicationRequest', null=True, blank=True,
        on_delete=models.PROTECT, related_name='validated_releases')
    validated_by_evaluation = models.ForeignKey('ApplicationEvaluationRun', null=True, blank=True,
        on_delete=models.PROTECT, related_name='validated_releases')
    workflow_snapshot = models.ForeignKey('workflows.Workflow', null=True, blank=True, on_delete=models.PROTECT, related_name='application_releases')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        constraints = [models.UniqueConstraint(fields=['application', 'version'], name='application_release_version_unique')]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(MESSAGES['immutable_release'])
        return super().save(*args, **kwargs)


class ApplicationAPIKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name='api_keys')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=32)
    key_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def digest(value):
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    @classmethod
    def issue(cls, **kwargs):
        value = KEY_PREFIX + secrets.token_urlsafe(32)
        return cls.objects.create(prefix=value[:24], key_hash=cls.digest(value), **kwargs), value

    @property
    def is_active(self):
        return not self.revoked_at and (not self.expires_at or self.expires_at > timezone.now())


class ApplicationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name='requests')
    release = models.ForeignKey(ApplicationRelease, null=True, blank=True, on_delete=models.PROTECT, related_name='requests')
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    api_key = models.ForeignKey(ApplicationAPIKey, null=True, blank=True, on_delete=models.PROTECT, related_name='requests')
    workflow_execution = models.ForeignKey('workflows.WorkflowExecution', null=True, blank=True, on_delete=models.PROTECT, related_name='application_requests')
    mode = models.CharField(max_length=10, choices=[('test', '测试'), ('invoke', '调用'), ('evaluation', '回归评测')])
    status = models.CharField(max_length=20, default='running', db_index=True)
    fingerprint = models.CharField(max_length=64, blank=True)
    workflow_manifest = models.JSONField(default=dict)
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(null=True, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    total_tokens = models.PositiveBigIntegerField(null=True, blank=True)
    cost = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    deadline_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    idempotency_hash = models.CharField(max_length=64, null=True, blank=True)
    http_status = models.PositiveSmallIntegerField(default=200)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['application', '-created_at'], name='app_request_created_idx')]
        constraints = [models.UniqueConstraint(fields=['application', 'idempotency_hash'], name='app_idempotency_unique')]


from .evaluation_models import (ApplicationTestSuite, ApplicationTestCase,
                                ApplicationEvaluationRun, ApplicationEvaluationResult)  # noqa: E402,F401
