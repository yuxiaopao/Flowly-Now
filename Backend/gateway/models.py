"""
Gateway models for AI model management.
"""

import uuid

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ModelProvider(models.Model):
    """AI Model Provider (OpenAI, Anthropic, etc.)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=100, verbose_name='提供商名称')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='标识')
    logo_url = models.URLField(blank=True, verbose_name='Logo URL')
    website = models.URLField(blank=True, verbose_name='官网')
    description = models.TextField(blank=True, verbose_name='描述')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        db_table = 'model_providers'
        verbose_name = '模型提供商'
        verbose_name_plural = '模型提供商'
        ordering = ['name']

    def __str__(self):
        return self.name


class AIModel(models.Model):
    """AI Model configuration."""

    MODEL_TYPE_CHOICES = [
        ('chat', '对话模型'),
        ('embedding', '嵌入模型'),
        ('image', '图像模型'),
        ('audio', '音频模型'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.CASCADE,
        related_name='models',
        verbose_name='提供商'
    )

    name = models.CharField(max_length=200, verbose_name='模型名称')
    model_id = models.CharField(max_length=200, verbose_name='模型ID')
    model_type = models.CharField(
        max_length=20,
        choices=MODEL_TYPE_CHOICES,
        default='chat',
        verbose_name='模型类型'
    )

    # Capabilities
    max_tokens = models.IntegerField(default=4096, verbose_name='最大Token数')
    supports_streaming = models.BooleanField(default=True, verbose_name='支持流式')
    supports_function_calling = models.BooleanField(default=False, verbose_name='支持函数调用')
    supports_vision = models.BooleanField(default=False, verbose_name='支持视觉')

    # Pricing (per 1M tokens)
    input_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name='输入价格'
    )
    output_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name='输出价格'
    )

    # Configuration
    default_temperature = models.FloatField(default=0.7, verbose_name='默认温度')
    default_top_p = models.FloatField(default=1.0, verbose_name='默认Top-P')

    # Status
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    is_default = models.BooleanField(default=False, verbose_name='是否为默认')
    description = models.TextField(blank=True, verbose_name='描述')

    # Metadata
    context_window = models.IntegerField(default=8192, verbose_name='上下文窗口')
    released_at = models.DateField(null=True, blank=True, verbose_name='发布时间')

    class Meta:
        db_table = 'ai_models'
        verbose_name = 'AI模型'
        verbose_name_plural = 'AI模型'
        unique_together = ['provider', 'model_id']
        ordering = ['provider', 'name']

    def __str__(self):
        return f"{self.provider.name} - {self.name}"


class UserAPIKey(models.Model):
    """User's API keys for external services."""

    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('azure', 'Azure OpenAI'),
        ('google', 'Google AI'),
        ('ollama', 'Ollama'),
        ('custom', '自定义'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys',
        verbose_name='用户',
        db_index=True
    )

    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        verbose_name='服务商'
    )

    name = models.CharField(max_length=100, verbose_name='名称')
    api_key = models.CharField(max_length=500, verbose_name='API Key')

    # For Azure OpenAI
    endpoint = models.URLField(blank=True, verbose_name='API Endpoint')
    api_version = models.CharField(max_length=50, blank=True, verbose_name='API版本')

    # Usage
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最后使用时间')
    total_usage = models.BigIntegerField(default=0, verbose_name='总使用量')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'user_api_keys'
        verbose_name = '用户API密钥'
        verbose_name_plural = '用户API密钥'
        unique_together = ['user', 'provider', 'name']

    def __str__(self):
        return f"{self.user.username} - {self.provider} - {self.name}"

    def get_masked_key(self):
        """Return masked API key for display."""
        if len(self.api_key) > 8:
            return f"{self.api_key[:4]}...{self.api_key[-4:]}"
        return "***"


class APICallLog(models.Model):
    """Log of API calls made through the gateway."""

    id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='api_logs',
        verbose_name='用户',
        db_index=True
    )

    # Request details
    provider = models.CharField(max_length=50, verbose_name='服务商', db_index=True)
    model = models.CharField(max_length=200, verbose_name='模型')
    endpoint = models.CharField(max_length=500, verbose_name='端点')

    # Usage
    input_tokens = models.IntegerField(default=0, verbose_name='输入Token')
    output_tokens = models.IntegerField(default=0, verbose_name='输出Token')
    total_tokens = models.IntegerField(default=0, verbose_name='总Token')

    # Timing
    latency_ms = models.IntegerField(default=0, verbose_name='延迟(毫秒)')

    # Status
    status_code = models.IntegerField(default=200, verbose_name='状态码')
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    # Cost
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        verbose_name='费用'
    )

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间戳')

    class Meta:
        db_table = 'api_call_logs'
        verbose_name = 'API调用日志'
        verbose_name_plural = 'API调用日志'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['provider', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.provider} - {self.model} - {self.timestamp}"
