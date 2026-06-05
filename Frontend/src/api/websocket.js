/**
 * WebSocket 服务 - 工作流执行实时通信
 */

import Cookies from 'js-cookie'
import { useAppStore } from '@/stores/app'

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
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.listeners = new Map()
    this.isConnected = false
    this.heartbeatTimer = null
    this.heartbeatInterval = 30000
    this.appStore = useAppStore()
  }

  /**
   * 连接 WebSocket
   * @param {string} url - WebSocket URL
   * @param {Object} params - 连接参数
   */
  connect(url, params = {}) {
    return new Promise((resolve, reject) => {
      const token = Cookies.get('access_token') || localStorage.getItem('access_token')
      
      // 构建 WebSocket URL
      const wsUrl = this._buildUrl(url, params, token)
      this.url = wsUrl

      try {
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          this.isConnected = true
          this.reconnectAttempts = 0
          this._startHeartbeat()
          this._sendMessage({ type: 'subscribe', events: params.events || ['all'] })
          resolve()
        }

        this.ws.onmessage = (event) => {
          this._handleMessage(event)
        }

        this.ws.onerror = () => {
          this.isConnected = false
        }

        this.ws.onclose = () => {
          this.isConnected = false
          this._stopHeartbeat()
          this._handleReconnect()
        }

      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * 构建 WebSocket URL
   */
  _buildUrl(url, params, token) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = import.meta.env.VITE_WS_URL || window.location.host
    
    let wsUrl = `${protocol}//${wsHost}${url}`
    
    // 添加查询参数
    const queryParams = new URLSearchParams()
    if (token) queryParams.set('token', token)
    if (params.executionId) queryParams.set('execution_id', params.executionId)
    if (params.workflowId) queryParams.set('workflow_id', params.workflowId)
    
    const queryString = queryParams.toString()
    if (queryString) {
      wsUrl += `?${queryString}`
    }
    
    return wsUrl
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
      const data = JSON.parse(event.data)
      const type = data.type || data.event

      // 触发对应的监听器
      if (this.listeners.has(type)) {
        this.listeners.get(type).forEach(callback => callback(data))
      }

      // 触发 'all' 监听器
      if (this.listeners.has('all')) {
        this.listeners.get('all').forEach(callback => callback(data))
      }
    } catch (error) {
      // Silently ignore malformed messages
    }
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
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
      
      setTimeout(() => {
        if (!this.isConnected && this.url) {
          this.connect(this.url).catch(() => {
            // Reconnect error already handled by onclose -> _handleReconnect
          })
        }
      }, delay)
    } else {
      this.appStore.error('WebSocket 连接失败，请刷新页面重试')
    }
  }

  /**
   * 启动心跳
   */
  _startHeartbeat() {
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
    this._stopHeartbeat()
    this.reconnectAttempts = this.maxReconnectAttempts // 防止重连
    if (this.ws) {
      this.ws.close()
      this.ws = null
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
