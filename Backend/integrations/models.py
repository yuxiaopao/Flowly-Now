"""
Webhook integration models for external system integration.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class WebhookEvent(models.TextChoices):
    """Webhook event types."""
    WORKFLOW_STARTED = 'workflow.started', '工作流开始'
    WORKFLOW_COMPLETED = 'workflow.completed', '工作流完成'
    WORKFLOW_FAILED = 'workflow.failed', '工作流失败'
    EXECUTION_STARTED = 'execution.started', '执行开始'
    EXECUTION_COMPLETED = 'execution.completed', '执行完成'
    EXECUTION_FAILED = 'execution.failed', '执行失败'
    AGENT_STARTED = 'agent.started', 'Agent开始'
    AGENT_COMPLETED = 'agent.completed', 'Agent完成'
    AGENT_MESSAGE = 'agent.message', 'Agent消息'
    USER_CREATED = 'user.created', '用户创建'
    SUBSCRIPTION_CHANGED = 'subscription.changed', '订阅变更'
    ALERT_TRIGGERED = 'alert.triggered', '告警触发'


class WebhookDeliveryStatus(models.TextChoices):
    """Webhook delivery status."""
    PENDING = 'pending', '等待中'
    SUCCESS = 'success', '成功'
    FAILED = 'failed', '失败'
    RETRYING = 'retrying', '重试中'


class Webhook(models.Model):
    """Webhook endpoint configuration."""

    name = models.CharField(max_length=200, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Owner
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='webhooks',
        verbose_name='用户'
    )

    # URL and authentication
    url = models.URLField(max_length=2000, verbose_name='Webhook URL')
    secret = models.CharField(max_length=500, blank=True, verbose_name='签名密钥')

    # Events
    events = models.JSONField(default=list, verbose_name='订阅事件')

    # Headers
    headers = models.JSONField(default=dict, verbose_name='自定义请求头')

    # Status
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    is_verified = models.BooleanField(default=False, verbose_name='是否验证')

    # Configuration
    retry_count = models.IntegerField(default=3, verbose_name='重试次数')
    timeout_seconds = models.IntegerField(default=30, verbose_name='超时时间(秒)')
    content_type = models.CharField(
        max_length=50,
        default='application/json',
        verbose_name='内容类型'
    )

    # Statistics
    total_deliveries = models.IntegerField(default=0, verbose_name='总发送次数')
    successful_deliveries = models.IntegerField(default=0, verbose_name='成功次数')
    failed_deliveries = models.IntegerField(default=0, verbose_name='失败次数')

    # Filters
    workflow_filter = models.JSONField(default=dict, blank=True, verbose_name='工作流过滤')
    tag_filter = models.JSONField(default=list, blank=True, verbose_name='标签过滤')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    last_triggered_at = models.DateTimeField(null=True, blank=True, verbose_name='上次触发时间')

    class Meta:
        db_table = 'webhooks'
        verbose_name = 'Webhook'
        verbose_name_plural = 'Webhooks'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def success_rate(self):
        if self.total_deliveries == 0:
            return 0
        return (self.successful_deliveries / self.total_deliveries) * 100

    def increment_stats(self, success: bool):
        self.total_deliveries += 1
        if success:
            self.successful_deliveries += 1
        else:
            self.failed_deliveries += 1
        self.last_triggered_at = timezone.now()
        self.save(update_fields=[
            'total_deliveries', 'successful_deliveries',
            'failed_deliveries', 'last_triggered_at'
        ])


class WebhookDelivery(models.Model):
    """Webhook delivery log."""

    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name='deliveries',
        verbose_name='Webhook'
    )

    # Event
    event = models.CharField(max_length=100, verbose_name='事件')
    event_id = models.CharField(max_length=100, verbose_name='事件ID')

    # Request
    payload = models.JSONField(default=dict, verbose_name='载荷')
    headers = models.JSONField(default=dict, verbose_name='请求头')
    url = models.URLField(max_length=2000, verbose_name='目标URL')

    # Response
    status_code = models.IntegerField(null=True, blank=True, verbose_name='状态码')
    response_body = models.TextField(blank=True, verbose_name='响应体')
    response_headers = models.JSONField(default=dict, blank=True, verbose_name='响应头')

    # Status
    status = models.CharField(
        max_length=20,
        choices=WebhookDeliveryStatus.choices,
        default=WebhookDeliveryStatus.PENDING,
        verbose_name='状态'
    )

    # Timing
    attempt = models.IntegerField(default=1, verbose_name='尝试次数')
    next_retry_at = models.DateTimeField(null=True, blank=True, verbose_name='下次重试时间')

    # Error
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    # Duration
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name='耗时(毫秒)')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='发送时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'webhook_deliveries'
        verbose_name = 'Webhook投递'
        verbose_name_plural = 'Webhook投递'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['webhook', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['event', '-created_at']),
        ]

    def __str__(self):
        return f"{self.webhook.name} - {self.event} - {self.created_at}"


class Integration(models.Model):
    """Third-party integrations."""

    class IntegrationType(models.TextChoices):
        ZAPIER = 'zapier', 'Zapier'
        MAKE = 'make', 'Make'
        n8n = 'n8n', 'n8n'
        POWERAUTOMATE = 'powerautomate', 'Power Automate'
        CUSTOM = 'custom', '自定义'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='integrations',
        verbose_name='用户'
    )

    name = models.CharField(max_length=200, verbose_name='名称')
    integration_type = models.CharField(
        max_length=30,
        choices=IntegrationType.choices,
        default=IntegrationType.CUSTOM,
        verbose_name='集成类型'
    )

    # Configuration
    config = models.JSONField(default=dict, verbose_name='配置')
    credentials = models.JSONField(default=dict, blank=True, verbose_name='凭证')

    # Status
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    is_connected = models.BooleanField(default=False, verbose_name='是否连接')

    # Sync
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='上次同步时间')
    sync_status = models.CharField(max_length=50, blank=True, verbose_name='同步状态')

    # Statistics
    total_syncs = models.IntegerField(default=0, verbose_name='总同步次数')
    failed_syncs = models.IntegerField(default=0, verbose_name='失败次数')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'integrations'
        verbose_name = '集成'
        verbose_name_plural = '集成'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_integration_type_display()})"


class IntegrationTemplate(models.Model):
    """Templates for common integrations."""

    name = models.CharField(max_length=200, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Template
    integration_type = models.CharField(
        max_length=30,
        choices=Integration.IntegrationType.choices,
        default=Integration.IntegrationType.CUSTOM,
        verbose_name='集成类型'
    )

    category = models.CharField(max_length=50, blank=True, verbose_name='类别')
    icon = models.CharField(max_length=50, blank=True, verbose_name='图标')
    color = models.CharField(max_length=20, default='#3b82f6', verbose_name='颜色')

    # Configuration template
    config_template = models.JSONField(default=dict, verbose_name='配置模板')
    required_config = models.JSONField(default=list, verbose_name='必需配置')
    optional_config = models.JSONField(default=list, verbose_name='可选配置')

    # Triggers and actions
    trigger_events = models.JSONField(default=list, verbose_name='触发事件')
    supported_actions = models.JSONField(default=list, verbose_name='支持的动作')

    # Documentation
    documentation_url = models.URLField(blank=True, verbose_name='文档URL')
    setup_guide = models.TextField(blank=True, verbose_name='设置指南')

    # Status
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    is_featured = models.BooleanField(default=False, verbose_name='是否推荐')

    usage_count = models.IntegerField(default=0, verbose_name='使用次数')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'integration_templates'
        verbose_name = '集成模板'
        verbose_name_plural = '集成模板'
        ordering = ['-usage_count', '-created_at']

    def __str__(self):
        return self.name
