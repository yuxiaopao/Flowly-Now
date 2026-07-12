"""
Billing and subscription models for multi-tenant SaaS platform.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class PlanType(models.TextChoices):
    """Subscription plan types."""
    FREE = 'free', '免费版'
    STARTER = 'starter', '入门版'
    PROFESSIONAL = 'professional', '专业版'
    ENTERPRISE = 'enterprise', '企业版'


# Fallback limits when no PriceTier row exists in the database.
DEFAULT_PLAN_LIMITS = {
    PlanType.FREE: {
        'max_workflows': 5,
        'max_executions_per_month': 100,
        'max_team_members': 1,
        'max_storage_gb': 1,
        'max_api_calls_per_month': 1000,
        'max_agents': 1,
    },
    PlanType.STARTER: {
        'max_workflows': 20,
        'max_executions_per_month': 1000,
        'max_team_members': 5,
        'max_storage_gb': 10,
        'max_api_calls_per_month': 10000,
        'max_agents': 5,
    },
    PlanType.PROFESSIONAL: {
        'max_workflows': 100,
        'max_executions_per_month': 10000,
        'max_team_members': 20,
        'max_storage_gb': 50,
        'max_api_calls_per_month': 100000,
        'max_agents': 20,
    },
    PlanType.ENTERPRISE: {
        'max_workflows': 999999,
        'max_executions_per_month': 999999,
        'max_team_members': 999999,
        'max_storage_gb': 999999,
        'max_api_calls_per_month': 999999,
        'max_agents': 999999,
    },
}


class BillingCycle(models.TextChoices):
    """Billing cycle options."""
    MONTHLY = 'monthly', '月付'
    YEARLY = 'yearly', '年付'


class SubscriptionStatus(models.TextChoices):
    """Subscription status."""
    ACTIVE = 'active', '激活'
    PAST_DUE = 'past_due', '逾期'
    CANCELED = 'canceled', '已取消'
    TRIALING = 'trialing', '试用中'
    INACTIVE = 'inactive', '未激活'


class PaymentStatus(models.TextChoices):
    """Payment status."""
    PENDING = 'pending', '待支付'
    PAID = 'paid', '已支付'
    FAILED = 'failed', '失败'
    REFUNDED = 'refunded', '已退款'


class PriceTier(models.Model):
    """Price tiers for different plans."""

    plan_type = models.CharField(
        max_length=30,
        choices=PlanType.choices,
        verbose_name='套餐类型'
    )

    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
        verbose_name='计费周期'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='价格'
    )
    currency = models.CharField(max_length=10, default='CNY', verbose_name='货币')

    # Features
    max_workflows = models.IntegerField(default=10, verbose_name='最大工作流数')
    max_executions_per_month = models.IntegerField(default=1000, verbose_name='每月最大执行次数')
    max_team_members = models.IntegerField(default=1, verbose_name='最大团队成员')
    max_storage_gb = models.IntegerField(default=5, verbose_name='最大存储(GB)')
    max_api_calls_per_month = models.IntegerField(default=10000, verbose_name='每月最大API调用')
    max_agents = models.IntegerField(default=5, verbose_name='最大Agent数量')

    # Feature flags
    enable_advanced_nodes = models.BooleanField(default=False, verbose_name='启用高级节点')
    enable_version_history = models.BooleanField(default=False, verbose_name='启用版本历史')
    enable_custom_domain = models.BooleanField(default=False, verbose_name='启用自定义域名')
    enable_sso = models.BooleanField(default=False, verbose_name='启用SSO')
    enable_priority_support = models.BooleanField(default=False, verbose_name='启用优先支持')
    enable_audit_logs = models.BooleanField(default=False, verbose_name='启用审计日志')
    enable_api_access = models.BooleanField(default=True, verbose_name='启用API访问')
    enable_webhooks = models.BooleanField(default=False, verbose_name='启用Webhook')

    # Limits
    max_execution_timeout_seconds = models.IntegerField(default=60, verbose_name='最大执行超时(秒)')
    max_nodes_per_workflow = models.IntegerField(default=50, verbose_name='每工作流最大节点数')
    max_file_size_mb = models.IntegerField(default=10, verbose_name='最大文件大小(MB)')

    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'price_tiers'
        verbose_name = '价格套餐'
        verbose_name_plural = '价格套餐'
        unique_together = ['plan_type', 'billing_cycle']

    def __str__(self):
        return f"{self.get_plan_type_display()} - {self.get_billing_cycle_display()}"


class Subscription(models.Model):
    """User subscription."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name='用户'
    )

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subscriptions',
        verbose_name='租户'
    )

    plan_type = models.CharField(
        max_length=30,
        choices=PlanType.choices,
        default=PlanType.FREE,
        verbose_name='套餐类型'
    )

    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
        verbose_name='计费周期'
    )

    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INACTIVE,
        verbose_name='状态'
    )

    # Trial
    is_trial = models.BooleanField(default=False, verbose_name='是否试用')
    trial_ends_at = models.DateTimeField(null=True, blank=True, verbose_name='试用结束时间')

    # Billing dates
    current_period_start = models.DateTimeField(null=True, blank=True, verbose_name='当前周期开始')
    current_period_end = models.DateTimeField(null=True, blank=True, verbose_name='当前周期结束')

    # External reference
    external_subscription_id = models.CharField(max_length=200, blank=True, verbose_name='外部订阅ID')
    external_customer_id = models.CharField(max_length=200, blank=True, verbose_name='外部客户ID')

    # Cancellation
    canceled_at = models.DateTimeField(null=True, blank=True, verbose_name='取消时间')
    cancel_at_period_end = models.BooleanField(default=False, verbose_name='周期结束时取消')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'subscriptions'
        verbose_name = '订阅'
        verbose_name_plural = '订阅'

    def __str__(self):
        return f"{self.user.username} - {self.get_plan_type_display()}"

    @property
    def is_active(self):
        return self.status == SubscriptionStatus.ACTIVE

    @property
    def is_trial_expired(self):
        if self.trial_ends_at:
            return timezone.now() > self.trial_ends_at
        return False

    def get_price_tier(self):
        """Get the price tier for this subscription."""
        try:
            return PriceTier.objects.get(
                plan_type=self.plan_type,
                billing_cycle=self.billing_cycle,
                is_active=True
            )
        except PriceTier.DoesNotExist:
            return None

    def get_usage_limits(self):
        """Get usage limits based on subscription."""
        tier = self.get_price_tier()
        if tier:
            return {
                'max_workflows': tier.max_workflows,
                'max_executions_per_month': tier.max_executions_per_month,
                'max_team_members': tier.max_team_members,
                'max_storage_gb': tier.max_storage_gb,
                'max_api_calls_per_month': tier.max_api_calls_per_month,
                'max_agents': tier.max_agents,
                'enable_advanced_nodes': tier.enable_advanced_nodes,
                'enable_version_history': tier.enable_version_history,
                'enable_custom_domain': tier.enable_custom_domain,
                'enable_sso': tier.enable_sso,
                'enable_priority_support': tier.enable_priority_support,
                'enable_audit_logs': tier.enable_audit_logs,
                'enable_api_access': tier.enable_api_access,
                'enable_webhooks': tier.enable_webhooks,
                'max_execution_timeout_seconds': tier.max_execution_timeout_seconds,
                'max_nodes_per_workflow': tier.max_nodes_per_workflow,
                'max_file_size_mb': tier.max_file_size_mb,
            }
        return DEFAULT_PLAN_LIMITS.get(self.plan_type, DEFAULT_PLAN_LIMITS[PlanType.FREE])


class UsageRecord(models.Model):
    """Usage records for billing."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='usage_records',
        verbose_name='用户'
    )

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='usage_records',
        verbose_name='租户'
    )

    # Usage period
    period_start = models.DateTimeField(verbose_name='周期开始')
    period_end = models.DateTimeField(verbose_name='周期结束')

    # Usage metrics
    workflow_count = models.IntegerField(default=0, verbose_name='工作流数')
    execution_count = models.IntegerField(default=0, verbose_name='执行次数')
    api_call_count = models.IntegerField(default=0, verbose_name='API调用次数')
    storage_used_mb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='存储使用(MB)'
    )
    agent_count = models.IntegerField(default=0, verbose_name='Agent数量')

    # Token usage (for AI calls)
    input_tokens = models.BigIntegerField(default=0, verbose_name='输入Token')
    output_tokens = models.BigIntegerField(default=0, verbose_name='输出Token')

    # Computed cost
    compute_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name='计算成本'
    )
    api_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name='API成本'
    )
    storage_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name='存储成本'
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='总成本'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'usage_records'
        verbose_name = '使用记录'
        verbose_name_plural = '使用记录'
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['user', '-period_start']),
            models.Index(fields=['tenant', '-period_start']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.period_start.strftime('%Y-%m')}"


class Invoice(models.Model):
    """Billing invoices."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name='用户'
    )

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invoices',
        verbose_name='租户'
    )

    invoice_number = models.CharField(max_length=50, unique=True, verbose_name='发票号')
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name='状态'
    )

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='小计')
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='税费')
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='折扣')
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='总计')
    currency = models.CharField(max_length=10, default='CNY', verbose_name='货币')

    # Period
    period_start = models.DateTimeField(verbose_name='计费周期开始')
    period_end = models.DateTimeField(verbose_name='计费周期结束')

    # Payment
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('alipay', '支付宝'),
            ('wechat', '微信支付'),
            ('bank_transfer', '银行转账'),
            ('credit_card', '信用卡'),
        ],
        blank=True,
        verbose_name='支付方式'
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='支付时间')
    due_date = models.DateTimeField(verbose_name='到期日')

    # External reference
    external_invoice_id = models.CharField(max_length=200, blank=True, verbose_name='外部发票ID')

    # Items
    line_items = models.JSONField(default=list, verbose_name='明细')

    # Notes
    notes = models.TextField(blank=True, verbose_name='备注')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'invoices'
        verbose_name = '发票'
        verbose_name_plural = '发票'
        ordering = ['-created_at']

    def __str__(self):
        return self.invoice_number

    @classmethod
    def generate_invoice_number(cls):
        """Generate a unique invoice number."""
        from datetime import datetime
        prefix = datetime.now().strftime('%Y%m')
        last = cls.objects.filter(
            invoice_number__startswith=f'INV-{prefix}'
        ).order_by('-invoice_number').first()

        if last:
            num = int(last.invoice_number.split('-')[-1]) + 1
        else:
            num = 1

        return f"INV-{prefix}-{num:06d}"


class Payment(models.Model):
    """Payment records."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='用户'
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='发票'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='金额')
    currency = models.CharField(max_length=10, default='CNY', verbose_name='货币')

    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('alipay', '支付宝'),
            ('wechat', '微信支付'),
            ('bank_transfer', '银行转账'),
            ('credit_card', '信用卡'),
        ],
        verbose_name='支付方式'
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '处理中'),
            ('success', '成功'),
            ('failed', '失败'),
            ('refunded', '已退款'),
        ],
        default='pending',
        verbose_name='状态'
    )

    # External reference
    external_payment_id = models.CharField(max_length=200, blank=True, verbose_name='外部支付ID')
    transaction_id = models.CharField(max_length=200, blank=True, verbose_name='交易号')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'payments'
        verbose_name = '支付记录'
        verbose_name_plural = '支付记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.amount}"


class Coupon(models.Model):
    """Discount coupons."""

    code = models.CharField(max_length=50, unique=True, verbose_name='优惠码')
    name = models.CharField(max_length=200, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Discount type
    discount_type = models.CharField(
        max_length=20,
        choices=[
            ('percentage', '百分比'),
            ('fixed', '固定金额'),
        ],
        verbose_name='折扣类型'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='折扣值')

    # Usage limits
    max_uses = models.IntegerField(null=True, blank=True, verbose_name='最大使用次数')
    used_count = models.IntegerField(default=0, verbose_name='已使用次数')
    per_user_limit = models.IntegerField(default=1, verbose_name='每人限用次数')

    # Validity
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    valid_from = models.DateTimeField(verbose_name='生效时间')
    valid_until = models.DateTimeField(verbose_name='过期时间')

    # Applies to
    applicable_plans = models.JSONField(default=list, verbose_name='适用套餐')
    applicable_users = models.JSONField(default=list, verbose_name='指定用户')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'coupons'
        verbose_name = '优惠券'
        verbose_name_plural = '优惠券'

    def __str__(self):
        return self.code

    def is_valid(self, user=None):
        """Check if coupon is still valid."""
        now = timezone.now()

        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False

        if user and self.per_user_limit:
            user_usage = CouponUsage.objects.filter(
                coupon=self,
                user=user
            ).count()
            if user_usage >= self.per_user_limit:
                return False

        return True


class CouponUsage(models.Model):
    """Track coupon usage."""

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name='优惠券'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        verbose_name='用户'
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        verbose_name='发票'
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='折扣金额'
    )

    used_at = models.DateTimeField(auto_now_add=True, verbose_name='使用时间')

    class Meta:
        db_table = 'coupon_usages'
        verbose_name = '优惠券使用'
        verbose_name_plural = '优惠券使用'
        unique_together = ['coupon', 'user', 'invoice']

    def __str__(self):
        return f"{self.coupon.code} - {self.user.username}"
