/**
 * WebSocket 客户端封装
 * 用于工作流执行、Agent 对话等实时通信
 */

import { ref, onMounted, onUnmounted } from 'vue'

export function useWebSocket(options = {}) {
  const {
    url,
    autoConnect = false,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    heartbeatInterval = 30000,
    onMessage,
    onOpen,
    onClose,
    onError
  } = options

  const ws = ref(null)
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const reconnectAttempts = ref(0)
  const lastMessage = ref(null)

  let reconnectTimer = null
  let heartbeatTimer = null

  function getWebSocketUrl() {
    if (url) return url

    // 根据当前页面协议自动判断
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}`
  }

  function connect() {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      return
    }

    isConnecting.value = true

    try {
      ws.value = new WebSocket(getWebSocketUrl())

      ws.value.onopen = (event) => {
        isConnected.value = true
        isConnecting.value = false
        reconnectAttempts.value = 0

        // 启动心跳
        startHeartbeat()

        if (onOpen) {
          onOpen(event)
        }
      }

      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastMessage.value = data

          if (onMessage) {
            onMessage(data)
          }
        } catch (e) {
          // 非 JSON 消息
          if (onMessage) {
            onMessage(event.data)
          }
        }
      }

      ws.value.onclose = (event) => {
        isConnected.value = false
        isConnecting.value = false
        stopHeartbeat()

        if (onClose) {
          onClose(event)
        }

        // 自动重连
        if (reconnectAttempts.value < maxReconnectAttempts) {
          scheduleReconnect()
        }
      }

      ws.value.onerror = (error) => {
        if (onError) {
          onError(error)
        }
      }
    } catch (error) {
      isConnecting.value = false
      if (onError) {
        onError(error)
      }
    }
  }

  function disconnect() {
    stopHeartbeat()
    clearReconnect()

    if (ws.value) {
      ws.value.close()
      ws.value = null
    }

    isConnected.value = false
    isConnecting.value = false
  }

  function send(data) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      const message = typeof data === 'string' ? data : JSON.stringify(data)
      ws.value.send(message)
      return true
    }
    return false
  }

  function sendPing() {
    send({ type: 'ping' })
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = setInterval(() => {
      sendPing()
    }, heartbeatInterval)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  function scheduleReconnect() {
    clearReconnect()
    reconnectTimer = setTimeout(() => {
      reconnectAttempts.value++
      connect()
    }, reconnectInterval)
  }

  function clearReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  onMounted(() => {
    if (autoConnect) {
      connect()
    }
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    isConnected,
    isConnecting,
    reconnectAttempts,
    lastMessage,
    connect,
    disconnect,
    send,
    sendPing
  }
}
