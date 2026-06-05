/**
 * Agent Composable
 * 提供 Agent 相关的逻辑
 */

import { ref, computed } from 'vue'
import { agentApi } from '@/api/agent'
import { useAgentStore } from '@/stores/agent'

const DEFAULT_MESSAGE_TIMESTAMP = () => new Date().toISOString()

export function useAgent(options = {}) {
  const agentStore = useAgentStore()

  // Agent 状态
  const currentAgent = ref(null)
  const isLoading = ref(false)
  const isExecuting = ref(false)
  const error = ref(null)

  // 对话状态
  const messages = ref([])
  const streamingContent = ref('')
  const isStreaming = ref(false)

  // 计算属性
  const agents = computed(() => agentStore.agents)
  const availableTools = computed(() => [])

  // ==================== Agent CRUD ====================

  /**
   * 获取 Agent 列表
   */
  async function fetchAgents(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await agentApi.getList(params)
      agentStore.agents = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 获取单个 Agent
   */
  async function fetchAgent(id) {
    isLoading.value = true
    error.value = null
    try {
      const response = await agentApi.getById(id)
      currentAgent.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 创建 Agent
   */
  async function createAgent(data) {
    isLoading.value = true
    error.value = null
    try {
      const response = await agentApi.create(data)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 更新 Agent
   */
  async function updateAgent(id, data) {
    isLoading.value = true
    error.value = null
    try {
      const response = await agentApi.update(id, data)
      if (currentAgent.value?.id === id) {
        currentAgent.value = response
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 删除 Agent
   */
  async function deleteAgent(id) {
    isLoading.value = true
    error.value = null
    try {
      await agentApi.delete(id)
      return true
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // ==================== 工具管理 ====================

  /**
   * 获取可用工具列表
   */
  async function fetchAvailableTools(agentId) {
    try {
      const response = await agentApi.getAvailableTools(agentId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ==================== 对话执行 ====================

  /**
   * 发送消息（普通请求）
   */
  async function sendMessage(content, context = {}) {
    if (!content?.trim()) {
      error.value = 'Message content is required'
      throw new Error('Message content is required')
    }

    isExecuting.value = true
    error.value = null

    const timestamp = DEFAULT_MESSAGE_TIMESTAMP()
    const userMessageId = `msg_${Date.now()}`
    messages.value.push({
      id: userMessageId,
      role: 'user',
      content,
      timestamp
    })

    try {
      const response = await agentApi.debug(currentAgent.value?.id, {
        message: content,
        context
      })

      messages.value.push({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: response.response || response.message || '',
        timestamp: DEFAULT_MESSAGE_TIMESTAMP(),
        metadata: {
          execution_id: response.execution_id,
          tool_calls: response.tool_calls,
          ...response.metadata
        }
      })

      return response
    } catch (err) {
      error.value = err.message
      messages.value.push({
        id: `msg_${Date.now()}`,
        role: 'error',
        content: err.message || '执行失败，请重试',
        timestamp: DEFAULT_MESSAGE_TIMESTAMP()
      })
      throw err
    } finally {
      isExecuting.value = false
    }
  }

  /**
   * 流式发送消息
   */
  async function sendMessageStream(content, context = {}, onChunk, onComplete, onError) {
    if (!content?.trim()) {
      appStore.warning('请输入消息内容')
      return
    }

    isExecuting.value = true
    isStreaming.value = true
    error.value = null
    streamingContent.value = ''

    // 添加用户消息
    const userMessageId = `msg_${Date.now()}`
    messages.value.push({
      id: userMessageId,
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    })

    // 创建助手消息占位
    const assistantMessageId = `msg_${Date.now() + 1}`
    const assistantMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString()
    }
    messages.value.push(assistantMessage)

    try {
      // Use config-based URL for stream request
      const baseUrl = APP_CONFIG.apiBaseUrl
      const apiPrefix = APP_CONFIG.apiPrefix
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${baseUrl}${apiPrefix}/agents/${currentAgent.value?.id}/stream_chat/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            message: content,
            context
          })
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        streamingContent.value += chunk
        assistantMessage.content = streamingContent.value

        // Parse SSE lines from accumulated content
        const lines = streamingContent.value.split('\n')
        let lastCompleteIndex = -1

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i]
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'content' && data.content) {
                assistantMessage.content = data.content
                streamingContent.value = data.content
              } else if (data.type === 'done') {
                assistantMessage.isStreaming = false
              } else if (data.type === 'error') {
                assistantMessage.content = `错误: ${data.error}`
                assistantMessage.isStreaming = false
                isStreaming.value = false
              }
              lastCompleteIndex = i
            } catch (e) {
              // JSON parsing failed, this line might be incomplete
            }
          }
        }

        // Keep only unprocessed content
        if (lastCompleteIndex >= 0) {
          streamingContent.value = lines.slice(lastCompleteIndex + 1).join('\n')
          assistantMessage.content = streamingContent.value
        }

        if (onChunk) {
          onChunk(chunk, streamingContent.value)
        }
      }

      if (onComplete) {
        onComplete(streamingContent.value)
      }

      return streamingContent.value
    } catch (err) {
      error.value = err.message
      assistantMessage.content = '流式响应出错，请重试'
      assistantMessage.isError = true

      if (onError) {
        onError(err)
      }
      throw err
    } finally {
      isExecuting.value = false
      isStreaming.value = false
      // Ensure reader is cancelled to free resources
      reader?.cancel().catch(() => {})
    }
  }

  /**
   * 清空对话历史
   */
  function clearMessages() {
    messages.value = []
    streamingContent.value = ''
  }

  /**
   * 删除单条消息
   */
  function deleteMessage(messageId) {
    const index = messages.value.findIndex(m => m.id === messageId)
    if (index > -1) {
      messages.value.splice(index, 1)
    }
  }

  // ==================== 调试 ====================

  /**
   * 获取 Agent 执行历史
   */
  async function fetchExecutionHistory(agentId, params = {}) {
    try {
      const response = await agentApi.getExecutionHistory(agentId, params)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  /**
   * 获取单次执行详情
   */
  async function fetchExecutionDetail(executionId) {
    try {
      const response = await agentApi.getExecutionDetail(executionId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    // 状态
    currentAgent,
    isLoading,
    isExecuting,
    isStreaming,
    error,
    messages,
    streamingContent,

    // 计算属性
    agents,
    availableTools,

    // Agent CRUD
    fetchAgents,
    fetchAgent,
    createAgent,
    updateAgent,
    deleteAgent,

    // 工具
    fetchAvailableTools,

    // 对话
    sendMessage,
    sendMessageStream,
    clearMessages,
    deleteMessage,

    // 调试
    fetchExecutionHistory,
    fetchExecutionDetail
  }
}

export default useAgent
