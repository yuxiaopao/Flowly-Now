"""
Desktop Agent models — registered training agents.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class DesktopAgent(models.Model):
    """
    Records a registered Flowly Desktop Agent.

    Agents are lightweight — they are identified by agent_id,
    carry GPU info, and report their online status via WebSocket heartbeat.
    Training jobs are tracked in TrainingJob, not here.
    """

    STATUS_CHOICES = [
        ('online', _('在线')),
        ('offline', _('离线')),
        ('training', _('训练中')),
        ('error', _('异常')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name='Agent ID',
        help_text='桌面端生成的唯一标识符'
    )

    # Registration info
    display_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='显示名称'
    )

    # Agent identity
    hostname = models.CharField(max_length=255, blank=True, verbose_name='主机名')
    platform = models.CharField(max_length=50, blank=True, verbose_name='操作系统')

    # GPU info snapshot
    gpu_info = models.JSONField(default=dict, verbose_name='GPU信息')
    gpu_available = models.BooleanField(default=False, verbose_name='是否有GPU')
    gpu_name = models.CharField(max_length=255, blank=True, verbose_name='GPU型号')

    # Capabilities
    capabilities = models.JSONField(default=list, verbose_name='能力列表')
    supports_yolo_training = models.BooleanField(default=False, verbose_name='支持YOLO训练')

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline',
        verbose_name='状态'
    )
    last_seen = models.DateTimeField(auto_now=True, verbose_name='最后活跃')

    # Cloud connection
    cloud_url = models.CharField(max_length=500, blank=True, verbose_name='云端服务器')
    connected_at = models.DateTimeField(null=True, blank=True, verbose_name='连接时间')

    # Owner (optional — can be unregistered)
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='desktop_agents',
        verbose_name='所有者'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='注册时间')

    class Meta:
        db_table = 'desktop_agents'
        verbose_name = '桌面Agent'
        verbose_name_plural = '桌面Agent列表'
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['gpu_available', 'status']),
            models.Index(fields=['owner', '-last_seen']),
        ]

    def __str__(self):
        return f"{self.display_name or self.agent_id} ({self.get_status_display()})"

    @property
    def is_online(self):
        return self.status in ('online', 'training')
