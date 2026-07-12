/**
 * 变量管理 API 服务
 * 后端路由: GET/POST /variables/ ，GET/PATCH/DELETE /variables/{uuid}/
 * 列表过滤: ?workflow={workflowId}
 */
import { request } from './index'

/** @param {Object} v */
function mapVariableFromApi(v) {
  if (!v || typeof v !== 'object') return v
  const varType = v.varType || v.type || 'string'
  const isSecret = Boolean(v.isSensitive) || varType === 'secret'
  return {
    ...v,
    type: isSecret ? 'secret' : varType,
    value: v.defaultValue ?? v.value ?? '',
    environment: v.environment || 'development',
  }
}

/** @param {string|number|null} workflowId @param {Object} data */
function mapVariableToApi(workflowId, data) {
  const frontendType = data.type || data.varType || 'string'
  const isSecret = frontendType === 'secret'
  const payload = {
    name: data.name,
    displayName: data.displayName || data.name,
    description: data.description || '',
    varType: isSecret ? 'secret' : frontendType,
    defaultValue: String(data.value ?? data.defaultValue ?? ''),
    source: data.source || 'workflow',
    isRequired: data.isRequired ?? false,
    isSensitive: isSecret || Boolean(data.isSensitive),
  }
  if (workflowId != null) {
    payload.workflow = workflowId
  }
  return payload
}

/**
 * 获取工作流变量列表
 * @param {string|number} workflowId
 * @returns {Promise<{ results: import('@/types/variable').Variable[] } | import('@/types/variable').Variable[]>}
 */
export async function getVariables(workflowId) {
  const response = await request.get('/variables/', { workflow: workflowId })
  if (Array.isArray(response)) {
    return response.map(mapVariableFromApi)
  }
  if (response?.results) {
    return { ...response, results: response.results.map(mapVariableFromApi) }
  }
  return response
}

/**
 * 创建变量
 * @param {string|number} workflowId
 * @param {import('@/types/variable').Variable} data
 * @returns {Promise<import('@/types/variable').Variable>}
 */
export async function createVariable(workflowId, data) {
  const payload = mapVariableToApi(workflowId, data)
  const created = await request.post('/variables/', payload)
  return mapVariableFromApi(created)
}

/**
 * 更新变量
 * @param {string} id
 * @param {Partial<import('@/types/variable').Variable>} data
 * @returns {Promise<import('@/types/variable').Variable>}
 */
export async function updateVariable(id, data) {
  const payload = mapVariableToApi(null, data)
  const updated = await request.patch(`/variables/${id}/`, payload)
  return mapVariableFromApi(updated)
}

/**
 * 删除变量
 * @param {string} id
 * @returns {Promise<void>}
 */
export async function deleteVariable(id) {
  return request.delete(`/variables/${id}/`)
}

/**
 * 验证变量引用（后端无专用端点，由前端 store 完成校验）
 * @param {string|number} workflowId
 * @param {Object} [_data]
 */
export async function validateVariables(_workflowId, _data = {}) {
  return { valid: true, errors: [], warnings: [] }
}

/**
 * 批量导入变量
 * @param {string|number} workflowId
 * @param {import('@/types/variable').Variable[]} variables
 */
export async function importVariables(workflowId, variables) {
  const results = { created: 0, updated: 0, errors: [] }
  for (const variable of variables) {
    try {
      await createVariable(workflowId, variable)
      results.created += 1
    } catch (err) {
      results.errors.push(err?.message || String(err))
    }
  }
  return results
}

/**
 * 导出变量为 JSON
 * @param {string|number} workflowId
 */
export async function exportVariables(workflowId) {
  const response = await getVariables(workflowId)
  const list = response?.results || response || []
  return JSON.stringify(list, null, 2)
}

/**
 * 轮换密钥（后端暂未实现，占位）
 * @param {string} id
 */
export async function rotateSecret(id) {
  return request.patch(`/variables/${id}/`, {
    defaultValue: crypto.randomUUID?.() || `${Date.now()}`,
    isSensitive: true,
    varType: 'secret',
  })
}

/**
 * 批量更新变量
 * @param {string|number} workflowId
 * @param {import('@/types/variable').Variable[]} variables
 */
export async function batchUpdateVariables(workflowId, variables) {
  const results = { created: 0, updated: 0, deleted: 0 }
  for (const variable of variables) {
    if (variable.id) {
      await updateVariable(variable.id, variable)
      results.updated += 1
    } else {
      await createVariable(workflowId, variable)
      results.created += 1
    }
  }
  return results
}
