import { request } from './index'

export const analyticsApi = {
  // Overview
  getOverview(params = {}) {
    return request.get('/monitoring/analytics/overview/', params)
  },

  // Workflow Analytics
  getTopWorkflows(params = {}) {
    return request.get('/monitoring/analytics/top_workflows/', params)
  },

  getRecentExecutions(params = {}) {
    return request.get('/monitoring/analytics/recent_executions/', params)
  },

  // API Usage
  getApiUsage(params = {}) {
    return request.get('/monitoring/analytics/api_usage/', params)
  },

  // Execution Trends
  getExecutionTrend(params = {}) {
    return request.get('/monitoring/analytics/execution_trend/', params)
  },

  // Custom Metrics
  getCustomMetrics(params = {}) {
    return request.get('/monitoring/metrics/', params)
  },

  aggregateMetrics(params = {}) {
    return request.get('/monitoring/metrics/aggregate/', params)
  },

  // Time-series data
  getTimeSeriesData(params = {}) {
    return request.get('/monitoring/analytics/timeseries/', params)
  },

  // Dashboard data
  getDashboardData(params = {}) {
    return request.get('/monitoring/metrics/dashboard/', params)
  }
}

export default analyticsApi
