import { defineStore } from 'pinia'
import { billingApi } from '@/api/billing'

export const useBillingStore = defineStore('billing', {
  state: () => ({
    subscription: null,
    plans: [],
    currentUsage: null,
    usageHistory: [],
    invoices: [],
    payments: [],
    coupons: [],
    isLoading: false,
    isSaving: false,
    error: null
  }),

  getters: {
    currentPlan: (state) => state.subscription?.plan_type || 'free',
    isPaid: (state) => {
      if (!state.subscription) return false
      return ['pro', 'enterprise'].includes(state.subscription.plan_type)
    },
    usagePercentages: (state) => state.currentUsage?.usage_percentages || {},
    usageLimits: (state) => state.currentUsage?.limits || {},
    remainingUsage: (state) => state.currentUsage?.remaining || {}
  },

  actions: {
    async fetchSubscription() {
      this.isLoading = true
      this.error = null
      try {
        const res = await billingApi.getMySubscription()
        this.subscription = res
      } catch (error) {
        this.error = error.message
      } finally {
        this.isLoading = false
      }
    },

    async fetchPlans() {
      try {
        const res = await billingApi.getPlans()
        this.plans = res
      } catch (error) {
        this.error = error.message
      }
    },

    async fetchUsage() {
      try {
        const res = await billingApi.getUsage()
        this.currentUsage = res
      } catch (error) {
        this.error = error.message
      }
    },

    async fetchUsageHistory(params = {}) {
      this.isLoading = true
      try {
        const res = await billingApi.getUsageHistoryDetail(params)
        this.usageHistory = res
      } catch (error) {
        this.error = error.message
      } finally {
        this.isLoading = false
      }
    },

    async fetchInvoices(params = {}) {
      try {
        const res = await billingApi.getInvoices(params)
        this.invoices = res
      } catch (error) {
        this.error = error.message
      }
    },

    async fetchPayments(params = {}) {
      try {
        const res = await billingApi.getPayments(params)
        this.payments = res
      } catch (error) {
        this.error = error.message
      }
    },

    async subscribe(data) {
      this.isSaving = true
      try {
        const res = await billingApi.subscribe(data)
        this.subscription = res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async cancelSubscription() {
      this.isSaving = true
      try {
        const res = await billingApi.cancelSubscription()
        if (this.subscription) {
          this.subscription.status = 'canceled'
        }
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async reactivateSubscription() {
      this.isSaving = true
      try {
        const res = await billingApi.reactivateSubscription()
        if (this.subscription) {
          this.subscription.status = 'active'
        }
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async validateCoupon(code) {
      try {
        return await billingApi.validateCoupon(code)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchAll() {
      await Promise.all([
        this.fetchSubscription(),
        this.fetchPlans(),
        this.fetchUsage(),
        this.fetchInvoices()
      ])
    }
  }
})
