"""
Models for augmentation app.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class AugmentationJob(models.Model):
    """
    Records an augmentation job for tracking.
    Tracks the progress and results of data augmentation operations.
    """

    STRATEGY_CHOICES = [
        ('geometric', '几何变换'),
        ('color', '颜色变换'),
        ('noise', '噪声注入'),
        ('mixup', '混合增强'),
        ('all', '全部策略'),
    ]

    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    OUTPUT_MODE_CHOICES = [
        ('create_new', '创建新数据集'),
        ('overwrite', '覆盖原数据集'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    input_dataset = models.ForeignKey(
        'datasets.Dataset',
        on_delete=models.CASCADE,
        related_name='augmentation_jobs',
        verbose_name='输入数据集'
    )
    output_dataset = models.ForeignKey(
        'datasets.Dataset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='input_from_augmentation',
        verbose_name='输出数据集'
    )

    strategy = models.CharField(
        max_length=20,
        choices=STRATEGY_CHOICES,
        default='geometric',
        verbose_name='增强策略'
    )
    ratio = models.FloatField(default=2.0, verbose_name='增强倍数')
    transformations = models.JSONField(default=list, blank=True, verbose_name='变换配置')

    augmented_count = models.IntegerField(default=0, verbose_name='增强后样本数')
    original_count = models.IntegerField(default=0, verbose_name='原始样本数')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态'
    )
    output_mode = models.CharField(
        max_length=20,
        choices=OUTPUT_MODE_CHOICES,
        default='create_new',
        verbose_name='输出模式'
    )
    output_dir = models.CharField(max_length=500, blank=True, verbose_name='输出目录')
    output_name = models.CharField(max_length=255, blank=True, verbose_name='输出数据集名称')

    error_message = models.TextField(blank=True, verbose_name='错误信息')
    progress = models.IntegerField(default=0, verbose_name='进度百分比')

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='augmentation_jobs',
        verbose_name='创建者'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='augmentation_jobs',
        verbose_name='所属租户',
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'augmentation_jobs'
        verbose_name = '增强任务'
        verbose_name_plural = '增强任务'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['tenant', '-created_at']),
        ]

    def __str__(self):
        return f"{self.input_dataset.name} - {self.get_strategy_display()} ({self.get_status_display()})"

    @property
    def is_complete(self):
        return self.status == 'completed'

    @property
    def is_running(self):
        return self.status == 'running'

    @property
    def is_failed(self):
        return self.status == 'failed'

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            from django.utils import timezone
            return (timezone.now() - self.started_at).total_seconds()
        return None

    def mark_running(self):
        from django.utils import timezone
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self, augmented_count=None, output_dataset=None):
        from django.utils import timezone
        self.status = 'completed'
        self.completed_at = timezone.now()
        if augmented_count is not None:
            self.augmented_count = augmented_count
        if output_dataset:
            self.output_dataset = output_dataset
        self.progress = 100
        self.save(update_fields=['status', 'completed_at', 'augmented_count', 'output_dataset', 'progress'])

    def mark_failed(self, error_message):
        from django.utils import timezone
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])
