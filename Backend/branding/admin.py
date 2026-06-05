"""
Admin configuration for branding app.
"""

from django.contrib import admin
from .models import BrandingConfig, EmailTemplate, CustomDomain, ThemePreset


@admin.register(BrandingConfig)
class BrandingConfigAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'company_name', 'primary_color', 'is_active', 'created_at')
    list_filter = ('is_active', 'tenant')
    search_fields = ('company_name', 'tenant__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('tenant', 'company_name', 'company_logo', 'company_favicon', 'company_website')
        }),
        ('主题颜色', {
            'fields': ('primary_color', 'primary_color_dark', 'primary_color_light', 'accent_color', 'success_color', 'warning_color', 'danger_color')
        }),
        ('背景颜色', {
            'fields': ('bg_color', 'bg_color_secondary', 'bg_color_dark')
        }),
        ('文字颜色', {
            'fields': ('text_color_primary', 'text_color_secondary', 'text_color_light')
        }),
        ('边框颜色', {
            'fields': ('border_color', 'border_color_light')
        }),
        ('登录页', {
            'fields': ('login_background', 'login_show_logo', 'login_message')
        }),
        ('邮件品牌', {
            'fields': ('email_logo', 'email_header_color', 'email_footer_text')
        }),
        ('页脚', {
            'fields': ('footer_text', 'footer_links')
        }),
        ('自定义代码', {
            'fields': ('custom_css', 'custom_js'),
            'classes': ('collapse',)
        }),
        ('功能设置', {
            'fields': ('hide_powered_by', 'custom_domain', 'is_active')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'template_type', 'is_active', 'use_default', 'created_at')
    list_filter = ('template_type', 'is_active', 'use_default')
    search_fields = ('name', 'subject', 'tenant__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('tenant', 'template_type', 'name', 'subject')
        }),
        ('内容', {
            'fields': ('header_html', 'body_html', 'footer_html')
        }),
        ('设置', {
            'fields': ('available_variables', 'is_active', 'use_default')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CustomDomain)
class CustomDomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'status', 'ssl_enabled', 'created_at')
    list_filter = ('status', 'ssl_enabled')
    search_fields = ('domain', 'tenant__name')
    readonly_fields = ('verification_token', 'verified_at', 'created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('tenant', 'domain', 'subdomain')
        }),
        ('DNS配置', {
            'fields': ('cname_target', 'txt_record')
        }),
        ('状态', {
            'fields': ('status', 'verification_token', 'verified_at')
        }),
        ('SSL配置', {
            'fields': ('ssl_enabled', 'ssl_cert_path', 'ssl_key_path')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['verify_domains', 'activate_domains']

    @admin.action(description='验证选中的域名')
    def verify_domains(self, request, queryset):
        for domain in queryset.filter(status='pending'):
            # Add verification logic here
            domain.status = 'verified'
            domain.save()

    @admin.action(description='激活选中的域名')
    def activate_domains(self, request, queryset):
        queryset.update(status='active')


@admin.register(ThemePreset)
class ThemePresetAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'primary_color', 'is_active', 'is_public')
    list_filter = ('is_active', 'is_public')
    search_fields = ('name', 'slug')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'description')
        }),
        ('颜色配置', {
            'fields': ('primary_color', 'accent_color', 'bg_color', 'text_color', 'border_color')
        }),
        ('预览', {
            'fields': ('preview_image',)
        }),
        ('状态', {
            'fields': ('is_active', 'is_public')
        }),
        ('时间', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
