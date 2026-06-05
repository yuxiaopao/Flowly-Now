/**
 * 触发器 API 服务
 * 提供工作流触发器的 CRUD 操作
 */
import { request } from './index'

// =============================================================================
// 类型定义
// =============================================================================

/**
 * 触发器类型
 * @typedef {'manual'|'schedule'|'cron'|'webhook'|'event'} TriggerType
 */

/**
 * 触发器数据结构
 * @typedef {Object} WorkflowTrigger
 * @property {number} id - 触发器ID
 * @property {number} workflowId - 工作流ID
 * @property {string} name - 触发器名称
 * @property {string} [description] - 描述
 * @property {TriggerType} triggerType - 触发类型
 * @property {boolean} isEnabled - 是否启用
 * @property {Object} config - 触发器配置
 * @property {string} [cronExpression] - Cron 表达式
 * @property {string} [scheduledAt] - 定时执行时间
 * @property {number} [intervalSeconds] - 执行间隔（秒）
 * @property {string} [scheduleType] - 定时类型 (once/recurring)
 * @property {string} [authType] - Webhook 认证方式 (none/header/signature)
 * @property {string} [webhookSecret] - Webhook 密钥
 * @property {string} [webhookUrl] - Webhook URL
 * @property {number} [maxExecutions] - 最大执行次数
 * @property {Array} [inputMappings] - 输入映射
 * @property {number} executionCount - 执行次数
 * @property {string} [lastTriggeredAt] - 最后触发时间
 * @property {string} createdAt - 创建时间
 * @property {string} updatedAt - 更新时间
 */

/**
 * 触发器执行记录
 * @typedef {Object} TriggerExecution
 * @property {number} id - 执行ID
 * @property {number} triggerId - 触发器ID
 * @property {string} status - 执行状态 (pending/running/completed/failed)
 * @property {Object} [inputData] - 输入数据
 * @property {Object} [outputData] - 输出数据
 * @property {string} [errorMessage] - 错误信息
 * @property {number} [durationMs] - 执行时长（毫秒）
 * @property {string} queuedAt - 入队时间
 * @property {string} [startedAt] - 开始时间
 * @property {string} [completedAt] - 完成时间
 */

// =============================================================================
// 触发器 CRUD
// =============================================================================

/**
 * 获取触发器列表
 * @param {Object} [params] - 查询参数
 * @param {number} [params.page] - 页码
 * @param {number} [params.page_size] - 每页数量
 * @param {number|string} [params.workflow_id] - 工作流ID
 * @returns {Promise<{count: number, results: WorkflowTrigger[]}>}
 */
export async function getTriggers(params = {}) {
  return request.get('/workflows/triggers/', params)
}

/**
 * 获取单个触发器
 * @param {number|string} id - 触发器ID
 * @returns {Promise<WorkflowTrigger>}
 */
export async function getTrigger(id) {
  return request.get(`/workflows/triggers/${id}/`)
}

/**
 * 创建触发器
 * @param {number|string} workflowId - 工作流ID
 * @param {Object} data - 触发器数据
 * @returns {Promise<WorkflowTrigger>}
 */
export async function createTrigger(workflowId, data) {
  return request.post(`/workflows/${workflowId}/triggers/`, data)
}

/**
 * 更新触发器
 * @param {number|string} id - 触发器ID
 * @param {Partial<WorkflowTrigger>} data - 更新数据
 * @returns {Promise<WorkflowTrigger>}
 */
export async function updateTrigger(id, data) {
  return request.patch(`/workflows/triggers/${id}/`, data)
}

/**
 * 删除触发器
 * @param {number|string} id - 触发器ID
 * @returns {Promise<void>}
 */
export async function deleteTrigger(id) {
  return request.delete(`/workflows/triggers/${id}/`)
}

// =============================================================================
// 触发器状态管理
// =============================================================================

/**
 * 切换触发器启用状态
 * @param {number|string} id - 触发器ID
 * @param {boolean} enabled - 是否启用
 * @returns {Promise<WorkflowTrigger>}
 */
export async function toggleTrigger(id, enabled) {
  return request.patch(`/workflows/triggers/${id}/`, { is_enabled: enabled })
}

// =============================================================================
// 执行历史
// =============================================================================

/**
 * 获取触发器执行历史
 * @param {number|string} triggerId - 触发器ID
 * @param {Object} [params] - 查询参数
 * @param {number} [params.page] - 页码
 * @param {number} [params.page_size] - 每页数量
 * @returns {Promise<{count: number, results: TriggerExecution[]}>}
 */
export async function getTriggerExecutions(triggerId, params = {}) {
  return request.get(`/workflows/triggers/${triggerId}/executions/`, params)
}

// =============================================================================
// Webhook 功能
// =============================================================================

/**
 * 测试 Webhook 触发器
 * @param {number|string} triggerId - 触发器ID
 * @param {Object} [testData] - 测试数据
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function testWebhook(triggerId, testData = {}) {
  return request.post(`/workflows/triggers/${triggerId}/test/`, testData)
}

// =============================================================================
// Cron 功能
// =============================================================================

/**
 * 获取 Cron 表达式下次执行时间预览
 * @param {string} cronExpression - Cron 表达式
 * @param {number} [count=5] - 预览数量
 * @returns {Promise<string[]>}
 */
export async function getCronPreview(cronExpression, count = 5) {
  return request.get('/workflows/triggers/cron-preview/', {
    expression: cronExpression,
    count
  })
}

// =============================================================================
// 导出 API 对象
// =============================================================================

export const triggerApi = {
  // CRUD
  getList: getTriggers,
  get: getTrigger,
  create: createTrigger,
  update: updateTrigger,
  delete: deleteTrigger,

  // 状态管理
  toggle: toggleTrigger,

  // 执行历史
  getExecutions: getTriggerExecutions,

  // Webhook
  testWebhook,

  // Cron
  getCronPreview
}

export default triggerApi
