"""
Notification models for user notifications.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class NotificationType(models.TextChoices):
    """Notification types."""
    WORKFLOW_COMPLETED = 'workflow_completed', '工作流完成'
    WORKFLOW_FAILED = 'workflow_failed', '工作流失败'
    WORKFLOW_SCHEDULED = 'workflow_scheduled', '工作流已调度'
    AGENT_COMPLETED = 'agent_completed', 'Agent 完成'
    AGENT_FAILED = 'agent_failed', 'Agent 失败'
    TRIGGER_ACTIVATED = 'trigger_activated', '触发器激活'
    ALERT_TRIGGERED = 'alert_triggered', '告警触发'
    SYSTEM_MESSAGE = 'system_message', '系统消息'
    USER_INVITATION = 'user_invitation', '用户邀请'
    COMMENT = 'comment', '评论'
    MENTION = 'mention', '提及'


class NotificationPriority(models.TextChoices):
    """Notification priority."""
    LOW = 'low', '低'
    NORMAL = 'normal', '普通'
    HIGH = 'high', '高'
    URGENT = 'urgent', '紧急'


class Notification(models.Model):
    """User notification."""

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='core_notifications',
        verbose_name='接收者'
    )

    # Notification content
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM_MESSAGE,
        verbose_name='通知类型'
    )

    title = models.CharField(max_length=200, verbose_name='标题')
    message = models.TextField(verbose_name='消息内容')
    link = models.CharField(max_length=500, blank=True, verbose_name='链接')

    # Priority and status
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL,
        verbose_name='优先级'
    )

    is_read = models.BooleanField(default=False, verbose_name='已读')
    is_archived = models.BooleanField(default=False, verbose_name='已归档')

    # Related objects (optional)
    related_workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='相关工作流'
    )
    related_execution = models.CharField(max_length=100, blank=True, verbose_name='相关执行')
    related_agent = models.ForeignKey(
        'agents.Agent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='相关Agent'
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')
    icon = models.CharField(max_length=50, blank=True, verbose_name='图标')
    color = models.CharField(max_length=20, blank=True, verbose_name='颜色')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='阅读时间')

    class Meta:
        db_table = 'notifications'
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"{self.recipient.username}: {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_unread(self):
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def create_notification(
        cls,
        recipient,
        notification_type: str,
        title: str,
        message: str,
        link: str = '',
        priority: str = NotificationPriority.NORMAL,
        **kwargs
    ):
        """Create a new notification."""
        icon_map = {
            NotificationType.WORKFLOW_COMPLETED: 'check-circle',
            NotificationType.WORKFLOW_FAILED: 'x-circle',
            NotificationType.WORKFLOW_SCHEDULED: 'clock',
            NotificationType.AGENT_COMPLETED: 'bot',
            NotificationType.AGENT_FAILED: 'alert-triangle',
            NotificationType.TRIGGER_ACTIVATED: 'zap',
            NotificationType.ALERT_TRIGGERED: 'bell',
            NotificationType.SYSTEM_MESSAGE: 'info',
            NotificationType.USER_INVITATION: 'user-plus',
            NotificationType.COMMENT: 'message-circle',
            NotificationType.MENTION: 'at-sign',
        }

        color_map = {
            NotificationType.WORKFLOW_COMPLETED: '#10b981',
            NotificationType.WORKFLOW_FAILED: '#ef4444',
            NotificationType.WORKFLOW_SCHEDULED: '#3b82f6',
            NotificationType.AGENT_COMPLETED: '#8b5cf6',
            NotificationType.AGENT_FAILED: '#ef4444',
            NotificationType.TRIGGER_ACTIVATED: '#f59e0b',
            NotificationType.ALERT_TRIGGERED: '#ef4444',
            NotificationType.SYSTEM_MESSAGE: '#6b7280',
            NotificationType.USER_INVITATION: '#3b82f6',
            NotificationType.COMMENT: '#06b6d4',
            NotificationType.MENTION: '#8b5cf6',
        }

        return cls.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            priority=priority,
            icon=icon_map.get(notification_type, 'bell'),
            color=color_map.get(notification_type, '#6b7280'),
            **kwargs
        )


class NotificationPreference(models.Model):
    """User notification preferences."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='用户'
    )

    # Enable/disable notifications by type
    workflow_completed = models.BooleanField(default=True, verbose_name='工作流完成')
    workflow_failed = models.BooleanField(default=True, verbose_name='工作流失败')
    workflow_scheduled = models.BooleanField(default=True, verbose_name='工作流已调度')
    agent_completed = models.BooleanField(default=True, verbose_name='Agent 完成')
    agent_failed = models.BooleanField(default=True, verbose_name='Agent 失败')
    trigger_activated = models.BooleanField(default=True, verbose_name='触发器激活')
    alert_triggered = models.BooleanField(default=True, verbose_name='告警触发')
    system_message = models.BooleanField(default=True, verbose_name='系统消息')
    user_invitation = models.BooleanField(default=True, verbose_name='用户邀请')
    comment = models.BooleanField(default=True, verbose_name='评论')
    mention = models.BooleanField(default=True, verbose_name='提及')

    # Delivery preferences
    email_enabled = models.BooleanField(default=False, verbose_name='邮件通知')
    push_enabled = models.BooleanField(default=True, verbose_name='推送通知')
    in_app_enabled = models.BooleanField(default=True, verbose_name='应用内通知')

    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False, verbose_name='免打扰模式')
    quiet_hours_start = models.TimeField(null=True, blank=True, verbose_name='免打扰开始时间')
    quiet_hours_end = models.TimeField(null=True, blank=True, verbose_name='免打扰结束时间')

    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'notification_preferences'
        verbose_name = '通知偏好'
        verbose_name_plural = '通知偏好'

    def __str__(self):
        return f"Preferences for {self.user.username}"

    def is_notification_enabled(self, notification_type: str):
        """Check if a specific notification type is enabled."""
        return getattr(self, notification_type, True)

    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create preferences for a user."""
        prefs, _ = cls.objects.get_or_create(user=user)
        return prefs
