/**
 * 工作流 API 服务
 * 完整的 HTTP 请求封装
 * @description 提供工作流、节点、连线、执行等所有 CRUD 操作
 */

import { request } from './index'
import Cookies from 'js-cookie'
import { getPublicApiUrl } from '@/config'

// =============================================================================
// 类型定义 (引用自 @/types/)
// =============================================================================

/**
 * @typedef {Object} WorkflowListParams
 * @property {number} [page] - 页码
 * @property {number} [page_size] - 每页数量，默认 20
 * @property {string} [search] - 搜索关键词
 * @property {string} [status] - 工作流状态筛选
 * @property {string} [ordering] - 排序字段 (如: -created_at, name)
 * @property {string} [tag] - 标签筛选
 * @property {string} [owner] - 创建者筛选
 */

/**
 * @typedef {Object} WorkflowCreateData
 * @property {string} name - 工作流名称
 * @property {string} [description] - 工作流描述
 * @property {string} [status] - 工作流状态 (draft/active/paused/archived)
 * @property {string[]} [tags] - 标签列表
 * @property {Object} [settings] - 工作流设置
 * @property {import('@/types/workflow').WorkflowNode[]} [nodes] - 节点列表
 * @property {import('@/types/workflow').WorkflowEdge[]} [edges] - 连线列表
 */

/**
 * @typedef {Object} WorkflowNode
 * @property {string} id - 节点ID
 * @property {string} type - 节点类型
 * @property {Object} position - 位置坐标 {x: number, y: number}
 * @property {Object} data - 节点数据
 */

/**
 * @typedef {Object} WorkflowEdge
 * @property {string} id - 连线ID
 * @property {string} source - 源节点ID
 * @property {string} target - 目标节点ID
 * @property {string} [label] - 连线标签
 */

/**
 * @typedef {Object} ExecuteParams
 * @property {Object} input_data - 输入数据
 * @property {boolean} [is_async] - 是否异步执行
 * @property {string} [trigger_type] - 触发类型
 */

/**
 * @typedef {Object} ExecutionResponse
 * @property {number} execution_id - 执行ID
 * @property {string} task_id - Celery任务ID
 * @property {string} status - 执行状态
 * @property {string} [message] - 返回消息
 * @property {Object} [output_data] - 输出数据
 */

// =============================================================================
// 工作流 CRUD
// =============================================================================

/**
 * 获取工作流列表
 * @param {WorkflowListParams} [params] - 查询参数
 * @param {number} [params.page] - 页码，从 1 开始
 * @param {number} [params.page_size] - 每页数量，默认 20
 * @param {string} [params.search] - 搜索关键词
 * @param {string} [params.status] - 工作流状态筛选
 * @param {string} [params.ordering] - 排序字段
 * @param {string} [params.tag] - 标签筛选
 * @returns {Promise<{count: number, results: import('@/types/workflow').WorkflowListItem[]}>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const result = await getWorkflowList({ page: 1, page_size: 20, search: 'test' })
 * console.log(result.results)
 */
export async function getWorkflowList(params = {}) {
  return request.get('/workflows/', params)
}

/**
 * 获取单个工作流详情
 * @param {number|string} id - 工作流ID (uuid 或数字ID)
 * @returns {Promise<import('@/types/workflow').Workflow>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const wf = await getWorkflowById(123)
 * console.log(wf.name, wf.nodes)
 */
export async function getWorkflowById(id) {
  return request.get(`/workflows/${id}/`)
}

/**
 * 创建工作流
 * @param {WorkflowCreateData} data - 工作流数据
 * @param {string} data.name - 工作流名称
 * @param {string} [data.description] - 工作流描述
 * @param {string} [data.status] - 状态，默认 draft
 * @param {string[]} [data.tags] - 标签
 * @param {Object} [data.settings] - 设置
 * @param {WorkflowNode[]} [data.nodes] - 初始节点
 * @param {WorkflowEdge[]} [data.edges] - 初始连线
 * @returns {Promise<import('@/types/workflow').Workflow>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const wf = await createWorkflow({
 *   name: 'My Workflow',
 *   description: 'A test workflow'
 * })
 */
export async function createWorkflow(data) {
  return request.post('/workflows/', data)
}

/**
 * 更新工作流
 * @param {number|string} id - 工作流ID
 * @param {Partial<WorkflowCreateData>} data - 更新数据
 * @returns {Promise<import('@/types/workflow').Workflow>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const wf = await updateWorkflow(123, { name: 'New Name' })
 */
export async function updateWorkflow(id, data) {
  return request.patch(`/workflows/${id}/`, data)
}

/**
 * 删除工作流
 * @param {number|string} id - 工作流ID
 * @returns {Promise<void>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * await deleteWorkflow(123)
 */
export async function deleteWorkflow(id) {
  return request.delete(`/workflows/${id}/`)
}

/**
 * 复制工作流
 * @param {number|string} id - 工作流ID
 * @returns {Promise<import('@/types/workflow').Workflow>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const newWf = await duplicateWorkflow(123)
 */
export async function duplicateWorkflow(id) {
  return request.post(`/workflows/${id}/duplicate/`)
}

/**
 * 导出工作流为 JSON
 * @param {number|string} id - 工作流ID
 * @returns {Promise<import('@/types/workflow').Workflow>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const exported = await exportWorkflow(123)
 */
export async function exportWorkflow(id) {
  return request.get(`/workflows/${id}/export/`)
}

/**
 * 导入工作流
 * @param {FormData|Object} data - 工作流数据 (JSON 对象或 FormData)
 * @returns {Promise<import('@/types/workflow').Workflow>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const wf = await importWorkflow(workflowJson)
 */
export async function importWorkflow(data) {
  return request.post('/workflows/import/', data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// =============================================================================
// 节点操作
// =============================================================================

/**
 * 获取工作流节点列表
 * @param {number|string} workflowId - 工作流ID
 * @returns {Promise<import('@/types/workflow').WorkflowNode[]>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const nodes = await getWorkflowNodes(123)
 */
export async function getWorkflowNodes(workflowId) {
  return request.get('/workflows/nodes/', { workflow: workflowId })
}

/**
 * 创建节点
 * @param {number|string} workflowId - 工作流ID
 * @param {Object} data - 节点数据
 * @param {string} data.type - 节点类型
 * @param {Object} data.position - 位置 {x, y}
 * @param {Object} data.data - 节点配置数据
 * @returns {Promise<import('@/types/workflow').WorkflowNode>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const node = await createNode(123, {
 *   type: 'llm',
 *   position: { x: 100, y: 200 },
 *   data: { label: 'LLM Node', config: {} }
 * })
 */
export async function createNode(workflowId, data) {
  return request.post('/workflows/nodes/', { ...data, workflow: workflowId })
}

/**
 * 更新节点
 * @param {number|string} nodeId - 节点ID
 * @param {Object} data - 更新数据
 * @param {string} [data.type] - 节点类型
 * @param {Object} [data.position] - 位置
 * @param {Object} [data.data] - 节点数据
 * @returns {Promise<import('@/types/workflow').WorkflowNode>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const node = await updateNode(nodeId, { data: { label: 'New Label' } })
 */
export async function updateNode(nodeId, data) {
  return request.patch(`/workflows/nodes/${nodeId}/`, data)
}

/**
 * 删除节点
 * @param {number|string} nodeId - 节点ID
 * @returns {Promise<void>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * await deleteNode(nodeId)
 */
export async function deleteNode(nodeId) {
  return request.delete(`/workflows/nodes/${nodeId}/`)
}

/**
 * 批量更新节点位置
 * @param {Array<{id: string|number, position: {x: number, y: number}}>} positions - 位置数组
 * @returns {Promise<void>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * await batchUpdateNodePositions([
 *   { id: 'node-1', position: { x: 100, y: 200 } },
 *   { id: 'node-2', position: { x: 300, y: 400 } }
 * ])
 */
export async function batchUpdateNodePositions(positions) {
  return request.post('/workflows/nodes/batch_update_positions/', { positions })
}

/**
 * 批量创建节点
 * @param {number|string} workflowId - 工作流ID
 * @param {Object[]} nodes - 节点数组
 * @returns {Promise<import('@/types/workflow').WorkflowNode[]>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const nodes = await batchCreateNodes(123, [node1, node2, node3])
 */
export async function batchCreateNodes(workflowId, nodes) {
  return request.post('/workflows/nodes/batch_create/', { workflow_id: workflowId, nodes })
}

// =============================================================================
// 连线操作
// =============================================================================

/**
 * 获取工作流连线列表
 * @param {number|string} workflowId - 工作流ID
 * @returns {Promise<import('@/types/workflow').WorkflowEdge[]>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const edges = await getWorkflowEdges(123)
 */
export async function getWorkflowEdges(workflowId) {
  return request.get('/workflows/edges/', { workflow: workflowId })
}

/**
 * 创建连线
 * @param {Object} data - 连线数据
 * @param {string} data.source - 源节点ID
 * @param {string} data.target - 目标节点ID
 * @param {string} [data.label] - 连线标签
 * @param {string} [data.type] - 连线类型
 * @returns {Promise<import('@/types/workflow').WorkflowEdge>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const edge = await createEdge({
 *   source: 'node-1',
 *   target: 'node-2',
 *   label: 'Yes'
 * })
 */
export async function createEdge(data) {
  return request.post('/workflows/edges/', data)
}

/**
 * 更新连线
 * @param {number|string} edgeId - 连线ID
 * @param {Object} data - 更新数据
 * @param {string} [data.source] - 源节点ID
 * @param {string} [data.target] - 目标节点ID
 * @param {string} [data.label] - 连线标签
 * @returns {Promise<import('@/types/workflow').WorkflowEdge>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const edge = await updateEdge(edgeId, { label: 'No' })
 */
export async function updateEdge(edgeId, data) {
  return request.patch(`/workflows/edges/${edgeId}/`, data)
}

/**
 * 删除连线
 * @param {number|string} edgeId - 连线ID
 * @returns {Promise<void>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * await deleteEdge(edgeId)
 */
export async function deleteEdge(edgeId) {
  return request.delete(`/workflows/edges/${edgeId}/`)
}

/**
 * 批量创建连线
 * @param {number|string} workflowId - 工作流ID
 * @param {Object[]} edges - 连线数组
 * @returns {Promise<import('@/types/workflow').WorkflowEdge[]>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const edges = await batchCreateEdges(123, [edge1, edge2])
 */
export async function batchCreateEdges(workflowId, edges) {
  return request.post('/workflows/edges/batch_create/', { workflow_id: workflowId, edges })
}

// =============================================================================
// 工作流执行
// =============================================================================

/**
 * 执行工作流
 * @param {number|string} workflowId - 工作流ID
 * @param {Object} [inputData] - 输入数据
 * @param {boolean} [isAsync=false] - 是否异步执行
 * @returns {Promise<import('@/types/execution').ExecutionResponse>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * // 同步执行
 * const result = await executeWorkflow(123, { name: 'test' }, false)
 * @example
 * // 异步执行
 * const result = await executeWorkflow(123, { name: 'test' }, true)
 */
export async function executeWorkflow(workflowId, inputData = {}, isAsync = false) {
  return request.post(`/workflows/${workflowId}/execute/`, {
    input_data: inputData,
    is_async: isAsync
  })
}

/**
 * 同步执行工作流（等待结果返回）
 * @param {number|string} workflowId - 工作流ID
 * @param {Object} [inputData] - 输入数据
 * @returns {Promise<import('@/types/execution').ExecutionResponse>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const result = await executeWorkflowSync(123, { name: 'test' })
 */
export async function executeWorkflowSync(workflowId, inputData = {}) {
  return executeWorkflow(workflowId, inputData, false)
}

/**
 * 异步执行工作流（立即返回任务ID）
 * @param {number|string} workflowId - 工作流ID
 * @param {Object} [inputData] - 输入数据
 * @returns {Promise<import('@/types/execution').ExecutionResponse>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const result = await executeWorkflowAsync(123, { name: 'test' })
 * console.log(result.task_id)
 */
export async function executeWorkflowAsync(workflowId, inputData = {}) {
  return executeWorkflow(workflowId, inputData, true)
}

// 兼容别名
export const executeSync = executeWorkflowSync
export const executeAsync = executeWorkflowAsync

/**
 * 流式执行工作流
 * @param {number|string} workflowId - 工作流ID
 * @param {Object} [inputData] - 输入数据
 * @returns {Promise<Response>} Fetch Response 对象，需自行处理流式数据
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const response = await streamExecuteWorkflow(123, { name: 'test' })
 * const reader = response.body.getReader()
 */
export async function streamExecuteWorkflow(workflowId, inputData = {}) {
  return request.stream(`/workflows/${workflowId}/stream_execute/`, {
    input_data: inputData
  })
}

// =============================================================================
// 执行管理
// =============================================================================

/**
 * 获取执行详情
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<import('@/types/execution').WorkflowExecution>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const execution = await getExecution(123)
 */
export async function getExecution(executionId) {
  return request.get(`/workflows/executions/${executionId}/`)
}

/**
 * 获取执行状态
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<{status: import('@/types/execution').ExecutionStatus, progress: number}>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const status = await getExecutionStatus(123)
 * console.log(status.status, status.progress)
 */
export async function getExecutionStatus(executionId) {
  return request.get(`/workflows/executions/${executionId}/status/`)
}

/**
 * 获取执行时间线（状态 + 节点执行 + 日志，单次请求）
 * @param {number|string} executionId
 */
export async function getExecutionTimeline(executionId) {
  return request.get(`/workflows/executions/${executionId}/timeline/`)
}

/**
 * 获取执行输出
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<{output_data: Object}>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const output = await getExecutionOutput(123)
 */
export async function getExecutionOutput(executionId) {
  return request.get(`/workflows/executions/${executionId}/output/`)
}

/**
 * 获取执行历史
 * @param {number|string} workflowId - 工作流ID
 * @param {Object} [params] - 查询参数
 * @param {number} [params.page] - 页码
 * @param {number} [params.page_size] - 每页数量
 * @param {string} [params.status] - 状态筛选
 * @returns {Promise<{count: number, results: import('@/types/execution').WorkflowExecution[]}>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const history = await getExecutionHistory(123, { page: 1, page_size: 20 })
 */
export async function getExecutionHistory(workflowId, params = {}) {
  return request.get('/workflows/executions/', { workflow: workflowId, ...params })
}

/**
 * 取消执行
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<{status: string, message: string}>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * await cancelExecution(123)
 */
export async function cancelExecution(executionId) {
  return request.post(`/workflows/executions/${executionId}/cancel/`)
}

/**
 * 重试执行
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<import('@/types/execution').ExecutionResponse>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const result = await retryExecution(123)
 */
export async function retryExecution(executionId, data = {}) {
  return request.post(`/workflows/executions/${executionId}/retry/`, data)
}

/**
 * 局部重试失败节点（保留已成功节点产物，重跑失败节点及其下游）
 * @param {number|string} executionId
 * @param {{ node_ids?: string[], include_downstream?: boolean }} [data]
 */
export async function retryFailedExecution(executionId, data = {}) {
  return request.post(`/workflows/executions/${executionId}/retry_failed/`, data)
}

/**
 * 分析是否可继续（失败点 / 未跑完）
 */
export async function analyzeContinueExecution(executionId) {
  return request.get(`/workflows/executions/${executionId}/continue/`)
}

/**
 * 智能继续：从失败点补跑，或从未完成处续跑，保证结果完整
 * @param {number|string} executionId
 * @param {{ mode?: 'auto'|'failed'|'resume'|'incomplete', node_ids?: string[], include_downstream?: boolean, force?: boolean }} [data]
 */
export async function continueExecution(executionId, data = {}) {
  return request.post(`/workflows/executions/${executionId}/continue/`, data)
}

/**
 * 删除执行记录
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<void>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * await deleteExecution(123)
 */
export async function deleteExecution(executionId) {
  return request.delete(`/workflows/executions/${executionId}/`)
}

/**
 * 暂停执行
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<{status: string, message: string}>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * await pauseExecution(123)
 */
export async function pauseExecution(executionId) {
  return request.post(`/workflows/executions/${executionId}/pause/`)
}

/**
 * 恢复执行
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<import('@/types/execution').ExecutionResponse>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * await resumeExecution(123)
 */
export async function resumeExecution(executionId) {
  return request.post(`/workflows/executions/${executionId}/resume/`)
}

/**
 * 获取执行日志
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<import('@/types/execution').ExecutionLogEntry[]>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const logs = await getExecutionLogs(123)
 */
export async function getExecutionLogs(executionId) {
  return request.get(`/workflows/executions/${executionId}/logs/`)
}

/**
 * 获取执行统计
 * @returns {Promise<import('@/types/execution').ExecutionStatistics>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const stats = await getExecutionStatistics()
 */
export async function getExecutionStatistics() {
  return request.get('/workflows/executions/statistics/')
}

/**
 * 获取执行节点列表
 * @param {number|string} executionId - 执行ID
 * @returns {Promise<Array>} 执行中各节点的状态
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const nodes = await getExecutionNodes(123)
 */
export async function getExecutionNodes(executionId) {
  const timeline = await getExecutionTimeline(executionId)
  return timeline.nodeExecutions ?? timeline.node_executions ?? []
}

/**
 * 获取执行节点详情
 * @param {number|string} executionId - 执行ID
 * @param {number|string} nodeId - 节点ID
 * @returns {Promise<Object>} 节点执行详情
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const nodeDetail = await getExecutionNodeDetail(123, 'node-1')
 */
export async function getExecutionNodeDetail(executionId, nodeId) {
  const nodes = await getExecutionNodes(executionId)
  const matched = nodes.find(n =>
    String(n.id) === String(nodeId) ||
    String(n.nodeId) === String(nodeId) ||
    String(n.node_id) === String(nodeId)
  )
  if (matched) return matched
  return request.get(`/node-executions/${nodeId}/`)
}

/**
 * SSE 流式执行（返回 EventSource 用于实时接收执行事件）
 * @param {number|string} workflowId - 工作流ID
 * @param {Object} [inputData] - 输入数据
 * @returns {EventSource} EventSource 实例
 * @example
 * const eventSource = await streamExecuteSSE(123, { name: 'test' })
 * eventSource.onmessage = (event) => {
 *   const data = JSON.parse(event.data)
 *   console.log(data)
 * }
 */
export async function streamExecuteSSE(workflowId, inputData = {}) {
  const token = Cookies.get('access_token') || localStorage.getItem('access_token')
  const url = getPublicApiUrl(`/workflows/${workflowId}/stream_execute/`)
  
  return new EventSource(`${url}?${new URLSearchParams({ input_data: JSON.stringify(inputData), token })}`)
}

/**
 * 获取所有执行列表（跨工作流）
 * @param {Object} [params] - 查询参数
 * @param {number} [params.page] - 页码
 * @param {number} [params.page_size] - 每页数量
 * @param {string} [params.status] - 状态筛选
 * @returns {Promise<{count: number, results: import('@/types/execution').WorkflowExecution[]}>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const executions = await getAllExecutions({ page: 1, page_size: 50 })
 */
export async function getAllExecutions(params = {}) {
  return request.get('/workflows/executions/', params)
}

// =============================================================================
// 工具方法
// =============================================================================

/**
 * 获取可用的工具列表
 * @param {Object} [params] - 查询参数
 * @param {string} [params.category] - 分类筛选
 * @param {string} [params.search] - 搜索关键词
 * @returns {Promise<Array<import('@/types/agent').AgentTool>>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const tools = await getTools({ category: 'api' })
 */
export async function getTools(params = {}) {
  return request.get('/tools/', params)
}

/**
 * 获取可用的节点类型
 * @returns {Promise<{types: Array<{value: string, label: string, category?: string}>}>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const { types } = await getAvailableNodeTypes()
 */
export async function getAvailableNodeTypes() {
  return request.get('/workflows/nodes/available_types/')
}

/**
 * 验证工作流
 * @param {number|string} workflowId - 工作流ID
 * @returns {Promise<import('@/types/workflow').ValidationResult>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const result = await validateWorkflow(123)
 * if (!result.valid) {
 *   console.log(result.errors)
 * }
 */
export async function validateWorkflow(workflowId) {
  return request.post(`/workflows/${workflowId}/validate/`)
}

/**
 * AI 优化工作流分析
 * @param {Object} workflowData - 工作流数据
 * @param {Array} workflowData.nodes - 节点列表
 * @param {Array} workflowData.edges - 连线列表
 * @param {string[]} [workflowData.dimensions] - 分析维度列表
 * @returns {Promise<{suggestions: Array}>}
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const result = await optimizeWorkflow({ nodes, edges, dimensions: ['performance', 'cost'] })
 */
export async function optimizeWorkflow(workflowData) {
  return request.post('/workflows/optimize/', workflowData)
}

// =============================================================================
// 模板画廊 API (新版)
// =============================================================================

function unwrapListResponse(response) {
  if (Array.isArray(response)) {
    return response
  }
  if (Array.isArray(response?.results)) {
    return response.results
  }
  return []
}

function unwrapPaginatedResponse(response) {
  if (response && typeof response === 'object' && Array.isArray(response.results)) {
    return {
      ...response,
      results: response.results,
      count: Number(response.count ?? response.results.length ?? 0),
    }
  }

  const results = unwrapListResponse(response)
  return {
    count: results.length,
    results,
  }
}

/**
 * 获取模板分类列表
 * @param {Object} params - 查询参数 { search, is_active }
 * @returns {Promise<Array>} 分类列表
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const categories = await getTemplateCategories({ search: 'ai' })
 */
export async function getTemplateCategories(params = {}) {
  return request.get('/template-categories/', { params }).then(unwrapListResponse)
}

/**
 * 获取单个模板分类
 * @param {string|number} id - 分类 ID
 * @returns {Promise<Object>} 分类详情
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const category = await getTemplateCategory(1)
 */
export async function getTemplateCategory(id) {
  return request.get(`/template-categories/${id}/`)
}

/**
 * 获取模板列表
 * @param {Object} params - 查询参数 { category, difficulty, featured, search, tag, page, page_size }
 * @returns {Promise<{count: number, results: Array}>} 模板列表
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const result = await getWorkflowTemplates({ category: 'ai', page: 1, page_size: 20 })
 */
export async function getWorkflowTemplates(params = {}) {
  return request.get('/templates/', { params }).then(unwrapPaginatedResponse)
}

/**
 * 获取模板详情（包含完整 workflow_data）
 * @param {string|number} id - 模板 ID
 * @returns {Promise<Object>} 模板详情
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const template = await getTemplate(1)
 * console.log(template.workflow_data)
 */
export async function getTemplate(id) {
  return request.get(`/templates/${id}/`)
}

/**
 * 从模板创建工作流
 * @param {string|number} id - 模板 ID
 * @param {Object} data - 创建参数 { name?, variables? }
 * @returns {Promise<import('@/types/workflow').Workflow>} 新创建的工作流
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const workflow = await createFromTemplate(1, { name: 'My Workflow' })
 */
export async function createFromTemplate(id, data = {}) {
  return request.post(`/templates/${id}/create_from_template/`, data)
}

/**
 * 获取精选模板
 * @returns {Promise<Array>} 精选模板列表
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const featured = await getFeaturedTemplates()
 */
export async function getFeaturedTemplates(params = {}) {
  return request.get('/templates/featured/', { params }).then(unwrapListResponse)
}

/**
 * 按分类获取模板（首页用）
 * @returns {Promise<Array<{category: Object, templates: Array}>>} 按分类分组的模板
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const grouped = await getTemplatesByCategory()
 */
export async function getTemplatesByCategory() {
  return request.get('/templates/by_category/').then(unwrapListResponse)
}

/**
 * 创建模板（发布态，非草稿）
 * @param {Object} data - 模板数据
 * @returns {Promise<Object>} 创建的模板
 */
export async function createTemplate(data) {
  return request.post('/templates/', data)
}

/**
 * 更新模板
 * @param {string|number} id - 模板 ID
 * @param {Object} data - 更新数据
 * @returns {Promise<Object>} 更新后的模板
 */
export async function updateTemplate(id, data) {
  return request.patch(`/templates/${id}/`, data)
}

/**
 * 删除模板
 * @param {string|number} id - 模板 ID
 */
export async function deleteTemplate(id) {
  return request.delete(`/templates/${id}/`)
}

/**
 * 发布模板
 * @param {string|number} id - 模板 ID
 * @returns {Promise<Object>} 更新后的模板
 */
export async function publishTemplate(id) {
  return request.patch(`/templates/${id}/publish/`)
}

/**
 * 取消发布模板
 * @param {string|number} id - 模板 ID
 * @returns {Promise<Object>} 更新后的模板
 */
export async function unpublishTemplate(id) {
  return request.patch(`/templates/${id}/unpublish/`)
}

/**
 * 安装模板（返回安装记录）
 * @param {string|number} id - 模板 ID
 * @returns {Promise<Object>} 安装结果
 */
export async function installTemplate(id) {
  return request.post(`/templates/${id}/install/`)
}

/**
 * 评分模板
 * @param {string|number} id - 模板 ID
 * @param {number} rating - 评分 1-5
 * @returns {Promise<Object>} 评分结果
 */
export async function rateTemplate(id, rating) {
  return request.post(`/templates/${id}/rate/`, { rating })
}

/**
 * 获取我的模板列表（分页）
 * @param {Object} params - 查询参数
 * @returns {Promise<Object>} 分页结果 { count, results }
 */
export async function getMyTemplates(params = {}) {
  return request.get('/templates/mine/', { params }).then(unwrapPaginatedResponse)
}

/**
 * 获取已安装模板列表（分页）
 * @param {Object} params - 查询参数
 * @returns {Promise<Object>} 分页结果 { count, results }
 */
export async function getInstalledTemplates(params = {}) {
  return request.get('/templates/installed/', { params }).then(unwrapPaginatedResponse)
}

/**
 * 领域节点类型元数据
 * @returns {Promise<Array>} 可用的领域节点类型
 * @throws {import('@/utils/request').RequestError}
 * @example
 * const nodeTypes = await getDomainNodeTypes()
 */
export async function getDomainNodeTypes() {
  return request.get('/workflows/nodes/available_types/')
}

/**
 * 系统/global SMTP 默认配置（供邮件节点预填，密码已脱敏）
 */
export async function getEmailSmtpDefaults() {
  return request.get('/workflows/email-smtp-defaults/')
}

/**
 * 上传视频/音频媒体（视频翻译等）
 * @param {File} file
 */
export async function uploadMedia(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/media/upload/', formData)
}

// =============================================================================
// 导出 workflowApi 对象
// =============================================================================

export const workflowApi = {
  // 工作流 CRUD
  getList: getWorkflowList,
  getById: getWorkflowById,
  create: createWorkflow,
  update: updateWorkflow,
  delete: deleteWorkflow,
  duplicate: duplicateWorkflow,
  export: exportWorkflow,
  import: importWorkflow,

  // 节点
  getNodes: getWorkflowNodes,
  createNode,
  updateNode,
  deleteNode,
  saveNodePositions: batchUpdateNodePositions,
  batchCreateNodes,

  // 连线
  getEdges: getWorkflowEdges,
  createEdge,
  updateEdge,
  deleteEdge,
  batchCreateEdges,

  // 执行
  execute: executeWorkflow,
  executeSync: executeWorkflowSync,
  executeAsync: executeWorkflowAsync,
  streamExecute: streamExecuteWorkflow,
  streamExecuteSSE,

  // 执行管理
  getExecution,
  getExecutionStatus,
  getExecutionTimeline,
  getExecutionOutput,
  getExecutionHistory,
  getAllExecutions,
  cancelExecution,
  retryExecution,
  retryFailedExecution,
  analyzeContinueExecution,
  continueExecution,
  deleteExecution,
  pauseExecution,
  resumeExecution,
  getExecutionLogs,
  getExecutionStatistics,
  getExecutionNodes,
  getExecutionNodeDetail,

  // 模板
  getTemplates: getWorkflowTemplates,
  getTemplate,
  createFromTemplate,
  getTemplateCategories,
  getTemplateCategory,
  getFeaturedTemplates,
  getTemplatesByCategory,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  publishTemplate,
  unpublishTemplate,
  installTemplate,
  rateTemplate,
  getMyTemplates,
  getInstalledTemplates,
  getDomainNodeTypes,
  getEmailSmtpDefaults,
  uploadMedia,

  // 工具
  getTools,
  getAvailableNodeTypes,
  validate: validateWorkflow,
  optimize: optimizeWorkflow
}

export default workflowApi
