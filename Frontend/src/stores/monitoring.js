import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { monitoringApi } from '@/api/monitoring'

export const useMonitoringStore = defineStore('monitoring', () => {
  // State
  const alerts = ref([])
  const alertSummary = ref(null)
  const alertRules = ref([])
  const metrics = ref([])
  const dashboardMetrics = ref(null)
  const channels = ref([])
  const executionLogs = ref([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref(null)

  // Getters
  const activeAlerts = computed(() =>
    alerts.value.filter(a => a.status === 'active')
  )

  const criticalAlerts = computed(() =>
    alerts.value.filter(a => a.severity === 'critical' && a.status === 'active')
  )

  // Actions - Alerts
  async function fetchAlerts(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await monitoringApi.getAlerts(params)
      alerts.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAlertSummary() {
    try {
      const response = await monitoringApi.getAlertSummary()
      alertSummary.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function acknowledgeAlert(id) {
    try {
      await monitoringApi.acknowledgeAlert(id)
      const alert = alerts.value.find(a => a.id === id)
      if (alert) {
        alert.status = 'acknowledged'
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function resolveAlert(id, note = '') {
    try {
      await monitoringApi.resolveAlert(id, note)
      const alert = alerts.value.find(a => a.id === id)
      if (alert) {
        alert.status = 'resolved'
        alert.resolution_note = note
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function muteAlert(id) {
    try {
      await monitoringApi.muteAlert(id)
      const alert = alerts.value.find(a => a.id === id)
      if (alert) {
        alert.status = 'muted'
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Actions - Alert Rules
  async function fetchAlertRules(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await monitoringApi.getAlertRules(params)
      alertRules.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createAlertRule(data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await monitoringApi.createAlertRule(data)
      alertRules.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateAlertRule(id, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await monitoringApi.updateAlertRule(id, data)
      const index = alertRules.value.findIndex(r => r.id === id)
      if (index !== -1) {
        alertRules.value[index] = { ...alertRules.value[index], ...response }
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteAlertRule(id) {
    isLoading.value = true
    error.value = null
    try {
      await monitoringApi.deleteAlertRule(id)
      alertRules.value = alertRules.value.filter(r => r.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Actions - Metrics
  async function fetchMetrics(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await monitoringApi.getMetrics(params)
      metrics.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchDashboardMetrics() {
    try {
      const response = await monitoringApi.getDashboardMetrics()
      dashboardMetrics.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Actions - Channels
  async function fetchChannels(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await monitoringApi.getChannels(params)
      channels.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createChannel(data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await monitoringApi.createChannel(data)
      channels.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteChannel(id) {
    isLoading.value = true
    error.value = null
    try {
      await monitoringApi.deleteChannel(id)
      channels.value = channels.value.filter(c => c.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function testChannel(id) {
    try {
      return await monitoringApi.testChannel(id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Actions - Execution Logs
  async function fetchExecutionLogs(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await monitoringApi.getExecutionLogs(params)
      executionLogs.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function clearStore() {
    alerts.value = []
    alertSummary.value = null
    alertRules.value = []
    metrics.value = []
    dashboardMetrics.value = null
    channels.value = []
    executionLogs.value = []
    error.value = null
  }

  return {
    // State
    alerts,
    alertSummary,
    alertRules,
    metrics,
    dashboardMetrics,
    channels,
    executionLogs,
    isLoading,
    isSaving,
    error,

    // Getters
    activeAlerts,
    criticalAlerts,

    // Actions - Alerts
    fetchAlerts,
    fetchAlertSummary,
    acknowledgeAlert,
    resolveAlert,
    muteAlert,

    // Actions - Alert Rules
    fetchAlertRules,
    createAlertRule,
    updateAlertRule,
    deleteAlertRule,

    // Actions - Metrics
    fetchMetrics,
    fetchDashboardMetrics,

    // Actions - Channels
    fetchChannels,
    createChannel,
    deleteChannel,
    testChannel,

    // Actions - Logs
    fetchExecutionLogs,

    clearStore
  }
})
