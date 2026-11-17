import { defineStore } from 'pinia'
import { analyticsApi } from '@/api/analytics'
const emptyValue = key => ['overview', 'apiUsage', 'dashboardData'].includes(key) ? null : []
const moduleKeys = ['overview', 'topWorkflows', 'recentExecutions', 'apiUsage', 'executionTrend', 'dashboardData', 'timeSeriesData']
export const useAnalyticsStore = defineStore('analytics', {
  state: () => ({
    ...Object.fromEntries(moduleKeys.map(key => [key, emptyValue(key)])),
    isLoading: false, error: null, moduleErrors: {}, moduleLoading: {}, requestVersions: {}, pendingRequests: 0,
    dateRange: { start: null, end: null },
  }),
  getters: {
    totalExecutions: state => state.overview?.totalExecutions ?? null,
    successRate: state => state.overview?.successRate ?? null,
    avgExecutionTime: state => state.overview?.avgExecutionTime ?? state.overview?.avgLatency ?? null,
  },
  actions: {
    async loadResource(key, loader, params) {
      const version = (this.requestVersions[key] || 0) + 1
      this.requestVersions[key] = version
      this.pendingRequests++
      this.isLoading = true
      this.moduleLoading[key] = true
      delete this.moduleErrors[key]
      this.error = Object.values(this.moduleErrors).join('；') || null
      try {
        const result = await loader(params)
        if (this.requestVersions[key] !== version) return undefined
        this[key] = Array.isArray(emptyValue(key)) ? (result?.results || result || []) : result
        return result
      } catch (error) {
        if (this.requestVersions[key] !== version) return undefined
        this[key] = emptyValue(key)
        this.moduleErrors[key] = error.message || '数据加载失败'
        this.error = Object.values(this.moduleErrors).join('；')
        return undefined
      } finally {
        this.pendingRequests--
        this.isLoading = this.pendingRequests > 0
        if (this.requestVersions[key] === version) this.moduleLoading[key] = false
      }
    },
    fetchOverview(params = {}) { return this.loadResource('overview', analyticsApi.getOverview, params) },
    fetchTopWorkflows(params = {}) { return this.loadResource('topWorkflows', analyticsApi.getTopWorkflows, params) },
    fetchRecentExecutions(params = {}) { return this.loadResource('recentExecutions', analyticsApi.getRecentExecutions, params) },
    fetchApiUsage(params = {}) { return this.loadResource('apiUsage', analyticsApi.getApiUsage, params) },
    fetchExecutionTrend(params = {}) { return this.loadResource('executionTrend', analyticsApi.getExecutionTrend, params) },
    fetchDashboardData(params = {}) { return this.loadResource('dashboardData', analyticsApi.getDashboardData, params) },
    fetchTimeSeriesData(params = {}) { return this.loadResource('timeSeriesData', analyticsApi.getTimeSeriesData, params) },
    async fetchAll(params = {}) {
      await Promise.all([this.fetchOverview(params), this.fetchTopWorkflows(params), this.fetchRecentExecutions(params), this.fetchExecutionTrend(params), this.fetchApiUsage(params)])
    },
    setDateRange(start, end) { this.dateRange = { start, end } },
    clearData() {
      for (const key of moduleKeys) { this.requestVersions[key] = (this.requestVersions[key] || 0) + 1; this[key] = emptyValue(key) }
      this.moduleErrors = {}
      this.moduleLoading = {}
      this.error = null
    },
  },
})
