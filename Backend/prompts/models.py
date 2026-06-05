"""
Reusable prompt library models for storing and managing prompt templates.
"""

import uuid

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PromptCategory(models.Model):
    """Category for organizing prompts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=100, verbose_name='名称')
    slug = models.SlugField(max_length=100, verbose_name='slug')
    description = models.TextField(blank=True, verbose_name='描述')

    icon = models.CharField(max_length=50, default='file-text', verbose_name='图标')
    color = models.CharField(max_length=20, default='#8b5cf6', verbose_name='颜色')

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='父分类'
    )

    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'prompt_categories'
        verbose_name = '提示词分类'
        verbose_name_plural = '提示词分类'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class PromptTemplate(models.Model):
    """Reusable prompt template."""

    TYPE_CHOICES = [
        ('system', '系统提示词'),
        ('user', '用户提示词'),
        ('assistant', '助手提示词'),
        ('task', '任务提示词'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Prompt content
    prompt_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='task',
        verbose_name='提示词类型'
    )

    template = models.TextField(verbose_name='提示词模板')

    # Variables
    variables = models.JSONField(default=list, verbose_name='变量定义')
    example_variables = models.JSONField(default=dict, verbose_name='变量示例')

    # Configuration
    model_preferences = models.JSONField(default=list, verbose_name='推荐模型')
    temperature = models.FloatField(default=0.7, verbose_name='温度参数')
    max_tokens = models.IntegerField(default=2000, verbose_name='最大Token数')

    # Metadata
    category = models.ForeignKey(
        PromptCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompts',
        verbose_name='分类'
    )

    tags = models.JSONField(default=list, verbose_name='标签')

    # Usage stats
    use_count = models.IntegerField(default=0, verbose_name='使用次数')
    success_rate = models.FloatField(default=0, verbose_name='成功率')
    avg_rating = models.FloatField(default=0, verbose_name='平均评分')

    # Sharing
    is_public = models.BooleanField(default=False, verbose_name='是否公开')
    share_link = models.CharField(max_length=100, blank=True, verbose_name='分享链接')

    # Ratings
    rating_count = models.IntegerField(default=0, verbose_name='评分次数')
    total_rating = models.IntegerField(default=0, verbose_name='总评分')

    # Owner
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prompt_templates',
        null=True,
        blank=True,
        verbose_name='创建者'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='prompt_templates',
        verbose_name='租户'
    )

    # Reference workflows
    workflows = models.ManyToManyField(
        'workflows.Workflow',
        through='PromptUsage',
        related_name='used_prompts',
        verbose_name='使用的工作流'
    )

    # Versioning
    version = models.CharField(max_length=20, default='1.0', verbose_name='版本')

    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    is_featured = models.BooleanField(default=False, verbose_name='是否精选')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'prompt_templates'
        verbose_name = '提示词模板'
        verbose_name_plural = '提示词模板'
        ordering = ['-use_count', '-created_at']

    def __str__(self):
        return self.name

    def update_rating(self, new_rating):
        """Update average rating."""
        self.total_rating += new_rating
        self.rating_count += 1
        self.avg_rating = self.total_rating / self.rating_count
        self.save(update_fields=['total_rating', 'rating_count', 'avg_rating'])

    def increment_use(self):
        """Increment use count."""
        self.use_count += 1
        self.save(update_fields=['use_count'])


class PromptUsage(models.Model):
    """Track prompt template usage."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    prompt = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name='提示词'
    )

    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.CASCADE,
        related_name='prompt_usages',
        verbose_name='工作流'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prompt_usages',
        verbose_name='用户'
    )

    # Usage context
    node_id = models.CharField(max_length=100, blank=True, verbose_name='节点ID')
    input_variables = models.JSONField(default=dict, verbose_name='输入变量')
    rendered_prompt = models.TextField(blank=True, verbose_name='渲染后的提示词')

    # Result
    was_successful = models.BooleanField(default=True, verbose_name='是否成功')
    feedback = models.TextField(blank=True, verbose_name='反馈')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'prompt_usages'
        verbose_name = '提示词使用记录'
        verbose_name_plural = '提示词使用记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} used {self.prompt.name}"


class PromptVersion(models.Model):
    """Version history for prompts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    prompt = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='提示词'
    )

    version = models.CharField(max_length=20, verbose_name='版本号')
    template = models.TextField(verbose_name='提示词模板')
    variables = models.JSONField(default=list, verbose_name='变量定义')
    changelog = models.TextField(blank=True, verbose_name='更新日志')

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prompt_versions',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'prompt_versions'
        verbose_name = '提示词版本'
        verbose_name_plural = '提示词版本'
        ordering = ['-created_at']
        unique_together = ['prompt', 'version']

    def __str__(self):
        return f"{self.prompt.name} v{self.version}"


class PromptRating(models.Model):
    """User ratings for prompts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    prompt = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name='提示词'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prompt_ratings',
        verbose_name='用户'
    )

    rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        verbose_name='评分'
    )
    comment = models.TextField(blank=True, verbose_name='评论')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'prompt_ratings'
        verbose_name = '提示词评分'
        verbose_name_plural = '提示词评分'
        unique_together = ['prompt', 'user']

    def __str__(self):
        return f"{self.user.username} rated {self.prompt.name} {self.rating} stars"
