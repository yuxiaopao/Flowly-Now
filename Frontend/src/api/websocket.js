/**
 * WebSocket 服务 - 工作流执行实时通信
 */

import Cookies from 'js-cookie'
import { markRaw } from 'vue'
import { useAppStore } from '@/stores/app'
import { APP_CONFIG, getWebSocketUrl } from '@/config'

// Only transport metadata is normalized. Node outputs and configuration are user data.
export function normalizeWebSocketMessage(message) {
  if (!message || typeof message !== 'object' || Array.isArray(message)) return null
  const payload = message.data && typeof message.data === 'object' && !Array.isArray(message.data)
    ? message.data : {}
  const normalized = { ...message, ...payload, type: message.type || message.event }
  for (const [key, value] of Object.entries(normalized)) {
    if (key.includes('_')) normalized[key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())] = value
  }
  return normalized
}

// WebSocket 事件类型
export const WebSocketEvents = {
  // 执行事件
  EXECUTION_START: 'execution_start',
  EXECUTION_COMPLETE: 'execution_complete',
  EXECUTION_ERROR: 'execution_error',
  EXECUTION_CANCELLED: 'execution_cancelled',
  EXECUTION_PAUSED: 'execution_paused',
  EXECUTION_RESUMED: 'execution_resumed',
  EXECUTION_STATUS: 'execution_status',
  
  // 节点事件
  NODE_START: 'node_start',
  NODE_COMPLETE: 'node_complete',
  NODE_ERROR: 'node_error',
  NODE_SKIPPED: 'node_skipped',
  NODE_OUTPUT: 'node_output',
  NODE_INPUT: 'node_input',
  NODE_STATUS: 'node_status',  // 节点实时状态更新 (queued, running, completed, failed)
  
  // 流式事件
  STREAM_OUTPUT: 'stream_output',
  STREAM_CHUNK: 'stream_chunk',
  THINKING_START: 'thinking_start',
  THINKING_STREAM: 'thinking_stream',
  THINKING_END: 'thinking_end',
  
  // Token 事件
  TOKEN_UPDATE: 'token_update',
  
  // 日志事件
  LOG: 'log',
  
  // 进度事件
  PROGRESS_UPDATE: 'progress_update'
}

class WebSocketService {
  constructor() {
    this.ws = null
    this.url = ''
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = APP_CONFIG.executionRealtime.maxReconnectAttempts
    this.reconnectDelay = APP_CONFIG.executionRealtime.reconnectDelayMs
    this.listeners = new Map()
    this.isConnected = false
    this.heartbeatTimer = null
    this.heartbeatInterval = APP_CONFIG.executionRealtime.heartbeatIntervalMs
    this.connectionPath = ''
    this.connectionParams = {}
    this.reconnectTimer = null
    this.connectionTimer = null
    this.rejectPendingConnection = null
    this.intentionallyClosed = false
  }

  /**
   * 连接 WebSocket
   * @param {string} url - WebSocket URL
   * @param {Object} params - 连接参数
   */
  connect(url, params = {}) {
    this._clearReconnect()
    this.connectionPath = url
    this.connectionParams = params
    this.intentionallyClosed = false
    return new Promise((resolve, reject) => {
      const token = Cookies.get('access_token') || localStorage.getItem('access_token')
      
      // 构建 WebSocket URL
      const wsUrl = this._buildUrl(url, params, token)
      this.url = wsUrl

      let settled = false
      const fail = (error) => {
        if (settled) return
        settled = true
        this._clearConnectionTimeout()
        this.rejectPendingConnection = null
        reject(error)
      }
      this.rejectPendingConnection = fail

      try {
        const socket = new WebSocket(wsUrl)
        this.ws = markRaw(socket)
        this.connectionTimer = setTimeout(() => {
          if (this.ws !== socket) return
          fail(new Error('WebSocket 连接超时'))
          socket.close()
        }, APP_CONFIG.executionRealtime.connectionTimeoutMs)

        socket.onopen = () => {
          if (this.ws !== socket || this.intentionallyClosed) return
          settled = true
          this._clearConnectionTimeout()
          this.rejectPendingConnection = null
          this.isConnected = true
          this.reconnectAttempts = 0
          this._startHeartbeat()
          this._sendMessage({ type: 'subscribe', events: params.events || ['all'] })
          this._emit('connection_open', {})
          resolve()
        }

        socket.onmessage = (event) => {
          if (this.ws === socket) this._handleMessage(event)
        }

        socket.onerror = () => {
          if (this.ws !== socket) return
          this.isConnected = false
          fail(new Error('WebSocket 连接失败'))
          this._emit('connection_error', {})
        }

        socket.onclose = (event) => {
          if (this.ws !== socket) return
          fail(new Error(`WebSocket 连接已关闭 (${event.code})`))
          this.isConnected = false
          this._stopHeartbeat()
          this._emit('connection_close', { code: event.code })
          this._handleReconnect()
        }

      } catch (error) {
        fail(error)
      }
    })
  }

  /**
   * 构建 WebSocket URL
   */
  _buildUrl(url, params, token) {
    const wsUrl = new URL(getWebSocketUrl(url))
    
    // 添加查询参数
    const queryParams = wsUrl.searchParams
    if (token) queryParams.set('token', token)
    if (params.executionId) queryParams.set('execution_id', params.executionId)
    if (params.workflowId) queryParams.set('workflow_id', params.workflowId)
    
    return wsUrl.toString()
  }

  /**
   * 发送消息
   */
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
      return true
    }
    return false
  }

  /**
   * 订阅事件
   */
  subscribe(events) {
    return this._sendMessage({
      type: 'subscribe',
      events: events
    })
  }

  /**
   * 发送消息
   */
  _sendMessage(data) {
    return this.send(data)
  }

  /**
   * 处理收到的消息
   */
  _handleMessage(event) {
    try {
      const data = normalizeWebSocketMessage(JSON.parse(event.data))
      if (!data) return
      const type = data.type || data.event

      // 触发对应的监听器
      this._emit(type, data)

      // 触发 'all' 监听器
      if (this.listeners.has('all')) {
        this.listeners.get('all').forEach(callback => callback(data))
      }
    } catch (error) {
      // Silently ignore malformed messages
    }
  }

  _emit(type, data) {
    this.listeners.get(type)?.forEach(callback => callback(data))
  }

  _clearReconnect() {
    clearTimeout(this.reconnectTimer)
    this.reconnectTimer = null
  }

  _clearConnectionTimeout() {
    clearTimeout(this.connectionTimer)
    this.connectionTimer = null
  }

  /**
   * 添加事件监听器
   * @param {string} event - 事件类型
   * @param {Function} callback - 回调函数
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  /**
   * 移除事件监听器
   * @param {string} event - 事件类型
   * @param {Function} callback - 回调函数
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  /**
   * 移除所有事件监听器
   */
  offAll() {
    this.listeners.clear()
  }

  /**
   * 处理重连
   */
  _handleReconnect() {
    if (this.intentionallyClosed) return
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
      
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null
        if (!this.intentionallyClosed && !this.isConnected && this.connectionPath) {
          this.connect(this.connectionPath, this.connectionParams).catch(() => {
            // Reconnect error already handled by onclose -> _handleReconnect
          })
        }
      }, delay)
    } else {
      useAppStore().error('WebSocket 连接失败，请刷新页面重试')
    }
  }

  /**
   * 启动心跳
   */
  _startHeartbeat() {
    this._stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: 'ping' })
      }
    }, this.heartbeatInterval)
  }

  /**
   * 停止心跳
   */
  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.intentionallyClosed = true
    this._clearReconnect()
    this._clearConnectionTimeout()
    this.rejectPendingConnection?.(new Error('WebSocket 连接已关闭'))
    this._stopHeartbeat()
    this.reconnectAttempts = this.maxReconnectAttempts // 防止重连
    if (this.ws) {
      const socket = this.ws
      this.ws = null
      socket.onopen = null
      socket.onmessage = null
      socket.onerror = null
      socket.onclose = null
      socket.close()
    }
    this.isConnected = false
    this.offAll()
  }
}

// 执行状态 WebSocket
class ExecutionWebSocket extends WebSocketService {
  constructor(executionId) {
    super()
    this.executionId = executionId
  }

  /**
   * 连接执行状态 WebSocket
   */
  async connect() {
    const wsUrl = `/ws/execution/${this.executionId}/`
    return super.connect(wsUrl, {
      executionId: this.executionId,
      events: Object.values(WebSocketEvents)
    })
  }

  /**
   * 取消执行
   */
  cancel() {
    return this.send({ type: 'cancel' })
  }

  /**
   * 暂停执行
   */
  pause() {
    return this.send({ type: 'pause' })
  }

  /**
   * 恢复执行
   */
  resume() {
    return this.send({ type: 'resume' })
  }

  /**
   * 获取状态
   */
  getStatus() {
    return this.send({ type: 'get_status' })
  }
}

// 工作流协作 WebSocket
class WorkflowWebSocket extends WebSocketService {
  constructor(workflowId) {
    super()
    this.workflowId = workflowId
  }

  /**
   * 连接工作流协作 WebSocket
   */
  async connect() {
    const wsUrl = `/ws/workflow/${this.workflowId}/`
    return super.connect(wsUrl, {
      workflowId: this.workflowId,
      events: ['workflow_update', 'node_update', 'node_position_update', 'workflow_saved', 'user_cursor']
    })
  }

  /**
   * 发送节点拖拽更新
   */
  sendNodeDrag(nodeId, position) {
    return this.send({
      type: 'node_drag',
      node_id: nodeId,
      position: position
    })
  }

  /**
   * 保存工作流
   */
  saveWorkflow() {
    return this.send({ type: 'save_workflow' })
  }

  /**
   * 发送光标位置
   */
  sendCursorPosition(position) {
    return this.send({
      type: 'cursor_position',
      position: position
    })
  }
}

// 导出单例
export const executionWs = new WebSocketService()
export const workflowWs = new WebSocketService()

// 导出类
export { WebSocketService, ExecutionWebSocket, WorkflowWebSocket }

export default WebSocketService
