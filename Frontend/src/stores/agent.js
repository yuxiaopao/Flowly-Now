import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentApi } from '@/api/agent'

export const useAgentStore = defineStore('agent', () => {
  // State
  const agents = ref([])
  const currentAgent = ref(null)
  const listPagination = ref({
    count: 0,
    totalPages: 1,
    currentPage: 1,
    pageSize: 20,
    next: null,
    previous: null
  })
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref(null)

  // Debug state
  const debugSessions = ref([])
  const currentDebugSession = ref(null)
  const debugMessages = ref([])
  const streamingContent = ref('')
  const isStreaming = ref(false)

  // Conversation state
  const conversations = ref([])
  const currentConversation = ref(null)

  // Message limit to prevent memory leak
  const MAX_MESSAGES = 100

  // Getters
  const activeAgents = computed(() => agents.value.filter(a => a.is_active))

  // Helper to parse SSE line
  function parseSSELine(line) {
    if (line.startsWith('data: ')) {
      try {
        return JSON.parse(line.slice(6))
      } catch {
        return null
      }
    }
    return null
  }

  // Actions
  async function fetchAgents(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await agentApi.getList(params)
      agents.value = response.results || response
      listPagination.value = {
        count: response.count ?? agents.value.length,
        totalPages: response.totalPages ?? response.total_pages ?? Math.max(1, Math.ceil((response.count ?? agents.value.length) / (params.page_size || params.pageSize || 20))),
        currentPage: response.currentPage ?? response.current_page ?? params.page ?? 1,
        pageSize: response.pageSize ?? response.page_size ?? params.page_size ?? params.pageSize ?? agents.value.length,
        next: response.next ?? null,
        previous: response.previous ?? null
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

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

  async function createAgent(data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await agentApi.create(data)
      agents.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateAgent(id, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await agentApi.update(id, data)
      const index = agents.value.findIndex(a => a.id === id)
      if (index !== -1) {
        agents.value[index] = { ...agents.value[index], ...response }
      }
      if (currentAgent.value?.id === id) {
        currentAgent.value = { ...currentAgent.value, ...response }
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteAgent(id) {
    isLoading.value = true
    error.value = null
    try {
      await agentApi.delete(id)
      agents.value = agents.value.filter(a => a.id !== id)
      if (currentAgent.value?.id === id) {
        currentAgent.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // ==================== Reset Memory ====================

  async function resetMemory(agentId) {
    isLoading.value = true
    error.value = null
    try {
      await agentApi.resetMemory(agentId)
      return { success: true }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Debug actions
  async function startDebugSession(agentId, params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await agentApi.debug(agentId, params)
      currentDebugSession.value = {
        ...response,
        session_id: response.execution_id
      }
      debugMessages.value = [
        { role: 'user', content: params.message, timestamp: new Date().toISOString() },
        { role: 'assistant', content: response.response || response.message, timestamp: new Date().toISOString() }
      ]
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function sendDebugMessage(agentId, message) {
    // Add user message
    debugMessages.value.push({ role: 'user', content: message, timestamp: new Date().toISOString() })
    // Trim messages to prevent memory leak
    if (debugMessages.value.length > MAX_MESSAGES) {
      debugMessages.value = debugMessages.value.slice(-MAX_MESSAGES)
    }

    try {
      const response = await agentApi.debug(agentId, {
        message,
        conversation_id: currentDebugSession.value?.conversation_id
      })

      debugMessages.value.push({
        role: 'assistant',
        content: response.response || response.message,
        timestamp: new Date().toISOString(),
        toolCalls: response.tool_calls || null
      })

      if (response.execution_id) {
        currentDebugSession.value = {
          ...currentDebugSession.value,
          session_id: response.execution_id
        }
      }

      return response
    } catch (err) {
      debugMessages.value.push({
        role: 'error',
        content: err.message,
        timestamp: new Date().toISOString()
      })
      throw err
    }
  }

  // 流式对话
  async function streamChatMessage(agentId, message) {
    // Add user message
    debugMessages.value.push({ role: 'user', content: message, timestamp: new Date().toISOString() })
    // Trim messages to prevent memory leak
    if (debugMessages.value.length > MAX_MESSAGES) {
      debugMessages.value = debugMessages.value.slice(-MAX_MESSAGES)
    }

    // Add placeholder for streaming response
    const assistantMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true
    }
    debugMessages.value.push(assistantMessage)

    isStreaming.value = true
    streamingContent.value = ''

    try {
      const response = await agentApi.streamChat(agentId, {
        message,
        conversation_id: currentDebugSession.value?.conversation_id
      })

      // Process SSE stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      // eslint-disable-next-line no-constant-condition -- SSE stream read loop
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          const data = parseSSELine(line)
          if (data) {
            if (data.type === 'content' && data.content) {
              streamingContent.value += data.content
              assistantMessage.content = streamingContent.value
              const msgIndex = debugMessages.value.findIndex(m => m === assistantMessage)
              if (msgIndex !== -1) {
                debugMessages.value[msgIndex] = { ...assistantMessage }
              }
            } else if (data.type === 'done') {
              assistantMessage.isStreaming = false
              assistantMessage.toolCalls = data.tool_calls || null
              const msgIndex = debugMessages.value.findIndex(m => m === assistantMessage)
              if (msgIndex !== -1) {
                debugMessages.value[msgIndex] = { ...assistantMessage }
              }
              currentDebugSession.value = {
                ...currentDebugSession.value,
                conversation_id: data.conversation_id
              }
            }
          }
        }
      }

      return { success: true }
    } catch (err) {
      assistantMessage.content = `错误: ${err.message}`
      assistantMessage.isStreaming = false
      throw err
    } finally {
      isStreaming.value = false
      streamingContent.value = ''
    }
  }

  async function fetchDebugHistory(agentId) {
    try {
      const response = await agentApi.getDebugHistory(agentId)
      debugSessions.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
    }
  }

  async function loadDebugSession(agentId, sessionId) {
    isLoading.value = true
    error.value = null
    try {
      const response = await agentApi.loadDebugSession(agentId, sessionId)
      currentDebugSession.value = {
        ...response,
        session_id: response.id || sessionId
      }

      // Load messages into debugMessages
      debugMessages.value = response.messages || []

      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function clearDebugHistory(agentId) {
    try {
      await agentApi.clearDebugHistory(agentId)
      debugSessions.value = []
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Conversation actions
  async function fetchConversations(agentId) {
    try {
      const response = await agentApi.getConversations(agentId)
      conversations.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
    }
  }

  function selectConversation(conversation) {
    currentConversation.value = conversation
  }

  function clearDebugSession() {
    currentDebugSession.value = null
    debugMessages.value = []
    streamingContent.value = ''
    isStreaming.value = false
  }

  // Clear store
  function clearStore() {
    agents.value = []
    currentAgent.value = null
    debugSessions.value = []
    currentDebugSession.value = null
    debugMessages.value = []
    conversations.value = []
    currentConversation.value = null
    error.value = null
    streamingContent.value = ''
    isStreaming.value = false
  }

  return {
    // State
    agents,
    currentAgent,
    listPagination,
    isLoading,
    isSaving,
    error,
    debugSessions,
    currentDebugSession,
    debugMessages,
    streamingContent,
    isStreaming,
    conversations,
    currentConversation,

    // Getters
    activeAgents,

    // Actions
    fetchAgents,
    fetchAgent,
    createAgent,
    updateAgent,
    deleteAgent,
    resetMemory,
    startDebugSession,
    sendDebugMessage,
    streamChatMessage,
    fetchDebugHistory,
    loadDebugSession,
    clearDebugHistory,
    fetchConversations,
    selectConversation,
    clearDebugSession,
    clearStore
  }
})
