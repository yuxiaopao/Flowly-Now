import { defineStore } from 'pinia'
import { billingApi } from '@/api/billing'

function normalizeListResponse(res) {
  if (Array.isArray(res)) return res
  if (res && Array.isArray(res.results)) return res.results
  return []
}

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
    currentPlan: (state) => state.subscription?.plan_type || state.subscription?.planType || 'free',
    isPaid: (state) => {
      if (!state.subscription) return false
      const planType = state.subscription.plan_type || state.subscription.planType
      return ['pro', 'enterprise', 'professional'].includes(planType)
    },
    usagePercentages: (state) => {
      const raw = state.currentUsage?.usagePercentages
        || state.currentUsage?.usage_percentages
        || {}
      return {
        workflows: raw.workflows ?? 0,
        executions: raw.executions ?? 0,
        storage: raw.storage ?? 0,
        agents: raw.agents ?? 0,
        api_calls: raw.apiCalls ?? raw.api_calls ?? 0,
      }
    },
    usageLimits: (state) => {
      const raw = state.currentUsage?.limits
        || state.subscription?.usageLimits
        || state.subscription?.usage_limits
        || {}
      return {
        max_workflows: raw.maxWorkflows ?? raw.max_workflows ?? 5,
        max_executions: raw.maxExecutionsPerMonth ?? raw.max_executions_per_month ?? 100,
        max_members: raw.maxTeamMembers ?? raw.max_team_members ?? 1,
        max_storage: raw.maxStorageGb ?? raw.max_storage_gb ?? 1,
        max_api_calls: raw.maxApiCallsPerMonth ?? raw.max_api_calls_per_month ?? 1000,
        max_agents: raw.maxAgents ?? raw.max_agents ?? 1,
      }
    },
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
        if (!this.subscription) {
          this.subscription = {
            planType: 'free',
            plan_type: 'free',
            status: 'active',
            billingCycle: 'monthly',
          }
        }
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
        this.usageHistory = normalizeListResponse(res)
      } catch (error) {
        this.error = error.message
        this.usageHistory = []
      } finally {
        this.isLoading = false
      }
    },

    async fetchInvoices(params = {}) {
      try {
        const res = await billingApi.getInvoices(params)
        this.invoices = normalizeListResponse(res)
      } catch (error) {
        this.error = error.message
        this.invoices = []
      }
    },

    async fetchPayments(params = {}) {
      try {
        const res = await billingApi.getPayments(params)
        this.payments = normalizeListResponse(res)
      } catch (error) {
        this.error = error.message
        this.payments = []
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
      await this.fetchSubscription()
      await Promise.all([
        this.fetchPlans(),
        this.fetchUsage(),
        this.fetchInvoices(),
      ])
    }
  }
})
