/**
 * Gateway Store - AI Model Gateway State Management
 */

import { defineStore } from 'pinia'
import {
  getProviders,
  getModels,
  getDefaultModels,
  testModel,
  getAPIKeys,
  createAPIKey,
  updateAPIKey,
  deleteAPIKey,
  verifyAPIKey,
  getAPILogs,
  getAPIAggregate,
  getRecentAPICalls,
  gatewayChat,
  gatewayEmbeddings
} from '@/api/gateway'

export const useGatewayStore = defineStore('gateway', {
  state: () => ({
    // Providers
    providers: [],
    providersLoading: false,

    // Models
    models: [],
    modelsLoading: false,
    defaultModels: {},

    // API Keys (legacy compatibility data sourced from unified credentials)
    apiKeys: [],
    apiKeysLoading: false,

    // API Logs
    apiLogs: [],
    apiLogsLoading: false,
    apiAggregate: null,

    // Gateway Chat
    chatLoading: false,
    chatHistory: [],

    // Embeddings
    embeddingsLoading: false,

    // Error
    error: null
  }),

  getters: {
    // Filter models by type
    chatModels: (state) => state.models.filter(m => m.model_type === 'chat'),
    embeddingModels: (state) => state.models.filter(m => m.model_type === 'embedding'),
    imageModels: (state) => state.models.filter(m => m.model_type === 'image'),

    // Filter models by provider
    modelsByProvider: (state) => (providerSlug) => {
      return state.models.filter(m => m.provider_slug === providerSlug)
    },

    // Get active API keys
    activeAPIKeys: (state) => state.apiKeys.filter(k => k.is_active),

    // Get recent logs
    recentLogs: (state) => state.apiLogs.slice(0, 20),

    // Check if any operation is in progress
    isLoading: (state) => {
      return state.providersLoading ||
             state.modelsLoading ||
             state.apiKeysLoading ||
             state.apiLogsLoading ||
             state.chatLoading ||
             state.embeddingsLoading
    }
  },

  actions: {
    // ==================== Providers ====================

    async fetchProviders() {
      this.providersLoading = true
      this.error = null
      try {
        const response = await getProviders()
        this.providers = response.results || response
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.providersLoading = false
      }
    },

    // ==================== Models ====================

    async fetchModels(params = {}) {
      this.modelsLoading = true
      this.error = null
      try {
        const response = await getModels(params)
        this.models = response.results || response
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.modelsLoading = false
      }
    },

    async fetchDefaultModels() {
      this.modelsLoading = true
      this.error = null
      try {
        const response = await getDefaultModels()
        this.defaultModels = response.results || response
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.modelsLoading = false
      }
    },

    async testModelConnection(modelId, data = {}) {
      try {
        const response = await testModel(modelId, data)
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    // ==================== API Keys ====================

    async fetchAPIKeys() {
      this.apiKeysLoading = true
      this.error = null
      try {
        const response = await getAPIKeys()
        this.apiKeys = response.results || response || []
        return this.apiKeys
      } catch (error) {
        this.error = error.message
        this.apiKeys = []
      } finally {
        this.apiKeysLoading = false
      }
    },

    async addAPIKey(data) {
      try {
        const response = await createAPIKey(data)
        this.apiKeys.push(response)
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async editAPIKey(id, data) {
      try {
        const response = await updateAPIKey(id, data)
        const index = this.apiKeys.findIndex(k => k.id === id)
        if (index !== -1) {
          this.apiKeys[index] = response.results || response
        }
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async removeAPIKey(id) {
      try {
        await deleteAPIKey(id)
        this.apiKeys = this.apiKeys.filter(k => k.id !== id)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async verifyAPIKeyConnection(id) {
      try {
        const response = await verifyAPIKey(id)
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    // ==================== API Logs ====================

    async fetchAPILogs(params = {}) {
      this.apiLogsLoading = true
      this.error = null
      try {
        const response = await getAPILogs(params)
        this.apiLogs = response.results || response
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.apiLogsLoading = false
      }
    },

    async fetchAPIAggregate(params = {}) {
      try {
        const response = await getAPIAggregate(params)
        this.apiAggregate = response.results || response
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchRecentAPICalls(limit = 20) {
      try {
        const response = await getRecentAPICalls(limit)
        this.apiLogs = response.results || response
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    // ==================== Gateway Chat ====================

    async sendChat(messages, options = {}) {
      this.chatLoading = true
      this.error = null
      try {
        const data = {
          messages,
          model: options.model || '',
          temperature: options.temperature ?? 0.7,
          max_tokens: options.max_tokens || 2048
        }

        const response = await gatewayChat(data)

        // Add to history
        this.chatHistory.push({
          role: 'user',
          content: messages[messages.length - 1]?.content || '',
          timestamp: new Date().toISOString()
        })

        this.chatHistory.push({
          role: 'assistant',
          content: response.content,
          model: response.model,
          usage: response.usage,
          timestamp: new Date().toISOString()
        })

        return response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.chatLoading = false
      }
    },

    clearChatHistory() {
      this.chatHistory = []
    },

    // ==================== Embeddings ====================

    async getEmbeddings(texts, model = 'text-embedding-ada-002') {
      this.embeddingsLoading = true
      this.error = null
      try {
        const response = await gatewayEmbeddings({ texts, model })
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.embeddingsLoading = false
      }
    },

    // ==================== Utilities ====================

    clearError() {
      this.error = null
    },

    reset() {
      this.$reset()
    }
  }
})
