"""
Training models for model training management.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Dataset(models.Model):
    """Dataset model for storing uploaded training datasets."""

    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('zip', 'ZIP'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name='数据集名称')
    description = models.TextField(blank=True, verbose_name='描述')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, verbose_name='文件格式')
    size = models.BigIntegerField(verbose_name='文件大小(字节)')
    row_count = models.IntegerField(default=0, verbose_name='行数')
    columns = models.JSONField(default=list, verbose_name='列名列表')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_datasets',
        verbose_name='创建者'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_datasets',
        verbose_name='所属租户',
        db_index=True
    )

    class Meta:
        db_table = 'training_datasets'
        verbose_name = '训练数据集'
        verbose_name_plural = '训练数据集'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['created_by']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['format']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_format_display()})"

    def save(self, *args, **kwargs):
        """Override save to auto-detect format from file path."""
        if not self.format and self.file_path:
            ext = self.file_path.split('.')[-1].lower()
            if ext in ['csv', 'json', 'zip']:
                self.format = ext
        super().save(*args, **kwargs)


class TrainingJob(models.Model):
    """Training job model for tracking model training tasks."""

    STATUS_CHOICES = [
        ('queued', '排队中'),
        ('provisioning', '资源分配中'),
        ('preparing', '准备数据中'),
        ('running', '训练中'),
        ('validating', '验证中'),
        ('packaging', '打包中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
        ('timeout', '超时'),
    ]

    TRAINING_KIND_CHOICES = [
        ('generic', '通用训练'),
        ('yolo', 'YOLO训练'),
        ('clip_cls', 'CLIP分类'),
        ('clip_ret', 'CLIP检索'),
        ('transformer', 'Transformer微调'),
    ]

    FRAMEWORK_CHOICES = [
        ('pytorch', 'PyTorch'),
        ('transformers', 'Transformers'),
        ('keras', 'Keras'),
        ('tensorflow', 'TensorFlow'),
        ('ultralytics', 'Ultralytics'),
    ]

    MODEL_TYPE_CHOICES = [
        ('classifier', '分类器'),
        ('classification', '分类'),
        ('regressor', '回归器'),
        ('generator', '生成器'),
        ('custom', '自定义'),
        ('detection', '目标检测'),
        ('retrieval', '检索'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, verbose_name='任务名称')
    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='training_jobs',
        verbose_name='所属工作流',
        db_index=True
    )
    node = models.ForeignKey(
        'workflows.Node',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='training_jobs',
        verbose_name='所属节点'
    )
    execution = models.ForeignKey(
        'workflows.WorkflowExecution',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='training_jobs',
        verbose_name='所属执行'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='queued',
        verbose_name='状态',
        db_index=True
    )
    training_kind = models.CharField(
        max_length=20,
        choices=TRAINING_KIND_CHOICES,
        default='generic',
        verbose_name='训练类型',
        db_index=True
    )
    config = models.JSONField(default=dict, verbose_name='节点配置快照')
    dataset_id = models.CharField(max_length=100, blank=True, verbose_name='数据集ID')
    dataset_path = models.CharField(max_length=500, blank=True, verbose_name='数据集路径')
    dataset_yaml_path = models.CharField(max_length=500, blank=True, verbose_name='YOLO数据集配置路径')
    dataset_source_mode = models.CharField(max_length=50, blank=True, verbose_name='数据集来源模式')
    annotation_project_id = models.CharField(max_length=100, blank=True, verbose_name='标注项目ID')
    class_names = models.JSONField(default=list, verbose_name='类别名称')
    model_path = models.CharField(max_length=500, blank=True, verbose_name='模型路径')
    best_weight_path = models.CharField(max_length=500, blank=True, verbose_name='最佳权重路径')
    last_weight_path = models.CharField(max_length=500, blank=True, verbose_name='最终权重路径')
    exported_artifacts = models.JSONField(default=dict, verbose_name='导出产物')
    framework = models.CharField(max_length=50, choices=FRAMEWORK_CHOICES, verbose_name='框架')
    model_type = models.CharField(max_length=50, verbose_name='模型类型')
    yolo_version = models.CharField(max_length=20, blank=True, verbose_name='YOLO版本')
    model_variant = models.CharField(max_length=20, blank=True, verbose_name='YOLO模型规格')
    gpu_info = models.JSONField(
        default=dict,
        verbose_name='GPU信息',
        help_text='{available, name, memory_total, memory_free, driver_version, recommended_batch_size}'
    )
    progress = models.IntegerField(default=0, verbose_name='进度(0-100)')
    current_epoch = models.IntegerField(default=0, verbose_name='当前轮次')
    total_epochs = models.IntegerField(default=0, verbose_name='总轮次')
    current_loss = models.FloatField(default=0.0, verbose_name='当前损失')
    current_metric = models.FloatField(default=0.0, verbose_name='当前指标')
    duration_seconds = models.IntegerField(default=0, verbose_name='训练时长(秒)')
    metrics_history = models.JSONField(
        default=list,
        verbose_name='训练历史',
        help_text='List of metrics per epoch'
    )
    loss_box_history = models.JSONField(default=list, verbose_name='YOLO Box Loss历史')
    loss_cls_history = models.JSONField(default=list, verbose_name='YOLO Cls Loss历史')
    loss_dfl_history = models.JSONField(default=list, verbose_name='YOLO DFL Loss历史')
    precision_history = models.JSONField(default=list, verbose_name='YOLO Precision历史')
    recall_history = models.JSONField(default=list, verbose_name='YOLO Recall历史')
    map50_history = models.JSONField(default=list, verbose_name='YOLO mAP50历史')
    map50_95_history = models.JSONField(default=list, verbose_name='YOLO mAP50-95历史')
    metrics = models.JSONField(
        default=dict,
        verbose_name='训练指标',
        help_text='{train_loss, train_acc, val_loss, val_acc} per epoch'
    )
    learning_rate = models.FloatField(default=0.0, verbose_name='当前学习率')
    best_epoch = models.IntegerField(default=0, verbose_name='最佳轮次')
    best_fitness = models.FloatField(default=0.0, verbose_name='最佳适应度')
    estimated_duration_seconds = models.IntegerField(default=0, verbose_name='预计总时长(秒)')
    eta_seconds = models.IntegerField(default=0, verbose_name='预计剩余时长(秒)')
    preview_samples = models.JSONField(default=list, verbose_name='验证样例预览')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    job_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Celery任务ID',
        db_index=True
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_jobs',
        verbose_name='创建者'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_jobs',
        verbose_name='所属租户',
        db_index=True
    )

    class Meta:
        db_table = 'training_jobs'
        verbose_name = '训练任务'
        verbose_name_plural = '训练任务'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['workflow']),
            models.Index(fields=['node']),
            models.Index(fields=['status']),
            models.Index(fields=['training_kind']),
            models.Index(fields=['framework']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['job_id']),
        ]

    def __str__(self):
        return f"TrainingJob {self.id} ({self.status})"

    def mark_running(self):
        """Mark job as running."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self, model_path: str = None):
        """Mark job as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.progress = 100
        if model_path:
            self.model_path = model_path
        self.save(update_fields=['status', 'completed_at', 'progress', 'model_path'])

    def mark_failed(self, error_message: str):
        """Mark job as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])

    def mark_cancelled(self):
        """Mark job as cancelled."""
        self.status = 'cancelled'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])

    def update_progress(self, epoch: int, total_epochs: int, metrics: dict = None):
        """Update training progress."""
        self.current_epoch = epoch
        self.total_epochs = total_epochs
        if metrics:
            self.metrics = metrics
        self.progress = min(100, int(epoch / total_epochs * 100)) if total_epochs > 0 else 0
        self.save(update_fields=['current_epoch', 'total_epochs', 'metrics', 'progress'])

    def add_metrics_entry(self, epoch: int, loss: float = None, metric: float = None):
        """Add an entry to the training metrics history."""
        if not hasattr(self, 'metrics_history') or not self.metrics_history:
            self.metrics_history = []
        self.metrics_history.append({
            'epoch': epoch,
            'loss': loss,
            'metric': metric,
            'timestamp': timezone.now().isoformat()
        })
        self.save(update_fields=['metrics_history'])
