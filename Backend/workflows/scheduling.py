"""
Workflow scheduling and trigger models.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class TriggerType(models.TextChoices):
    """Available trigger types."""
    MANUAL = 'manual', '手动触发'
    SCHEDULE = 'schedule', '定时触发'
    WEBHOOK = 'webhook', 'Webhook'
    EVENT = 'event', '事件触发'
    CRON = 'cron', 'Cron 表达式'


class TriggerStatus(models.TextChoices):
    """Trigger status."""
    ACTIVE = 'active', '活跃'
    PAUSED = 'paused', '暂停'
    DISABLED = 'disabled', '禁用'


class WorkflowTrigger(models.Model):
    """Workflow trigger configuration."""

    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.CASCADE,
        related_name='triggers',
        verbose_name='工作流'
    )

    name = models.CharField(max_length=200, verbose_name='触发器名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Trigger configuration
    trigger_type = models.CharField(
        max_length=20,
        choices=TriggerType.choices,
        default=TriggerType.MANUAL,
        verbose_name='触发类型'
    )

    # Schedule configuration (for schedule/cron triggers)
    schedule_type = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('once', '单次'),
            ('recurring', '循环'),
            ('cron', 'Cron 表达式')
        ],
        default='once',
        verbose_name='调度类型'
    )

    # For one-time triggers
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='计划执行时间')

    # For recurring triggers
    interval_seconds = models.IntegerField(null=True, blank=True, verbose_name='间隔(秒)')

    # For cron triggers
    cron_expression = models.CharField(max_length=100, blank=True, verbose_name='Cron 表达式')

    # Webhook configuration
    webhook_path = models.CharField(max_length=200, blank=True, verbose_name='Webhook 路径')
    webhook_secret = models.CharField(max_length=200, blank=True, verbose_name='Webhook 密钥')

    # Event configuration
    event_type = models.CharField(max_length=100, blank=True, verbose_name='事件类型')
    event_filter = models.JSONField(default=dict, blank=True, verbose_name='事件过滤条件')

    # Input mapping
    input_mapping = models.JSONField(default=dict, blank=True, verbose_name='输入映射')

    # Status
    status = models.CharField(
        max_length=20,
        choices=TriggerStatus.choices,
        default=TriggerStatus.ACTIVE,
        verbose_name='状态'
    )

    # Metadata
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    max_executions = models.IntegerField(null=True, blank=True, verbose_name='最大执行次数')
    execution_count = models.IntegerField(default=0, verbose_name='已执行次数')

    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_triggers',
        verbose_name='创建者'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    last_triggered_at = models.DateTimeField(null=True, blank=True, verbose_name='上次触发时间')

    class Meta:
        db_table = 'workflow_triggers'
        verbose_name = '工作流触发器'
        verbose_name_plural = '工作流触发器'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.workflow.name} - {self.name}"

    @property
    def can_execute(self):
        if not self.is_enabled:
            return False
        if self.status != TriggerStatus.ACTIVE:
            return False
        if self.max_executions and self.execution_count >= self.max_executions:
            return False
        return True

    @property
    def webhook_url(self):
        if self.trigger_type == TriggerType.WEBHOOK:
            return f"/api/webhooks/{self.webhook_path}"
        return None

    def increment_execution_count(self):
        self.execution_count += 1
        self.last_triggered_at = timezone.now()
        self.save(update_fields=['execution_count', 'last_triggered_at'])


class TriggerExecution(models.Model):
    """Log of trigger executions."""

    trigger = models.ForeignKey(
        WorkflowTrigger,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='触发器'
    )

    execution_id = models.CharField(max_length=100, verbose_name='执行ID')
    workflow_execution_id = models.CharField(max_length=100, blank=True, verbose_name='工作流执行ID')

    # Trigger details
    trigger_source = models.CharField(max_length=50, blank=True, verbose_name='触发来源')
    event_data = models.JSONField(default=dict, blank=True, verbose_name='事件数据')

    # Result
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '等待中'),
            ('running', '执行中'),
            ('success', '成功'),
            ('failed', '失败'),
            ('skipped', '跳过')
        ],
        default='pending',
        verbose_name='状态'
    )
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    # Timing
    queued_at = models.DateTimeField(auto_now_add=True, verbose_name='入队时间')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'trigger_executions'
        verbose_name = '触发器执行记录'
        verbose_name_plural = '触发器执行记录'
        ordering = ['-queued_at']

    def __str__(self):
        return f"{self.trigger.name} - {self.queued_at}"

    @property
    def duration_ms(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None


class Webhook(models.Model):
    """Webhook endpoint for external triggers."""

    name = models.CharField(max_length=200, verbose_name='名称')
    path = models.CharField(max_length=200, unique=True, verbose_name='路径')

    # Authentication
    auth_type = models.CharField(
        max_length=20,
        choices=[
            ('none', '无'),
            ('header', 'Header 认证'),
            ('signature', '签名认证')
        ],
        default='none',
        verbose_name='认证类型'
    )
    auth_secret = models.CharField(max_length=500, blank=True, verbose_name='认证密钥')

    # Workflow binding
    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.CASCADE,
        related_name='webhooks',
        verbose_name='工作流'
    )

    # Input mapping
    input_mapping = models.JSONField(default=dict, blank=True, verbose_name='输入映射')

    # Status
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    # Statistics
    total_calls = models.IntegerField(default=0, verbose_name='总调用次数')
    failed_calls = models.IntegerField(default=0, verbose_name='失败次数')

    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='webhooks',
        verbose_name='创建者'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workflow_webhooks'
        verbose_name = 'Webhook'
        verbose_name_plural = 'Webhooks'

    def __str__(self):
        return self.name

    @property
    def full_url(self):
        return f"/api/webhooks/{self.path}"

    def record_call(self, success=True):
        self.total_calls += 1
        if not success:
            self.failed_calls += 1
        self.save(update_fields=['total_calls', 'failed_calls'])
