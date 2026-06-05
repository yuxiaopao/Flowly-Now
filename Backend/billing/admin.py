"""
Admin configuration for billing app.
"""

from django.contrib import admin
from .models import (
    PriceTier, Subscription, Payment, Invoice,
    UsageRecord, Coupon, CouponUsage
)


@admin.register(PriceTier)
class PriceTierAdmin(admin.ModelAdmin):
    list_display = ('plan_type', 'billing_cycle', 'price', 'max_workflows', 'max_executions_per_month')
    list_filter = ('plan_type', 'billing_cycle', 'is_active')
    search_fields = ('plan_type',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'plan_type', 'status', 'billing_cycle', 'current_period_end')
    list_filter = ('status', 'plan_type', 'billing_cycle')
    search_fields = ('user__username', 'tenant__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'tenant', 'plan_type', 'status', 'billing_cycle')
        }),
        ('订阅信息', {
            'fields': ('external_subscription_id', 'external_customer_id')
        }),
        ('周期', {
            'fields': ('current_period_start', 'current_period_end', 'trial_ends_at')
        }),
        ('Stripe信息', {
            'fields': ('is_trial',),
            'classes': ('collapse',)
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'invoice', 'amount', 'currency', 'status', 'completed_at')
    list_filter = ('status', 'currency', 'payment_method')
    search_fields = ('user__username',)
    readonly_fields = ('created_at',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'total', 'currency', 'status', 'due_date', 'paid_at')
    list_filter = ('status', 'currency')
    search_fields = ('invoice_number', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'period_start', 'period_end', 'workflow_count', 'api_call_count', 'storage_used_mb')
    list_filter = ('period_start',)
    search_fields = ('user__username',)
    readonly_fields = ('created_at',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'max_uses', 'valid_from', 'valid_until', 'is_active')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'invoice', 'discount_amount', 'used_at')
    search_fields = ('coupon__code', 'user__username')
    readonly_fields = ('used_at',)
