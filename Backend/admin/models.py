"""
Admin app models - system settings and platform configuration.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from .constants import DEFAULT_SYSTEM_SETTINGS


class SystemSetting(models.Model):
    """Key-value store for system-level settings managed from the admin panel."""

    key = models.CharField(max_length=100, unique=True, verbose_name='设置键')
    value = models.JSONField(verbose_name='设置值')

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_system_settings',
        verbose_name='最后修改人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'admin_system_settings'
        verbose_name = '系统设置'
        verbose_name_plural = '系统设置'
        ordering = ['key']

    def __str__(self):
        return self.key

    @classmethod
    def get_all(cls):
        settings_map = dict(DEFAULT_SYSTEM_SETTINGS)
        for item in cls.objects.all():
            settings_map[item.key] = item.value
        return settings_map

    @classmethod
    def get(cls, key, default=None):
        merged = cls.get_all()
        if key in merged:
            return merged[key]
        return default

    @classmethod
    def set_many(cls, data, user=None):
        for key, value in data.items():
            cls.objects.update_or_create(
                key=key,
                defaults={'value': value, 'updated_by': user},
            )


class LegalDocument(models.Model):
    """Legal documents with version control (terms, privacy, login agreement)."""

    DOC_TYPE_CHOICES = [
        ('terms', '服务条款'),
        ('privacy', '隐私政策'),
        ('login', '登录协议'),
    ]

    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, verbose_name='文档类型')
    version = models.CharField(max_length=32, verbose_name='版本号')
    title = models.CharField(max_length=200, verbose_name='标题')
    content_html = models.TextField(verbose_name='HTML 内容')
    content_markdown = models.TextField(blank=True, verbose_name='Markdown 内容')
    is_active = models.BooleanField(default=False, verbose_name='当前生效')
    require_acceptance = models.BooleanField(default=True, verbose_name='注册需确认')
    effective_at = models.DateTimeField(default=timezone.now, verbose_name='生效时间')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_legal_documents',
        verbose_name='创建人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'admin_legal_documents'
        verbose_name = '法律文档'
        verbose_name_plural = '法律文档'
        ordering = ['-effective_at', '-created_at']
        unique_together = [('doc_type', 'version')]

    def __str__(self):
        return f'{self.get_doc_type_display()} v{self.version}'

    def save(self, *args, **kwargs):
        if self.is_active:
            LegalDocument.objects.filter(
                doc_type=self.doc_type,
                is_active=True,
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class UserTermsAcceptance(models.Model):
    """Record of user acceptance of legal documents."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='terms_acceptances',
        verbose_name='用户',
    )
    document = models.ForeignKey(
        LegalDocument,
        on_delete=models.CASCADE,
        related_name='acceptances',
        verbose_name='文档',
    )
    document_version = models.CharField(max_length=32, verbose_name='确认版本')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 地址')
    user_agent = models.CharField(max_length=500, blank=True, verbose_name='User Agent')
    accepted_at = models.DateTimeField(auto_now_add=True, verbose_name='确认时间')

    class Meta:
        db_table = 'admin_user_terms_acceptance'
        verbose_name = '条款确认记录'
        verbose_name_plural = '条款确认记录'
        ordering = ['-accepted_at']
        indexes = [
            models.Index(fields=['user', 'document']),
        ]

    def __str__(self):
        return f'{self.user_id} accepted {self.document_id}@{self.document_version}'


class FeatureVisibilityRule(models.Model):
    """Control feature visibility by role, group, or globally."""

    SCOPE_CHOICES = [
        ('global', '全局'),
        ('role', '用户角色'),
        ('group', '用户组'),
    ]

    feature_key = models.CharField(max_length=200, verbose_name='功能标识')
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='global', verbose_name='作用范围')
    role = models.CharField(max_length=50, blank=True, verbose_name='角色')
    group = models.ForeignKey(
        'auth.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='feature_visibility_rules',
        verbose_name='用户组',
    )
    is_visible = models.BooleanField(default=True, verbose_name='可见')
    is_enabled = models.BooleanField(default=True, verbose_name='启用')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feature_visibility_updates',
        verbose_name='最后修改人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'admin_feature_visibility_rules'
        verbose_name = '功能可见性规则'
        verbose_name_plural = '功能可见性规则'
        ordering = ['feature_key', 'scope']

    def __str__(self):
        return f'{self.feature_key} ({self.scope})'


class GatewayRouteRule(models.Model):
    """API gateway route and rate-limit configuration."""

    name = models.CharField(max_length=100, verbose_name='规则名称')
    path_pattern = models.CharField(max_length=500, verbose_name='路径匹配')
    target_service = models.CharField(max_length=200, verbose_name='目标服务')
    methods = models.JSONField(default=list, verbose_name='HTTP 方法')
    rate_limit_per_minute = models.PositiveIntegerField(default=60, verbose_name='每分钟限流')
    is_enabled = models.BooleanField(default=True, verbose_name='启用')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    config = models.JSONField(default=dict, blank=True, verbose_name='扩展配置')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gateway_route_updates',
        verbose_name='最后修改人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'admin_gateway_route_rules'
        verbose_name = '网关路由规则'
        verbose_name_plural = '网关路由规则'
        ordering = ['-priority', 'name']

    def __str__(self):
        return self.name


class PaymentProviderConfig(models.Model):
    """Platform payment provider configuration."""

    PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
        ('alipay', '支付宝'),
        ('wechat', '微信支付'),
        ('paypal', 'PayPal'),
    ]

    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES, verbose_name='支付渠道')
    display_name = models.CharField(max_length=100, verbose_name='显示名称')
    is_enabled = models.BooleanField(default=False, verbose_name='启用')
    config = models.JSONField(default=dict, blank=True, verbose_name='渠道配置')
    fee_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0, verbose_name='费率')
    refund_rules = models.JSONField(default=dict, blank=True, verbose_name='退款规则')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_config_updates',
        verbose_name='最后修改人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'admin_payment_provider_configs'
        verbose_name = '支付渠道配置'
        verbose_name_plural = '支付渠道配置'
        ordering = ['sort_order', 'provider']
        unique_together = [('provider',)]

    def __str__(self):
        return self.display_name or self.get_provider_display()


class EmailSendLog(models.Model):
    """Email delivery audit log."""

    STATUS_CHOICES = [
        ('queued', '排队中'),
        ('sent', '已发送'),
        ('failed', '失败'),
    ]

    to_email = models.CharField(max_length=254, verbose_name='收件人')
    subject = models.CharField(max_length=500, verbose_name='主题')
    template_key = models.CharField(max_length=100, blank=True, verbose_name='模板标识')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued', verbose_name='状态')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails',
        verbose_name='发送人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='发送时间')

    class Meta:
        db_table = 'admin_email_send_logs'
        verbose_name = '邮件发送记录'
        verbose_name_plural = '邮件发送记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.to_email} - {self.subject}'


class BackupRecord(models.Model):
    """System backup metadata."""

    BACKUP_TYPE_CHOICES = [
        ('full', '完整备份'),
        ('database', '数据库'),
        ('files', '文件'),
    ]
    STATUS_CHOICES = [
        ('completed', '完成'),
        ('failed', '失败'),
        ('in_progress', '进行中'),
    ]

    name = models.CharField(max_length=255, verbose_name='文件名')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPE_CHOICES, verbose_name='备份类型')
    size = models.BigIntegerField(default=0, verbose_name='大小(字节)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed', verbose_name='状态')
    include_media = models.BooleanField(default=True, verbose_name='包含媒体文件')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_backups',
        verbose_name='创建人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'admin_backup_records'
        verbose_name = '备份记录'
        verbose_name_plural = '备份记录'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
