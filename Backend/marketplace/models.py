"""
Marketplace models for workflow templates.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TemplateCategory(models.Model):
    """Category for workflow templates."""

    name = models.CharField(max_length=100, verbose_name='名称')
    slug = models.SlugField(unique=True, verbose_name='标识')
    description = models.TextField(blank=True, verbose_name='描述')
    icon = models.CharField(max_length=50, blank=True, verbose_name='图标')
    order = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'template_categories'
        verbose_name = '模板分类'
        verbose_name_plural = '模板分类'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class WorkflowTemplate(models.Model):
    """Workflow template for marketplace."""

    name = models.CharField(max_length=200, verbose_name='模板名称')
    description = models.TextField(verbose_name='描述')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL标识')

    # Category
    category = models.ForeignKey(
        TemplateCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='templates',
        verbose_name='分类'
    )

    # Template data
    workflow_data = models.JSONField(default=dict, verbose_name='工作流数据')
    nodes = models.JSONField(default=list, verbose_name='节点定义')
    edges = models.JSONField(default=list, verbose_name='连接定义')

    # Tags
    tags = models.JSONField(default=list, verbose_name='标签')

    # Stats
    install_count = models.IntegerField(default=0, verbose_name='安装次数')
    view_count = models.IntegerField(default=0, verbose_name='浏览次数')
    avg_rating = models.FloatField(default=0, verbose_name='平均评分')
    report_count = models.IntegerField(default=0, verbose_name='举报次数')

    # Preview
    preview_image = models.URLField(blank=True, verbose_name='预览图')

    # Status
    is_published = models.BooleanField(default=False, verbose_name='是否发布')
    is_featured = models.BooleanField(default=False, verbose_name='是否精选')
    is_verified = models.BooleanField(default=False, verbose_name='是否认证')

    # Owner
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='marketplace_created_templates',
        verbose_name='创建者'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'marketplace_workflow_templates'
        verbose_name = '工作流模板'
        verbose_name_plural = '工作流模板'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TemplateInstall(models.Model):
    """Record of template installations."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_installs',
        verbose_name='用户'
    )
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='installs',
        verbose_name='模板'
    )

    # Installed workflow
    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installed_from',
        verbose_name='生成的工作流'
    )

    installed_at = models.DateTimeField(auto_now_add=True, verbose_name='安装时间')

    class Meta:
        db_table = 'template_installs'
        verbose_name = '模板安装'
        verbose_name_plural = '模板安装'
        unique_together = ['user', 'template']
        ordering = ['-installed_at']

    def __str__(self):
        return f"{self.user.username} -> {self.template.name}"


class TemplateRating(models.Model):
    """User ratings for templates."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_ratings',
        verbose_name='用户'
    )
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name='模板'
    )
    rating = models.IntegerField(verbose_name='评分')  # 1-5

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评分时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'template_ratings'
        verbose_name = '模板评分'
        verbose_name_plural = '模板评分'
        unique_together = ['user', 'template']

    def __str__(self):
        return f"{self.user.username}: {self.rating} stars"


class TemplateComment(models.Model):
    """Comments on templates."""

    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='模板'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_comments',
        verbose_name='用户'
    )

    content = models.TextField(verbose_name='评论内容')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='父评论'
    )

    # Stats
    like_count = models.IntegerField(default=0, verbose_name='点赞数')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评论时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'template_comments'
        verbose_name = '模板评论'
        verbose_name_plural = '模板评论'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}"


class TemplateFavorite(models.Model):
    """User favorites for templates."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='marketplace_template_favorites',
        verbose_name='用户'
    )
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='模板'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='收藏时间')

    class Meta:
        db_table = 'marketplace_template_favorites'
        verbose_name = '模板收藏'
        verbose_name_plural = '模板收藏'
        unique_together = ['user', 'template']

    def __str__(self):
        return f"{self.user.username} -> {self.template.name}"
