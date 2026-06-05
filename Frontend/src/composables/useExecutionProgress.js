/**
 * 执行进度追踪 Composable
 * 负责 WebSocket 连接管理和实时执行进度更新
 */

import { ref, computed, onUnmounted, watch } from 'vue'
import { useExecutionStore } from '@/stores/execution'
import { ExecutionWebSocket, WebSocketEvents } from '@/api/websocket'

export function useExecutionProgress(options = {}) {
  const {
    executionId,
    autoConnect = false,
    onNodeStart,
    onNodeComplete,
    onNodeError,
    onExecutionStart,
    onExecutionComplete,
    onExecutionError,
    onProgress,
    onStatusChange
  } = options

  // Stores
  const executionStore = useExecutionStore()

  // State
  const wsInstance = ref(null)
  const isConnecting = ref(false)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = ref(5)
  const reconnectInterval = ref(3000)
  const currentExecutionId = ref(executionId)
  const lastError = ref(null)

  // Reconnect timer
  let reconnectTimer = null

  // Event callbacks
  const callbacks = {
    onNodeStart,
    onNodeComplete,
    onNodeError,
    onExecutionStart,
    onExecutionComplete,
    onExecutionError,
    onProgress,
    onStatusChange
  }

  // Computed
  const progressPercentage = computed(() => {
    return executionStore.progressPercentage
  })

  const nodeStatusMap = computed(() => {
    return executionStore.nodeStatusMap
  })

  const executionStatus = computed(() => {
    return executionStore.executionStatus
  })

  const currentNodeId = computed(() => {
    return executionStore.currentNodeId
  })

  const isRunning = computed(() => {
    return executionStore.isRunning
  })

  const isFinished = computed(() => {
    return executionStore.isFinished
  })

  const nodeSummary = computed(() => {
    return executionStore.nodeStatusSummary
  })

  /**
   * 创建 WebSocket 实例
   */
  function createWebSocketInstance(execId) {
    if (wsInstance.value) {
      disconnect()
    }

    wsInstance.value = new ExecutionWebSocket(execId)
    setupEventHandlers()
    return wsInstance.value
  }

  /**
   * 设置 WebSocket 事件处理器
   */
  function setupEventHandlers() {
    if (!wsInstance.value) return

    // 连接成功
    wsInstance.value.on('connected', (data) => {
      isConnected.value = true
      isConnecting.value = false
      reconnectAttempts.value = 0
      lastError.value = null
      console.log(`[ExecutionProgress] WebSocket connected for execution ${currentExecutionId.value}`)
    })

    // 执行开始
    wsInstance.value.on(WebSocketEvents.EXECUTION_START, (data) => {
      executionStore.executionStatus = 'running'
      executionStore.executionProgress = 0
      callbacks.onExecutionStart?.(data)
    })

    // 节点开始
    wsInstance.value.on(WebSocketEvents.NODE_START, (data) => {
      executionStore.nodeStatusMap[data.nodeId] = 'running'
      executionStore.currentNodeId = data.nodeId
      callbacks.onNodeStart?.(data)
    })

    // 节点完成
    wsInstance.value.on(WebSocketEvents.NODE_COMPLETE, (data) => {
      executionStore.nodeStatusMap[data.nodeId] = data.status === 'completed' ? 'completed' : 'failed'
      callbacks.onNodeComplete?.(data)
    })

    // 节点错误
    wsInstance.value.on(WebSocketEvents.NODE_ERROR, (data) => {
      executionStore.nodeStatusMap[data.nodeId] = 'failed'
      callbacks.onNodeError?.(data)
    })

    // 节点状态实时更新 (queued, running, completed, failed)
    wsInstance.value.on(WebSocketEvents.NODE_STATUS, (data) => {
      executionStore.nodeStatusMap[data.nodeId] = data.status
      executionStore.currentNodeId = data.nodeId

      // 更新节点输出
      if (data.output && data.status === 'completed') {
        executionStore.nodeOutputs[data.nodeId] = data.output
      }

      // 计算进度
      if (callbacks.onProgress) {
        const totalNodes = Object.keys(executionStore.nodeStatusMap).length
        const completedNodes = Object.values(executionStore.nodeStatusMap)
          .filter(s => s === 'completed' || s === 'failed' || s === 'skipped').length
        const progress = totalNodes > 0 ? Math.round((completedNodes / totalNodes) * 100) : 0
        callbacks.onProgress(progress, data)
      }
    })

    // 执行完成
    wsInstance.value.on(WebSocketEvents.EXECUTION_COMPLETE, (data) => {
      executionStore.executionStatus = 'completed'
      executionStore.executionProgress = 100
      executionStore.outputData = data.outputData
      callbacks.onExecutionComplete?.(data)
    })

    // 执行错误
    wsInstance.value.on(WebSocketEvents.EXECUTION_ERROR, (data) => {
      executionStore.executionStatus = 'failed'
      executionStore.errorMessage = data.error
      callbacks.onExecutionError?.(data)
    })

    // 取消执行
    wsInstance.value.on(WebSocketEvents.EXECUTION_CANCELLED, () => {
      executionStore.executionStatus = 'cancelled'
      callbacks.onStatusChange?.('cancelled')
    })

    // 暂停执行
    wsInstance.value.on(WebSocketEvents.EXECUTION_PAUSED, () => {
      executionStore.executionStatus = 'paused'
      callbacks.onStatusChange?.('paused')
    })

    // 恢复执行
    wsInstance.value.on(WebSocketEvents.EXECUTION_RESUMED, () => {
      executionStore.executionStatus = 'running'
      callbacks.onStatusChange?.('running')
    })

    // 流式输出
    wsInstance.value.on(WebSocketEvents.STREAM_OUTPUT, (data) => {
      executionStore.streamingOutput += data.text || ''
      executionStore.isStreaming = true
    })

    // Token 统计
    wsInstance.value.on(WebSocketEvents.TOKEN_UPDATE, (data) => {
      if (data.prompt_tokens) {
        executionStore.tokenStats.prompt += data.prompt_tokens
      }
      if (data.completion_tokens) {
        executionStore.tokenStats.completion += data.completion_tokens
      }
      executionStore.tokenStats.total = executionStore.tokenStats.prompt + executionStore.tokenStats.completion
    })

    // 节点跳过
    wsInstance.value.on(WebSocketEvents.NODE_SKIPPED, (data) => {
      executionStore.nodeStatusMap[data.nodeId] = 'skipped'
    })

    // 日志
    wsInstance.value.on(WebSocketEvents.LOG, (data) => {
      executionStore.executionLogs.push({
        type: 'log',
        level: data.level || 'info',
        nodeId: data.nodeId,
        nodeName: data.nodeName,
        message: data.message,
        timestamp: data.timestamp || new Date().toISOString()
      })
    })
  }

  /**
   * 连接 WebSocket
   */
  async function connect(execId) {
    if (isConnecting.value || isConnected.value) {
      return
    }

    const targetId = execId || currentExecutionId.value
    if (!targetId) {
      lastError.value = 'No execution ID provided'
      return
    }

    isConnecting.value = true
    lastError.value = null
    currentExecutionId.value = targetId

    try {
      createWebSocketInstance(targetId)
      await wsInstance.value.connect()
    } catch (error) {
      isConnecting.value = false
      isConnected.value = false
      lastError.value = error.message
      console.error(`[ExecutionProgress] Failed to connect: ${error.message}`)
      scheduleReconnect()
    }
  }

  /**
   * 断开 WebSocket 连接
   */
  function disconnect() {
    clearReconnectTimer()

    if (wsInstance.value) {
      wsInstance.value.disconnect()
      wsInstance.value = null
    }

    isConnected.value = false
    isConnecting.value = false
  }

  /**
   * 调度重连
   */
  function scheduleReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts.value) {
      lastError.value = 'Max reconnection attempts reached'
      return
    }

    clearReconnectTimer()

    const delay = reconnectInterval.value * Math.pow(2, reconnectAttempts.value)
    reconnectAttempts.value++

    reconnectTimer = setTimeout(() => {
      if (!isConnected.value && currentExecutionId.value) {
        connect(currentExecutionId.value)
      }
    }, delay)
  }

  /**
   * 清除重连定时器
   */
  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  /**
   * 取消执行
   */
  async function cancel() {
    if (wsInstance.value) {
      wsInstance.value.cancel()
    }
  }

  /**
   * 暂停执行
   */
  async function pause() {
    if (wsInstance.value) {
      wsInstance.value.pause()
    }
  }

  /**
   * 恢复执行
   */
  async function resume() {
    if (wsInstance.value) {
      wsInstance.value.resume()
    }
  }

  /**
   * 获取执行状态
   */
  async function getStatus() {
    if (wsInstance.value) {
      wsInstance.value.getStatus()
    }
  }

  /**
   * 重置执行状态
   */
  function reset() {
    disconnect()
    executionStore.reset()
    reconnectAttempts.value = 0
    lastError.value = null
    currentExecutionId.value = null
  }

  /**
   * 更新节点状态 (手动设置)
   */
  function updateNodeStatus(nodeId, status) {
    executionStore.nodeStatusMap[nodeId] = status
  }

  /**
   * 清除节点状态
   */
  function clearNodeStatus(nodeId) {
    if (nodeId) {
      delete executionStore.nodeStatusMap[nodeId]
    }
  }

  /**
   * 清除所有节点状态
   */
  function clearAllNodeStatus() {
    executionStore.nodeStatusMap = {}
  }

  /**
   * 获取节点状态
   */
  function getNodeStatus(nodeId) {
    return executionStore.nodeStatusMap[nodeId] || null
  }

  /**
   * 检查节点是否处于某状态
   */
  function isNodeInStatus(nodeId, status) {
    return executionStore.nodeStatusMap[nodeId] === status
  }

  /**
   * 获取执行中的节点 ID
   */
  function getRunningNodes() {
    return Object.entries(executionStore.nodeStatusMap)
      .filter(([_, status]) => status === 'running')
      .map(([nodeId]) => nodeId)
  }

  /**
   * 获取已完成的节点 ID
   */
  function getCompletedNodes() {
    return Object.entries(executionStore.nodeStatusMap)
      .filter(([_, status]) => status === 'completed')
      .map(([nodeId]) => nodeId)
  }

  /**
   * 获取失败的节点 ID
   */
  function getFailedNodes() {
    return Object.entries(executionStore.nodeStatusMap)
      .filter(([_, status]) => status === 'failed')
      .map(([nodeId]) => nodeId)
  }

  /**
   * 获取待处理的节点 ID
   */
  function getPendingNodes(allNodeIds) {
    const executedNodes = new Set(Object.keys(executionStore.nodeStatusMap))
    return allNodeIds.filter(id => !executedNodes.has(id))
  }

  // Auto-connect if enabled
  if (autoConnect && executionId) {
    connect(executionId)
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect()
  })

  // Watch for execution ID changes
  if (executionId) {
    watch(() => executionId, (newId) => {
      if (newId && newId !== currentExecutionId.value) {
        currentExecutionId.value = newId
        connect(newId)
      }
    })
  }

  return {
    // State
    wsInstance,
    isConnecting,
    isConnected,
    reconnectAttempts,
    currentExecutionId,
    lastError,

    // Computed
    progressPercentage,
    nodeStatusMap,
    executionStatus,
    currentNodeId,
    isRunning,
    isFinished,
    nodeSummary,

    // Methods
    connect,
    disconnect,
    cancel,
    pause,
    resume,
    getStatus,
    reset,
    updateNodeStatus,
    clearNodeStatus,
    clearAllNodeStatus,
    getNodeStatus,
    isNodeInStatus,
    getRunningNodes,
    getCompletedNodes,
    getFailedNodes,
    getPendingNodes,

    // Direct store access
    executionStore
  }
}

// 节点状态常量
export const NodeStatus = {
  PENDING: 'pending',
  QUEUED: 'queued',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  SKIPPED: 'skipped'
}

// 状态颜色映射
export const StatusColors = {
  pending: '#9ca3af',    // 灰色
  queued: '#9ca3af',     // 灰色
  running: '#3b82f6',    // 蓝色
  completed: '#10b981',   // 绿色
  failed: '#ef4444',      // 红色
  skipped: '#f59e0b'      // 橙色
}

// 状态文本映射
export const StatusLabels = {
  pending: '等待中',
  queued: '排队中',
  running: '执行中',
  completed: '已完成',
  failed: '失败',
  skipped: '已跳过'
}

// 状态图标映射
export const StatusIcons = {
  pending: 'Clock',
  queued: 'Clock',
  running: 'Loader',
  completed: 'Check',
  failed: 'X',
  skipped: 'SkipForward'
}

export default useExecutionProgress
