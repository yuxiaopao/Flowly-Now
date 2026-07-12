"""
Django Admin registration for flowly_admin app models.
"""

from django.contrib import admin

from .models import (
    BackupRecord,
    EmailSendLog,
    FeatureVisibilityRule,
    GatewayRouteRule,
    LegalDocument,
    PaymentProviderConfig,
    SystemSetting,
    UserTermsAcceptance,
)


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'updated_by', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('key',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('key',)


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'doc_type', 'version', 'is_active', 'effective_at', 'updated_at')
    list_filter = ('doc_type', 'is_active')
    search_fields = ('title', 'version')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserTermsAcceptance)
class UserTermsAcceptanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'document', 'document_version', 'accepted_at', 'ip_address')
    list_filter = ('accepted_at',)
    search_fields = ('user__username', 'document__title')
    readonly_fields = ('accepted_at',)


@admin.register(FeatureVisibilityRule)
class FeatureVisibilityRuleAdmin(admin.ModelAdmin):
    list_display = ('feature_key', 'scope', 'role', 'group', 'is_visible', 'is_enabled')
    list_filter = ('scope', 'is_visible', 'is_enabled')
    search_fields = ('feature_key',)


@admin.register(GatewayRouteRule)
class GatewayRouteRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'path_pattern', 'target_service', 'rate_limit_per_minute', 'is_enabled', 'priority')
    list_filter = ('is_enabled',)
    search_fields = ('name', 'path_pattern', 'target_service')


@admin.register(PaymentProviderConfig)
class PaymentProviderConfigAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'provider', 'is_enabled', 'fee_rate', 'sort_order')
    list_filter = ('provider', 'is_enabled')
    search_fields = ('display_name', 'provider')


@admin.register(EmailSendLog)
class EmailSendLogAdmin(admin.ModelAdmin):
    list_display = ('to_email', 'subject', 'status', 'sent_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('to_email', 'subject')
    readonly_fields = ('created_at', 'sent_at')


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = ('name', 'backup_type', 'size', 'status', 'created_by', 'created_at')
    list_filter = ('backup_type', 'status')
    search_fields = ('name',)
    readonly_fields = ('created_at',)
