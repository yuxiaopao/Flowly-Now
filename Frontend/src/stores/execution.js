/**
 * 执行 Store - 工作流执行状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { workflowApi } from '@/api/workflow'
import { ExecutionWebSocket } from '@/api/websocket'
import { useAppStore } from '@/stores/app'

export const useExecutionStore = defineStore('execution', () => {
  // ==================== State ====================
  
  // 当前执行状态
  const currentExecution = ref(null)
  const executionStatus = ref('idle') // idle, running, paused, completed, failed, cancelled
  const executionProgress = ref(0)
  const currentNodeId = ref(null)
  const nodeStatusMap = ref({}) // { nodeId: status }
  const executionLogs = ref([])
  const outputData = ref(null)
  const errorMessage = ref(null)
  const traceback = ref(null)
  
  // WebSocket 连接
  const wsConnection = ref(null)
  const isWsConnected = ref(false)

  // Get appStore for toast notifications
  const appStore = useAppStore()
  
  // 执行历史
  const executionHistory = ref([])
  const historyLoading = ref(false)
  
  // 流式输出
  const streamingOutput = ref('')
  const isStreaming = ref(false)
  const streamingNode = ref('')
  
  // Token 统计
  const tokenStats = ref({
    prompt: 0,
    completion: 0,
    total: 0
  })
  
  // 节点输出缓存
  const nodeOutputs = ref({}) // { nodeId: output }
  const nodeInputs = ref({}) // { nodeId: input }
  
  // ==================== Getters ====================
  
  const isRunning = computed(() => executionStatus.value === 'running')
  const isPaused = computed(() => executionStatus.value === 'paused')
  const isCompleted = computed(() => executionStatus.value === 'completed')
  const isFailed = computed(() => executionStatus.value === 'failed')
  const isCancelled = computed(() => executionStatus.value === 'cancelled')
  const isFinished = computed(() => ['completed', 'failed', 'cancelled'].includes(executionStatus.value))
  
  const nodeCount = computed(() => Object.keys(nodeStatusMap.value).length)
  
  const completedNodeCount = computed(() => 
    Object.values(nodeStatusMap.value).filter(s => s === 'completed').length
  )
  
  const failedNodeCount = computed(() => 
    Object.values(nodeStatusMap.value).filter(s => s === 'failed').length
  )
  
  const progressPercentage = computed(() => {
    if (nodeCount.value === 0) return 0
    return Math.round((completedNodeCount.value / nodeCount.value) * 100)
  })
  
  const nodeStatusSummary = computed(() => {
    const status = {
      pending: 0,
      running: 0,
      completed: 0,
      failed: 0,
      skipped: 0
    }
    Object.values(nodeStatusMap.value).forEach(s => {
      if (status.hasOwnProperty(s)) {
        status[s]++
      }
    })
    return status
  })

  // ==================== Actions ====================
  
  /**
   * 初始化执行（同步）
   */
  async function initExecution(workflowId, inputData = {}) {
    try {
      const response = await workflowApi.executeSync(workflowId, inputData)
      currentExecution.value = response
      updateFromExecution(response)
      return response
    } catch (error) {
      handleExecutionError(error)
      throw error
    }
  }
  
  /**
   * 启动异步执行
   */
  async function startAsyncExecution(workflowId, inputData = {}) {
    try {
      const response = await workflowApi.executeAsync(workflowId, inputData)
      currentExecution.value = response
      executionStatus.value = 'pending'
      return response
    } catch (error) {
      handleExecutionError(error)
      throw error
    }
  }
  
  /**
   * 启动流式执行
   */
  async function startStreamingExecution(workflowId, inputData = {}) {
    try {
      executionStatus.value = 'running'
      isStreaming.value = true
      streamingOutput.value = ''
      
      // 创建执行记录
      const response = await workflowApi.executeAsync(workflowId, inputData)
      currentExecution.value = response
      
      // 连接 WebSocket 获取实时更新
      await connectWebSocket(response.id)
      
      return response
    } catch (error) {
      handleExecutionError(error)
      throw error
    }
  }
  
  /**
   * 连接 WebSocket 获取执行更新
   */
  async function connectWebSocket(executionId) {
    // 关闭已有连接
    disconnectWebSocket()
    
    // 创建新的 WebSocket 连接
    wsConnection.value = new ExecutionWebSocket(executionId)
    
    // 设置事件监听
    wsConnection.value.on('execution_start', (data) => {
      executionStatus.value = 'running'
      if (data.workflowId) {
        currentExecution.value = {
          ...currentExecution.value,
          workflowId: data.workflowId,
          workflowName: data.workflowName
        }
      }
    })
    
    wsConnection.value.on('node_start', (data) => {
      nodeStatusMap.value[data.nodeId] = 'running'
      currentNodeId.value = data.nodeId
      executionLogs.value.push({
        type: 'node_start',
        nodeId: data.nodeId,
        nodeName: data.nodeName,
        timestamp: new Date().toISOString()
      })
    })
    
    wsConnection.value.on('node_complete', (data) => {
      nodeStatusMap.value[data.nodeId] = data.status === 'completed' ? 'completed' : 'failed'
      executionLogs.value.push({
        type: 'node_complete',
        nodeId: data.nodeId,
        nodeName: data.nodeName,
        status: data.status,
        output: data.output,
        timestamp: new Date().toISOString()
      })
      
      // 更新输出数据
      if (data.output) {
        updateOutputData(data.output)
      }
    })
    
    wsConnection.value.on('node_error', (data) => {
      nodeStatusMap.value[data.nodeId] = 'failed'
      executionLogs.value.push({
        type: 'node_error',
        nodeId: data.nodeId,
        nodeName: data.nodeName,
        error: data.error,
        timestamp: new Date().toISOString()
      })
    })
    
    wsConnection.value.on('stream_output', (data) => {
      streamingOutput.value += data.text || ''
      streamingNode.value = data.nodeName || data.nodeId || ''
      executionLogs.value.push({
        type: 'stream_output',
        level: 'info',
        nodeId: data.nodeId,
        nodeName: data.nodeName,
        text: data.text,
        partial: data.partial,
        timestamp: new Date().toISOString()
      })
    })
    
    wsConnection.value.on('stream_chunk', (data) => {
      streamingOutput.value += data.chunk || ''
      streamingNode.value = data.nodeName || ''
      isStreaming.value = true
    })
    
    wsConnection.value.on('execution_complete', (data) => {
      executionStatus.value = 'completed'
      executionProgress.value = 100
      outputData.value = data.outputData
      isStreaming.value = false
      
      appStore.success('工作流执行完成')
      
      // 刷新执行详情
      fetchExecutionDetails(data.executionId)
    })
    
    wsConnection.value.on('execution_error', (data) => {
      executionStatus.value = 'failed'
      errorMessage.value = data.error
      isStreaming.value = false
      
      appStore.error(`执行失败: ${data.error}`)
    })
    
    wsConnection.value.on('execution_cancelled', () => {
      executionStatus.value = 'cancelled'
      isStreaming.value = false
      appStore.warning('执行已取消')
    })
    
    wsConnection.value.on('execution_paused', () => {
      executionStatus.value = 'paused'
      appStore.info('执行已暂停')
    })
    
    wsConnection.value.on('execution_resumed', () => {
      executionStatus.value = 'running'
      appStore.info('执行已恢复')
    })
    
    wsConnection.value.on('execution_status', (data) => {
      updateFromStatus(data)
    })
    
    // LLM Token 更新
    wsConnection.value.on('token_update', (data) => {
      if (data.prompt_tokens) {
        tokenStats.value.prompt += data.prompt_tokens
      }
      if (data.completion_tokens) {
        tokenStats.value.completion += data.completion_tokens
      }
      tokenStats.value.total = tokenStats.value.prompt + tokenStats.value.completion
    })
    
    // 节点输出更新
    wsConnection.value.on('node_output', (data) => {
      nodeOutputs.value[data.nodeId] = data.output
    })
    
    // 节点输入更新
    wsConnection.value.on('node_input', (data) => {
      nodeInputs.value[data.nodeId] = data.input
    })
    
    // 节点跳过
    wsConnection.value.on('node_skipped', (data) => {
      nodeStatusMap.value[data.nodeId] = 'skipped'
      executionLogs.value.push({
        type: 'node_skipped',
        level: 'info',
        nodeId: data.nodeId,
        nodeName: data.nodeName,
        message: data.message || `节点 ${data.nodeName} 已跳过`,
        timestamp: new Date().toISOString()
      })
    })
    
    // 节点状态实时更新 (queued, running, completed, failed)
    wsConnection.value.on('node_status', (data) => {
      nodeStatusMap.value[data.nodeId] = data.status
      executionLogs.value.push({
        type: 'node_status',
        level: 'info',
        nodeId: data.nodeId,
        nodeName: data.nodeName,
        nodeType: data.nodeType,
        status: data.status,
        progress: data.progress,
        output: data.output,
        error: data.error,
        timestamp: data.timestamp || new Date().toISOString()
      })
      
      // 更新输出数据
      if (data.output && data.status === 'completed') {
        updateOutputData(data.output)
      }
    })
    
    // 日志消息
    wsConnection.value.on('log', (data) => {
      executionLogs.value.push({
        type: 'log',
        level: data.level || 'info',
        nodeId: data.nodeId,
        nodeName: data.nodeName,
        message: data.message,
        timestamp: data.timestamp || new Date().toISOString()
      })
    })
    
    // 连接
    await wsConnection.value.connect()
    isWsConnected.value = true
  }
  
  /**
   * 断开 WebSocket 连接
   */
  function disconnectWebSocket() {
    if (wsConnection.value) {
      wsConnection.value.disconnect()
      wsConnection.value = null
    }
    isWsConnected.value = false
  }
  
  /**
   * 取消执行
   * @param {number|string} executionId - 执行ID（可选，默认使用当前执行）
   */
  async function cancelExecution(executionId = null) {
    const id = executionId || currentExecution.value?.id
    if (!id) return
    
    try {
      // 先断开 WebSocket
      disconnectWebSocket()
      
      // 调用 API 取消
      await workflowApi.cancelExecution(id)
      executionStatus.value = 'cancelled'
      
      appStore.warning('执行已取消')
    } catch (error) {
      appStore.error('取消执行失败')
      throw error
    }
  }
  
  /**
   * 暂停执行
   * @param {number|string} executionId - 执行ID（可选，默认使用当前执行）
   */
  async function pauseExecution(executionId = null) {
    const id = executionId || currentExecution.value?.id
    if (!id) return
    
    try {
      await workflowApi.pauseExecution(id)
      executionStatus.value = 'paused'
    } catch (error) {
      appStore.error('暂停执行失败')
      throw error
    }
  }
  
  /**
   * 恢复执行
   * @param {number|string} executionId - 执行ID（可选，默认使用当前执行）
   */
  async function resumeExecution(executionId = null) {
    const id = executionId || currentExecution.value?.id
    if (!id) return
    
    try {
      await workflowApi.resumeExecution(id)
      executionStatus.value = 'running'
    } catch (error) {
      appStore.error('恢复执行失败')
      throw error
    }
  }
  
  /**
   * 重试执行
   * @param {number|string} executionId - 执行ID（可选，默认使用当前执行）
   */
  async function retryExecution(executionId = null) {
    const id = executionId || currentExecution.value?.id
    if (!id) return
    
    try {
      const response = await workflowApi.retryExecution(id)
      currentExecution.value = response
      executionStatus.value = 'pending'
      executionProgress.value = 0
      nodeStatusMap.value = {}
      executionLogs.value = []
      outputData.value = null
      errorMessage.value = null
      
      appStore.success('重试已启动')
      
      // 连接 WebSocket 获取实时更新
      await connectWebSocket(response.id || id)
      
      return response
    } catch (error) {
      appStore.error('重试执行失败')
      throw error
    }
  }
  
  /**
   * 刷新执行详情
   */
  async function fetchExecutionDetails(executionId) {
    try {
      const response = await workflowApi.getExecution(executionId)
      currentExecution.value = response
      updateFromExecution(response)
      return response
    } catch (error) {
      throw error
    }
  }

  /**
   * 获取执行状态
   */
  async function fetchExecutionStatus(executionId) {
    try {
      const response = await workflowApi.getExecutionStatus(executionId)
      updateFromStatus(response)
      return response
    } catch (error) {
      throw error
    }
  }

  /**
   * 获取执行日志
   * @param {number|string} executionId - 执行ID
   * @param {Object} [params] - 查询参数
   * @param {string} [params.level] - 日志级别 (DEBUG, INFO, WARNING, ERROR)
   * @param {string} [params.node_id] - 节点ID (UUID)
   */
  async function fetchExecutionLogs(executionId, params = {}) {
    try {
      const response = await workflowApi.getExecutionLogs(executionId)
      // Support both paginated (results) and direct array responses
      const logs = response.results || response || []
      executionLogs.value = logs.map(log => ({
        ...log,
        // Normalize field names for ExecutionLogsPanel compatibility
        level: (log.level || 'info').toLowerCase(),
        timestamp: log.timestamp || log.time || new Date().toISOString(),
        message: log.message || log.text || '',
        node: log.node || log.nodeName || log.node_name || '',
        nodeName: log.nodeName || log.node_name || '',
      }))
      return executionLogs.value
    } catch (error) {
      // Silently fail - logs are not critical
      console.warn('Failed to fetch execution logs:', error)
      return []
    }
  }
  
  /**
   * 获取执行历史
   */
  async function fetchHistory(workflowId, params = {}) {
    historyLoading.value = true
    try {
      const response = await workflowApi.getExecutionHistory(workflowId, params)
      executionHistory.value = response.results || response
      return executionHistory.value
    } catch (error) {
      throw error
    } finally {
      historyLoading.value = false
    }
  }
  
  /**
   * 从执行对象更新状态
   */
  function updateFromExecution(execution) {
    if (!execution) return
    
    currentExecution.value = execution
    executionStatus.value = execution.status
    executionProgress.value = execution.progress || 0
    currentNodeId.value = execution.currentNodeId
    nodeStatusMap.value = execution.nodeStatus || {}
    outputData.value = execution.outputData || execution.output_data
    errorMessage.value = execution.errorMessage || execution.error_message
    traceback.value = execution.traceback
    
    // 更新 Token 统计
    if (execution.tokens) {
      tokenStats.value = {
        prompt: execution.tokens.prompt || 0,
        completion: execution.tokens.completion || 0,
        total: (execution.tokens.prompt || 0) + (execution.tokens.completion || 0)
      }
    }
    
    // 更新节点输出
    if (execution.nodeResults || execution.node_results) {
      const results = execution.nodeResults || execution.node_results
      Object.entries(results).forEach(([nodeId, result]) => {
        nodeOutputs.value[nodeId] = result.output
        nodeInputs.value[nodeId] = result.input
      })
    }
    
    // 更新执行日志
    if (execution.executionLogs || execution.logs) {
      executionLogs.value = execution.executionLogs || execution.logs
    }
  }
  
  /**
   * 从状态响应更新
   */
  function updateFromStatus(status) {
    executionStatus.value = status.status
    nodeStatusMap.value = status.nodeStatus || {}
    outputData.value = status.outputData
    errorMessage.value = status.errorMessage
    executionProgress.value = status.progress || 0
    currentNodeId.value = status.currentNodeId
  }
  
  /**
   * 更新输出数据
   */
  function updateOutputData(newOutput) {
    if (!outputData.value) {
      outputData.value = {}
    }
    
    if (typeof newOutput === 'object') {
      outputData.value = { ...outputData.value, ...newOutput }
    } else {
      outputData.value.lastOutput = newOutput
    }
  }
  
  /**
   * 处理执行错误
   */
  function handleExecutionError(error) {
    executionStatus.value = 'failed'
    errorMessage.value = error.message || '执行失败'
    isStreaming.value = false
    appStore.error(errorMessage.value)
  }
  
  /**
   * 重置执行状态
   */
  function reset() {
    disconnectWebSocket()
    
    currentExecution.value = null
    executionStatus.value = 'idle'
    executionProgress.value = 0
    currentNodeId.value = null
    nodeStatusMap.value = {}
    executionLogs.value = []
    outputData.value = null
    errorMessage.value = null
    traceback.value = null
    streamingOutput.value = ''
    isStreaming.value = false
    streamingNode.value = ''
    tokenStats.value = { prompt: 0, completion: 0, total: 0 }
    nodeOutputs.value = {}
    nodeInputs.value = {}
  }

  /**
   * 获取节点输出
   */
  function getNodeOutput(nodeId) {
    return nodeOutputs.value[nodeId] || null
  }

  /**
   * 获取节点输入
   */
  function getNodeInput(nodeId) {
    return nodeInputs.value[nodeId] || null
  }

  /**
   * 清除日志
   */
  function clearLogs() {
    executionLogs.value = []
  }

  // ==================== Return ====================
  
  return {
    // State
    currentExecution,
    executionStatus,
    executionProgress,
    currentNodeId,
    nodeStatusMap,
    executionLogs,
    outputData,
    errorMessage,
    traceback,
    isWsConnected,
    executionHistory,
    historyLoading,
    streamingOutput,
    isStreaming,
    streamingNode,
    tokenStats,
    nodeOutputs,
    nodeInputs,
    
    // Getters
    isRunning,
    isPaused,
    isCompleted,
    isFailed,
    isCancelled,
    isFinished,
    nodeCount,
    completedNodeCount,
    failedNodeCount,
    progressPercentage,
    nodeStatusSummary,
    
    // Actions
    initExecution,
    startAsyncExecution,
    startStreamingExecution,
    connectWebSocket,
    disconnectWebSocket,
    cancelExecution,
    pauseExecution,
    resumeExecution,
    retryExecution,
    fetchExecutionDetails,
    fetchExecutionStatus,
    fetchExecutionLogs,
    fetchHistory,
    updateFromExecution,
    updateFromStatus,
    updateOutputData,
    reset,
    getNodeOutput,
    getNodeInput,
    clearLogs
  }
})
