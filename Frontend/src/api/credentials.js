/**
 * Credentials API — 凭证管理接口
 */
import api from './index'

// ============================================
// 凭证 CRUD
// ============================================

export function listCredentials(params = {}) {
  return api.get('/credentials/', { params })
}

export function getCredential(id) {
  return api.get(`/credentials/${id}/`)
}

export function createCredential(data) {
  return api.post('/credentials/', data)
}

export function updateCredential(id, data) {
  return api.put(`/credentials/${id}/`, data)
}

export function patchCredential(id, data) {
  return api.patch(`/credentials/${id}/`, data)
}

export function deleteCredential(id) {
  return api.delete(`/credentials/${id}/`)
}

// ============================================
// 用户级凭证（仅自己的）
// ============================================

export function listMyCredentials(params = {}) {
  return api.get('/credentials/my/', { params })
}

// ============================================
// 全局凭证（管理员）
// ============================================

export function listGlobalCredentials(params = {}) {
  return api.get('/credentials/global/', { params })
}

// ============================================
// 租户级凭证（管理员）
// ============================================

export function listTenantCredentials(params = {}) {
  return api.get('/credentials/tenant-list/', { params })
}

// ============================================
// 凭证操作
// ============================================

export function verifyCredential(id, data = {}) {
  return api.post(`/credentials/${id}/verify/`, data)
}

export function rotateCredential(id, data) {
  return api.post(`/credentials/${id}/rotate/`, data)
}

export function testProviderCredential(provider, apiKey = null, credentialId = null) {
  return api.post('/credentials/test-provider/', {
    provider,
    api_key: apiKey,
    credential_id: credentialId
  })
}

// ============================================
// 字典接口
// ============================================

export function listProviders() {
  return api.get('/credentials/providers/')
}

export function listScopes() {
  return api.get('/credentials/scopes/')
}
