"""
White-label and custom branding models.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BrandingConfig(models.Model):
    """Custom branding configuration for tenants."""

    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='branding',
        verbose_name='租户'
    )

    # Company Info
    company_name = models.CharField(max_length=200, verbose_name='公司名称')
    company_logo = models.URLField(blank=True, verbose_name='公司Logo')
    company_favicon = models.URLField(blank=True, verbose_name='网站图标')
    company_website = models.URLField(blank=True, verbose_name='公司网站')

    # Primary Colors
    primary_color = models.CharField(max_length=20, default='#3b82f6', verbose_name='主题色')
    primary_color_dark = models.CharField(max_length=20, blank=True, verbose_name='主题色深')
    primary_color_light = models.CharField(max_length=20, blank=True, verbose_name='主题色浅')

    # Accent Colors
    accent_color = models.CharField(max_length=20, default='#8b5cf6', verbose_name='强调色')
    success_color = models.CharField(max_length=20, default='#10b981', verbose_name='成功色')
    warning_color = models.CharField(max_length=20, default='#f59e0b', verbose_name='警告色')
    danger_color = models.CharField(max_length=20, default='#ef4444', verbose_name='危险色')

    # Background Colors
    bg_color = models.CharField(max_length=20, default='#ffffff', verbose_name='背景色')
    bg_color_secondary = models.CharField(max_length=20, default='#f3f4f6', verbose_name='次要背景色')
    bg_color_dark = models.CharField(max_length=20, blank=True, verbose_name='深色背景色')

    # Text Colors
    text_color_primary = models.CharField(max_length=20, default='#1f2937', verbose_name='主文字色')
    text_color_secondary = models.CharField(max_length=20, default='#6b7280', verbose_name='次要文字色')
    text_color_light = models.CharField(max_length=20, blank=True, verbose_name='浅色文字色')

    # Border Colors
    border_color = models.CharField(max_length=20, default='#e5e7eb', verbose_name='边框色')
    border_color_light = models.CharField(max_length=20, blank=True, verbose_name='浅边框色')

    # Login Page
    login_background = models.URLField(blank=True, verbose_name='登录背景图')
    login_show_logo = models.BooleanField(default=True, verbose_name='登录页显示Logo')
    login_message = models.TextField(blank=True, verbose_name='登录页自定义消息')

    # Email Branding
    email_logo = models.URLField(blank=True, verbose_name='邮件Logo')
    email_header_color = models.CharField(max_length=20, blank=True, verbose_name='邮件标题颜色')
    email_footer_text = models.TextField(blank=True, verbose_name='邮件页脚文字')

    # Footer
    footer_text = models.TextField(blank=True, verbose_name='页脚文字')
    footer_links = models.JSONField(default=list, verbose_name='页脚链接')

    # Custom CSS/JS
    custom_css = models.TextField(blank=True, verbose_name='自定义CSS')
    custom_js = models.TextField(blank=True, verbose_name='自定义JS')

    # Features
    hide_powered_by = models.BooleanField(default=False, verbose_name='隐藏技术支持')
    custom_domain = models.CharField(max_length=255, blank=True, verbose_name='自定义域名')

    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'branding_configs'
        verbose_name = '品牌配置'
        verbose_name_plural = '品牌配置'

    def __str__(self):
        return f"{self.tenant.name} Branding"


class EmailTemplate(models.Model):
    """Custom email templates for tenants."""

    TEMPLATE_TYPES = [
        ('welcome', '欢迎邮件'),
        ('password_reset', '密码重置'),
        ('email_verification', '邮箱验证'),
        ('workflow_notification', '工作流通知'),
        ('execution_complete', '执行完成通知'),
        ('execution_failed', '执行失败通知'),
        ('subscription_alert', '订阅提醒'),
        ('usage_alert', '用量提醒'),
        ('team_invitation', '团队邀请'),
    ]

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='email_templates',
        verbose_name='租户'
    )

    template_type = models.CharField(
        max_length=50,
        choices=TEMPLATE_TYPES,
        verbose_name='模板类型'
    )

    name = models.CharField(max_length=200, verbose_name='模板名称')
    subject = models.CharField(max_length=255, verbose_name='邮件主题')

    # Content
    header_html = models.TextField(blank=True, verbose_name='自定义头部HTML')
    body_html = models.TextField(verbose_name='邮件正文')
    footer_html = models.TextField(blank=True, verbose_name='自定义页脚HTML')

    # Variables
    available_variables = models.JSONField(
        default=list,
        verbose_name='可用变量'
    )

    # Settings
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    use_default = models.BooleanField(
        default=False,
        verbose_name='使用默认模板'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'email_templates'
        verbose_name = '邮件模板'
        verbose_name_plural = '邮件模板'
        unique_together = ['tenant', 'template_type']

    def __str__(self):
        return f"{self.tenant.name} - {self.get_template_type_display()}"


class CustomDomain(models.Model):
    """Custom domain configuration."""

    STATUS_CHOICES = [
        ('pending', '待验证'),
        ('verified', '已验证'),
        ('active', '已激活'),
        ('failed', '验证失败'),
    ]

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='custom_domains',
        verbose_name='租户'
    )

    domain = models.CharField(max_length=255, unique=True, verbose_name='域名')
    subdomain = models.CharField(max_length=255, blank=True, verbose_name='子域名')

    # DNS Configuration
    cname_target = models.CharField(max_length=255, verbose_name='CNAME目标')
    txt_record = models.CharField(max_length=255, blank=True, verbose_name='TXT记录')

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态'
    )

    # SSL
    ssl_enabled = models.BooleanField(default=True, verbose_name='启用SSL')
    ssl_cert_path = models.CharField(max_length=500, blank=True, verbose_name='SSL证书路径')
    ssl_key_path = models.CharField(max_length=500, blank=True, verbose_name='SSL密钥路径')

    # Verification
    verification_token = models.CharField(max_length=100, blank=True, verbose_name='验证Token')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='验证时间')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'custom_domains'
        verbose_name = '自定义域名'
        verbose_name_plural = '自定义域名'

    def __str__(self):
        return self.domain


class ThemePreset(models.Model):
    """Pre-defined theme presets."""

    name = models.CharField(max_length=100, verbose_name='预设名称')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='slug')

    # Colors
    primary_color = models.CharField(max_length=20, verbose_name='主题色')
    accent_color = models.CharField(max_length=20, verbose_name='强调色')
    bg_color = models.CharField(max_length=20, verbose_name='背景色')
    text_color = models.CharField(max_length=20, verbose_name='文字色')
    border_color = models.CharField(max_length=20, verbose_name='边框色')

    # Preview
    preview_image = models.URLField(blank=True, verbose_name='预览图')
    description = models.TextField(blank=True, verbose_name='描述')

    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    is_public = models.BooleanField(default=True, verbose_name='是否公开')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'theme_presets'
        verbose_name = '主题预设'
        verbose_name_plural = '主题预设'

    def __str__(self):
        return self.name

    def apply_to(self, branding_config):
        """Apply this preset to a branding config."""
        branding_config.primary_color = self.primary_color
        branding_config.accent_color = self.accent_color
        branding_config.bg_color = self.bg_color
        branding_config.text_color_primary = self.text_color
        branding_config.border_color = self.border_color
        branding_config.save()
