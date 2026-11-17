/**
 * Gateway Store - AI Model Gateway State Management
 */

import { defineStore } from 'pinia'
import { APP_CONFIG } from '@/config'
import { gatewayErrorMessage } from '@/config/gateway'
import {
  getProviders,
  getModels,
  getDefaultModels,
  testModel,
  setModelDefault,
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

async function collectPages(load, params = {}) {
  const items = []
  let page = Number(params.page) || 1
  let response
  do {
    response = await load({ ...params, page })
    items.push(...(Array.isArray(response) ? response : response.results || []))
    page++
  } while (response.next)
  return items
}

export const useGatewayStore = defineStore('gateway', {
  state: () => ({
    // Providers
    providers: [],
    providersLoading: false,
    providersError: null,

    // Models
    models: [],
    modelsLoading: false,
    defaultModels: {},
    defaultModelsLoading: false,

    // API Keys (legacy compatibility data sourced from unified credentials)
    apiKeys: [],
    apiKeysLoading: false,
    apiKeysError: null,
    modelsError: null,
    aggregateError: null,

    // API Logs
    apiLogs: [],
    apiLogsLoading: false,
    apiLogsError: null,
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
    chatModels: (state) => state.models.filter(m => m.modelType === 'chat'),
    embeddingModels: (state) => state.models.filter(m => m.modelType === 'embedding'),
    imageModels: (state) => state.models.filter(m => m.modelType === 'image'),

    // Filter models by provider
    modelsByProvider: (state) => (providerSlug) => {
      return state.models.filter(m => m.providerSlug === providerSlug)
    },

    // Get active API keys
    activeAPIKeys: (state) => state.apiKeys.filter(k => k.isActive),

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
      this.providersError = null
      try {
        this.providers = await collectPages(getProviders)
        return this.providers
      } catch (error) {
        this.error = this.providersError = gatewayErrorMessage(error, '提供商列表加载失败')
        throw error
      } finally {
        this.providersLoading = false
      }
    },

    // ==================== Models ====================

    async fetchModels(params = {}) {
      this.modelsLoading = true
      this.error = null
      this.modelsError = null
      try {
        this.models = await collectPages(getModels, params)
        return this.models
      } catch (error) {
        this.error = this.modelsError = gatewayErrorMessage(error, '模型列表加载失败')
        throw error
      } finally {
        this.modelsLoading = false
      }
    },

    async fetchDefaultModels() {
      this.defaultModelsLoading = true
      this.error = null
      try {
        const response = await getDefaultModels()
        this.defaultModels = response.results || response
        return response.results || response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.defaultModelsLoading = false
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

    async setCatalogDefault(model, isDefault) {
      const result = await setModelDefault(model.id, isDefault)
      this.models = this.models.map(item => item.id === result.id ? result : result.isDefault && item.modelType === result.modelType ? { ...item, isDefault: false } : item)
      if (result.isDefault) this.defaultModels[result.modelType] = result
      else delete this.defaultModels[result.modelType]
      const refreshed = await Promise.allSettled([this.fetchModels(), this.fetchDefaultModels()])
      return { model: result, refreshFailed: refreshed.some(item => item.status === 'rejected') }
    },

    // ==================== API Keys ====================

    async fetchAPIKeys() {
      this.apiKeysLoading = true
      this.error = null
      this.apiKeysError = null
      try {
        this.apiKeys = await collectPages(getAPIKeys)
        return this.apiKeys
      } catch (error) {
        this.error = this.apiKeysError = gatewayErrorMessage(error, 'API 密钥加载失败')
        this.apiKeys = []
        throw error
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
      this.apiLogsError = null
      try {
        const response = await getAPILogs(params)
        this.apiLogs = response.results || response
        return response.results || response
      } catch (error) {
        this.error = this.apiLogsError = gatewayErrorMessage(error, '调用日志加载失败')
        throw error
      } finally {
        this.apiLogsLoading = false
      }
    },

    async fetchAPIAggregate(params = {}) {
      this.aggregateError = null
      try {
        const response = await getAPIAggregate(params)
        this.apiAggregate = response.results || response
        return response.results || response
      } catch (error) {
        this.error = this.aggregateError = gatewayErrorMessage(error, '用量统计加载失败')
        this.apiAggregate = null
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

    async getEmbeddings(texts, model = APP_CONFIG.embedding.defaultModel) {
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
