import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentApi } from '@/api/agent'
import { readJsonSse } from '@/utils/jsonSse'

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
  let debugRevision = 0
  let streamController = null
  let agentRevision = 0
  let historyRevision = 0

  // Conversation state
  const conversations = ref([])
  const currentConversation = ref(null)

  // Message limit to prevent memory leak
  const MAX_MESSAGES = 100

  // Getters
  const activeAgents = computed(() => agents.value.filter(a => a.isActive ?? a.is_active))

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
    const revision = ++agentRevision
    currentAgent.value = null
    isLoading.value = true
    error.value = null
    try {
      const response = await agentApi.getById(id)
      if (revision !== agentRevision) return response
      currentAgent.value = response
      return response
    } catch (err) {
      if (revision !== agentRevision) return undefined
      error.value = err.message
      throw err
    } finally {
      if (revision === agentRevision) isLoading.value = false
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
        session_id: response.executionId ?? response.execution_id,
        usage: response.usage ?? null,
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
    if (isStreaming.value || isLoading.value) throw new Error('请等待当前请求完成')
    const revision = ++debugRevision
    isLoading.value = true
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

      if (revision !== debugRevision) return { cancelled: true }

      debugMessages.value.push({
        role: 'assistant',
        content: response.response || response.message,
        timestamp: new Date().toISOString(),
        toolCalls: response.toolCalls ?? response.tool_calls ?? null
      })

      if (response.executionId || response.execution_id) {
        currentDebugSession.value = {
          ...currentDebugSession.value,
          session_id: response.executionId ?? response.execution_id,
          usage: response.usage ?? null,
        }
      }

      return response
    } catch (err) {
      if (revision !== debugRevision) return { cancelled: true }
      debugMessages.value.push({
        role: 'error',
        content: err.message,
        timestamp: new Date().toISOString()
      })
      throw err
    } finally {
      if (revision === debugRevision) isLoading.value = false
    }
  }

  // 流式对话
  async function streamChatMessage(agentId, message) {
    if (isStreaming.value || isLoading.value) throw new Error('请等待当前请求完成')
    const revision = ++debugRevision
    const controller = new AbortController()
    streamController = controller
    debugMessages.value.push({ role: 'user', content: message, timestamp: new Date().toISOString() })
    if (debugMessages.value.length >= MAX_MESSAGES) debugMessages.value = debugMessages.value.slice(-(MAX_MESSAGES - 1))
    debugMessages.value.push({ role: 'assistant', content: '', timestamp: new Date().toISOString(), isStreaming: true })
    const messageIndex = debugMessages.value.length - 1
    isStreaming.value = true
    streamingContent.value = ''
    let completed = false
    try {
      const response = await agentApi.streamChat(agentId, {
        message, conversation_id: currentDebugSession.value?.conversation_id,
      }, { signal: controller.signal })
      for await (const data of readJsonSse(response)) {
        if (revision !== debugRevision) return { cancelled: true }
        if (data.type === 'error') throw new Error(data.error || '模型响应失败')
        if (data.type === 'content' && typeof data.content === 'string') {
          streamingContent.value += data.content
          debugMessages.value[messageIndex] = { ...debugMessages.value[messageIndex], content: streamingContent.value }
        } else if (data.type === 'done') {
          completed = true
          debugMessages.value[messageIndex] = { ...debugMessages.value[messageIndex], isStreaming: false, toolCalls: data.tool_calls ?? data.toolCalls ?? null }
          currentDebugSession.value = { ...currentDebugSession.value,
            conversation_id: data.conversation_id ?? data.conversationId ?? currentDebugSession.value?.conversation_id,
            usage: data.usage ?? null,
          }
          break
        }
      }
      if (revision !== debugRevision) return { cancelled: true }
      if (!completed) throw new Error('响应连接提前关闭，请检查本轮结果后重试')
      return { success: true }
    } catch (err) {
      if (revision !== debugRevision) return { cancelled: true }
      error.value = err.message
      debugMessages.value[messageIndex] = { ...debugMessages.value[messageIndex], isStreaming: false, role: 'error', content: err.message }
      throw err
    } finally {
      if (revision === debugRevision) {
        isStreaming.value = false
        streamingContent.value = ''
        streamController = null
      }
    }
  }

  async function fetchDebugHistory(agentId) {
    const revision = ++historyRevision
    debugSessions.value = []
    try {
      const response = await agentApi.getDebugHistory(agentId)
      if (revision !== historyRevision) return response
      debugSessions.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
    }
  }

  async function loadDebugSession(agentId, sessionId) {
    clearDebugSession()
    const revision = debugRevision
    isLoading.value = true
    error.value = null
    try {
      const response = await agentApi.loadDebugSession(agentId, sessionId)
      if (revision !== debugRevision) return { cancelled: true }
      currentDebugSession.value = {
        ...response,
        conversation_id: response.conversationId ?? response.conversation_id,
        session_id: response.id || sessionId
      }

      // Load messages into debugMessages
      debugMessages.value = response.messages || []

      return response
    } catch (err) {
      if (revision !== debugRevision) return { cancelled: true }
      error.value = err.message
      throw err
    } finally {
      if (revision === debugRevision) isLoading.value = false
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
    debugRevision++
    streamController?.abort()
    streamController = null
    currentDebugSession.value = null
    debugMessages.value = []
    streamingContent.value = ''
    isStreaming.value = false
    isLoading.value = false
  }

  // Clear store
  function clearStore() {
    agentRevision++
    historyRevision++
    clearDebugSession()
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
