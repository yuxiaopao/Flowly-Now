"""
Workflow models for Flowly.
"""

import json
import uuid
from typing import Optional

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Workflow(models.Model):
    """Workflow model."""

    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflows',
        verbose_name='所属租户',
        db_index=True
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workflows',
        verbose_name='所有者',
        db_index=True
    )

    name = models.CharField(max_length=200, verbose_name='工作流名称')
    description = models.TextField(null=True, blank=True, verbose_name='描述')
    version = models.IntegerField(default=1, verbose_name='版本号')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='状态',
        db_index=True
    )
    category = models.CharField(max_length=100, null=True, blank=True, verbose_name='分类')

    tags = models.JSONField(default=list, blank=True, verbose_name='标签')
    config = models.JSONField(default=dict, blank=True, verbose_name='配置')

    # Execution statistics
    total_executions = models.IntegerField(default=0, verbose_name='总执行次数')
    successful_executions = models.IntegerField(default=0, verbose_name='成功次数')
    failed_executions = models.IntegerField(default=0, verbose_name='失败次数')
    avg_execution_time_ms = models.IntegerField(null=True, blank=True, verbose_name='平均执行时间(ms)')
    last_executed_at = models.DateTimeField(null=True, blank=True, verbose_name='最后执行时间')

    # Permissions
    is_public = models.BooleanField(default=False, verbose_name='是否公开')
    share_token = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        verbose_name='分享令牌'
    )

    # Version control
    parent_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions',
        verbose_name='父版本'
    )
    change_summary = models.TextField(null=True, blank=True, verbose_name='变更说明')

    # Soft delete
    is_deleted = models.BooleanField(default=False, verbose_name='已删除')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='删除时间')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'workflows'
        verbose_name = '工作流'
        verbose_name_plural = '工作流'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['owner', '-updated_at']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} (v{self.version})"

    @property
    def node_count(self):
        return self.nodes.count()

    @property
    def execution_count(self):
        return self.executions.count()


class Node(models.Model):
    """Workflow node model."""

    NODE_TYPE_CHOICES = [
        ('start', '开始'),
        ('end', '结束'),
        ('llm', '大语言模型'),
        ('prompt', '提示词'),
        ('condition', '条件判断'),
        ('tool', '工具调用'),
        ('input', '输入'),
        ('output', '输出'),
        ('code', '代码执行'),
        ('loop', '循环'),
        ('switch', '分支选择'),
        ('delay', '延时'),
        ('subworkflow', '子工作流'),
        ('http_request', 'HTTP请求'),
        ('data_transform', '数据转换'),
        ('email', '邮件'),
        ('webhook', 'Webhook'),
        ('template', '模板'),
        ('variable', '变量'),
        ('rag', '知识检索'),
        # Multimodal
        ('image_generation', '图像生成'),
        ('video_generation', '视频生成'),
        ('audio_generation', '音频生成'),
        ('subtitle_generation', '字幕生成'),
        ('image_editing', '图像编辑'),
        ('video_translation', '视频翻译'),
        ('video_upload', '视频上传'),
        ('subtitle_translate', '字幕翻译'),
        ('segment_dubbing', '分段配音'),
        ('lip_sync', '口型同步'),
        ('subtitle_burn', '字幕烧录'),
        # Data
        ('dataset_upload', '数据集上传'),
        ('data_annotation', '数据标注'),
        ('data_augmentation', '数据增强'),
        # MLOps
        ('model_training', '模型训练'),
        ('model_evaluation', '模型评估'),
        ('model_deployment', '模型部署'),
        ('website_generator', '网站生成'),
        ('backend_setup', '后端搭建'),
        ('frontend_setup', '前端搭建'),
        ('ui_beautify', 'UI美化'),
        ('site_code_review', '代码复查'),
        ('environment_provision', '环境配置'),
        ('site_qa', '站点自查'),
        ('site_preview', '站点预览'),
        # RAG
        ('document_loader', '文档加载'),
        ('embedding', 'Embedding生成'),
        ('vector_store', '向量存储'),
        ('retriever', '检索器'),
        ('reranker', '重排序'),
        # Agent
        ('agent', '智能代理'),
        ('planner', '规划器'),
        ('executor', '执行器'),
        ('memory', '记忆'),
        # Utility
        ('file_reader', '文件读取'),
        ('file_writer', '文件写入'),
        ('web_scraper', '网页抓取'),
        ('csv_transform', 'CSV转换'),
        ('json_transform', 'JSON转换'),
        ('json_parser', 'JSON解析'),
        ('text_template', '文本模板'),
        # Control flow extensions
        ('merge', '合并'),
        ('split', '批量拆分'),
        ('filter', '过滤器'),
        ('set', 'Set赋值'),
        ('datetime', '日期时间'),
        # Triggers
        ('manual', '手动触发'),
        ('schedule', '定时触发'),
        ('form', '表单触发'),
        ('yolo_training', 'YOLO训练'),
        ('clip_classification', 'CLIP分类'),
        ('clip_retrieval', 'CLIP检索'),
        ('project_profiler', '场景分析'),
        ('project_agent', '项目Agent'),
        # Integrations
        ('slack', 'Slack'),
        ('discord', 'Discord'),
        ('telegram', 'Telegram'),
        ('microsoft_teams', 'Microsoft Teams'),
        ('notion', 'Notion'),
        ('google_sheets', 'Google Sheets'),
        ('google_drive', 'Google Drive'),
        ('github', 'GitHub'),
        ('gitlab', 'GitLab'),
        ('jira', 'Jira'),
        ('airtable', 'Airtable'),
        ('trello', 'Trello'),
        ('mysql', 'MySQL'),
        ('postgres', 'PostgreSQL'),
        ('mongodb', 'MongoDB'),
        ('redis', 'Redis'),
        ('elasticsearch', 'Elasticsearch'),
        ('aws_s3', 'AWS S3'),
        ('ftp', 'FTP/SFTP'),
        ('stripe', 'Stripe'),
        ('twilio', 'Twilio'),
        ('sendgrid', 'SendGrid'),
        ('openai_api', 'OpenAI API'),
        ('huggingface', 'Hugging Face'),
        ('push_notification', '推送通知'),
        ('rss_feed', 'RSS订阅'),
        ('feishu', '飞书'),
        ('dingtalk', '钉钉'),
        ('wechat_work', '企业微信'),
    ]

    ERROR_HANDLING_CHOICES = [
        ('stop', '停止'),
        ('skip', '跳过'),
        ('retry', '重试'),
        ('fallback', '备用值'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='nodes',
        verbose_name='所属工作流',
        db_index=True
    )
    parent_node = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_nodes',
        verbose_name='父节点'
    )

    node_type = models.CharField(
        max_length=50,
        choices=NODE_TYPE_CHOICES,
        verbose_name='节点类型',
        db_index=True
    )
    name = models.CharField(max_length=200, verbose_name='节点名称')
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='描述')

    # Position (canvas coordinates)
    position_x = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='X坐标'
    )
    position_y = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Y坐标'
    )
    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='宽度'
    )
    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='高度'
    )

    # Sort order - preserves the canvas arrangement order
    sort_order = models.IntegerField(default=0, verbose_name='排序')

    # Configuration
    config = models.JSONField(null=True, blank=True, verbose_name='节点配置')
    input_schema = models.JSONField(null=True, blank=True, verbose_name='输入模式')
    output_schema = models.JSONField(null=True, blank=True, verbose_name='输出模式')

    # Styling
    style = models.JSONField(default=dict, blank=True, verbose_name='节点样式')

    # Error handling configuration
    error_handling = models.CharField(
        max_length=20,
        choices=ERROR_HANDLING_CHOICES,
        default='stop',
        verbose_name='错误处理策略'
    )
    max_retries = models.IntegerField(default=3, verbose_name='最大重试次数')
    retry_delay_seconds = models.IntegerField(default=5, verbose_name='重试延迟(秒)')
    fallback_value = models.JSONField(
        null=True,
        blank=True,
        verbose_name='备用值'
    )

    # Condition expression
    condition_expression = models.TextField(null=True, blank=True, verbose_name='条件表达式')

    # Execution control
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    timeout_seconds = models.IntegerField(null=True, blank=True, verbose_name='超时时间(秒)')

    # Version
    version = models.IntegerField(default=1, verbose_name='版本号')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'nodes'
        verbose_name = '节点'
        verbose_name_plural = '节点'
        ordering = ['sort_order', 'created_at']
        indexes = [
            models.Index(fields=['workflow']),
            models.Index(fields=['node_type']),
            models.Index(fields=['is_enabled']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_node_type_display()})"


class Edge(models.Model):
    """Workflow edge model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='edges',
        verbose_name='所属工作流',
        db_index=True
    )

    source_node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='outgoing_edges',
        verbose_name='源节点',
        db_index=True
    )
    source_handle = models.CharField(max_length=50, default='default', verbose_name='源节点出口')

    target_node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='incoming_edges',
        verbose_name='目标节点',
        db_index=True
    )
    target_handle = models.CharField(max_length=50, default='default', verbose_name='目标节点入口')

    label = models.CharField(max_length=200, null=True, blank=True, verbose_name='标签')
    style = models.JSONField(null=True, blank=True, verbose_name='连线样式')

    # Conditional edge
    condition_expression = models.TextField(null=True, blank=True, verbose_name='条件表达式')
    condition_priority = models.IntegerField(default=0, verbose_name='条件优先级')

    animated = models.BooleanField(default=False, verbose_name='是否动画')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'edges'
        verbose_name = '连接'
        verbose_name_plural = '连接'
        constraints = [
            models.UniqueConstraint(
                fields=['source_node', 'source_handle', 'target_node', 'target_handle'],
                name='unique_edge_connection'
            )
        ]
        indexes = [
            models.Index(fields=['workflow']),
            models.Index(fields=['source_node']),
            models.Index(fields=['target_node']),
        ]

    def __str__(self):
        return f"{self.source_node.name} → {self.target_node.name}"


class WorkflowExecution(models.Model):
    """Workflow execution record."""

    TRIGGER_TYPE_CHOICES = [
        ('manual', '手动触发'),
        ('scheduled', '定时任务'),
        ('webhook', 'Webhook'),
        ('api', 'API调用'),
        ('event', '事件触发'),
    ]

    STATUS_CHOICES = [
        ('queued', '排队中'),
        ('pending', '等待中'),
        ('running', '运行中'),
        ('paused', '已暂停'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
        ('timeout', '超时'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='工作流',
        db_index=True
    )
    version = models.IntegerField(verbose_name='工作流版本')

    trigger_type = models.CharField(
        max_length=20,
        choices=TRIGGER_TYPE_CHOICES,
        default='manual',
        verbose_name='触发类型',
        db_index=True
    )
    trigger_config = models.JSONField(null=True, blank=True, verbose_name='触发配置')
    trigger_source = models.JSONField(default=dict, blank=True, verbose_name='触发源信息')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='queued',
        verbose_name='状态',
        db_index=True
    )

    # Input/Output data
    input_data = models.JSONField(null=True, blank=True, verbose_name='输入数据')
    output_data = models.JSONField(null=True, blank=True, verbose_name='输出数据')

    # Node execution statistics
    total_nodes = models.IntegerField(null=True, blank=True, verbose_name='总节点数')
    executed_nodes = models.IntegerField(null=True, blank=True, verbose_name='已执行节点数')
    skipped_nodes = models.IntegerField(null=True, blank=True, verbose_name='已跳过节点数')
    failed_nodes = models.IntegerField(null=True, blank=True, verbose_name='失败节点数')

    # Error tracking
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息')
    error_stack = models.TextField(null=True, blank=True, verbose_name='错误堆栈')

    # Node execution status (node_id -> status mapping)
    node_status = models.JSONField(
        default=dict,
        verbose_name='节点执行状态'
    )

    # Node execution logs (detailed per-node execution info)
    execution_logs = models.JSONField(
        default=list,
        blank=True,
        verbose_name='执行日志'
    )

    # Token usage and cost
    token_usage = models.JSONField(null=True, blank=True, verbose_name='Token使用量')
    cost_amount = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='费用'
    )
    cost_currency = models.CharField(max_length=10, default='USD', verbose_name='货币')

    # Timing
    queued_at = models.DateTimeField(auto_now_add=True, verbose_name='排队时间')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    paused_at = models.DateTimeField(null=True, blank=True, verbose_name='暂停时间')
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name='执行耗时(ms)')

    # Metadata
    triggered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_executions',
        verbose_name='触发者',
        db_index=True
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executions',
        verbose_name='租户',
        db_index=True
    )

    # Celery task ID
    task_id = models.CharField(max_length=255, blank=True, verbose_name='Celery Task ID')

    # Progress tracking
    progress = models.IntegerField(
        default=0,
        verbose_name='进度百分比'
    )
    current_node_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='当前执行节点ID'
    )

    # Context snapshot (for pause/resume)
    context_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='上下文快照'
    )

    context_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='上下文数据'
    )

    class Meta:
        db_table = 'workflow_executions'
        verbose_name = '执行记录'
        verbose_name_plural = '执行记录'
        ordering = ['-queued_at']
        indexes = [
            models.Index(fields=['workflow', '-queued_at']),
            models.Index(fields=['status']),
            models.Index(fields=['trigger_type']),
            models.Index(fields=['triggered_by', '-queued_at']),
            models.Index(fields=['tenant']),
            models.Index(fields=['-started_at']),
            models.Index(fields=['-queued_at']),
        ]

    def __str__(self):
        return f"{self.workflow.name} - {self.get_status_display()} ({self.id})"

    @property
    def duration(self):
        """Get execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_running(self):
        """Check if execution is currently running."""
        return self.status == 'running'

    @property
    def is_finished(self):
        """Check if execution has finished (completed, failed, or cancelled)."""
        return self.status in ['completed', 'failed', 'cancelled', 'timeout']

    def mark_started(self):
        """Mark execution as started."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self, output_data=None):
        """Mark execution as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.progress = 100
        if output_data:
            self.output_data = output_data
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save(update_fields=['status', 'completed_at', 'progress', 'output_data', 'duration_ms'])

    def mark_failed(self, error_message, error_stack=None):
        """Mark execution as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        if error_stack:
            self.error_stack = error_stack
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save(update_fields=['status', 'completed_at', 'error_message', 'error_stack', 'duration_ms'])

    def update_node_status(self, node_id: int, status: str, extra_data: dict = None):
        """Update the status of a specific node."""
        if self.node_status is None:
            self.node_status = {}

        self.node_status[str(node_id)] = status

        if extra_data:
            if str(node_id) not in self.node_status:
                self.node_status[str(node_id)] = {}
            if isinstance(self.node_status[str(node_id)], dict):
                self.node_status[str(node_id)].update(extra_data)
            else:
                self.node_status[str(node_id)] = {'status': status, **extra_data}

        self.save(update_fields=['node_status'])

    def add_execution_log(self, log_entry: dict):
        """Add an execution log entry."""
        if self.execution_logs is None:
            self.execution_logs = []

        self.execution_logs.append(log_entry)
        self.save(update_fields=['execution_logs'])

    def pause(self):
        """Pause the execution."""
        if self.status == 'running':
            self.status = 'paused'
            self.paused_at = timezone.now()
            self.save(update_fields=['status', 'paused_at'])

    def resume(self):
        """Resume a paused execution."""
        if self.status == 'paused':
            self.status = 'running'
            self.paused_at = None
            self.save(update_fields=['status', 'paused_at'])

    def cancel(self):
        """Cancel the execution."""
        if self.status in ['pending', 'queued', 'running', 'paused']:
            self.status = 'cancelled'
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at'])

    def save_context_snapshot(self, context_data: dict):
        """Save a snapshot of the execution context for pause/resume."""
        self.context_snapshot = context_data
        self.save(update_fields=['context_snapshot'])

    def get_context_snapshot(self) -> dict:
        """Get the saved context snapshot."""
        return self.context_snapshot or {}


class WebhookDeliveryLog(models.Model):
    """Log of webhook delivery attempts."""

    webhook_url = models.URLField(max_length=500, verbose_name='Webhook URL')
    execution = models.ForeignKey(
        'WorkflowExecution',
        on_delete=models.CASCADE,
        related_name='webhook_logs',
        verbose_name='执行记录'
    )

    # Request
    request_payload = models.TextField(verbose_name='请求载荷')

    # Response
    response_status_code = models.IntegerField(null=True, blank=True, verbose_name='响应状态码')
    response_body = models.TextField(blank=True, verbose_name='响应内容')

    # Status
    status = models.CharField(max_length=20, default='pending', verbose_name='状态')
    success = models.BooleanField(default=False, verbose_name='是否成功')

    # Error handling
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    retry_count = models.IntegerField(default=0, verbose_name='重试次数')

    # Timing
    duration_ms = models.IntegerField(default=0, verbose_name='耗时(ms)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workflow_webhook_delivery_logs'
        verbose_name = 'Webhook投递日志'
        verbose_name_plural = 'Webhook投递日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['execution', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.webhook_url} - {self.status}"


class NodeExecution(models.Model):
    """
    Node execution record for detailed per-node execution tracking.
    Tracks individual node execution status, timing, token usage, and cache hits.
    """

    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('skipped', '已跳过'),
        ('retrying', '重试中'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.CASCADE,
        related_name='node_executions',
        verbose_name='执行记录',
        db_index=True
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='节点',
        db_index=True
    )
    node_version = models.IntegerField(verbose_name='节点版本')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态',
        db_index=True
    )

    # Input/Output data
    input_data = models.JSONField(null=True, blank=True, verbose_name='输入数据')
    output_data = models.JSONField(null=True, blank=True, verbose_name='输出数据')

    # Timing
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name='执行耗时(ms)')

    # Error handling
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息')
    retry_count = models.IntegerField(default=0, verbose_name='重试次数')
    max_retries_exceeded = models.BooleanField(default=False, verbose_name='超过最大重试')

    # Model call info (for LLM nodes)
    model_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='模型名称')
    prompt_tokens = models.IntegerField(null=True, blank=True, verbose_name='输入Token')
    completion_tokens = models.IntegerField(null=True, blank=True, verbose_name='输出Token')
    total_tokens = models.IntegerField(null=True, blank=True, verbose_name='总Token')
    model_latency_ms = models.IntegerField(null=True, blank=True, verbose_name='模型延迟(ms)')

    # Cache info
    cache_hit = models.BooleanField(default=False, verbose_name='缓存命中', db_index=True)
    cache_key = models.CharField(max_length=100, null=True, blank=True, verbose_name='缓存键')

    # Token usage (for LLM nodes, stored as JSON for flexibility)
    token_usage = models.JSONField(default=dict, blank=True, verbose_name='Token使用量')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'node_executions'
        verbose_name = '节点执行'
        verbose_name_plural = '节点执行'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['execution']),
            models.Index(fields=['node']),
            models.Index(fields=['status']),
            models.Index(fields=['cache_hit']),
            models.Index(fields=['-started_at']),
        ]

    def __str__(self):
        return f"{self.node.name} - {self.get_status_display()}"

    @property
    def duration_seconds(self):
        """Get duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def mark_started(self):
        """Mark node execution as started."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])

    def mark_completed(self, output_data: dict = None):
        """Mark node execution as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if output_data is not None:
            try:
                self.output_data = json.loads(json.dumps(output_data, default=str, ensure_ascii=False))
            except (TypeError, ValueError):
                self.output_data = {'_raw': str(output_data)}
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save(update_fields=['status', 'completed_at', 'output_data', 'duration_ms', 'updated_at'])

    def mark_failed(self, error_message: str):
        """Mark node execution as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save(update_fields=['status', 'completed_at', 'error_message', 'duration_ms', 'updated_at'])

    def mark_skipped(self):
        """Mark node execution as skipped."""
        self.status = 'skipped'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def mark_retrying(self, error_message: str = ''):
        """Mark node execution as retrying."""
        self.status = 'retrying'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])


class ExecutionLog(models.Model):
    """
    Execution log for detailed per-node and workflow-level logging.
    Stores structured log entries with levels, messages, and metadata.
    """

    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.CASCADE,
        related_name='exec_logs',
        verbose_name='执行记录',
        db_index=True
    )

    node_execution = models.ForeignKey(
        NodeExecution,
        on_delete=models.CASCADE,
        related_name='exec_logs',
        null=True,
        blank=True,
        verbose_name='节点执行',
        db_index=True
    )

    level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        default='INFO',
        verbose_name='日志级别',
        db_index=True
    )

    message = models.TextField(verbose_name='日志消息')

    details = models.JSONField(default=dict, blank=True, verbose_name='详细信息')

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间戳')

    class Meta:
        db_table = 'execution_logs'
        verbose_name = '执行日志'
        verbose_name_plural = '执行日志'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['execution', 'timestamp']),
            models.Index(fields=['level']),
            models.Index(fields=['node_execution']),
        ]

    def __str__(self):
        return f"[{self.level}] {self.message[:100]}"


class Variable(models.Model):
    """
    Variable model for workflow variables management.
    Supports different variable types including secrets that can reference external credential stores.
    """

    TYPE_CHOICES = [
        ('string', '字符串'),
        ('number', '数字'),
        ('boolean', '布尔值'),
        ('json', 'JSON'),
        ('array', '数组'),
        ('secret', '密钥'),
    ]

    SOURCE_CHOICES = [
        ('user_input', '用户输入'),
        ('system', '系统'),
        ('workflow', '工作流'),
        ('execution', '执行'),
        ('secret', '密钥库'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='variables',
        verbose_name='所属工作流',
        null=True,
        blank=True,
        db_index=True
    )

    name = models.CharField(max_length=100, verbose_name='变量名称')
    display_name = models.CharField(max_length=200, blank=True, verbose_name='显示名称')
    description = models.TextField(blank=True, verbose_name='描述')

    var_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='string',
        verbose_name='变量类型',
        db_index=True
    )
    default_value = models.TextField(blank=True, verbose_name='默认值')
    validation_rules = models.JSONField(default=dict, blank=True, verbose_name='验证规则')

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='user_input',
        verbose_name='变量来源',
        db_index=True
    )
    secret_path = models.CharField(max_length=500, blank=True, verbose_name='密钥路径')

    is_required = models.BooleanField(default=False, verbose_name='是否必填')
    is_sensitive = models.BooleanField(default=False, verbose_name='是否敏感')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'variables'
        verbose_name = '变量'
        verbose_name_plural = '变量'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_var_type_display()})"


class Tool(models.Model):
    """
    Tool model for workflow tools/function definitions.
    Supports built-in tools, custom tools, API tools, and script tools.
    """

    TOOL_TYPE_CHOICES = [
        ('builtin', '内置工具'),
        ('custom', '自定义工具'),
        ('api', 'API工具'),
        ('script', '脚本工具'),
    ]

    AUTH_TYPE_CHOICES = [
        ('none', '无'),
        ('api_key', 'API Key'),
        ('oauth2', 'OAuth2'),
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tools',
        verbose_name='所属租户'
    )

    name = models.CharField(max_length=100, unique=True, verbose_name='工具名称')
    display_name = models.CharField(max_length=200, blank=True, verbose_name='显示名称')
    description = models.TextField(blank=True, verbose_name='描述')
    category = models.CharField(max_length=100, blank=True, verbose_name='分类', db_index=True)

    tool_type = models.CharField(
        max_length=20,
        choices=TOOL_TYPE_CHOICES,
        default='custom',
        verbose_name='工具类型',
        db_index=True
    )

    # Tool definition (JSON Schema format)
    definition = models.JSONField(default=dict, verbose_name='工具定义')
    input_schema = models.JSONField(default=dict, blank=True, verbose_name='输入模式')
    output_schema = models.JSONField(default=dict, blank=True, verbose_name='输出模式')

    # Authentication config
    auth_type = models.CharField(
        max_length=20,
        choices=AUTH_TYPE_CHOICES,
        default='none',
        verbose_name='认证类型'
    )
    credential = models.ForeignKey(
        'APICredential',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tools',
        verbose_name='关联凭证'
    )

    # Execution config
    timeout_seconds = models.IntegerField(default=30, verbose_name='超时时间(秒)')
    retry_policy = models.JSONField(default=dict, blank=True, verbose_name='重试策略')
    rate_limit = models.JSONField(default=dict, blank=True, verbose_name='速率限制')

    # Status
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用', db_index=True)
    is_public = models.BooleanField(default=False, verbose_name='是否公开')

    # Usage stats
    usage_count = models.IntegerField(default=0, verbose_name='使用次数')
    avg_execution_time_ms = models.IntegerField(null=True, blank=True, verbose_name='平均执行时间(ms)')
    success_rate = models.FloatField(default=0, verbose_name='成功率')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'tools'
        verbose_name = '工具'
        verbose_name_plural = '工具'
        ordering = ['name']
        indexes = [
            models.Index(fields=['tool_type']),
            models.Index(fields=['category']),
            models.Index(fields=['is_enabled']),
        ]

    def __str__(self):
        return f"{self.display_name or self.name} ({self.get_tool_type_display()})"


class APICredential(models.Model):
    """
    API Credential model for secure storage of third-party service credentials.
    Supports multiple credential types and encrypts sensitive data.
    """

    # Provider to environment variable mapping
    PROVIDER_ENV_MAP = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'stability': 'STABILITY_API_KEY',
        'replicate': 'REPLICATE_API_KEY',
        'elevenlabs': 'ELEVENLABS_API_KEY',
        'pinecone': 'PINECONE_API_KEY',
        'huggingface': 'HUGGINGFACE_API_TOKEN',
        'cohere': 'COHERE_API_KEY',
        'runway': 'RUNWAY_API_KEY',
        'pika': 'PIKA_API_KEY',
        'azure_tts': 'AZURE_TTS_KEY',
        'qdrant': 'QDRANT_API_KEY',
        'azure': 'AZURE_OPENAI_API_KEY',
        'dashscope': 'DASHSCOPE_API_KEY',
        'agnes': 'AGNES_API_KEY',
    }

    CREDENTIAL_TYPE_CHOICES = [
        ('api_key', 'API Key'),
        ('oauth2', 'OAuth2'),
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
        ('aws', 'AWS'),
        ('azure', 'Azure'),
    ]

    SERVICE_TYPE_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('google', 'Google AI'),
        ('azure', 'Azure'),
        ('aws', 'AWS'),
        ('slack', 'Slack'),
        ('discord', 'Discord'),
        ('github', 'GitHub'),
        ('feishu', '飞书'),
        ('dingtalk', '钉钉'),
        ('wechat_work', '企业微信'),
        ('telegram', 'Telegram'),
        ('notion', 'Notion'),
        ('jira', 'Jira'),
        ('mysql', 'MySQL'),
        ('postgres', 'PostgreSQL'),
        ('mongodb', 'MongoDB'),
        ('redis', 'Redis'),
        ('stripe', 'Stripe'),
        ('twilio', 'Twilio'),
        ('sendgrid', 'SendGrid'),
        ('microsoft_teams', 'Microsoft Teams'),
        ('stability', 'Stability AI'),
        ('replicate', 'Replicate'),
        ('elevenlabs', 'ElevenLabs'),
        ('pinecone', 'Pinecone'),
        ('huggingface', 'HuggingFace'),
        ('cohere', 'Cohere'),
        ('runway', 'Runway'),
        ('pika', 'Pika'),
        ('deepseek', 'DeepSeek'),
        ('ollama', 'Ollama'),
        ('mistral', 'Mistral'),
        ('groq', 'Groq'),
        ('dashscope', '阿里云百炼(DashScope)'),
        ('agnes', 'Agnes AI'),
        ('custom', '自定义'),
    ]

    SCOPE_CHOICES = [
        ('user', '用户级 — 仅自己可用'),
        ('tenant', '租户级 — 租户内共享'),
        ('global', '全局 — 所有用户可用'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_credentials',
        verbose_name='所属租户',
        db_index=True
    )

    name = models.CharField(max_length=200, verbose_name='凭证名称')
    description = models.TextField(blank=True, verbose_name='描述')

    credential_type = models.CharField(
        max_length=20,
        choices=CREDENTIAL_TYPE_CHOICES,
        verbose_name='凭证类型',
        db_index=True
    )

    # Credential data (encrypted)
    credential_data = models.TextField(verbose_name='凭证数据(加密)')
    credential_data_hash = models.CharField(max_length=64, blank=True, verbose_name='凭证数据哈希')

    # Encryption flag
    is_encrypted = models.BooleanField(default=True, verbose_name='是否加密', db_index=True)

    # Associated service
    service_type = models.CharField(
        max_length=50,
        choices=SERVICE_TYPE_CHOICES,
        blank=True,
        verbose_name='服务类型',
        db_index=True
    )
    service_config = models.JSONField(default=dict, blank=True, verbose_name='服务配置')

    # Scope: user / tenant / global
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default='user',
        verbose_name='作用域',
        db_index=True
    )

    # Permission scope
    scope_permission = models.JSONField(default=list, blank=True, verbose_name='权限范围')

    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_credentials',
        verbose_name='所有者',
        db_index=True
    )

    # Status
    is_active = models.BooleanField(default=True, verbose_name='是否启用', db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='过期时间')
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最后使用时间')
    usage_count = models.IntegerField(default=0, verbose_name='使用次数')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'api_credentials'
        verbose_name = 'API凭证'
        verbose_name_plural = 'API凭证'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['credential_type']),
            models.Index(fields=['service_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['scope']),
            models.Index(fields=['scope', 'service_type', 'is_active']),
            models.Index(fields=['tenant', 'scope', 'service_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'service_type', 'name'],
                name='unique_credential_per_user'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_credential_type_display()})"

    @property
    def scope_display_text(self) -> str:
        """Return human-readable scope."""
        return dict(self.SCOPE_CHOICES).get(self.scope, self.scope)

    @classmethod
    def get_by_provider(cls, user, provider: str) -> Optional['APICredential']:
        """
        Get active credential for a user and provider.

        Args:
            user: User instance
            provider: Service provider name

        Returns:
            APICredential instance or None
        """
        return cls.objects.filter(
            owner=user,
            service_type=provider,
            is_active=True
        ).first()

    @classmethod
    def get_best_for_user(
        cls,
        user,
        provider: str,
        tenant_id=None,
        include_expired=False
    ) -> Optional['APICredential']:
        """
        Get the best available credential for a user with priority:
        user-level → tenant-level → global-level.

        Args:
            user: User instance
            provider: Service provider name
            tenant_id: Current tenant ID (optional)
            include_expired: If True, include expired credentials

        Returns:
            APICredential instance or None
        """
        from django.utils import timezone
        qs = cls.objects.filter(service_type=provider, is_active=True)
        if not include_expired:
            qs = qs.filter(
                models.Q(expires_at__isnull=True) |
                models.Q(expires_at__gt=timezone.now())
            )

        candidates = list(qs.filter(
            scope='user',
            owner=user
        ).order_by('-is_active', '-created_at'))

        if not candidates and tenant_id:
            candidates = list(qs.filter(
                scope='tenant',
                tenant_id=tenant_id
            ).order_by('-is_active', '-created_at'))

        if not candidates:
            candidates = list(qs.filter(
                scope='global'
            ).order_by('-is_active', '-created_at'))

        return candidates[0] if candidates else None

    @classmethod
    def get_for_user(cls, user, credential_id) -> Optional['APICredential']:
        """按 ID 获取用户有权访问的凭证。"""
        if not user or not credential_id:
            return None

        try:
            credential = cls.objects.get(id=credential_id, is_active=True)
        except cls.DoesNotExist:
            return None

        if user.is_superuser:
            return credential

        if credential.scope == 'global':
            return credential

        if credential.owner_id == user.id:
            return credential

        if credential.scope == 'tenant' and credential.tenant_id:
            try:
                from tenants.access import get_accessible_tenant_ids
                if credential.tenant_id in get_accessible_tenant_ids(user):
                    return credential
            except Exception:
                pass

        return None

    def get_decrypted_data(self) -> str:
        """
        Get the decrypted credential data.
        
        Returns:
            Decrypted credential string or empty string if unavailable
        """
        if not self.credential_data:
            return ''
        
        if self.is_encrypted:
            from .services.encryption_utils import decrypt_value
            return decrypt_value(self.credential_data)
        
        return self.credential_data

    def set_encrypted_data(self, plaintext: str) -> None:
        """
        Encrypt and store credential data.
        
        Args:
            plaintext: The plain text credential to encrypt and store
        """
        from .services.encryption_utils import encrypt_value, hash_value
        
        self.credential_data = encrypt_value(plaintext)
        self.credential_data_hash = hash_value(plaintext)
        self.is_encrypted = True

    def get_masked_data(self) -> str:
        """
        Get a masked version of the credential for display.
        
        Returns:
            Masked string like "sk-ab...xy"
        """
        from .services.encryption_utils import generate_masked_value
        
        decrypted = self.get_decrypted_data()
        return generate_masked_value(decrypted)

    def update_last_used(self) -> None:
        """Update last used timestamp and increment usage count."""
        self.last_used_at = timezone.now()
        self.usage_count += 1
        self.save(update_fields=['last_used_at', 'usage_count', 'updated_at'])

    def is_expired(self) -> bool:
        """Check if credential is expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def verify_integrity(self) -> bool:
        """
        Verify credential data integrity using hash.
        
        Returns:
            True if hash matches, False otherwise
        """
        if not self.credential_data_hash:
            return True
        
        from .services.encryption_utils import hash_value
        decrypted = self.get_decrypted_data()
        return hash_value(decrypted) == self.credential_data_hash


class AuditLog(models.Model):
    """
    Audit log model for tracking all sensitive operations.
    Records user actions, resource changes, and security-relevant events.
    """

    ACTION_CHOICES = [
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('execute', '执行'),
        ('login', '登录'),
        ('login_failure', '登录失败'),
        ('logout', '登出'),
        ('access', '访问'),
        ('export', '导出'),
        ('import', '导入'),
        ('share', '分享'),
        ('revoke', '撤销'),
    ]

    STATUS_CHOICES = [
        ('success', '成功'),
        ('failure', '失败'),
    ]

    id = models.BigAutoField(primary_key=True)

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='所属租户'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name='操作用户'
    )

    action = models.CharField(max_length=100, verbose_name='操作类型', db_index=True)
    resource_type = models.CharField(max_length=50, verbose_name='资源类型', db_index=True)
    resource_id = models.CharField(max_length=100, blank=True, verbose_name='资源ID', db_index=True)

    old_value = models.JSONField(null=True, blank=True, verbose_name='旧值')
    new_value = models.JSONField(null=True, blank=True, verbose_name='新值')

    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.CharField(max_length=500, blank=True, verbose_name='User Agent')
    request_id = models.CharField(max_length=100, blank=True, verbose_name='请求ID')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='success',
        verbose_name='状态'
    )
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        db_table = 'audit_logs'
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['resource_type']),
            models.Index(fields=['resource_id']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} {self.resource_type} @ {self.timestamp}"

    @classmethod
    def log(cls, user, action, resource_type, resource_id=None,
            old_value=None, new_value=None, request=None, status='success',
            error_message=None, tenant=None):
        """
        Create an audit log entry.
        """
        ip_address = None
        user_agent = None
        request_id = None

        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            request_id = request.META.get('HTTP_X_REQUEST_ID', '')

        return cls.objects.create(
            tenant=tenant,
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message or ''
        )


class TemplateCategory(models.Model):
    """Template category for organizing workflow templates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=20, default="#8b5cf6")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflows_template_categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class WorkflowTemplate(models.Model):
    """Workflow template for pre-built workflow patterns."""

    DIFFICULTY_CHOICES = [
        ('beginner', '入门'),
        ('intermediate', '进阶'),
        ('advanced', '高级'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        TemplateCategory,
        on_delete=models.CASCADE,
        related_name='templates'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='beginner'
    )
    tags = models.JSONField(default=list, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    workflow_data = models.JSONField()  # { nodes: [], edges: [] }
    variables_schema = models.JSONField(default=list, blank=True)
    estimated_duration = models.CharField(max_length=50, blank=True)
    required_apis = models.JSONField(default=list, blank=True)
    use_count = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)  # Whether the template is publicly listed
    report_count = models.IntegerField(default=0)
    version = models.IntegerField(default=1)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflow_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflows_workflow_templates'
        ordering = ['-use_count', '-rating']
        verbose_name = 'Workflow Template'
        verbose_name_plural = 'Workflow Templates'

    def __str__(self):
        return self.name


class TemplateInstall(models.Model):
    """
    Canonical record of template installations.
    Tracks which user installed which template and the resulting workflow.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_installs',
        verbose_name='User'
    )
    template = models.ForeignKey(
        'WorkflowTemplate',
        on_delete=models.CASCADE,
        related_name='installs',
        verbose_name='Template'
    )
    workflow = models.ForeignKey(
        'Workflow',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='template_install',
        verbose_name='Installed Workflow'
    )
    installed_at = models.DateTimeField(auto_now_add=True, verbose_name='Installed At')

    class Meta:
        db_table = 'workflows_template_installs'
        verbose_name = 'Template Install'
        verbose_name_plural = 'Template Installs'
        unique_together = ['user', 'template']
        ordering = ['-installed_at']
        indexes = [
            models.Index(fields=['template', '-installed_at']),
            models.Index(fields=['user', '-installed_at']),
        ]

    def __str__(self):
        return f"{self.user} installed {self.template}"


class TemplateRatingRecord(models.Model):
    """
    Canonical record of template ratings.
    Stores individual user ratings for templates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_ratings',
        verbose_name='User'
    )
    template = models.ForeignKey(
        'WorkflowTemplate',
        on_delete=models.CASCADE,
        related_name='rating_records',
        verbose_name='Template'
    )
    rating = models.PositiveSmallIntegerField(verbose_name='Rating (1-5)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'workflows_template_ratings'
        verbose_name = 'Template Rating'
        verbose_name_plural = 'Template Ratings'
        unique_together = ['user', 'template']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template', '-rating']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user} rated {self.template}: {self.rating}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not (1 <= self.rating <= 5):
            raise ValidationError({'rating': 'Rating must be between 1 and 5.'})


class TemplateReport(models.Model):
    """
    Canonical record of template reports.
    Tracks user-submitted reports against workflow templates.
    """
    REASON_CHOICES = [
        ('inappropriate', '不当内容'),
        ('spam', '垃圾信息'),
        ('copyright', '侵权内容'),
        ('misleading', '误导性内容'),
        ('broken', '内容损坏/不可用'),
        ('other', '其他'),
    ]

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('reviewed', '已审核'),
        ('resolved', '已处理'),
        ('dismissed', '已驳回'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_reports',
        verbose_name='举报人'
    )
    template = models.ForeignKey(
        'WorkflowTemplate',
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='被举报模板'
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        verbose_name='举报原因'
    )
    description = models.TextField(blank=True, verbose_name='补充说明')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='处理状态'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_template_reports',
        verbose_name='审核人'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    reviewed_notes = models.TextField(blank=True, verbose_name='审核备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='举报时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'workflows_template_reports'
        verbose_name = 'Template Report'
        verbose_name_plural = 'Template Reports'
        unique_together = ['user', 'template', 'reason']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user} reported {self.template} ({self.reason})"


class ExecutionCache(models.Model):
    """
    Execution cache - stores execution results based on node config hash.
    Enables idempotent execution: nodes with identical config return cached results directly.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config_hash = models.CharField(max_length=64, db_index=True, unique=True)
    node_type = models.CharField(max_length=50, db_index=True)
    node_config = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    access_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)
    is_valid = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name_plural = 'Execution caches'
        db_table = 'execution_cache'
        indexes = [
            models.Index(fields=['node_type', 'is_valid']),
            models.Index(fields=['last_accessed']),
        ]

    def __str__(self):
        return f"{self.node_type}@{self.config_hash[:8]}"

    def invalidate(self):
        """Mark cache entry as invalid."""
        self.is_valid = False
        self.save(update_fields=['is_valid'])

    @property
    def is_expired(self):
        """Check if cache entry has expired."""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at


class ExecutionCacheConfig(models.Model):
    """
    Cache configuration - controls which node types have caching enabled.
    """
    node_type = models.CharField(max_length=50, primary_key=True)
    enabled = models.BooleanField(default=True)
    ttl_hours = models.IntegerField(default=24, help_text='Cache TTL in hours')
    max_size_mb = models.IntegerField(default=100, help_text='Max cache size per node type in MB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.node_type}: {'ON' if self.enabled else 'OFF'} (TTL={self.ttl_hours}h)"

    class Meta:
        verbose_name_plural = 'Execution cache configs'
        db_table = 'execution_cache_config'


# Trigger / scheduling models (see scheduling.py)
from .scheduling import WorkflowTrigger, TriggerExecution  # noqa: F401, E402
