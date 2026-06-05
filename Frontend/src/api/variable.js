/**
 * 变量管理 API 服务
 */
import { request } from './index'

/**
 * 获取工作流变量列表
 * @param {string|number} workflowId
 * @returns {Promise<import('@/types/variable').Variable[]>}
 */
export async function getVariables(workflowId) {
  return request.get(`/workflows/${workflowId}/variables/`)
}

/**
 * 创建变量
 * @param {string|number} workflowId
 * @param {import('@/types/variable').Variable} data
 * @returns {Promise<import('@/types/variable').Variable>}
 */
export async function createVariable(workflowId, data) {
  return request.post(`/workflows/${workflowId}/variables/`, data)
}

/**
 * 更新变量
 * @param {number} id
 * @param {Partial<import('@/types/variable').Variable>} data
 * @returns {Promise<import('@/types/variable').Variable>}
 */
export async function updateVariable(id, data) {
  return request.patch(`/workflows/variables/${id}/`, data)
}

/**
 * 删除变量
 * @param {number} id
 * @returns {Promise<void>}
 */
export async function deleteVariable(id) {
  return request.delete(`/workflows/variables/${id}/`)
}

/**
 * 验证变量引用
 * @param {string|number} workflowId
 * @param {Object} [data]
 * @returns {Promise<{valid: boolean, errors: string[], warnings: string[]}>}
 */
export async function validateVariables(workflowId, data = {}) {
  return request.post(`/workflows/${workflowId}/variables/validate/`, data)
}

/**
 * 批量导入变量
 * @param {string|number} workflowId
 * @param {import('@/types/variable').Variable[]} variables
 * @returns {Promise<{created: number, updated: number, errors: string[]}>}
 */
export async function importVariables(workflowId, variables) {
  return request.post(`/workflows/${workflowId}/variables/import/`, { variables })
}

/**
 * 导出变量为 JSON
 * @param {string|number} workflowId
 * @returns {Promise<string>} JSON string
 */
export async function exportVariables(workflowId) {
  return request.get(`/workflows/${workflowId}/variables/export/`)
}

/**
 * 轮换密钥
 * @param {number} id
 * @returns {Promise<{newValue: string}>}
 */
export async function rotateSecret(id) {
  return request.post(`/workflows/variables/${id}/rotate/`)
}

/**
 * 批量更新变量
 * @param {string|number} workflowId
 * @param {import('@/types/variable').Variable[]} variables
 * @returns {Promise<{created: number, updated: number, deleted: number}>}
 */
export async function batchUpdateVariables(workflowId, variables) {
  return request.put(`/workflows/${workflowId}/variables/`, { variables })
}
