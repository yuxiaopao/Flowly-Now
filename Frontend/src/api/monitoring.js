import { request } from './index'

export const monitoringApi = {
  // Alerts
  getAlerts(params = {}) {
    return request.get('/monitoring/alerts/', params)
  },

  getAlert(id) {
    return request.get(`/monitoring/alerts/${id}/`)
  },

  acknowledgeAlert(id) {
    return request.post(`/monitoring/alerts/${id}/acknowledge/`)
  },

  resolveAlert(id, note = '') {
    return request.post(`/monitoring/alerts/${id}/resolve/`, { note })
  },

  muteAlert(id) {
    return request.post(`/monitoring/alerts/${id}/mute/`)
  },

  getAlertSummary() {
    return request.get('/monitoring/alerts/summary/')
  },

  // Alert Rules
  getAlertRules(params = {}) {
    return request.get('/monitoring/rules/', params)
  },

  getAlertRule(id) {
    return request.get(`/monitoring/rules/${id}/`)
  },

  createAlertRule(data) {
    return request.post('/monitoring/rules/', data)
  },

  updateAlertRule(id, data) {
    return request.patch(`/monitoring/rules/${id}/`, data)
  },

  deleteAlertRule(id) {
    return request.delete(`/monitoring/rules/${id}/`)
  },

  // Metrics
  getMetrics(params = {}) {
    return request.get('/monitoring/metrics/', params)
  },

  getDashboardMetrics() {
    return request.get('/monitoring/metrics/dashboard/')
  },

  getMetricsAggregate(params = {}) {
    return request.get('/monitoring/metrics/aggregate/', params)
  },

  exportMetrics(params = {}) {
    return request.get('/monitoring/metrics/export/', params)
  },

  // Execution Monitoring APIs
  getExecutionStats(params = {}) {
    return request.get('/monitoring/stats/', params)
  },

  getActiveExecutions() {
    return request.get('/monitoring/active-executions/')
  },

  getExecutionTrend(params = {}) {
    return request.get('/monitoring/trend/', params)
  },

  getWorkflowHealth(workflowId) {
    return request.get('/monitoring/health/', { workflow_id: workflowId })
  },

  getResourceUsage() {
    return request.get('/monitoring/resources/')
  },

  getExecutionLogsById(executionId) {
    return request.get(`/executions/${executionId}/logs/`)
  },

  // Notification Channels
  getChannels(params = {}) {
    return request.get('/monitoring/channels/', params)
  },

  getChannel(id) {
    return request.get(`/monitoring/channels/${id}/`)
  },

  createChannel(data) {
    return request.post('/monitoring/channels/', data)
  },

  updateChannel(id, data) {
    return request.patch(`/monitoring/channels/${id}/`, data)
  },

  deleteChannel(id) {
    return request.delete(`/monitoring/channels/${id}/`)
  },

  testChannel(id) {
    return request.post(`/monitoring/channels/${id}/test/`)
  },

  // Execution Logs
  getExecutionLogs(params = {}) {
    return request.get('/monitoring/logs/', params)
  }
}

export default monitoringApi
