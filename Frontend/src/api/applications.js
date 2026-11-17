import { request } from './index'
import { APPLICATIONS, newApplicationRequestKey } from '@/config/applications'

const options = Object.freeze({ preserveRequestKeys: true, preserveResponseKeys: true, skipErrorToast: true })
const toCamel = key => key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
const opaqueKeys = new Set(['draft', 'configuration', 'input_data', 'output_data', 'inputData', 'outputData'])

// Only documented metadata is adapted. Resource configuration and user payloads are opaque.
export function adaptApplicationMetadata(value) {
  if (Array.isArray(value)) return value.map(adaptApplicationMetadata)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [toCamel(key),
    opaqueKeys.has(key) ? item
      : ['active_release', 'activeRelease', 'evaluation_gate', 'evaluationGate', 'results', 'recent_applications', 'recentApplications', 'recent_requests', 'recentRequests'].includes(key) ? adaptApplicationMetadata(item) : item,
  ]))
}

function applicationError(error) {
  const payload = error.response?.data
  const detail = payload?.message || payload?.detail
  if (typeof detail === 'string') error.message = detail
  else if (payload && typeof payload === 'object') {
    const messages = Object.entries(payload.errors || payload)
      .filter(([key]) => !['code', 'data', 'errors'].includes(key))
      .flatMap(([key, item]) => typeof item === 'string' ? [`${key}: ${item}`] : Array.isArray(item) ? [`${key}: ${item.join('；')}`] : [])
    if (messages.length) error.message = messages.join('；')
  }
  if (payload?.data?.id && payload.data.status) error.applicationRequest = adaptApplicationMetadata(payload.data)
  return error
}

async function call(method, path, data = {}, extraOptions = {}) {
  const config = { ...options, ...extraOptions }
  try {
    const result = method === 'get'
      ? await request.get(path, data, config)
      : method === 'delete' ? await request.delete(path, config)
      : await request[method](path, data, config)
    return adaptApplicationMetadata(result)
  } catch (error) { throw applicationError(error) }
}

const itemPath = id => `${APPLICATIONS.resource}${encodeURIComponent(id)}/`

function workflowTraceMetadata(value) {
  if (!value || typeof value.id !== 'string' || typeof value.status !== 'string' || !Array.isArray(value.nodes)) {
    throw new Error('工作流执行概要响应格式错误，请稍后重试。')
  }
  return {
    id: value.id, status: value.status, startedAt: value.started_at ?? null, completedAt: value.completed_at ?? null,
    nodes: value.nodes.map(node => {
      if (!node || typeof node.node_id !== 'string' || typeof node.status !== 'string') throw new Error('工作流节点概要响应格式错误，请稍后重试。')
      return { nodeId: node.node_id, nodeName: node.node_name, nodeType: node.node_type, status: node.status,
        startedAt: node.started_at ?? null, completedAt: node.completed_at ?? null, errorMessage: node.error_message || '' }
    })
  }
}

export const applicationsApi = {
  list: params => call('get', APPLICATIONS.resource, params),
  overview: () => call('get', `${APPLICATIONS.resource}overview/`),
  get: id => call('get', itemPath(id)),
  readiness: async id => {
    try { return await request.get(`${itemPath(id)}readiness/`, {}, options) }
    catch (error) { throw applicationError(error) }
  },
  create: data => call('post', APPLICATIONS.resource, data),
  update: (id, data) => call('patch', itemPath(id), data),
  remove: id => call('delete', itemPath(id)),
  test: (id, inputData, idempotencyKey = newApplicationRequestKey()) => call('post', `${itemPath(id)}test/`, { input_data: inputData }, { timeout: APPLICATIONS.executionTimeoutMs, headers: { 'Idempotency-Key': idempotencyKey } }),
  publish: id => call('post', `${itemPath(id)}publish/`),
  rollback: (id, releaseId) => call('post', `${itemPath(id)}rollback/`, { release_id: releaseId }),
  unpublish: id => call('post', `${itemPath(id)}unpublish/`),
  releases: (id, params) => call('get', `${itemPath(id)}releases/`, params),
  keys: (id, params) => call('get', `${itemPath(id)}api-keys/`, params),
  createKey: (id, data) => call('post', `${itemPath(id)}api-keys/`, data),
  revokeKey: (id, keyId) => call('post', `${itemPath(id)}api-keys/${encodeURIComponent(keyId)}/revoke/`),
  requests: (id, params) => call('get', `${itemPath(id)}requests/`, params),
  request: (id, requestId) => call('get', `${itemPath(id)}requests/${encodeURIComponent(requestId)}/`),
  requestExecution: async (id, requestId, extraOptions = {}) => {
    try {
      const result = await request.get(`${itemPath(id)}requests/${encodeURIComponent(requestId)}/execution/`, {}, { ...options, ...extraOptions })
      return workflowTraceMetadata(result)
    } catch (error) { throw applicationError(error) }
  },
  resources: params => call('get', `${APPLICATIONS.resource}resources/`, params),
  tenants: params => call('get', '/tenants/tenants/', { page_size: APPLICATIONS.pageSize, ...params }),
}
