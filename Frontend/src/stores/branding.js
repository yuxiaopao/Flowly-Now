import { defineStore } from 'pinia'
import { brandingApi } from '@/api/branding'

export const useBrandingStore = defineStore('branding', {
  state: () => ({
    currentBranding: null,
    presets: [],
    emailTemplates: [],
    currentEmailTemplate: null,
    customDomains: [],
    currentDomain: null,
    isLoading: false,
    isSaving: false,
    error: null
  }),

  getters: {
    hasCustomBranding: (state) => {
      if (!state.currentBranding) return false
      return state.currentBranding.company_name !== 'Flowly'
    }
  },

  actions: {
    async fetchCurrentBranding() {
      this.isLoading = true
      try {
        const res = await brandingApi.getCurrentBranding()
        this.currentBranding = res
        return res
      } catch (error) {
        this.error = error.message
      } finally {
        this.isLoading = false
      }
    },

    async updateBranding(data) {
      this.isSaving = true
      try {
        const res = await brandingApi.updateBranding(data)
        this.currentBranding = res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async applyPreset(presetId) {
      this.isSaving = true
      try {
        const res = await brandingApi.applyPreset(presetId)
        this.currentBranding = res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async fetchPresets() {
      try {
        const res = await brandingApi.getPresets()
        this.presets = res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async previewBranding(data) {
      try {
        return await brandingApi.previewBranding(data)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    // Email Templates
    async fetchEmailTemplates(params = {}) {
      this.isLoading = true
      try {
        const res = await brandingApi.getEmailTemplates(params)
        this.emailTemplates = res.results || res
        return res
      } catch (error) {
        this.error = error.message
      } finally {
        this.isLoading = false
      }
    },

    async fetchEmailTemplate(id) {
      try {
        const res = await brandingApi.getEmailTemplate(id)
        this.currentEmailTemplate = res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async createEmailTemplate(data) {
      this.isSaving = true
      try {
        const res = await brandingApi.createEmailTemplate(data)
        this.emailTemplates.unshift(res)
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async updateEmailTemplate(id, data) {
      this.isSaving = true
      try {
        const res = await brandingApi.updateEmailTemplate(id, data)
        const index = this.emailTemplates.findIndex(t => t.id === id)
        if (index !== -1) {
          this.emailTemplates[index] = res
        }
        if (this.currentEmailTemplate?.id === id) {
          this.currentEmailTemplate = res
        }
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async deleteEmailTemplate(id) {
      try {
        await brandingApi.deleteEmailTemplate(id)
        this.emailTemplates = this.emailTemplates.filter(t => t.id !== id)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async resetEmailTemplate(id) {
      try {
        const res = await brandingApi.resetEmailTemplate(id)
        const index = this.emailTemplates.findIndex(t => t.id === id)
        if (index !== -1) {
          this.emailTemplates[index] = res
        }
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async sendTestEmail(id) {
      try {
        return await brandingApi.sendTestEmail(id)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    // Custom Domains
    async fetchCustomDomains(params = {}) {
      try {
        const res = await brandingApi.getCustomDomains(params)
        this.customDomains = res.results || res
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async createCustomDomain(data) {
      this.isSaving = true
      try {
        const res = await brandingApi.createCustomDomain(data)
        this.customDomains.unshift(res)
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async verifyDomain(id) {
      try {
        const res = await brandingApi.verifyDomain(id)
        const index = this.customDomains.findIndex(d => d.id === id)
        if (index !== -1) {
          this.customDomains[index] = res
        }
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async refreshSSL(id) {
      try {
        return await brandingApi.refreshSSL(id)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async deleteCustomDomain(id) {
      try {
        await brandingApi.deleteCustomDomain(id)
        this.customDomains = this.customDomains.filter(d => d.id !== id)
      } catch (error) {
        this.error = error.message
        throw error
      }
    }
  }
})
