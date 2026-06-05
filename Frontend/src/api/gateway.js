/**
 * Gateway API - AI Model Gateway
 * @module api/gateway
 */

import { request } from './index'

/** @returns {Promise<import('@/types/gateway').ModelProvider[]>} */
export function getProviders() {
  return request.get('/gateway/providers/')
}

/** @param {string|number} id @returns {Promise<import('@/types/gateway').ModelProvider>} */
export function getProvider(id) {
  return request.get(`/gateway/providers/${id}/`)
}

/**
 * @param {Record<string, string|number|boolean>} [params]
 * @returns {Promise<{count: number, results: import('@/types/gateway').AIModel[]}>}
 */
export function getModels(params = {}) {
  return request.get('/gateway/models/', params)
}

/**
 * @param {Record<string, string|number|boolean>} [params]
 * @returns {Promise<{count: number, results: import('@/types/gateway').AIModel[]}>}
 */
export function getAvailableModels(params = {}) {
  return request.get('/gateway/models/available/', params)
}

/** @param {string|number} id @returns {Promise<import('@/types/gateway').AIModel>} */
export function getModel(id) {
  return request.get(`/gateway/models/${id}/`)
}

/** @returns {Promise<import('@/types/gateway').AIModel[]>} */
export function getDefaultModels() {
  return request.get('/gateway/models/default_models/')
}

/**
 * @param {string|number} id
 * @param {{model?: string, messages?: Array<{role: string, content: string}>}} data
 * @returns {Promise<import('@/types/gateway').GatewayChatResponse>}
 */
export function testModel(id, data) {
  return request.post(`/gateway/models/${id}/test/`, data)
}

/** @returns {Promise<{count: number, results: import('@/types/gateway').UserAPIKey[]}>} Legacy compatibility endpoint backed by unified credentials. */
export function getAPIKeys() {
  return request.get('/gateway/api-keys/')
}

/**
 * @param {import('@/types/gateway').CreateAPIKeyData} data
 * @returns {Promise<import('@/types/gateway').UserAPIKey>}
 */
export function createAPIKey(data) {
  return request.post('/gateway/api-keys/', data)
}

/**
 * @param {string|number} id
 * @param {Partial<import('@/types/gateway').UserAPIKey>} data
 * @returns {Promise<import('@/types/gateway').UserAPIKey>}
 */
export function updateAPIKey(id, data) {
  return request.put(`/gateway/api-keys/${id}/`, data)
}

/** @param {string|number} id @returns {Promise<void>} */
export function deleteAPIKey(id) {
  return request.delete(`/gateway/api-keys/${id}/`)
}

/**
 * @param {string|number} id
 * @returns {Promise<{valid: boolean, message?: string}>}
 */
export function verifyAPIKey(id) {
  return request.post(`/gateway/api-keys/${id}/verify/`)
}

/**
 * @param {Record<string, string|number>} [params]
 * @returns {Promise<{count: number, results: import('@/types/gateway').APICallLog[]}>}
 */
export function getAPILogs(params = {}) {
  return request.get('/gateway/logs/', params)
}

/**
 * @param {{days?: number, limit?: number}} [params]
 * @returns {Promise<import('@/types/gateway').APICallAggregate>}
 */
export function getAPIAggregate(params = {}) {
  return request.get('/gateway/logs/aggregate/', params)
}

/**
 * @param {number} [limit=20]
 * @returns {Promise<import('@/types/gateway').APICallLog[]>}
 */
export function getRecentAPICalls(limit = 20) {
  return request.get('/gateway/logs/recent/', { limit })
}

/**
 * @param {import('@/types/gateway').GatewayChatRequest} data
 * @returns {Promise<import('@/types/gateway').GatewayChatResponse>}
 */
export function gatewayChat(data) {
  return request.post('/gateway/chat/', data)
}

/**
 * @param {import('@/types/gateway').GatewayEmbeddingsRequest} data
 * @returns {Promise<import('@/types/gateway').GatewayEmbeddingsResponse>}
 */
export function gatewayEmbeddings(data) {
  return request.post('/gateway/embeddings/', data)
}

// Export all functions as default
export default {
  // Providers
  getProviders,
  getProvider,
  // Models
  getModels,
  getAvailableModels,
  getModel,
  getDefaultModels,
  testModel,
  // API Keys (legacy compatibility endpoints backed by unified credentials)
  getAPIKeys,
  createAPIKey,
  updateAPIKey,
  deleteAPIKey,
  verifyAPIKey,
  // Logs
  getAPILogs,
  getAPIAggregate,
  getRecentAPICalls,
  // Gateway
  gatewayChat,
  gatewayEmbeddings
}
