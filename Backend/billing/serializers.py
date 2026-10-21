"""
Billing API serializers.
"""

from rest_framework import serializers
from .models import (
    PriceTier, Subscription, UsageRecord, Invoice,
    Payment, Coupon, CouponUsage, PlanType, BillingCycle
)


class PriceTierSerializer(serializers.ModelSerializer):
    """Serializer for price tiers."""

    plan_type_display = serializers.CharField(
        source='get_plan_type_display',
        read_only=True
    )
    billing_cycle_display = serializers.CharField(
        source='get_billing_cycle_display',
        read_only=True
    )

    class Meta:
        model = PriceTier
        fields = [
            'id', 'plan_type', 'plan_type_display', 'billing_cycle',
            'billing_cycle_display', 'price', 'currency',
            'max_workflows', 'max_executions_per_month', 'max_team_members',
            'max_storage_gb', 'max_api_calls_per_month', 'max_agents',
            'enable_advanced_nodes', 'enable_version_history',
            'enable_custom_domain', 'enable_sso', 'enable_priority_support',
            'enable_audit_logs', 'enable_api_access', 'enable_webhooks',
            'max_execution_timeout_seconds', 'max_nodes_per_workflow',
            'max_file_size_mb', 'is_active'
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscriptions."""

    plan_type_display = serializers.CharField(
        source='get_plan_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    usage_limits = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            'id', 'plan_type', 'plan_type_display', 'billing_cycle',
            'status', 'status_display', 'is_trial', 'trial_ends_at',
            'current_period_start', 'current_period_end',
            'cancel_at_period_end', 'usage_limits', 'created_at'
        ]

    def get_usage_limits(self, obj):
        return obj.get_usage_limits() or {}


class SubscriptionCreateSerializer(serializers.Serializer):
    """Serializer for creating subscriptions."""

    plan_type = serializers.ChoiceField(choices=PlanType.choices, default=PlanType.FREE)
    billing_cycle = serializers.ChoiceField(choices=BillingCycle.choices, default=BillingCycle.MONTHLY)


class UsageRecordSerializer(serializers.ModelSerializer):
    """Serializer for usage records."""

    class Meta:
        model = UsageRecord
        fields = [
            'id', 'period_start', 'period_end', 'workflow_count',
            'execution_count', 'api_call_count', 'storage_used_mb',
            'agent_count', 'input_tokens', 'output_tokens',
            'compute_cost', 'api_cost', 'storage_cost', 'total_cost'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for invoices."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'status', 'status_display',
            'subtotal', 'tax', 'discount', 'total', 'currency',
            'period_start', 'period_end', 'payment_method',
            'payment_method_display', 'paid_at', 'due_date',
            'line_items', 'notes', 'created_at'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )

    class Meta:
        model = Payment
        fields = [
            'id', 'invoice', 'amount', 'currency', 'payment_method',
            'payment_method_display', 'status', 'status_display',
            'external_payment_id', 'transaction_id', 'created_at', 'completed_at'
        ]


class CouponSerializer(serializers.ModelSerializer):
    """Serializer for coupons."""

    discount_type_display = serializers.CharField(
        source='get_discount_type_display',
        read_only=True
    )
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'name', 'description', 'discount_type',
            'discount_type_display', 'discount_value', 'max_uses',
            'used_count', 'is_active', 'valid_from', 'valid_until',
            'applicable_plans', 'is_valid'
        ]

    def get_is_valid(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        return obj.is_valid(user)


class CouponValidateSerializer(serializers.Serializer):
    """Serializer for validating coupons."""

    code = serializers.CharField(max_length=50)


class UsageSummarySerializer(serializers.Serializer):
    """Serializer for usage summary."""

    current_usage = UsageRecordSerializer()
    limits = serializers.DictField()
    usage_percentages = serializers.DictField()
    remaining = serializers.DictField()
