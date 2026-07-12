import { request } from './index'
import { APP_CONFIG, getApiBaseUrl } from '@/config'

const NL_REQUEST_TIMEOUT = APP_CONFIG.nlWorkflowRequestTimeout
import Cookies from 'js-cookie'

export const nlWorkflowApi = {
  /**
   * 获取可用的模型列表
   */
  getModels(includeAll = false) {
    return request.get('/nl-workflow/models/', {
      params: includeAll ? { include_all: true } : {}
    })
  },

  /**
   * 创建 NL 会话并生成工作流
   * @param {Object} data - { description, name, model, temperature }
   */
  createSession(data) {
    return request.post('/nl-workflow/sessions/', data, { timeout: NL_REQUEST_TIMEOUT })
  },

  /**
   * 获取 NL 会话列表
   */
  getSessions() {
    return request.get('/nl-workflow/sessions/')
  },

  /**
   * 获取会话详情
   * @param {number} sessionId
   */
  getSession(sessionId) {
    return request.get(`/nl-workflow/sessions/${sessionId}/`)
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
    return request.patch(`/nl-workflow/sessions/${sessionId}/`, data)
  },

  /**
   * 发送消息继续对话
   * @param {number} sessionId
   * @param {string} message
   * @param {Object} options - { model, temperature }
   */
  sendMessage(sessionId, message, options = {}) {
    return request.post(`/nl-workflow/sessions/${sessionId}/message/`, {
      message,
      ...options
    }, { timeout: NL_REQUEST_TIMEOUT })
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
    const { workflow, workflowJson, ...rest } = options
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
      body: JSON.stringify(payload)
    })
  },

  /**
   * 确认并保存生成的工作流
   * @param {number} sessionId
   */
  confirmWorkflow(sessionId) {
    return request.post(`/nl-workflow/sessions/${sessionId}/confirm/`)
  },

  /**
   * 流式生成工作流 (SSE)
   * @param {Object} data - { description, name, model, temperature }
   * @returns {Promise<ReadableStream>} Fetch response with streaming body
   */
  streamWorkflow(data) {
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
