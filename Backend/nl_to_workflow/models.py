"""
NL to Workflow models.
"""

import uuid

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class NLSession(models.Model):
    """Natural Language to Workflow session."""

    STATUS_CHOICES = [
        ('active', '进行中'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='nl_sessions',
        verbose_name='用户',
        db_index=True
    )
    name = models.CharField(max_length=200, verbose_name='会话名称')
    description = models.TextField(blank=True, verbose_name='需求描述')

    # Generated workflow
    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nl_sessions',
        verbose_name='生成的工作流'
    )
    workflow_name = models.CharField(max_length=200, blank=True, verbose_name='工作流名称')
    workflow_json = models.JSONField(default=dict, blank=True, verbose_name='工作流JSON')

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='状态',
        db_index=True
    )
    messages = models.JSONField(default=list, verbose_name='对话历史')
    conversation_summary = models.TextField(blank=True, default='', verbose_name='对话摘要')
    celery_task_id = models.CharField(max_length=64, blank=True, default='', verbose_name='Celery任务ID')

    # Model used
    model_used = models.CharField(max_length=100, blank=True, verbose_name='使用的模型')
    provider = models.CharField(max_length=50, blank=True, verbose_name='模型提供商')

    # Error tracking
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'nl_sessions'
        verbose_name = '语创会话'
        verbose_name_plural = '语创会话'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} - {self.user.username}"
