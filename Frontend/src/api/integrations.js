import { request } from './index'

export const integrationsApi = {
  // Webhooks
  getWebhooks(params = {}) {
    return request.get('/integrations/webhooks/', params)
  },

  getWebhook(id) {
    return request.get(`/integrations/webhooks/${id}/`)
  },

  createWebhook(data) {
    return request.post('/integrations/webhooks/', data)
  },

  updateWebhook(id, data) {
    return request.patch(`/integrations/webhooks/${id}/`, data)
  },

  deleteWebhook(id) {
    return request.delete(`/integrations/webhooks/${id}/`)
  },

  testWebhook(id) {
    return request.post(`/integrations/webhooks/${id}/test/`)
  },

  getWebhookDeliveries(id, params = {}) {
    return request.get(`/integrations/webhooks/${id}/deliveries/`, params)
  },

  getWebhookStats(id) {
    return request.get(`/integrations/webhooks/${id}/stats/`)
  },

  // Integrations
  getIntegrations(params = {}) {
    return request.get('/integrations/integrations/', params)
  },

  getIntegration(id) {
    return request.get(`/integrations/integrations/${id}/`)
  },

  createIntegration(data) {
    return request.post('/integrations/integrations/', data)
  },

  updateIntegration(id, data) {
    return request.patch(`/integrations/integrations/${id}/`, data)
  },

  deleteIntegration(id) {
    return request.delete(`/integrations/integrations/${id}/`)
  },

  connectIntegration(id) {
    return request.post(`/integrations/integrations/${id}/connect/`)
  },

  testIntegration(id) {
    return request.post(`/integrations/integrations/${id}/test/`)
  },

  getIntegrationDeliveries(id) {
    return request.get(`/integrations/integrations/${id}/deliveries/`)
  },

  disconnectIntegration(id) {
    return request.post(`/integrations/integrations/${id}/disconnect/`)
  },

  syncIntegration(id) {
    return request.post(`/integrations/integrations/${id}/sync/`)
  },

  getAvailableIntegrations() {
    return request.get('/integrations/integrations/available/')
  },

  // Integration Templates
  getIntegrationTemplates(params = {}) {
    return request.get('/integrations/templates/', params)
  },

  getIntegrationTemplate(id) {
    return request.get(`/integrations/templates/${id}/`)
  },

  getTemplatesByCategory() {
    return request.get('/integrations/templates/categories/')
  },

  getFeaturedTemplates() {
    return request.get('/integrations/templates/featured/')
  },

  // Webhook Receiver
  registerWebhookReceiver(webhookUrl, events, secret) {
    return request.post('/integrations/webhook-receiver/', { webhookUrl, events, secret })
  }
}

export default integrationsApi
