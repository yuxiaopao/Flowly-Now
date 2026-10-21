import { defineStore } from 'pinia'
import { getSiteConfig } from '@/api/public'
import { applyRuntimeConfig } from '@/config'
import { toSnakeCaseKeys } from '@/api'

export const useSiteConfigStore = defineStore('siteConfig', {
  state: () => ({
    loaded: false,
    site: {
      name: 'Flowly',
      description: '',
      logo: '',
      favicon: '',
      contactEmail: '',
      contactPhone: '',
      supportUrl: '',
      footerText: '',
    },
    auth: {
      allowRegistration: true,
      emailVerification: false,
      requireTermsOnRegister: true,
      passwordMinLength: 8,
    },
    terms: {
      terms: null,
      privacy: null,
      login: null,
    },
    features: {
      enableMarketplace: true,
      enableNlWorkflow: true,
      enableApiDocs: true,
    },
    defaults: {
      role: 'user',
    },
    payment: {
      defaultCurrency: 'CNY',
      enableRefunds: true,
      providers: [],
    },
    runtime: null,
  }),

  getters: {
    defaultLlmModel: (state) => state.runtime?.llm?.default_model || null,
    defaultEmbeddingModel: (state) => state.runtime?.embedding?.default_model || null,
    publicApiBaseUrl: (state) => state.runtime?.api_base_url || null,
  },

  actions: {
    async fetchPublicConfig(options) {
      try {
        const data = toSnakeCaseKeys(await getSiteConfig(options))
        if (data.site) {
          this.site = {
            name: data.site.name || 'Flowly',
            description: data.site.description || '',
            logo: data.site.logo || '',
            favicon: data.site.favicon || '',
            contactEmail: data.site.contact_email || '',
            contactPhone: data.site.contact_phone || '',
            supportUrl: data.site.support_url || '',
            footerText: data.site.footer_text || '',
          }
        }
        if (data.auth) {
          this.auth = {
            allowRegistration: data.auth.allow_registration !== false,
            emailVerification: !!data.auth.email_verification,
            requireTermsOnRegister: data.auth.require_terms_on_register !== false,
            passwordMinLength: data.auth.password_min_length || 8,
          }
        }
        if (data.terms) {
          this.terms = {
            terms: data.terms.terms,
            privacy: data.terms.privacy,
            login: data.terms.login,
          }
        }
        if (data.features) {
          this.features = {
            enableMarketplace: data.features.enable_marketplace !== false,
            enableNlWorkflow: data.features.enable_nl_workflow !== false,
            enableApiDocs: data.features.enable_api_docs !== false,
          }
        }
        if (data.defaults) {
          this.defaults = { role: data.defaults.role || 'user' }
        }
        if (data.payment) {
          this.payment = {
            defaultCurrency: data.payment.default_currency || 'CNY',
            enableRefunds: data.payment.enable_refunds !== false,
            providers: data.payment.providers || [],
          }
        }
        if (data.runtime) {
          this.runtime = data.runtime
          applyRuntimeConfig(data.runtime)
        }
        this.loaded = true
        if (this.site.name) {
          document.title = this.site.name
        }
      } catch {
        this.loaded = false
      }
    },
  },
})
