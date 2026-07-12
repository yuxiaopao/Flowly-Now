"""
Agent models for Flowly.
"""

import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

# Import constants for default values
from config.constants import (
    DEFAULT_LLM_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_CONTEXT_WINDOW,
)

# DesktopAgent lives in models_desktop.py for separation of concerns
from .models_desktop import DesktopAgent  # noqa: F401


class Agent(models.Model):
    """AI Agent model."""

    AGENT_TYPES = [
        ('conversational', _('Conversational')),
        ('task', _('Task')),
        ('research', _('Research')),
        ('coding', _('Coding')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        verbose_name='所属租户'
    )

    name = models.CharField(max_length=200, verbose_name='Agent名称')
    description = models.TextField(blank=True, verbose_name='描述')
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='agents',
        verbose_name='所有者',
        db_index=True
    )

    agent_type = models.CharField(
        max_length=50,
        choices=AGENT_TYPES,
        default='conversational',
        verbose_name='Agent类型'
    )

    # Configuration
    system_prompt = models.TextField(blank=True, verbose_name='系统提示词')
    model = models.CharField(max_length=100, default=DEFAULT_LLM_MODEL, verbose_name='使用的模型')
    temperature = models.FloatField(default=DEFAULT_TEMPERATURE, verbose_name='温度参数')
    max_tokens = models.IntegerField(default=DEFAULT_MAX_TOKENS, verbose_name='最大Token数')

    # Capabilities
    tools = models.JSONField(default=list, verbose_name='可用工具')
    skills = models.JSONField(default=list, verbose_name='技能')
    memory_enabled = models.BooleanField(default=True, verbose_name='启用记忆')
    context_window = models.IntegerField(default=DEFAULT_CONTEXT_WINDOW, verbose_name='上下文窗口数')

    # Knowledge base binding: list of rag.DocumentCollection UUID strings this
    # agent may search via the 'knowledge_base' tool (requires 'knowledge_base'
    # to also be present in `tools`).
    knowledge_collections = models.JSONField(default=list, verbose_name='关联知识库集合')

    # Marketplace: publish this agent as a public, cloneable template
    is_public = models.BooleanField(default=False, verbose_name='已发布到市场')

    # Status
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    settings = models.JSONField(default=dict, verbose_name='其他设置')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'agents'
        verbose_name = 'Agent'
        verbose_name_plural = 'Agent'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['agent_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_public']),
        ]

    def __str__(self):
        return self.name


class AgentTool(models.Model):
    """Agent tool configuration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='agent_tools',
        verbose_name='Agent'
    )
    name = models.CharField(max_length=100, verbose_name='工具名称')
    tool_type = models.CharField(max_length=50, verbose_name='工具类型')
    config = models.JSONField(default=dict, verbose_name='工具配置')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        db_table = 'agent_tools'
        verbose_name = 'Agent工具'
        verbose_name_plural = 'Agent工具'

    def __str__(self):
        return f"{self.agent.name} - {self.name}"


class AgentConversation(models.Model):
    """Agent conversation history."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name='Agent',
        db_index=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='agent_conversations',
        verbose_name='用户',
        db_index=True
    )
    messages = models.JSONField(default=list, verbose_name='消息历史')
    summary = models.TextField(blank=True, verbose_name='对话摘要')

    # Stats
    message_count = models.IntegerField(default=0, verbose_name='消息数')
    token_count = models.IntegerField(default=0, verbose_name='Token数')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'agent_conversations'
        verbose_name = 'Agent对话'
        verbose_name_plural = 'Agent对话'
        ordering = ['-updated_at']
        unique_together = [['agent', 'user']]
        indexes = [
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self):
        return f"{self.agent.name} - {self.user.username}"


class AgentExecution(models.Model):
    """Agent execution record."""

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='Agent',
        db_index=True
    )
    conversation = models.ForeignKey(
        AgentConversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executions',
        verbose_name='对话'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态',
        db_index=True
    )
    input_data = models.JSONField(default=dict, verbose_name='输入数据')
    output_data = models.JSONField(default=dict, blank=True, verbose_name='输出数据')
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    started_at = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'agent_executions'
        verbose_name = 'Agent执行'
        verbose_name_plural = 'Agent执行'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['agent']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.agent.name} - {self.get_status_display()}"


class AgentCollaborationRun(models.Model):
    """A multi-agent collaboration run (Planner/Executor/Critic/Reporter)."""

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_collaboration_runs',
        verbose_name='所属团队'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='agent_collaboration_runs',
        verbose_name='发起人'
    )

    task = models.TextField(verbose_name='任务描述')

    # roles_config: list of {role, agent_id (optional), name, system_prompt, model}
    roles_config = models.JSONField(default=list, verbose_name='角色配置')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态',
        db_index=True
    )

    # trace: ordered list of {phase, role, agent, content, timestamp} step records
    trace = models.JSONField(default=list, verbose_name='执行轨迹')
    final_report = models.TextField(blank=True, verbose_name='最终报告')
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    started_at = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'agent_collaboration_runs'
        verbose_name = 'AI协作任务'
        verbose_name_plural = 'AI协作任务'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['created_by']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Collaboration[{self.id}] - {self.get_status_display()}"
