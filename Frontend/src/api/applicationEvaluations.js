import { request } from './index'
import { applicationsApi } from './applications'
import { APPLICATIONS, newApplicationRequestKey } from '@/config/applications'

const options = {
  preserveRequestKeys: true,
  preserveResponseKeys: true,
  skipErrorToast: true
}
const opaque = new Set([
  'input_data',
  'inputData',
  'output_data',
  'outputData',
  'assertions',
  'expected',
  'actual',
  'configuration'
])
const nested = new Set([
  'results',
  'assertion_results',
  'assertionResults',
  'cases',
  'suite'
])
const camel = (key) =>
  key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
export function adaptEvaluationMetadata(value) {
  if (Array.isArray(value)) return value.map(adaptEvaluationMetadata)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      camel(key),
      opaque.has(key)
        ? item
        : nested.has(key)
          ? adaptEvaluationMetadata(item)
          : item
    ])
  )
}
async function normalizeError(error) {
  let payload = error.response?.data
  if (typeof Blob !== 'undefined' && payload instanceof Blob) {
    try {
      payload = JSON.parse(await payload.text())
    } catch {
      /* Keep the transport error when the body is not JSON. */
    }
  }
  if (typeof payload?.message === 'string') error.message = payload.message
  else if (typeof payload?.detail === 'string') error.message = payload.detail
  else if (payload && typeof payload === 'object') {
    const messages = Object.entries(payload.errors || payload)
      .filter(([key]) => !['code', 'data'].includes(key))
      .flatMap(([key, value]) =>
        typeof value === 'string'
          ? [`${key}: ${value}`]
          : Array.isArray(value)
            ? [`${key}: ${value.join('；')}`]
            : []
      )
    if (messages.length) error.message = messages.join('；')
  }
  if (
    payload?.data?.id &&
    payload.data.status &&
    payload.data.total !== undefined
  )
    error.evaluationRun = adaptEvaluationMetadata(payload.data)
  return error
}
async function call(method, url, data = {}, extra = {}) {
  try {
    const config = { ...options, ...extra }
    const result =
      method === 'get'
        ? await request.get(url, data, config)
        : method === 'delete'
          ? await request.delete(url, config)
          : await request[method](url, data, config)
    return adaptEvaluationMetadata(result)
  } catch (error) {
    throw await normalizeError(error)
  }
}
const app = (id) => `${APPLICATIONS.resource}${encodeURIComponent(id)}/`
const suite = (id, suiteId) =>
  `${app(id)}test-suites/${encodeURIComponent(suiteId)}/`
const run = (id, runId) =>
  `${app(id)}evaluation-runs/${encodeURIComponent(runId)}/`
export const applicationEvaluationsApi = {
  suites: (id, params, extra) =>
    call('get', `${app(id)}test-suites/`, params, extra),
  createSuite: (id, data) => call('post', `${app(id)}test-suites/`, data),
  updateSuite: (id, suiteId, data) => call('patch', suite(id, suiteId), data),
  removeSuite: (id, suiteId) => call('delete', suite(id, suiteId)),
  cases: (id, suiteId, params, extra) =>
    call('get', `${suite(id, suiteId)}cases/`, params, extra),
  createCase: (id, suiteId, data) =>
    call('post', `${suite(id, suiteId)}cases/`, data),
  updateCase: (id, suiteId, caseId, data) =>
    call(
      'patch',
      `${suite(id, suiteId)}cases/${encodeURIComponent(caseId)}/`,
      data
    ),
  removeCase: (id, suiteId, caseId) =>
    call('delete', `${suite(id, suiteId)}cases/${encodeURIComponent(caseId)}/`),
  importSuite: (id, artifact) =>
    call('post', `${app(id)}test-suites-import/`, artifact),
  exportSuite: async (id, suiteId) => {
    try {
      return await request.get(
        `${suite(id, suiteId)}export/`,
        {},
        { ...options, responseType: 'blob' }
      )
    } catch (error) {
      throw await normalizeError(error)
    }
  },
  runs: (id, params, extra) =>
    call('get', `${app(id)}evaluation-runs/`, params, extra),
  startRun: (id, data, key = newApplicationRequestKey()) =>
    call('post', `${app(id)}evaluation-runs/`, data, {
      headers: { 'Idempotency-Key': key }
    }),
  run: (id, runId, extra) => call('get', run(id, runId), {}, extra),
  cancelRun: (id, runId) => call('post', `${run(id, runId)}cancel/`),
  compare: (id, runId, baselineId) =>
    call('get', `${run(id, runId)}compare/`, { baseline_id: baselineId }),
  saveGate: (id, suiteId) =>
    applicationsApi.update(id, {
      required_evaluation_suite_id: suiteId || null
    })
}
