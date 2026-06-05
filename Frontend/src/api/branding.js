import { request } from './index'

export const brandingApi = {
  // Branding Config
  getCurrentBranding() {
    return request.get('/branding/branding/current/')
  },

  updateBranding(data) {
    return request.post('/branding/branding/update_config/', data)
  },

  applyPreset(presetId) {
    return request.post('/branding/branding/apply_preset/', { preset_id: presetId })
  },

  getPresets() {
    return request.get('/branding/branding/presets/')
  },

  previewBranding(data) {
    return request.post('/branding/branding/preview/', data)
  },

  // Email Templates
  getEmailTemplates(params = {}) {
    return request.get('/branding/email-templates/', params)
  },

  getEmailTemplate(id) {
    return request.get(`/branding/email-templates/${id}/`)
  },

  createEmailTemplate(data) {
    return request.post('/branding/email-templates/', data)
  },

  updateEmailTemplate(id, data) {
    return request.patch(`/branding/email-templates/${id}/`, data)
  },

  deleteEmailTemplate(id) {
    return request.delete(`/branding/email-templates/${id}/`)
  },

  resetEmailTemplate(id) {
    return request.post(`/branding/email-templates/${id}/reset_to_default/`)
  },

  sendTestEmail(id) {
    return request.post(`/branding/email-templates/${id}/send_test/`)
  },

  // Custom Domains
  getCustomDomains(params = {}) {
    return request.get('/branding/domains/', params)
  },

  getCustomDomain(id) {
    return request.get(`/branding/domains/${id}/`)
  },

  createCustomDomain(data) {
    return request.post('/branding/domains/', data)
  },

  updateCustomDomain(id, data) {
    return request.patch(`/branding/domains/${id}/`, data)
  },

  deleteCustomDomain(id) {
    return request.delete(`/branding/domains/${id}/`)
  },

  verifyDomain(id) {
    return request.post(`/branding/domains/${id}/verify/`)
  },

  refreshSSL(id) {
    return request.post(`/branding/domains/${id}/refresh_ssl/`)
  },

  // Theme Presets
  getThemePresets() {
    return request.get('/branding/presets/')
  },

  getThemePreset(id) {
    return request.get(`/branding/presets/${id}/`)
  }
}

export default brandingApi
