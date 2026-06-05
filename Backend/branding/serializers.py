"""
White-label and branding serializers.
"""

from rest_framework import serializers
from .models import BrandingConfig, EmailTemplate, CustomDomain, ThemePreset


class BrandingConfigSerializer(serializers.ModelSerializer):
    """Serializer for branding configuration."""

    class Meta:
        model = BrandingConfig
        fields = [
            'id', 'company_name', 'company_logo', 'company_favicon', 'company_website',
            'primary_color', 'primary_color_dark', 'primary_color_light',
            'accent_color', 'success_color', 'warning_color', 'danger_color',
            'bg_color', 'bg_color_secondary', 'bg_color_dark',
            'text_color_primary', 'text_color_secondary', 'text_color_light',
            'border_color', 'border_color_light',
            'login_background', 'login_show_logo', 'login_message',
            'email_logo', 'email_header_color', 'email_footer_text',
            'footer_text', 'footer_links',
            'custom_css', 'custom_js',
            'hide_powered_by', 'custom_domain',
            'is_active', 'created_at', 'updated_at'
        ]


class BrandingPreviewSerializer(serializers.ModelSerializer):
    """Serializer for branding preview (limited fields)."""

    class Meta:
        model = BrandingConfig
        fields = [
            'company_name', 'company_logo', 'primary_color',
            'accent_color', 'bg_color', 'text_color_primary'
        ]


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Serializer for email templates."""

    template_type_display = serializers.CharField(
        source='get_template_type_display',
        read_only=True
    )

    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'template_type', 'template_type_display', 'name',
            'subject', 'header_html', 'body_html', 'footer_html',
            'available_variables', 'is_active', 'use_default',
            'created_at', 'updated_at'
        ]


class EmailTemplateCreateSerializer(serializers.Serializer):
    """Serializer for creating email templates."""

    template_type = serializers.ChoiceField(choices=EmailTemplate.TEMPLATE_TYPES)
    name = serializers.CharField(max_length=200)
    subject = serializers.CharField(max_length=255)
    header_html = serializers.CharField(required=False, allow_blank=True)
    body_html = serializers.CharField()
    footer_html = serializers.CharField(required=False, allow_blank=True)


class CustomDomainSerializer(serializers.ModelSerializer):
    """Serializer for custom domains."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = CustomDomain
        fields = [
            'id', 'domain', 'subdomain', 'cname_target', 'txt_record',
            'status', 'status_display',
            'ssl_enabled', 'ssl_cert_path', 'ssl_key_path',
            'verification_token', 'verified_at',
            'created_at', 'updated_at'
        ]


class CustomDomainCreateSerializer(serializers.Serializer):
    """Serializer for creating custom domains."""

    domain = serializers.CharField(max_length=255)
    subdomain = serializers.CharField(max_length=255, required=False, allow_blank=True)


class ThemePresetSerializer(serializers.ModelSerializer):
    """Serializer for theme presets."""

    class Meta:
        model = ThemePreset
        fields = [
            'id', 'name', 'slug', 'primary_color', 'accent_color',
            'bg_color', 'text_color', 'border_color',
            'preview_image', 'description', 'is_active', 'is_public'
        ]


class BrandingUpdateSerializer(serializers.Serializer):
    """Serializer for updating branding config."""

    company_name = serializers.CharField(max_length=200, required=False)
    company_logo = serializers.URLField(required=False, allow_blank=True)
    company_favicon = serializers.URLField(required=False, allow_blank=True)
    company_website = serializers.URLField(required=False, allow_blank=True)
    primary_color = serializers.CharField(max_length=20, required=False)
    accent_color = serializers.CharField(max_length=20, required=False)
    bg_color = serializers.CharField(max_length=20, required=False)
    text_color_primary = serializers.CharField(max_length=20, required=False)
    border_color = serializers.CharField(max_length=20, required=False)
    custom_css = serializers.CharField(required=False, allow_blank=True)
    custom_js = serializers.CharField(required=False, allow_blank=True)
    custom_domain = serializers.CharField(max_length=255, required=False, allow_blank=True)
