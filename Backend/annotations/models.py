"""
Models for annotations app.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class AnnotationProject(models.Model):
    """
    Annotation project that wraps a dataset for labeling tasks.
    """

    ANNOTATION_TYPES = [
        ('classification', '分类'),
        ('ner', '命名实体识别'),
        ('sentiment', '情感分析'),
        ('detection', '目标检测'),
    ]

    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name='项目名称')
    annotation_type = models.CharField(
        max_length=20,
        choices=ANNOTATION_TYPES,
        default='classification',
        verbose_name='标注类型'
    )
    labels = models.JSONField(default=list, verbose_name='标签列表')
    dataset = models.ForeignKey(
        'datasets.Dataset',
        on_delete=models.CASCADE,
        related_name='annotation_projects',
        verbose_name='关联数据集'
    )
    model_assisted = models.BooleanField(default=False, verbose_name='AI辅助标注')
    model_id = models.CharField(max_length=255, blank=True, verbose_name='LLM模型ID')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='状态'
    )
    total_items = models.IntegerField(default=0, verbose_name='总条数')
    annotated_items = models.IntegerField(default=0, verbose_name='已标注条数')

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='annotation_projects',
        verbose_name='所属租户',
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='annotation_projects',
        verbose_name='创建者',
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'annotation_projects'
        verbose_name = '标注项目'
        verbose_name_plural = '标注项目'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['created_by']),
            models.Index(fields=['status']),
            models.Index(fields=['annotation_type']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_annotation_type_display()})"

    @property
    def progress_percentage(self):
        """Calculate annotation progress percentage."""
        if self.total_items == 0:
            return 0
        return round((self.annotated_items / self.total_items) * 100, 1)


class AnnotationItem(models.Model):
    """
    Individual annotation item within a project.
    """

    STATUS_CHOICES = [
        ('pending', '待标注'),
        ('annotated', '已标注'),
        ('skipped', '已跳过'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        AnnotationProject,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='所属项目'
    )
    data_id = models.CharField(max_length=255, verbose_name='数据ID')
    data_content = models.JSONField(default=dict, verbose_name='数据内容')
    pre_label = models.CharField(max_length=255, blank=True, verbose_name='AI预标注')
    label = models.CharField(max_length=255, blank=True, verbose_name='最终标签')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态'
    )
    annotated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='annotation_items',
        verbose_name='标注人'
    )
    annotated_at = models.DateTimeField(null=True, blank=True, verbose_name='标注时间')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'annotation_items'
        verbose_name = '标注项'
        verbose_name_plural = '标注项'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['data_id']),
        ]

    def __str__(self):
        return f"{self.data_id} - {self.label or self.pre_label or 'pending'}"
