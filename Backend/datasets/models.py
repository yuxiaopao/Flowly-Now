"""
Models for datasets app.
"""

import uuid
import os
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings


User = get_user_model()


def dataset_upload_path(instance, filename):
    """Generate upload path for dataset files."""
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('datasets', new_filename)


class Dataset(models.Model):
    """
    Dataset model for storing uploaded datasets.
    Supports multiple data sources: local upload, URL download, and S3 storage.
    """

    SOURCE_CHOICES = [
        ('upload', '本地上传'),
        ('url', 'URL下载'),
        ('s3', 'S3存储'),
    ]

    FORMAT_CHOICES = [
        ('text', 'TXT'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('parquet', 'Parquet'),
    ]

    STATUS_CHOICES = [
        ('pending', '处理中'),
        ('ready', '就绪'),
        ('error', '错误'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255, verbose_name='数据集名称')
    description = models.TextField(blank=True, verbose_name='描述')

    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default='upload',
        verbose_name='数据来源'
    )

    file_path = models.CharField(max_length=500, blank=True, verbose_name='文件路径')
    file = models.FileField(
        upload_to=dataset_upload_path,
        blank=True,
        null=True,
        verbose_name='上传文件'
    )
    url = models.URLField(max_length=1000, blank=True, verbose_name='数据URL')
    s3_path = models.CharField(max_length=500, blank=True, verbose_name='S3路径')
    s3_bucket = models.CharField(max_length=255, blank=True, verbose_name='S3存储桶')

    format = models.CharField(
        max_length=10,
        choices=FORMAT_CHOICES,
        default='csv',
        verbose_name='数据格式'
    )

    size_bytes = models.BigIntegerField(default=0, verbose_name='文件大小(字节)')
    row_count = models.IntegerField(default=0, verbose_name='行数')
    column_count = models.IntegerField(default=0, verbose_name='列数')
    columns = models.JSONField(default=list, blank=True, verbose_name='列信息')
    preview_data = models.JSONField(default=list, blank=True, verbose_name='预览数据')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态'
    )
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='datasets',
        verbose_name='所属租户',
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='datasets',
        verbose_name='创建者',
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'datasets'
        verbose_name = '数据集'
        verbose_name_plural = '数据集'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['created_by']),
            models.Index(fields=['source']),
            models.Index(fields=['format']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_format_display()})"

    @property
    def size_display(self):
        """Get human-readable file size."""
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    @property
    def is_ready(self):
        """Check if dataset is ready for use."""
        return self.status == 'ready' and self.row_count > 0

    def get_absolute_file_path(self):
        """Get the absolute file path for the dataset."""
        if self.file:
            return self.file.path
        elif self.file_path:
            return os.path.join(settings.MEDIA_ROOT, self.file_path)
        return None

    def delete_file(self):
        """Delete the associated file if it exists."""
        if self.file:
            try:
                if os.path.exists(self.file.path):
                    os.remove(self.file.path)
            except Exception:
                pass
            self.file.delete(save=True)
