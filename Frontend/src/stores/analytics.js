import { defineStore } from 'pinia'
import { analyticsApi } from '@/api/analytics'

export const useAnalyticsStore = defineStore('analytics', {
  state: () => ({
    overview: null,
    topWorkflows: [],
    recentExecutions: [],
    apiUsage: null,
    executionTrend: [],
    dashboardData: null,
    timeSeriesData: [],
    isLoading: false,
    error: null,
    dateRange: {
      start: null,
      end: null
    }
  }),

  getters: {
    totalExecutions: (state) => {
      if (!state.overview) return 0
      return state.overview.total_executions || 0
    },
    successRate: (state) => {
      if (!state.overview) return 0
      return state.overview.success_rate || 0
    },
    avgExecutionTime: (state) => {
      if (!state.overview) return 0
      return state.overview.avg_execution_time || 0
    }
  },

  actions: {
    async fetchOverview(params = {}) {
      this.isLoading = true
      this.error = null
      try {
        const res = await analyticsApi.getOverview(params)
        this.overview = res
        return res
      } catch (error) {
        this.error = error.message
      } finally {
        this.isLoading = false
      }
    },

    async fetchTopWorkflows(params = {}) {
      try {
        const res = await analyticsApi.getTopWorkflows(params)
        this.topWorkflows = res.results || res
        return res
      } catch (error) {
        this.error = error.message
      }
    },

    async fetchRecentExecutions(params = {}) {
      try {
        const res = await analyticsApi.getRecentExecutions(params)
        this.recentExecutions = res.results || res
        return res
      } catch (error) {
        this.error = error.message
      }
    },

    async fetchApiUsage(params = {}) {
      try {
        const res = await analyticsApi.getApiUsage(params)
        this.apiUsage = res
        return res
      } catch (error) {
        this.error = error.message
      }
    },

    async fetchExecutionTrend(params = {}) {
      try {
        const res = await analyticsApi.getExecutionTrend(params)
        this.executionTrend = res
        return res
      } catch (error) {
        this.error = error.message
      }
    },

    async fetchDashboardData(params = {}) {
      this.isLoading = true
      try {
        const res = await analyticsApi.getDashboardData(params)
        this.dashboardData = res
        return res
      } catch (error) {
        this.error = error.message
      } finally {
        this.isLoading = false
      }
    },

    async fetchTimeSeriesData(params = {}) {
      try {
        const res = await analyticsApi.getTimeSeriesData(params)
        this.timeSeriesData = res
        return res
      } catch (error) {
        this.error = error.message
      }
    },

    async fetchAll(params = {}) {
      this.isLoading = true
      await Promise.all([
        this.fetchOverview(params),
        this.fetchTopWorkflows(params),
        this.fetchRecentExecutions(params),
        this.fetchExecutionTrend(params),
        this.fetchDashboardData(params)
      ])
      this.isLoading = false
    },

    setDateRange(start, end) {
      this.dateRange = { start, end }
    },

    clearData() {
      this.overview = null
      this.topWorkflows = []
      this.recentExecutions = []
      this.apiUsage = null
      this.executionTrend = []
      this.dashboardData = null
      this.timeSeriesData = []
    }
  }
})
