/**
 * Vue composable for WebSocket-based training progress streaming.
 * 
 * @example
 * ```javascript
 * import { useTrainingWebSocket } from '@/composables/useTrainingWebSocket'
 * 
 * const {
 *   isConnected,
 *   progress,
 *   currentEpoch,
 *   totalEpochs,
 *   metrics,
 *   error,
 *   isComplete,
 *   connect,
 *   disconnect,
 * } = useTrainingWebSocket('train_abc123')
 * 
 * // Connect to WebSocket
 * connect()
 * ```
 */
import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

export function useTrainingWebSocket(jobId) {
  const isConnected = ref(false)
  const lastEvent = ref(null)
  const progress = ref(0)
  const currentEpoch = ref(0)
  const totalEpochs = ref(0)
  const metrics = ref(null)
  const error = ref(null)
  const isComplete = ref(false)
  const isCancelled = ref(false)
  const trainingHistory = ref([])
  const modelPath = ref(null)
  const totalTime = ref(0)

  let ws = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 5
  let reconnectTimer = null

  /**
   * Get the WebSocket URL for the training job
   */
  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_WS_URL || window.location.host
    return `${protocol}//${host}/ws/training/${jobId}/`
  }

  /**
   * Connect to the training WebSocket
   */
  const connect = () => {
    // Clear any existing reconnect timer
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    // Close existing connection
    if (ws) {
      ws.close()
      ws = null
    }

    try {
      ws = new WebSocket(getWebSocketUrl())

      ws.onopen = () => {
        isConnected.value = true
        reconnectAttempts = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastEvent.value = data

          switch (data.type) {
            case 'connected':
              // Connection established
              break

            case 'training_started':
              // Training has started
              progress.value = 0
              error.value = null
              isComplete.value = false
              isCancelled.value = false
              break

            case 'epoch_start':
              currentEpoch.value = data.epoch
              totalEpochs.value = data.total_epochs
              progress.value = data.progress || 0
              break

            case 'epoch_complete':
              currentEpoch.value = data.epoch
              progress.value = data.progress || 0
              metrics.value = data.metrics
              if (data.metrics) {
                trainingHistory.value.push(data.metrics)
              }
              break

            case 'training_complete':
              progress.value = 100
              isComplete.value = true
              modelPath.value = data.model_path
              totalTime.value = data.total_time
              if (data.training_history) {
                trainingHistory.value = data.training_history
              }
              ElMessage.success('训练完成！')
              break

            case 'training_error':
              error.value = data.error
              isComplete.value = false
              ElMessage.error(`训练错误: ${data.error}`)
              break

            case 'training_cancelled':
              isCancelled.value = true
              isComplete.value = false
              ElMessage.warning('训练已取消')
              break

            case 'pong':
              // Keep-alive response
              break

            case 'info':
              // Informational message
              break

            default:
              console.debug('Unknown training event type:', data.type)
          }
        } catch (e) {
          console.warn('Failed to parse training WebSocket message:', e, event.data)
        }
      }

      ws.onerror = (e) => {
        console.error('Training WebSocket error:', e)
        error.value = 'WebSocket连接错误'
      }

      ws.onclose = (event) => {
        isConnected.value = false
        
        // Don't reconnect if training is complete or cancelled
        if (isComplete.value || isCancelled.value || error.value) {
          return
        }

        // Attempt reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++
          const delay = Math.min(2000 * reconnectAttempts, 10000) // Cap at 10 seconds
          reconnectTimer = setTimeout(() => {
            if (!isComplete.value && !isCancelled.value && !error.value) {
              connect()
            }
          }, delay)
        } else {
          error.value = '连接断开，无法重连'
        }
      }
    } catch (e) {
      console.error('Failed to create WebSocket connection:', e)
      error.value = `创建连接失败: ${e.message}`
    }
  }

  /**
   * Disconnect from the training WebSocket
   */
  const disconnect = () => {
    reconnectAttempts = maxReconnectAttempts // Prevent reconnection
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    isConnected.value = false
  }

  /**
   * Send a ping to keep the connection alive
   */
  const sendPing = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }

  /**
   * Request current status
   */
  const sendStatusRequest = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'status' }))
    }
  }

  // Clean up on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    // State
    isConnected,
    lastEvent,
    progress,
    currentEpoch,
    totalEpochs,
    metrics,
    error,
    isComplete,
    isCancelled,
    trainingHistory,
    modelPath,
    totalTime,

    // Methods
    connect,
    disconnect,
    sendPing,
    sendStatusRequest,
  }
}

/**
 * Composable for managing multiple training jobs
 */
export function useTrainingJobs() {
  const jobs = ref(new Map())
  const activeJobs = ref([])

  /**
   * Subscribe to a training job's progress
   * @param {string} jobId - The training job ID
   * @returns {object} - The composable state for this job
   */
  const subscribe = (jobId) => {
    if (jobs.value.has(jobId)) {
      return jobs.value.get(jobId)
    }

    const training = useTrainingWebSocket(jobId)
    jobs.value.set(jobId, training)
    training.connect()

    return training
  }

  /**
   * Unsubscribe from a training job
   * @param {string} jobId - The training job ID
   */
  const unsubscribe = (jobId) => {
    const training = jobs.value.get(jobId)
    if (training) {
      training.disconnect()
      jobs.value.delete(jobId)
    }
  }

  /**
   * Get the composable for a specific job
   * @param {string} jobId - The training job ID
   */
  const getJob = (jobId) => {
    return jobs.value.get(jobId)
  }

  // Clean up on unmount
  onUnmounted(() => {
    jobs.value.forEach((training) => {
      training.disconnect()
    })
    jobs.value.clear()
  })

  return {
    jobs,
    subscribe,
    unsubscribe,
    getJob,
  }
}

export default useTrainingWebSocket
