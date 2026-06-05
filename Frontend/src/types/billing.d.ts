/**
 * Billing API Type Definitions
 * Price tiers, subscriptions, usage records, invoices, payments, and coupons.
 */

/** Price tier / plan */
export interface PriceTier {
  id: string
  plan_type: PriceTierPlanType
  plan_type_display?: string
  billing_cycle: BillingCycle
  billing_cycle_display?: string
  price: number
  currency: string
  max_workflows: number
  max_executions: number
  max_storage_mb: number
  max_agents: number
  max_tokens: number
  max_api_calls: number
  max_concurrent_executions: number
  allow_collaboration: boolean
  allow_custom_domains: boolean
  allow_api_access: boolean
  allow_priority_support: boolean
  trial_days: number
  is_active: boolean
  features: string[]
  created_at: string
  updated_at: string
}

export type PriceTierPlanType = 'free' | 'starter' | 'pro' | 'enterprise'
export type BillingCycle = 'monthly' | 'yearly'

/** User subscription */
export interface Subscription {
  id: string
  plan_type: PriceTierPlanType
  status: SubscriptionStatus
  is_trial: boolean
  trial_ends_at: string | null
  billing_cycle: BillingCycle | null
  periods: number
  cancel_at_period_end: boolean
  current_period_start: string
  current_period_end: string
  usage_limits: UsageLimits
  created_at: string
  updated_at: string
}

export type SubscriptionStatus =
  | 'active'
  | 'trialing'
  | 'past_due'
  | 'canceled'
  | 'unpaid'
  | 'incomplete'

/** Usage limits for a subscription */
export interface UsageLimits {
  max_workflows: number
  max_executions: number
  max_storage_mb: number
  max_agents: number
  max_tokens: number
  max_api_calls: number
  max_concurrent_executions: number
}

/** Usage record for a billing period */
export interface UsageRecord {
  id: string
  period_start: string
  period_end: string
  workflow_count: number
  execution_count: number
  api_call_count: number
  storage_used_mb: number
  agent_count: number
  tokens_used: number
  total_cost: number
}

/** Invoice summary */
export interface Invoice {
  id: string
  invoice_number: string
  status: InvoiceStatus
  status_display?: string
  subtotal: number
  tax: number
  total: number
  currency: string
  period_start: string
  period_end: string
  paid_at: string | null
  payment_method: PaymentMethod | null
  payment_method_display?: string
  download_url: string | null
  created_at: string
}

export type InvoiceStatus = 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'
export type PaymentMethod = 'card' | 'paypal' | 'bank_transfer' | 'alipay' | 'wechat'

/** Payment record */
export interface Payment {
  id: string
  invoice: string
  amount: number
  currency: string
  payment_method: PaymentMethod
  payment_method_display?: string
  status: PaymentStatus
  status_display?: string
  external_payment_id: string | null
  paid_at: string | null
  created_at: string
}

export type PaymentStatus = 'pending' | 'processing' | 'succeeded' | 'failed' | 'refunded'

/** Coupon / discount */
export interface Coupon {
  id: string
  code: string
  name: string
  discount_type: DiscountType
  discount_type_display?: string
  discount_value: number
  max_uses: number | null
  used_count: number
  valid_from: string
  valid_until: string
  applicable_plans: PriceTierPlanType[]
  is_valid: boolean
}

export type DiscountType = 'percentage' | 'fixed_amount' | 'free_trial'

/** Coupon validation result */
export interface CouponValidationResult {
  valid: boolean
  coupon?: Coupon
  error?: string
}

/** Current usage summary */
export interface UsageSummary {
  current_usage: {
    workflow_count: number
    execution_count: number
    api_call_count: number
    storage_used_mb: number
    agent_count: number
    tokens_used: number
  }
  limits: UsageLimits
  usage_percentages: Record<keyof UsageLimits, number>
  remaining: Record<keyof UsageLimits, number>
}
