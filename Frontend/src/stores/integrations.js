import { defineStore } from 'pinia'
import { integrationsApi } from '@/api/integrations'

export const useIntegrationsStore = defineStore('integrations', {
  state: () => ({
    webhooks: [],
    currentWebhook: null,
    integrations: [],
    currentIntegration: null,
    templates: [],
    categories: [],
    availableIntegrations: [],
    isLoading: false,
    isSaving: false,
    error: null
  }),

  getters: {
    activeWebhooks: (state) => state.webhooks.filter(w => w.is_active),
    connectedIntegrations: (state) => state.integrations.filter(i => i.is_connected),
    featuredTemplates: (state) => state.templates.filter(t => t.is_featured)
  },

  actions: {
    // Webhooks
    async fetchWebhooks(params = {}) {
      this.isLoading = true
      try {
        const res = await integrationsApi.getWebhooks(params)
        this.webhooks = res.results || res
      } catch (error) {
        this.error = error.message
      } finally {
        this.isLoading = false
      }
    },

    async fetchWebhook(id) {
      try {
        const res = await integrationsApi.getWebhook(id)
        this.currentWebhook = res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async createWebhook(data) {
      this.isSaving = true
      try {
        const res = await integrationsApi.createWebhook(data)
        this.webhooks.unshift(res)
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async updateWebhook(id, data) {
      this.isSaving = true
      try {
        const res = await integrationsApi.updateWebhook(id, data)
        const index = this.webhooks.findIndex(w => w.id === id)
        if (index !== -1) {
          this.webhooks[index] = res
        }
        if (this.currentWebhook?.id === id) {
          this.currentWebhook = res
        }
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async deleteWebhook(id) {
      try {
        await integrationsApi.deleteWebhook(id)
        this.webhooks = this.webhooks.filter(w => w.id !== id)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async testWebhook(id) {
      try {
        return await integrationsApi.testWebhook(id)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    // Integrations
    async fetchIntegrations(params = {}) {
      this.isLoading = true
      try {
        const res = await integrationsApi.getIntegrations(params)
        this.integrations = res.results || res
      } catch (error) {
        this.error = error.message
      } finally {
        this.isLoading = false
      }
    },

    async fetchAvailableIntegrations() {
      try {
        const res = await integrationsApi.getAvailableIntegrations()
        this.availableIntegrations = res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async connectIntegration(id) {
      try {
        const res = await integrationsApi.connectIntegration(id)
        const index = this.integrations.findIndex(i => i.id === id)
        if (index !== -1) {
          this.integrations[index].is_connected = true
        }
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async disconnectIntegration(id) {
      try {
        const res = await integrationsApi.disconnectIntegration(id)
        const index = this.integrations.findIndex(i => i.id === id)
        if (index !== -1) {
          this.integrations[index].is_connected = false
        }
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async syncIntegration(id) {
      try {
        return await integrationsApi.syncIntegration(id)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    // Templates
    async fetchIntegrationTemplates(params = {}) {
      try {
        const res = await integrationsApi.getIntegrationTemplates(params)
        this.templates = res.results || res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchTemplatesByCategory() {
      try {
        const res = await integrationsApi.getTemplatesByCategory()
        this.categories = res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    }
  }
})
