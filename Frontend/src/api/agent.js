import { request } from './index'

/**
 * @typedef {Object} AgentAPI
 * @property {function(Object=): Promise<{count:number, results: import('@/types/agent').Agent[]}>} getList
 * @property {function(string|number): Promise<import('@/types/agent').Agent>} getById
 * @property {function(import('@/types/agent').AgentInput): Promise<import('@/types/agent').Agent>} create
 * @property {function(string|number, Object): Promise<import('@/types/agent').Agent>} update
 * @property {function(string|number): Promise<void>} delete
 * @property {function(string|number): Promise<import('@/types/agent').AgentTool[]>} getAvailableTools
 * @property {function(string|number, string[]): Promise<import('@/types/agent').Agent>} addTools
 * @property {function(string|number, string): Promise<import('@/types/agent').Agent>} removeTool
 * @property {function(string|number, {message: string, context?: Object}): Promise<import('@/types/agent').AgentDebugResponse>} debug
 * @property {function(string|number, Object=): Promise<{count:number, results: import('@/types/agent').AgentDebugSession[]}>} getDebugHistory
 * @property {function(string|number): Promise<void>} clearDebugHistory
 * @property {function(string|number): Promise<import('@/types/agent').AgentSkill[]>} getSkills
 * @property {function(string|number, import('@/types/agent').AgentSkill[]): Promise<import('@/types/agent').Agent>} updateSkills
 * @property {function(string|number, Object=): Promise<{count:number, results: import('@/types/agent').AgentConversation[]}>} getConversations
 * @property {function(string|number): Promise<import('@/types/agent').AgentConversation>} getConversation
 * @property {function(string|number): Promise<void>} deleteConversation
 * @property {function(string|number): Promise<import('@/types/agent').AgentMessage[]>} getMessages
 * @property {function(string|number, string|number): Promise<import('@/types/agent').AgentDebugSession>} loadDebugSession
 * @property {function(string|number, {message: string, conversation_id?: string}): Promise<import('@/types/agent').AgentChatResponse>} sendMessage
 * @property {function(string|number, {message: string, conversation_id?: string}): Promise<Response>} streamChat
 * @property {function(string|number): Promise<import('@/types/agent').Agent>} resetMemory
 * @property {function(string|number, Object=): Promise<{count:number, results: import('@/types/agent').AgentExecution[]}>} getExecutionHistory
 * @property {function(string|number): Promise<import('@/types/agent').AgentExecution>} getExecutionDetail
 */

/**
 * Agent API - CRUD, tools, skills, conversations, and streaming chat.
 * @type {AgentAPI}
 */
export const agentApi = {
  // ==================== Agent CRUD ====================

  /**
   * 获取 Agent 列表
   * @param {Object} params
   */
  getList(params = {}) {
    return request.get('/agents/', params)
  },

  /**
   * 获取单个 Agent
   * @param {number|string} id
   */
  getById(id) {
    return request.get(`/agents/${id}/`)
  },

  /**
   * 创建 Agent
   * @param {Object} data
   */
  create(data) {
    return request.post('/agents/', data)
  },

  /**
   * 更新 Agent
   * @param {number|string} id
   * @param {Object} data
   */
  update(id, data) {
    return request.patch(`/agents/${id}/`, data)
  },

  /**
   * 删除 Agent
   * @param {number|string} id
   */
  delete(id) {
    return request.delete(`/agents/${id}/`)
  },

  // ==================== 工具管理 ====================

  /**
   * 获取 Agent ��用工具列表
   * @param {number|string} agentId
   */
  getAvailableTools(agentId) {
    return request.get(`/agents/${agentId}/tools/`)
  },

  /**
   * 为 Agent 添加工具
   * @param {number|string} agentId
   * @param {Array} toolNames - 工具名称列表
   */
  addTools(agentId, toolNames) {
    return request.post(`/agents/${agentId}/tools/`, { tools: toolNames })
  },

  /**
   * 移除 Agent 的工具
   * @param {number|string} agentId
   * @param {string} tool - 工具名称
   */
  removeTool(agentId, tool) {
    return request.post(`/agents/${agentId}/tools_remove/`, { tool })
  },

  // ==================== 调试与执行 ====================

  /**
   * 调试 Agent
   * @param {number|string} id
   * @param {Object} params - { message, context }
   */
  debug(id, params) {
    return request.post(`/agents/${id}/debug/`, params)
  },

  /**
   * 获取调试历史
   * @param {number|string} id
   * @param {Object} params
   */
  getDebugHistory(id, params = {}) {
    return request.get(`/agents/${id}/debug_history/`, params)
  },

  /**
   * 清除调试历史
   * @param {number|string} id
   */
  clearDebugHistory(id) {
    return request.delete(`/agents/${id}/debug_history/`)
  },

  // ==================== 技能管理 ====================

  /**
   * 获取 Agent 技能列表
   * @param {number|string} id
   */
  getSkills(id) {
    return request.get(`/agents/${id}/skills/`)
  },

  /**
   * 更新 Agent 技能
   * @param {number|string} id
   * @param {Array} skills
   */
  updateSkills(id, skills) {
    return request.patch(`/agents/${id}/update_skills/`, { skills })
  },

  // ==================== 对话管理 ====================

  /**
   * 获取 Agent 对话列表
   * @param {number|string} agentId
   * @param {Object} params
   */
  getConversations(agentId, params = {}) {
    return request.get('/agents/conversations/', { ...params, agent_id: agentId })
  },

  /**
   * 获取单个对话
   * @param {number|string} conversationId
   */
  getConversation(conversationId) {
    return request.get(`/agents/conversations/${conversationId}/`)
  },

  /**
   * 删除对话
   * @param {number|string} conversationId
   */
  deleteConversation(conversationId) {
    return request.delete(`/agents/conversations/${conversationId}/`)
  },

  /**
   * 获取对话中的消息
   * @param {number|string} conversationId
   */
  getMessages(conversationId) {
    return request.get(`/agents/conversations/${conversationId}/messages/`)
  },

  /**
   * 加载单个调试会话
   * @param {number|string} agentId
   * @param {number|string} sessionId
   */
  loadDebugSession(agentId, sessionId) {
    return request.get(`/agents/debug/sessions/${sessionId}/`, { agent_id: agentId })
  },

  /**
   * 发送消息
   * @param {number|string} agentId
   * @param {Object} data - { message, conversation_id }
   */
  sendMessage(agentId, data) {
    return request.post(`/agents/${agentId}/chat/`, data)
  },

  /**
   * 流式聊天（返回原始响应，可用于 SSE）
   * @param {number|string} agentId
   * @param {Object} data - { message, conversation_id }
   */
  streamChat(agentId, data) {
    return request.stream(`/agents/${agentId}/stream_chat/`, data)
  },

  // ==================== Memory ====================

  /**
   * 重置 Agent 记忆
   * @param {number|string} agentId
   */
  resetMemory(agentId) {
    return request.post(`/agents/${agentId}/reset_memory/`)
  },

  // ==================== Execution History ====================

  /**
   * 获取 Agent 执行历史
   * @param {number|string} agentId
   * @param {Object} params
   */
  getExecutionHistory(agentId, params = {}) {
    return request.get(`/agents/${agentId}/debug_history/`, params)
  },

  /**
   * 获取执行详情
   * @param {number|string} executionId
   */
  getExecutionDetail(executionId) {
    return request.get(`/agents/executions/${executionId}/`)
  }
}

export default agentApi
