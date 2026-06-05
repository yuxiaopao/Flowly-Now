"""
Monitoring models.
"""

import uuid

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ExecutionLog(models.Model):
    """Log of workflow executions."""

    LEVEL_CHOICES = [
        ('debug', '调试'),
        ('info', '信息'),
        ('warning', '警告'),
        ('error', '错误'),
    ]

    id = models.BigAutoField(primary_key=True)

    workflow_execution = models.ForeignKey(
        'workflows.WorkflowExecution',
        on_delete=models.CASCADE,
        related_name='monitoring_logs',
        verbose_name='工作流执行',
        db_index=True
    )
    node_execution = models.ForeignKey(
        'workflows.NodeExecution',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='monitoring_logs',
        verbose_name='节点执行'
    )

    node_id = models.CharField(max_length=100, blank=True, verbose_name='节点ID')
    node_name = models.CharField(max_length=200, blank=True, verbose_name='节点名称')

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='info',
        verbose_name='日志级别'
    )

    message = models.TextField(verbose_name='日志消息')
    details = models.JSONField(default=dict, blank=True, verbose_name='详细信息')

    source = models.CharField(max_length=50, null=True, blank=True, verbose_name='日志来源')

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间戳')

    class Meta:
        db_table = 'monitoring_execution_logs'
        verbose_name = '执行日志'
        verbose_name_plural = '执行日志'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['workflow_execution', '-timestamp']),
            models.Index(fields=['node_execution']),
            models.Index(fields=['level', '-timestamp']),
            models.Index(fields=['node_id']),
        ]

    def __str__(self):
        return f"[{self.level}] {self.message[:50]}"


class AlertRule(models.Model):
    """Alert rule configuration."""

    SEVERITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '严重'),
    ]

    CONDITION_CHOICES = [
        ('execution_failed', '执行失败'),
        ('execution_timeout', '执行超时'),
        ('error_rate_high', '错误率高'),
        ('execution_duration_high', '执行时间过长'),
        ('api_quota_exceeded', 'API配额超限'),
        ('user_quota_exceeded', '用户配额超限'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200, verbose_name='规则名称')
    description = models.TextField(blank=True, verbose_name='描述')

    condition = models.CharField(
        max_length=50,
        choices=CONDITION_CHOICES,
        verbose_name='触发条件'
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='medium',
        verbose_name='严重程度'
    )

    # Threshold settings
    threshold = models.IntegerField(default=1, verbose_name='阈值')
    time_window_minutes = models.IntegerField(default=5, verbose_name='时间窗口(分钟)')

    # Notification settings
    notify_email = models.BooleanField(default=True, verbose_name='邮件通知')
    notify_webhook = models.BooleanField(default=False, verbose_name='Webhook通知')
    webhook_url = models.URLField(max_length=500, blank=True, verbose_name='Webhook URL')

    # Status
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='alert_rules',
        null=True,
        blank=True,
        verbose_name='创建者'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'monitoring_alert_rules'
        verbose_name = '告警规则'
        verbose_name_plural = '告警规则'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_condition_display()})"


class Alert(models.Model):
    """Alert instance."""

    SEVERITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '严重'),
    ]

    STATUS_CHOICES = [
        ('active', '活跃'),
        ('acknowledged', '已确认'),
        ('resolved', '已解决'),
        ('muted', '已静默'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    rule = models.ForeignKey(
        AlertRule,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name='告警规则'
    )

    # Alert details
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        verbose_name='严重程度'
    )

    title = models.CharField(max_length=200, verbose_name='告警标题')
    message = models.TextField(verbose_name='告警消息')

    # Triggered by
    triggered_by_type = models.CharField(max_length=50, blank=True, verbose_name='触发对象类型')
    triggered_by_id = models.CharField(max_length=100, blank=True, verbose_name='触发对象ID')

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='状态'
    )

    # Resolution
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        verbose_name='解决人'
    )
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='解决时间')
    resolution_note = models.TextField(blank=True, verbose_name='解决备注')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='触发时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'monitoring_alerts'
        verbose_name = '告警'
        verbose_name_plural = '告警'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['severity', 'status']),
        ]

    def __str__(self):
        return f"{self.severity}: {self.title}"

    def resolve(self, user, note=''):
        """Mark alert as resolved."""
        self.status = 'resolved'
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_note = note
        self.save()


class Metric(models.Model):
    """Metrics data point."""

    METRIC_TYPE_CHOICES = [
        ('execution_count', '执行次数'),
        ('execution_duration', '执行时长'),
        ('execution_success_rate', '成功率'),
        ('api_call_count', 'API调用次数'),
        ('api_call_cost', 'API调用成本'),
        ('token_usage', 'Token使用量'),
        ('user_count', '用户数'),
        ('workflow_count', '工作流数'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    metric_type = models.CharField(
        max_length=50,
        choices=METRIC_TYPE_CHOICES,
        verbose_name='指标类型',
        db_index=True
    )

    value = models.FloatField(verbose_name='指标值')
    unit = models.CharField(max_length=50, blank=True, verbose_name='单位')

    # Dimension tags
    tags = models.JSONField(default=dict, verbose_name='标签')

    # Associated objects
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='metrics',
        verbose_name='用户'
    )
    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='metrics',
        verbose_name='工作流'
    )

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间戳')

    class Meta:
        db_table = 'monitoring_metrics'
        verbose_name = '指标'
        verbose_name_plural = '指标'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_type', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['workflow', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.metric_type}: {self.value}"


class NotificationChannel(models.Model):
    """Notification channel configuration."""

    TYPE_CHOICES = [
        ('email', '邮件'),
        ('webhook', 'Webhook'),
        ('slack', 'Slack'),
        ('discord', 'Discord'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200, verbose_name='通道名称')
    channel_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name='通道类型'
    )

    # Configuration
    config = models.JSONField(default=dict, verbose_name='配置')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_channels',
        verbose_name='创建者'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'monitoring_notification_channels'
        verbose_name = '通知通道'
        verbose_name_plural = '通知通道'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class Notification(models.Model):
    """User notification model."""

    TYPE_CHOICES = [
        ('info', '信息'),
        ('success', '成功'),
        ('warning', '警告'),
        ('error', '错误'),
        ('execution', '执行状态'),
        ('system', '系统通知'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='用户'
    )
    title = models.CharField(max_length=255, verbose_name='标题')
    content = models.TextField(blank=True, verbose_name='内容')
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='info',
        verbose_name='类型'
    )
    is_read = models.BooleanField(default=False, verbose_name='已读')
    link = models.CharField(max_length=500, blank=True, verbose_name='链接')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'monitoring_notifications'
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return self.title

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read', 'updated_at'])
