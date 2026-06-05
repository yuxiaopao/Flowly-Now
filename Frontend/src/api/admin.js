import { request } from './index'

export const adminApi = {
  // Users
  getUsers(params = {}) {
    return request.get('/admin/users/', params)
  },

  getUser(id) {
    return request.get(`/admin/users/${id}/`)
  },

  updateUser(id, data) {
    return request.patch(`/admin/users/${id}/`, data)
  },

  deleteUser(id) {
    return request.delete(`/admin/users/${id}/`)
  },

  // Workflows
  getAllWorkflows(params = {}) {
    return request.get('/admin/workflows/', params)
  },

  getWorkflow(id) {
    return request.get(`/admin/workflows/${id}/`)
  },

  // Agents
  getAllAgents(params = {}) {
    return request.get('/admin/agents/', params)
  },

  // Usage Stats
  getSystemUsage(params = {}) {
    return request.get('/admin/usage/', params)
  },

  // System Health
  getSystemHealth() {
    return request.get('/admin/health/')
  },

  // Settings
  getSystemSettings() {
    return request.get('/admin/settings/')
  },

  updateSystemSettings(data) {
    return request.patch('/admin/settings/', data)
  },

  // API Keys
  getApiKeys(params = {}) {
    return request.get('/admin/api-keys/', params)
  },

  createApiKey(data) {
    return request.post('/admin/api-keys/', data)
  },

  revokeApiKey(id) {
    return request.post(`/admin/api-keys/${id}/revoke/`)
  }
}

export default adminApi
