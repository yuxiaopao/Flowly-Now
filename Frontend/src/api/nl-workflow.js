import { request } from './index'
import { APP_CONFIG, getApiBaseUrl } from '@/config'
import { NL_CREATOR } from '@/config/nlCreator'

const NL_REQUEST_TIMEOUT = APP_CONFIG.nlWorkflowRequestTimeout
import Cookies from 'js-cookie'

export const nlWorkflowApi = {
  /**
   * 获取可用的模型列表
   */
  getModels(includeAll = false) {
    return request.get('/nl-workflow/models/', includeAll ? { include_all: true } : {})
  },

  /**
   * 创建 NL 会话并生成工作流
   * @param {Object} data - { description, name, model, temperature, async? }
   */
  createSession(data, { signal } = {}) {
    return request.post('/nl-workflow/sessions/', data, { timeout: NL_REQUEST_TIMEOUT, preserveWorkflowKeys: true, signal })
  },

  /**
   * 轮询异步生成任务状态
   * @param {string} sessionId
   * @param {Object} [params] - { task_id? }
   */
  getTaskStatus(sessionId, params = {}) {
    return request.get(`/nl-workflow/sessions/${sessionId}/task/`, params, { preserveWorkflowKeys: true })
  },

  /**
   * 重试卡住的异步生成任务
   * @param {string} sessionId
   * @param {Object} [data] - { action?, model?, temperature? }
   */
  retryTask(sessionId, data = {}) {
    return request.post(`/nl-workflow/sessions/${sessionId}/task/`, {
      action: 'retry',
      ...data
    }, { timeout: NL_REQUEST_TIMEOUT, preserveWorkflowKeys: true })
  },

  /**
   * 获取 NL 会话列表
   */
  getSessions(params = {}) {
    return request.get('/nl-workflow/sessions/', params)
  },

  /**
   * 获取会话详情
   * @param {number} sessionId
   */
  getSession(sessionId) {
    return request.get(`/nl-workflow/sessions/${sessionId}/`, {}, { preserveWorkflowKeys: true })
  },

  async ensureWorkspaceVersion(sessionId) {
    const session = await nlWorkflowApi.getSession(sessionId)
    if (Number(session.workspaceVersion || 0) < NL_CREATOR.apiVersion) throw new Error(NL_CREATOR.outdatedBackend)
    return session
  },

  /**
   * 删除会话
   * @param {number} sessionId
   */
  deleteSession(sessionId) {
    return request.delete(`/nl-workflow/sessions/${sessionId}/`)
  },

  /**
   * 更新会话（重命名等）
   * @param {number} sessionId
   * @param {Object} data - { name }
   */
  updateSession(sessionId, data) {
    return request.patch(`/nl-workflow/sessions/${sessionId}/`, data, { preserveWorkflowKeys: true })
  },

  /**
   * 发送消息继续对话
   * @param {number} sessionId
   * @param {string} message
   * @param {Object} options - { model, temperature }
   */
  sendMessage(sessionId, message, options = {}, { signal } = {}) {
    return request.post(`/nl-workflow/sessions/${sessionId}/message/`, {
      message,
      ...options
    }, { timeout: NL_REQUEST_TIMEOUT, preserveWorkflowKeys: true, signal })
  },

  /**
   * 流式发送消息继续对话 (SSE)
   * @param {number} sessionId
   * @param {string} message
   * @param {Object} options - { model, temperature }
   * @returns {Promise<ReadableStream>} Fetch response with streaming body
   */
  streamMessage(sessionId, message, options = {}) {
    const token = Cookies.get('access_token') || localStorage.getItem('access_token')
    const { workflow, workflowJson, signal, ...rest } = options
    const payload = {
      message,
      ...rest
    }
    if (workflow || workflowJson) {
      payload.workflow = workflow || workflowJson
    }
    return fetch(`${getApiBaseUrl()}/nl-workflow/sessions/${sessionId}/message/stream/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      credentials: 'include',
      signal,
      body: JSON.stringify(payload)
    })
  },

  /**
   * 确认并保存生成的工作流
   * @param {number} sessionId
   */
  confirmWorkflow(sessionId, workflow) {
    return request.post(`/nl-workflow/sessions/${sessionId}/confirm/`, workflow ? { workflow_json: JSON.stringify(workflow) } : {})
  },

  /**
   * 流式生成工作流 (SSE)
   * @param {Object} data - { description, name, model, temperature }
   * @returns {Promise<ReadableStream>} Fetch response with streaming body
   */
  streamWorkflow(data, { signal } = {}) {
    const token = Cookies.get('access_token') || localStorage.getItem('access_token')
    const payload = { ...data }
    if (data.workflow || data.workflowJson) {
      payload.workflow = data.workflow || data.workflowJson
    }
    return fetch(`${getApiBaseUrl()}/nl-workflow/stream/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      credentials: 'include',
      signal,
      body: JSON.stringify(payload)
    })
  },

  /**
   * 预览生成的工作流（不保存）
   * @param {Object} data - { description, model, temperature }
   */
  preview(data) {
    return request.post('/nl-workflow/preview/', data)
  },

  /**
   * 编辑器排布助手同步应用（不占用 stream 限流配额）
   * @param {Object} data - { message, workflow, mode?, model?, temperature? }
   */
  applyEditorAction(data) {
    return request.post('/nl-workflow/editor/apply/', data, { timeout: NL_REQUEST_TIMEOUT })
  },

  /**
   * 分析用户消息意图
   * @param {string} message - User message to analyze
   */
  analyzeIntent(message) {
    return request.post('/nl-workflow/analyze-intent/', { message })
  },

  /**
   * 获取工作流修改建议
   * @param {Object} data - { workflow?, description? }
   */
  suggest(data) {
    return request.post('/nl-workflow/suggest/', data)
  }
}

export default nlWorkflowApi
