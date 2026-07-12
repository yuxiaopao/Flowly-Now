/**
 * WebSocket 客户端封装
 * 用于工作流执行、Agent 对话等实时通信
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { getWebSocketUrl as buildWebSocketUrl } from '@/config'

function resolveWebSocketUrl(target) {
  if (!target) return buildWebSocketUrl('/')
  if (target.startsWith('ws://') || target.startsWith('wss://')) return target
  return buildWebSocketUrl(target.startsWith('/') ? target : `/${target}`)
}

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
  let activeUrl = url ? resolveWebSocketUrl(url) : null
  let activeHandlers = { onMessage, onOpen, onClose, onError }

  function connect(overrideUrl, handlerOverrides = {}) {
    if (overrideUrl) {
      activeUrl = resolveWebSocketUrl(overrideUrl)
    } else if (!activeUrl && url) {
      activeUrl = resolveWebSocketUrl(url)
    }

    if (handlerOverrides && typeof handlerOverrides === 'object') {
      activeHandlers = {
        onMessage: handlerOverrides.onMessage || onMessage,
        onOpen: handlerOverrides.onOpen || onOpen,
        onClose: handlerOverrides.onClose || onClose,
        onError: handlerOverrides.onError || onError
      }
    }

    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      return
    }

    isConnecting.value = true

    try {
      ws.value = new WebSocket(activeUrl || buildWebSocketUrl('/'))

      ws.value.onopen = (event) => {
        isConnected.value = true
        isConnecting.value = false
        reconnectAttempts.value = 0

        startHeartbeat()

        activeHandlers.onOpen?.(event)
      }

      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastMessage.value = data
          activeHandlers.onMessage?.(data)
        } catch {
          activeHandlers.onMessage?.(event.data)
        }
      }

      ws.value.onclose = (event) => {
        isConnected.value = false
        isConnecting.value = false
        stopHeartbeat()

        activeHandlers.onClose?.(event)

        if (reconnectAttempts.value < maxReconnectAttempts) {
          scheduleReconnect()
        }
      }

      ws.value.onerror = (error) => {
        activeHandlers.onError?.(error)
      }
    } catch (error) {
      isConnecting.value = false
      activeHandlers.onError?.(error)
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
