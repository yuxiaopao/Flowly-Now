import { request } from './index'

/**
 * @typedef {Object} BillingAPI
 * @property {function(Object=): Promise<{count:number, results: import('@/types/billing').PriceTier[]}>} getPriceTiers
 * @property {function(): Promise<import('@/types/billing').PriceTier[]>} getPlans
 * @property {function(): Promise<import('@/types/billing').Subscription>} getMySubscription
 * @property {function({plan_type: string, billing_cycle?: string}): Promise<import('@/types/billing').Subscription>} subscribe
 * @property {function(): Promise<import('@/types/billing').Subscription>} cancelSubscription
 * @property {function(): Promise<import('@/types/billing').Subscription>} reactivateSubscription
 * @property {function(): Promise<import('@/types/billing').UsageSummary>} getUsage
 * @property {function(Object=): Promise<{count:number, results: import('@/types/billing').UsageRecord[]}>} getUsageHistory
 * @property {function(Object=): Promise<import('@/types/billing').UsageRecord[]>} getUsageHistoryDetail
 * @property {function(Object=): Promise<{count:number, results: import('@/types/billing').Invoice[]}>} getInvoices
 * @property {function(string|number): Promise<import('@/types/billing').Invoice>} getInvoice
 * @property {function(string|number): Promise<Blob>} downloadInvoice
 * @property {function(Object=): Promise<{count:number, results: import('@/types/billing').Payment[]}>} getPayments
 * @property {function(string): Promise<import('@/types/billing').CouponValidationResult>} validateCoupon
 * @property {function(): Promise<{count:number, results: import('@/types/billing').Coupon[]}>} getMyCoupons
 */

/** @type {BillingAPI} */
export const billingApi = {
  // Price Tiers
  /** @param {Object=} params @returns {Promise<{count:number, results: import('@/types/billing').PriceTier[]}>} */
  getPriceTiers(params = {}) {
    return request.get('/billing/prices/', params)
  },

  /** @returns {Promise<import('@/types/billing').PriceTier[]>} */
  getPlans() {
    return request.get('/billing/prices/plans/')
  },

  // Subscription
  /** @returns {Promise<import('@/types/billing').Subscription>} */
  getMySubscription() {
    return request.get('/billing/subscriptions/my/')
  },

  /**
   * @param {{plan_type: string, billing_cycle?: string}} data
   * @returns {Promise<import('@/types/billing').Subscription>}
   */
  subscribe(data) {
    return request.post('/billing/subscriptions/subscribe/', data)
  },

  /** @returns {Promise<import('@/types/billing').Subscription>} */
  cancelSubscription() {
    return request.post('/billing/subscriptions/cancel/')
  },

  /** @returns {Promise<import('@/types/billing').Subscription>} */
  reactivateSubscription() {
    return request.post('/billing/subscriptions/reactivate/')
  },

  /** @returns {Promise<import('@/types/billing').UsageSummary>} */
  getUsage() {
    return request.get('/billing/subscriptions/usage/')
  },

  // Usage Records
  /** @param {Object=} params @returns {Promise<{count:number, results: import('@/types/billing').UsageRecord[]}>} */
  getUsageHistory(params = {}) {
    return request.get('/billing/usage/', params)
  },

  /** @param {Object=} params @returns {Promise<import('@/types/billing').UsageRecord[]>} */
  getUsageHistoryDetail(params = {}) {
    return request.get('/billing/usage/history/', params)
  },

  // Invoices
  /** @param {Object=} params @returns {Promise<{count:number, results: import('@/types/billing').Invoice[]}>} */
  getInvoices(params = {}) {
    return request.get('/billing/invoices/', params)
  },

  /** @param {string|number} id @returns {Promise<import('@/types/billing').Invoice>} */
  getInvoice(id) {
    return request.get(`/billing/invoices/${id}/`)
  },

  /** @param {string|number} id @returns {Promise<Blob>} */
  downloadInvoice(id) {
    return request.get(`/billing/invoices/${id}/download/`)
  },

  // Payments
  /** @param {Object=} params @returns {Promise<{count:number, results: import('@/types/billing').Payment[]}>} */
  getPayments(params = {}) {
    return request.get('/billing/payments/', params)
  },

  // Coupons
  /**
   * @param {string} code
   * @returns {Promise<import('@/types/billing').CouponValidationResult>}
   */
  validateCoupon(code) {
    return request.post('/billing/coupons/validate/', { code })
  },

  /** @returns {Promise<{count:number, results: import('@/types/billing').Coupon[]}>} */
  getMyCoupons() {
    return request.get('/billing/coupons/my/')
  }
}

export default billingApi
