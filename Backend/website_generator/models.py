"""
Models for website generator app.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class GeneratedSite(models.Model):
    """
    Records a generated website from trained ML model.
    Tracks the generation progress, generated files, and deployment status.
    """

    STATUS_CHOICES = [
        ('generating', '生成中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('iterating', '迭代中'),
    ]

    STATUS_CHOICES += [
        ('profiling', 'Profiling'),
        ('environment_ready', 'Environment ready'),
        ('backend_ready', 'Backend ready'),
        ('frontend_ready', 'Frontend ready'),
        ('ui_polished', 'UI polished'),
        ('reviewing', 'Reviewing'),
        ('qa_running', 'QA running'),
        ('repairing', 'Repairing'),
        ('preview_ready', 'Preview ready'),
        ('failed_with_report', 'Failed with report'),
    ]

    PREVIEW_STATUS_CHOICES = [
        ('', '未知'),
        ('live', '可预览'),
        ('blocked', '已阻断'),
        ('stale', '已过期'),
    ]

    WEBSITE_TYPE_CHOICES = [
        ('classification', '图像分类'),
        ('regression', '回归预测'),
        ('detection', '目标检测'),
        ('segmentation', '图像分割'),
        ('clip_retrieval', 'CLIP 检索'),
        ('nlp_classification', '文本分类'),
        ('ner', '命名实体识别'),
    ]

    FRONTEND_FRAMEWORK_CHOICES = [
        ('vue', 'Vue 3'),
        ('react', 'React'),
        ('html', '纯HTML/JS'),
    ]

    BACKEND_FRAMEWORK_CHOICES = [
        ('flask', 'Flask'),
        ('fastapi', 'FastAPI'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name='网站名称')
    description = models.TextField(blank=True, verbose_name='网站描述')

    # Model info
    model_path = models.CharField(max_length=500, verbose_name='模型路径')
    model_type = models.CharField(
        max_length=50,
        default='classification',
        verbose_name='模型类型'
    )
    labels = models.JSONField(default=list, verbose_name='类别标签')
    framework = models.CharField(max_length=50, default='pytorch', verbose_name='框架')

    # YOLO Training Link
    training_run_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='训练运行ID',
        help_text='关联的 YOLO 训练运行 ID'
    )
    yolo_version = models.CharField(max_length=20, blank=True, verbose_name='YOLO版本')
    yolo_variant = models.CharField(max_length=20, blank=True, verbose_name='YOLO模型规格')
    best_weight_path = models.CharField(max_length=500, blank=True, verbose_name='最佳权重路径')
    last_weight_path = models.CharField(max_length=500, blank=True, verbose_name='最终权重路径')
    class_names = models.JSONField(default=list, verbose_name='类别名称')

    model_artifact_manifest = models.JSONField(default=dict, blank=True, verbose_name='Model artifact manifest')

    # Generated code
    output_dir = models.CharField(max_length=500, verbose_name='输出目录')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='generating',
        verbose_name='状态'
    )
    generated_files = models.JSONField(default=list, verbose_name='生成的文件列表')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    progress = models.IntegerField(default=0, verbose_name='进度百分比')

    # Website config
    website_type = models.CharField(
        max_length=50,
        choices=WEBSITE_TYPE_CHOICES,
        default='classification',
        verbose_name='网站类型'
    )
    frontend_framework = models.CharField(
        max_length=50,
        choices=FRONTEND_FRAMEWORK_CHOICES,
        default='vue',
        verbose_name='前端框架'
    )
    backend_framework = models.CharField(
        max_length=50,
        choices=BACKEND_FRAMEWORK_CHOICES,
        default='flask',
        verbose_name='后端框架'
    )

    site_brief = models.JSONField(default=dict, blank=True, verbose_name='Site brief')
    required_features = models.JSONField(default=list, blank=True, verbose_name='Required features')
    theme_profile = models.JSONField(default=dict, blank=True, verbose_name='Theme profile')
    environment_config = models.JSONField(default=dict, blank=True, verbose_name='Environment config')
    agent_memory_enabled = models.BooleanField(default=True, verbose_name='Agent memory enabled')

    # Deployment info
    inference_endpoint = models.CharField(max_length=500, blank=True, verbose_name='推理端点')
    port = models.IntegerField(default=5000, verbose_name='后端端口')
    codegraph_project_id = models.IntegerField(null=True, blank=True, verbose_name='CodeGraph 项目ID')
    show_in_nav = models.BooleanField(default=True, verbose_name='显示在侧栏导航')
    last_qa_gate = models.CharField(max_length=20, blank=True, verbose_name='最近QA档位')
    last_qa_report = models.JSONField(default=dict, blank=True, verbose_name='最近QA报告')
    last_preview_url = models.CharField(max_length=500, blank=True, verbose_name='最近预览URL')
    preview_status = models.CharField(
        max_length=20,
        choices=PREVIEW_STATUS_CHOICES,
        blank=True,
        default='',
        verbose_name='预览状态',
    )
    rag_collection_id = models.UUIDField(null=True, blank=True, verbose_name='项目RAG集合ID')
    last_agent_reply = models.JSONField(default=dict, blank=True, verbose_name='最近Agent回复')

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='generated_sites',
        verbose_name='所属租户',
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_sites',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'generated_sites'
        verbose_name = '生成网站'
        verbose_name_plural = '生成网站'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['website_type']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['tenant', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def is_complete(self):
        return self.status == 'completed'

    @property
    def is_failed(self):
        return self.status == 'failed'

    @property
    def is_generating(self):
        return self.status == 'generating'

    @property
    def duration_seconds(self):
        if self.created_at and self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return None

    def mark_generating(self):
        from django.utils import timezone
        self.status = 'generating'
        self.save(update_fields=['status'])

    def mark_completed(self, generated_files=None):
        from django.utils import timezone
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.progress = 100
        if generated_files:
            self.generated_files = generated_files
            self.save(update_fields=['status', 'completed_at', 'progress', 'generated_files'])
        else:
            self.save(update_fields=['status', 'completed_at', 'progress'])

    def mark_failed(self, error_message):
        from django.utils import timezone
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])

    def mark_iterating(self):
        self.status = 'iterating'
        self.save(update_fields=['status'])

    def update_progress(self, progress):
        self.progress = min(progress, 99)
        self.save(update_fields=['progress'])
