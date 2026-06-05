"""
Workflow template system models for reusable workflow patterns.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TemplateCategory(models.Model):
    """Category for organizing workflow templates."""

    name = models.CharField(max_length=100, verbose_name='名称')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='slug')
    description = models.TextField(blank=True, verbose_name='描述')

    icon = models.CharField(max_length=50, default='folder', verbose_name='图标')
    color = models.CharField(max_length=20, default='#3b82f6', verbose_name='颜色')

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
        db_table = 'workflow_template_categories'
        verbose_name = '模板分类'
        verbose_name_plural = '模板分类'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class WorkflowTemplate(models.Model):
    """Reusable workflow template."""

    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    ]

    ACCESS_CHOICES = [
        ('private', '私有'),
        ('team', '团队'),
        ('public', '公开'),
    ]

    name = models.CharField(max_length=200, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Template data
    workflow_data = models.JSONField(default=dict, verbose_name='工作流数据')
    nodes = models.JSONField(default=list, verbose_name='节点')
    edges = models.JSONField(default=list, verbose_name='连接')

    # Metadata
    category = models.ForeignKey(
        TemplateCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates',
        verbose_name='分类'
    )

    tags = models.JSONField(default=list, verbose_name='标签')
    variables = models.JSONField(default=dict, verbose_name='变量')

    # Publishing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='状态'
    )
    access = models.CharField(
        max_length=20,
        choices=ACCESS_CHOICES,
        default='private',
        verbose_name='访问权限'
    )

    # Statistics
    view_count = models.IntegerField(default=0, verbose_name='浏览次数')
    use_count = models.IntegerField(default=0, verbose_name='使用次数')
    like_count = models.IntegerField(default=0, verbose_name='点赞次数')
    likes = models.ManyToManyField(
        User,
        blank=True,
        related_name='liked_templates',
        verbose_name='点赞用户'
    )

    # Rating
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        verbose_name='评分'
    )
    rating_count = models.IntegerField(default=0, verbose_name='评分人数')

    # Preview
    thumbnail = models.URLField(blank=True, verbose_name='缩略图')
    preview_images = models.JSONField(default=list, verbose_name='预览图')

    # Verification
    is_verified = models.BooleanField(default=False, verbose_name='已认证')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='认证时间')

    # Owner
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_templates',
        verbose_name='创建者'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='templates',
        verbose_name='租户'
    )

    # Workflow reference (optional - if created from existing workflow)
    source_workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates',
        verbose_name='源工作流'
    )

    # Config
    config = models.JSONField(default=dict, verbose_name='配置')

    published_at = models.DateTimeField(null=True, blank=True, verbose_name='发布时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'workflow_templates'
        verbose_name = '工作流模板'
        verbose_name_plural = '工作流模板'
        ordering = ['-use_count', '-created_at']
        indexes = [
            models.Index(fields=['status', '-use_count']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['-rating']),
        ]

    def __str__(self):
        return self.name


class TemplateVersion(models.Model):
    """Version history for templates."""

    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='模板'
    )

    version = models.CharField(max_length=20, verbose_name='版本号')
    name = models.CharField(max_length=200, verbose_name='名称')

    nodes = models.JSONField(default=list, verbose_name='节点')
    edges = models.JSONField(default=list, verbose_name='连接')
    variables = models.JSONField(default=dict, verbose_name='变量')

    changelog = models.TextField(blank=True, verbose_name='更新日志')

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='template_versions',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workflow_template_versions'
        verbose_name = '模板版本'
        verbose_name_plural = '模板版本'
        ordering = ['-created_at']
        unique_together = ['template', 'version']

    def __str__(self):
        return f"{self.template.name} v{self.version}"


class TemplateUsage(models.Model):
    """Track template usage."""

    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name='模板'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_usages',
        verbose_name='用户'
    )

    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.CASCADE,
        related_name='template_usages',
        verbose_name='创建的工作流'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workflow_template_usages'
        verbose_name = '模板使用记录'
        verbose_name_plural = '模板使用记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} used {self.template.name}"


class TemplateReview(models.Model):
    """User reviews for templates."""

    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='模板'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_reviews',
        verbose_name='用户'
    )

    rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        verbose_name='评分'
    )
    title = models.CharField(max_length=200, blank=True, verbose_name='标题')
    content = models.TextField(blank=True, verbose_name='内容')

    is_verified = models.BooleanField(default=False, verbose_name='已验证购买')

    helpful_count = models.IntegerField(default=0, verbose_name='有帮助次数')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'workflow_template_reviews'
        verbose_name = '模板评论'
        verbose_name_plural = '模板评论'
        ordering = ['-helpful_count', '-created_at']
        unique_together = ['template', 'user']

    def __str__(self):
        return f"{self.user.username}'s review of {self.template.name}"


class TemplateFavorite(models.Model):
    """User favorites for templates."""

    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='模板'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_favorites',
        verbose_name='用户'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workflow_template_favorites'
        verbose_name = '模板收藏'
        verbose_name_plural = '模板收藏'
        unique_together = ['template', 'user']

    def __str__(self):
        return f"{self.user.username} favorited {self.template.name}"
