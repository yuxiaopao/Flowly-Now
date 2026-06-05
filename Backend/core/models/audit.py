"""
Audit logging models for tracking user actions.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditAction(models.TextChoices):
    """Audit action types."""
    # Authentication
    LOGIN = 'login', '登录'
    LOGOUT = 'logout', '登出'
    LOGIN_FAILED = 'login_failed', '登录失败'
    PASSWORD_CHANGE = 'password_change', '修改密码'
    PASSWORD_RESET = 'password_reset', '重置密码'

    # User management
    USER_CREATE = 'user_create', '创建用户'
    USER_UPDATE = 'user_update', '更新用户'
    USER_DELETE = 'user_delete', '删除用户'
    USER_ROLE_CHANGE = 'user_role_change', '角色变更'

    # Workflow
    WORKFLOW_CREATE = 'workflow_create', '创建工作流'
    WORKFLOW_UPDATE = 'workflow_update', '更新工作流'
    WORKFLOW_DELETE = 'workflow_delete', '删除工作流'
    WORKFLOW_EXECUTE = 'workflow_execute', '执行工作流'
    WORKFLOW_EXPORT = 'workflow_export', '导出工作流'
    WORKFLOW_IMPORT = 'workflow_import', '导入工作流'
    WORKFLOW_VERSION_CREATE = 'workflow_version_create', '创建版本'

    # Agent
    AGENT_CREATE = 'agent_create', '创建Agent'
    AGENT_UPDATE = 'agent_update', '更新Agent'
    AGENT_DELETE = 'agent_delete', '删除Agent'
    AGENT_EXECUTE = 'agent_execute', '执行Agent'

    # API Keys
    API_KEY_CREATE = 'api_key_create', '创建API Key'
    API_KEY_REVOKE = 'api_key_revoke', '撤销API Key'

    # Settings
    SETTINGS_UPDATE = 'settings_update', '更新设置'
    TEAM_UPDATE = 'team_update', '更新团队'

    # Billing
    SUBSCRIPTION_CREATE = 'subscription_create', '创建订阅'
    SUBSCRIPTION_UPDATE = 'subscription_update', '更新订阅'
    SUBSCRIPTION_CANCEL = 'subscription_cancel', '取消订阅'
    PAYMENT_SUCCESS = 'payment_success', '支付成功'
    PAYMENT_FAILED = 'payment_failed', '支付失败'

    # Data
    DATA_EXPORT = 'data_export', '数据导出'
    DATA_DELETE = 'data_delete', '数据删除'

    # Other
    OTHER = 'other', '其他'


class AuditLevel(models.TextChoices):
    """Audit log levels."""
    INFO = 'info', '信息'
    WARNING = 'warning', '警告'
    ERROR = 'error', '错误'
    CRITICAL = 'critical', '严重'


class AuditLog(models.Model):
    """Audit log entry."""

    # Actor (who performed the action)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='core_audit_logs',
        verbose_name='用户'
    )

    # Action details
    action = models.CharField(
        max_length=50,
        choices=AuditAction.choices,
        default=AuditAction.OTHER,
        verbose_name='操作'
    )

    level = models.CharField(
        max_length=20,
        choices=AuditLevel.choices,
        default=AuditLevel.INFO,
        verbose_name='级别'
    )

    # Description
    description = models.TextField(verbose_name='描述')
    message = models.TextField(blank=True, verbose_name='消息')

    # Target (what was affected)
    target_type = models.CharField(max_length=50, blank=True, verbose_name='目标类型')
    target_id = models.CharField(max_length=100, blank=True, verbose_name='目标ID')
    target_name = models.CharField(max_length=200, blank=True, verbose_name='目标名称')

    # Changes (for updates)
    changes = models.JSONField(default=dict, blank=True, verbose_name='变更内容')
    old_values = models.JSONField(default=dict, blank=True, verbose_name='旧值')
    new_values = models.JSONField(default=dict, blank=True, verbose_name='新值')

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 地址')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    request_method = models.CharField(max_length=10, blank=True, verbose_name='请求方法')
    request_path = models.CharField(max_length=500, blank=True, verbose_name='请求路径')

    # Resource
    resource_type = models.CharField(max_length=50, blank=True, verbose_name='资源类型')
    resource_id = models.CharField(max_length=100, blank=True, verbose_name='资源ID')

    # Metadata
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')
    status_code = models.IntegerField(null=True, blank=True, verbose_name='状态码')

    # Tenant (for multi-tenancy)
    tenant_id = models.CharField(max_length=100, blank=True, verbose_name='租户ID')

    # Timing
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name='执行时长(毫秒)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'core_audit_logs'
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['tenant_id', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"{user_str} - {self.get_action_display()} - {self.created_at}"

    @classmethod
    def log(
        cls,
        action: str,
        description: str,
        user=None,
        level: str = AuditLevel.INFO,
        target_type: str = '',
        target_id: str = '',
        target_name: str = '',
        changes: dict = None,
        old_values: dict = None,
        new_values: dict = None,
        ip_address: str = None,
        user_agent: str = '',
        request_method: str = '',
        request_path: str = '',
        resource_type: str = '',
        resource_id: str = '',
        metadata: dict = None,
        status_code: int = None,
        tenant_id: str = '',
        duration_ms: int = None,
    ):
        """Create an audit log entry."""
        return cls.objects.create(
            user=user,
            action=action,
            level=level,
            description=description,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            changes=changes or {},
            old_values=old_values or {},
            new_values=new_values or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
            status_code=status_code,
            tenant_id=tenant_id,
            duration_ms=duration_ms,
        )


class LoginHistory(models.Model):
    """Track user login history."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name='用户'
    )

    # Login details
    login_type = models.CharField(
        max_length=20,
        choices=[
            ('password', '密码登录'),
            ('sso', 'SSO登录'),
            ('oauth', 'OAuth登录'),
            ('api_key', 'API Key'),
        ],
        default='password',
        verbose_name='登录类型'
    )

    ip_address = models.GenericIPAddressField(verbose_name='IP 地址')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')

    # Location
    country = models.CharField(max_length=100, blank=True, verbose_name='国家')
    city = models.CharField(max_length=100, blank=True, verbose_name='城市')

    # Status
    success = models.BooleanField(default=True, verbose_name='是否成功')
    failure_reason = models.CharField(max_length=200, blank=True, verbose_name='失败原因')

    # Device info
    device_type = models.CharField(max_length=50, blank=True, verbose_name='设备类型')
    browser = models.CharField(max_length=100, blank=True, verbose_name='浏览器')
    os = models.CharField(max_length=100, blank=True, verbose_name='操作系统')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='登录时间')

    class Meta:
        db_table = 'login_history'
        verbose_name = '登录历史'
        verbose_name_plural = '登录历史'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]

    def __str__(self):
        status = '成功' if self.success else '失败'
        return f"{self.user.username} - {status} - {self.created_at}"


class DataExport(models.Model):
    """Track data exports for compliance."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='data_exports',
        verbose_name='用户'
    )

    export_type = models.CharField(
        max_length=30,
        choices=[
            ('full', '全量导出'),
            ('workflows', '工作流导出'),
            ('executions', '执行记录导出'),
            ('usage', '使用记录导出'),
            ('audit_logs', '审计日志导出'),
        ],
        verbose_name='导出类型'
    )

    # Format
    format = models.CharField(
        max_length=20,
        choices=[
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('xlsx', 'Excel'),
        ],
        default='json',
        verbose_name='格式'
    )

    # Filters
    date_from = models.DateTimeField(null=True, blank=True, verbose_name='开始日期')
    date_to = models.DateTimeField(null=True, blank=True, verbose_name='结束日期')
    filters = models.JSONField(default=dict, blank=True, verbose_name='筛选条件')

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待处理'),
            ('processing', '处理中'),
            ('completed', '已完成'),
            ('failed', '失败'),
        ],
        default='pending',
        verbose_name='状态'
    )

    # File
    file_name = models.CharField(max_length=200, blank=True, verbose_name='文件名')
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name='文件大小')
    file_url = models.URLField(blank=True, verbose_name='文件URL')

    # Download
    download_count = models.IntegerField(default=0, verbose_name='下载次数')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='过期时间')

    # Error
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'data_exports'
        verbose_name = '数据导出'
        verbose_name_plural = '数据导出'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_export_type_display()} - {self.created_at}"
