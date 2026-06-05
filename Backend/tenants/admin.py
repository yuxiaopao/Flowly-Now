"""
Admin configuration for tenants app.
"""

from django.contrib import admin
from .models import Tenant, TenantMembership, TenantInvitation, TenantUsage


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'owner', 'status', 'plan', 'max_users', 'created_at')
    list_filter = ('status', 'plan')
    search_fields = ('name', 'slug', 'owner__username', 'billing_email')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'description', 'owner')
        }),
        ('状态', {
            'fields': ('status', 'plan')
        }),
        ('限制', {
            'fields': ('max_users', 'max_workflows', 'max_executions_per_month')
        }),
        ('设置', {
            'fields': ('settings', 'custom_domain')
        }),
        ('账单', {
            'fields': ('billing_email', 'subscription_id', 'subscription_end')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_tenants', 'suspend_tenants']

    @admin.action(description='激活选中的租户')
    def activate_tenants(self, request, queryset):
        queryset.update(status='active')

    @admin.action(description='暂停选中的租户')
    def suspend_tenants(self, request, queryset):
        queryset.update(status='suspended')


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__username', 'tenant__name')
    readonly_fields = ('joined_at',)


@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'tenant', 'role', 'invited_by', 'status', 'expires_at')
    list_filter = ('status', 'role')
    search_fields = ('email', 'tenant__name', 'invited_by__username')
    readonly_fields = ('token', 'created_at', 'accepted_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('tenant', 'email', 'role')
        }),
        ('邀请信息', {
            'fields': ('invited_by', 'token')
        }),
        ('状态', {
            'fields': ('status', 'expires_at', 'accepted_at')
        }),
        ('时间', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['resend_invitations', 'expire_invitations']

    @admin.action(description='使选中的邀请过期')
    def expire_invitations(self, request, queryset):
        queryset.update(status='expired')


@admin.register(TenantUsage)
class TenantUsageAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'current_month_executions', 'current_month_users', 
                   'total_executions', 'total_tokens_used', 'last_reset_at')
    search_fields = ('tenant__name',)
    readonly_fields = ('tenant', 'last_reset_at')

    def has_add_permission(self, request):
        return False
