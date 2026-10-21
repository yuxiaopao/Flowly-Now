import { defineStore } from 'pinia'
import { integrationsApi } from '@/api/integrations'
import { INTEGRATION_PAGE_SIZE } from '@/config/integrationCatalog'

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
    activeWebhooks: (state) => state.webhooks.filter(w => w.isActive ?? w.is_active),
    connectedIntegrations: (state) => state.integrations.filter(i => i.isConnected ?? i.is_connected),
    featuredTemplates: (state) => state.templates.filter(t => t.isFeatured ?? t.is_featured)
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

    // Catalog IDs are service keys; connection IDs are user-owned database records.
    async fetchIntegrations(params = {}) {
      const records = []
      let page = 1
      for (;;) {
        const res = await integrationsApi.getIntegrations({ page_size: INTEGRATION_PAGE_SIZE, ...params, page })
        records.push(...(res.results || res))
        if (!res.next) break
        page++
      }
      this.integrations = records
      return records
    },

    async fetchAvailableIntegrations() {
      const res = await integrationsApi.getAvailableIntegrations()
      this.availableIntegrations = res
      return res
    },

    async loadCatalog() {
      this.isLoading = true
      this.error = null
      try {
        await Promise.all([this.fetchAvailableIntegrations(), this.fetchIntegrations()])
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isLoading = false
      }
    },

    upsertIntegration(record) {
      const index = this.integrations.findIndex(item => item.id === record.id)
      if (index === -1) this.integrations.unshift(record)
      else this.integrations[index] = record
      return record
    },

    async saveIntegration(data, id) {
      const res = id ? await integrationsApi.updateIntegration(id, data) : await integrationsApi.createIntegration(data)
      return this.upsertIntegration(res)
    },

    async connectIntegration(id) {
      const res = await integrationsApi.connectIntegration(id)
      this.upsertIntegration(res.integration)
      return res
    },

    async testIntegration(id) {
      const res = await integrationsApi.testIntegration(id)
      this.upsertIntegration(res.integration)
      return res
    },

    async disconnectIntegration(id) {
      const res = await integrationsApi.disconnectIntegration(id)
      return this.upsertIntegration(res)
    },

    async deleteIntegration(id) {
      await integrationsApi.deleteIntegration(id)
      this.integrations = this.integrations.filter(item => item.id !== id)
    },

    async syncIntegration(id) {
      const res = await integrationsApi.syncIntegration(id)
      this.upsertIntegration(res.integration)
      return res
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
