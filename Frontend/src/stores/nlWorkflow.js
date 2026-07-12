/**
 * NL Workflow Store - Natural Language to Workflow
 *
 * Manages NL-to-workflow conversation state.
 * Used by components that need centralized state management.
 */

import { defineStore } from 'pinia'
import { nlWorkflowApi } from '@/api/nl-workflow'

export const useNLWorkflowStore = defineStore('nlWorkflow', {
  state: () => ({
    // Current conversation
    messages: [],

    // Generation status
    isGenerating: false,
    generationError: null,
    streamingProgress: 0,
    streamingStage: '',
    isStreaming: false,

    // Generated workflow
    generatedWorkflow: null,

    // Intent analysis
    lastIntent: null,

    // History
    history: [],
    historyLoading: false,

    // Available models
    models: [],
    selectedModel: null,
    modelsLoading: false,

    // Current session
    currentSessionId: null,

    // Generation settings
    settings: {
      includeDescription: true,
      includeValidation: true,
      temperature: 0.7,
      maxTokens: 2048
    },

    // Editor assistant mode: chat | editor | generate
    assistantMode: 'editor',

    // Set when backend returns a workflow that should auto-apply to canvas
    pendingAutoApply: false
  }),

  getters: {
    // Get conversation history for API
    conversationHistory: (state) => {
      return state.messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }))
    },

    // Get last user message
    lastUserMessage: (state) => {
      const userMessages = state.messages.filter(m => m.role === 'user')
      return userMessages[userMessages.length - 1] || null
    },

    // Check if can continue
    canContinue: (state) => {
      return state.generatedWorkflow !== null && !state.isGenerating
    },

    // Get message count
    messageCount: (state) => state.messages.length,

    // Check if conversation is empty
    isEmpty: (state) => state.messages.length === 0,

    // Has active session
    hasSession: (state) => state.currentSessionId !== null
  },

  actions: {
    // ==================== Message Management ====================

    addMessage(role, content, metadata = {}) {
      this.messages.push({
        id: Date.now() + Math.random(),
        role,
        content,
        metadata,
        timestamp: new Date().toISOString()
      })
    },

    addUserMessage(content) {
      this.addMessage('user', content)
    },

    addAssistantMessage(content, metadata = {}) {
      this.addMessage('assistant', content, metadata)
    },

    addSystemMessage(content) {
      this.addMessage('system', content)
    },

    updateLastAssistantMessage(content, metadata = {}) {
      const lastAssistant = [...this.messages].reverse().find(m => m.role === 'assistant')
      if (lastAssistant) {
        lastAssistant.content = content
        if (metadata.suggestions) lastAssistant.suggestions = metadata.suggestions
        if (metadata.workflow) lastAssistant.workflow = metadata.workflow
        if (metadata.changes) lastAssistant.changes = metadata.changes
        if (metadata.nodeGuidance) lastAssistant.nodeGuidance = metadata.nodeGuidance
        if (metadata.emailGuidance) lastAssistant.emailGuidance = metadata.emailGuidance
        if (metadata.readyToGenerate !== undefined) lastAssistant.readyToGenerate = metadata.readyToGenerate
        if (metadata.autoApplied !== undefined) lastAssistant.autoApplied = metadata.autoApplied
        if (metadata.isStreaming !== undefined) lastAssistant.isStreaming = metadata.isStreaming
        if (metadata.error) lastAssistant.error = metadata.error
        lastAssistant.metadata = { ...lastAssistant.metadata, ...metadata }
      }
    },

    clearMessages() {
      this.messages = []
      this.generatedWorkflow = null
      this.generationError = null
    },

    // ==================== Model Management ====================

    async loadModels() {
      if (this.models.length > 0) return

      this.modelsLoading = true
      try {
        const response = await nlWorkflowApi.getModels()
        this.models = response.models || []

        if (response.default) {
          this.selectedModel = response.default
        } else if (this.models.length > 0) {
          this.selectedModel = this.models[0].model_id
        }
      } catch (error) {
        this.generationError = '加载模型列表失败'
      } finally {
        this.modelsLoading = false
      }
    },

    setAssistantMode(mode) {
      this.assistantMode = mode
    },

    resolveAssistantMode(hasCanvasWorkflow, explicitMode) {
      if (explicitMode) return explicitMode
      if (hasCanvasWorkflow) {
        if (this.assistantMode === 'chat') return 'chat'
        if (this.assistantMode === 'generate') return 'generate'
        return 'editor'
      }
      return this.assistantMode === 'generate' ? 'generate' : 'chat'
    },

    _handleStreamDone(data, fullContent) {
      if (data.workflow_json) {
        try {
          this.generatedWorkflow = JSON.parse(data.workflow_json)
        } catch {
          // ignore parse errors
        }
      }
      if (data.workflow) {
        this.generatedWorkflow = data.workflow
      }
      this.streamingProgress = 100
      const shouldAutoApply = Boolean(
        data.workflow?.nodes?.length
        && this.assistantMode === 'editor'
        && (data.intent === 'modify' || data.intent === 'delete' || data.changes?.length)
      )
      if (shouldAutoApply) {
        this.pendingAutoApply = true
      }
      this.updateLastAssistantMessage(
        data.message || fullContent || '我理解了，您还有其他需要调整的地方吗？',
        {
          workflow: this.generatedWorkflow,
          suggestions: data.suggestions || [],
          changes: data.changes || [],
          readyToGenerate: data.ready_to_generate || false,
          isStreaming: false,
          intent: data.intent,
          autoApplied: shouldAutoApply,
          nodeGuidance: data.node_guidance || data.nodeGuidance || null,
        }
      )
    },

    // ==================== Session Management ====================

    async createSession(description, name) {
      this.isGenerating = true
      this.generationError = null
      this.streamingProgress = 0
      this.streamingStage = ''

      try {
        const response = await nlWorkflowApi.createSession({
          description,
          name: name || `NL Workflow ${Date.now()}`,
          model: this.selectedModel,
          temperature: this.settings.temperature
        })

        // Handle both session_id and id field names
        this.currentSessionId = response.session_id || response.id

        if (response.error) {
          this.generationError = response.error
          this.updateLastAssistantMessage(`抱歉，生成工作流时遇到了问题：${response.error}`, { error: true })
          return response
        }

        // Handle both workflow_json and workflow field names
        const workflowData = response.workflow_json || response.workflow
        if (workflowData && Object.keys(workflowData).length > 0) {
          this.generatedWorkflow = workflowData
          this.updateLastAssistantMessage(
            response.message || '我已根据您的描述生成了工作流',
            { workflow: workflowData }
          )
        } else {
          this.updateLastAssistantMessage(response.message || '正在处理您的请求...')
        }

        return response
      } catch (error) {
        this.generationError = error.message
        this.updateLastAssistantMessage('抱歉，生成工作流时遇到了问题。请稍后重试。', { error: true })
        throw error
      } finally {
        this.isGenerating = false
      }
    },

    /**
     * Stream workflow generation with real-time updates
     * @param {string} description - Workflow description
     * @param {string} name - Optional session name
     * @returns {Promise} Resolves when streaming completes
     */
    async streamWorkflow(description, name, options = {}) {
      this.isGenerating = true
      this.isStreaming = true
      this.generationError = null
      this.streamingProgress = 0
      this.streamingStage = ''

      const { currentWorkflow, mode: explicitMode, ...streamOptions } = options
      const requestMode = this.resolveAssistantMode(Boolean(currentWorkflow?.nodes?.length), explicitMode)

      try {
        this.addAssistantMessage('', { isStreaming: true })

        const sessionName = name || `NL Workflow ${Date.now()}`
        
        // Use fetch API for SSE streaming with POST
        const response = await nlWorkflowApi.streamWorkflow({
          description,
          name: sessionName,
          model: this.selectedModel,
          temperature: this.settings.temperature,
          mode: requestMode,
          ...(currentWorkflow ? { workflow: currentWorkflow } : {}),
          ...streamOptions
        })

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let fullContent = ''
        let buffer = ''

        let readResult = await reader.read()
        while (!readResult.done) {
          const value = readResult.value

          const chunk = decoder.decode(value, { stream: true })
          buffer += chunk
          
          // Process complete SSE events
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                switch (data.type) {
                  case 'session':
                    this.currentSessionId = data.session_id
                    break
                    
                  case 'progress':
                  case 'step':
                    this.streamingProgress = data.progress || 0
                    this.streamingStage = data.stage || data.message || ''
                    this.updateLastAssistantMessage(data.message || '', { isStreaming: true })
                    break
                    
                  case 'token':
                    fullContent += data.content
                    this.updateLastAssistantMessage(fullContent, { isStreaming: true })
                    break
                    
                  case 'workflow':
                    this.generatedWorkflow = data.workflow
                    this.updateLastAssistantMessage(
                      data.message || '工作流生成完成！',
                      { workflow: data.workflow, isStreaming: false }
                    )
                    break

                  case 'node_guidance':
                    if (data.node_guidance) {
                      this.updateLastAssistantMessage(
                        this.messages[this.messages.length - 1]?.content || '',
                        { nodeGuidance: data.node_guidance }
                      )
                    }
                    break

                  case 'email_guidance':
                    if (data.email_guidance) {
                      this.updateLastAssistantMessage(
                        this.messages[this.messages.length - 1]?.content || '',
                        { emailGuidance: data.email_guidance }
                      )
                    }
                    break

                  case 'changes':
                    if (data.changes?.length) {
                      this.updateLastAssistantMessage(
                        this.messages[this.messages.length - 1]?.content || '',
                        { changes: data.changes }
                      )
                    }
                    break
                    
                  case 'ready_to_generate':
                    this.updateLastAssistantMessage(
                      this.messages[this.messages.length - 1]?.content || '',
                      { readyToGenerate: true }
                    )
                    break

                  case 'done':
                    this._handleStreamDone(data, fullContent)
                    break
                    
                  case 'error':
                    this.generationError = data.error
                    this.updateLastAssistantMessage(
                      `生成失败：${data.error}`,
                      { error: true, isStreaming: false }
                    )
                    return
                    
                  case 'intent':
                    this.lastIntent = data
                    this.updateLastAssistantMessage(fullContent, { 
                      isStreaming: true,
                      intent: data 
                    })
                    break
                }
              } catch (e) {
                // Skip malformed SSE data silently
              }
            }
          }

          readResult = await reader.read()
        }

      } catch (error) {
        this.generationError = error.message
        this.updateLastAssistantMessage(
          '抱歉，生成工作流时遇到了问题。请稍后重试。',
          { error: true, isStreaming: false }
        )
        throw error
      } finally {
        this.isGenerating = false
        this.isStreaming = false
        this.streamingProgress = 100
      }
    },

    async sendMessage(message) {
      if (!this.currentSessionId) {
        throw new Error('No active session')
      }

      this.isGenerating = true
      this.generationError = null

      try {
        this.addUserMessage(message)

        const response = await nlWorkflowApi.sendMessage(
          this.currentSessionId,
          message,
          { model: this.selectedModel, temperature: this.settings.temperature }
        )

        // Handle workflow updates
        const workflowData = response.workflow_json || response.workflow
        if (workflowData && Object.keys(workflowData).length > 0) {
          this.generatedWorkflow = workflowData
          this.updateLastAssistantMessage(response.message, { workflow: workflowData })
        } else {
          this.updateLastAssistantMessage(response.message || '我理解了，您还有其他需要调整的地方吗？')
        }

        return response
      } catch (error) {
        this.generationError = error.message
        this.updateLastAssistantMessage('抱歉，处理请求时遇到了问题。请稍后重试。', { error: true })
        throw error
      } finally {
        this.isGenerating = false
      }
    },

    /**
     * Stream message response with real-time token updates
     * @param {string} message - User message
     * @returns {Promise} Resolves when streaming completes
     */
    async streamSendMessage(message, options = {}) {
      if (!this.currentSessionId) {
        throw new Error('No active session')
      }

      this.isGenerating = true
      this.isStreaming = true
      this.generationError = null
      this.streamingProgress = 0
      this.streamingStage = '正在处理...'

      const { currentWorkflow, mode: explicitMode, ...streamOptions } = options
      const requestMode = this.resolveAssistantMode(Boolean(currentWorkflow?.nodes?.length), explicitMode)

      try {
        this.addAssistantMessage('', { isStreaming: true })

        const response = await nlWorkflowApi.streamMessage(
          this.currentSessionId,
          message,
          {
            model: this.selectedModel,
            temperature: this.settings.temperature,
            mode: requestMode,
            ...(currentWorkflow ? { workflow: currentWorkflow } : {}),
            ...streamOptions
          }
        )

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let fullContent = ''
        let buffer = ''

        let readResult = await reader.read()
        while (!readResult.done) {
          const value = readResult.value

          const chunk = decoder.decode(value, { stream: true })
          buffer += chunk

          // Process complete SSE events
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))

                switch (data.type) {
                  case 'progress':
                  case 'step':
                    this.streamingProgress = data.progress || 0
                    this.streamingStage = data.stage || data.message || ''
                    this.updateLastAssistantMessage(data.message || fullContent, { isStreaming: true })
                    break

                  case 'token':
                    fullContent += data.content
                    this.updateLastAssistantMessage(fullContent, { isStreaming: true })
                    break

                  case 'workflow':
                    this.generatedWorkflow = data.workflow
                    this.streamingProgress = 90
                    this.updateLastAssistantMessage(
                      data.message || '工作流已更新',
                      { workflow: data.workflow, isStreaming: false }
                    )
                    break

                  case 'node_guidance':
                    if (data.node_guidance) {
                      this.updateLastAssistantMessage(
                        this.messages[this.messages.length - 1]?.content || '',
                        { nodeGuidance: data.node_guidance }
                      )
                    }
                    break

                  case 'email_guidance':
                    if (data.email_guidance) {
                      this.updateLastAssistantMessage(
                        this.messages[this.messages.length - 1]?.content || '',
                        { emailGuidance: data.email_guidance }
                      )
                    }
                    break

                  case 'changes':
                    if (data.changes?.length) {
                      this.updateLastAssistantMessage(
                        this.messages[this.messages.length - 1]?.content || '',
                        { changes: data.changes }
                      )
                    }
                    break

                  case 'ready_to_generate':
                    this.updateLastAssistantMessage(
                      fullContent || this.messages[this.messages.length - 1]?.content || '',
                      { readyToGenerate: true, isStreaming: false }
                    )
                    break

                  case 'done':
                    this._handleStreamDone(data, fullContent)
                    break

                  case 'error':
                    this.generationError = data.error
                    this.updateLastAssistantMessage(
                      `处理失败：${data.error}`,
                      { error: true, isStreaming: false }
                    )
                    return

                  case 'suggestions':
                    this.updateLastAssistantMessage(fullContent, {
                      isStreaming: false,
                      suggestions: data.suggestions
                    })
                    break
                }
              } catch (e) {
                // Skip malformed SSE data silently
              }
            }
          }

          readResult = await reader.read()
        }

      } catch (error) {
        this.generationError = error.message
        this.updateLastAssistantMessage(
          '抱歉，处理请求时遇到了问题。请稍后重试。',
          { error: true, isStreaming: false }
        )
        throw error
      } finally {
        this.isGenerating = false
        this.isStreaming = false
        this.streamingProgress = 100
        this.streamingStage = ''
      }
    },

    /**
     * Analyze user message intent
     * @param {string} message - Message to analyze
     * @returns {Promise<Object>} Intent analysis result
     */
    async analyzeIntent(message) {
      try {
        const response = await nlWorkflowApi.analyzeIntent(message)
        this.lastIntent = response
        return response
      } catch (error) {
        return { intent: 'unknown', error: error.message }
      }
    },

    async getSuggestions(options = {}) {
      try {
        const response = await nlWorkflowApi.suggest(options)
        return response.suggestions || []
      } catch (error) {
        return []
      }
    },

    /**
     * Editor assistant: apply layout/modify synchronously (no SSE stream).
     * @param {string} message
     * @param {Object} options - { currentWorkflow, mode }
     */
    async applyEditorAction(message, options = {}) {
      const { currentWorkflow, mode: explicitMode, ...rest } = options
      if (!currentWorkflow?.nodes?.length) {
        throw new Error('Editor workflow context is required')
      }

      this.isGenerating = true
      this.generationError = null
      this.streamingProgress = 0
      this.streamingStage = '正在处理...'

      const requestMode = this.resolveAssistantMode(true, explicitMode)

      try {
        this.addAssistantMessage('', { isStreaming: true })

        const response = await nlWorkflowApi.applyEditorAction({
          message,
          workflow: currentWorkflow,
          mode: requestMode,
          model: this.selectedModel,
          temperature: this.settings.temperature,
          ...rest,
        })

        const payload = response?.data ?? response
        this._handleStreamDone(payload, payload?.message || '')
        return payload
      } catch (error) {
        this.generationError = error.message
        this.updateLastAssistantMessage(
          '抱歉，处理请求时遇到了问题。请稍后重试。',
          { error: true, isStreaming: false }
        )
        throw error
      } finally {
        this.isGenerating = false
        this.isStreaming = false
        this.streamingProgress = 100
        this.streamingStage = ''
      }
    },

    async confirmWorkflow() {
      if (!this.currentSessionId) {
        throw new Error('No active session to confirm')
      }

      const response = await nlWorkflowApi.confirmWorkflow(this.currentSessionId)

      const workflowId = response.workflow_id || response.id
      if (workflowId) {
        this.reset()
        return workflowId
      }

      throw new Error('Failed to save workflow')
    },

    async loadHistory() {
      this.historyLoading = true
      try {
        const response = await nlWorkflowApi.getSessions()
        this.history = response || []
        return this.history
      } finally {
        this.historyLoading = false
      }
    },

    async deleteSession(sessionId) {
      await nlWorkflowApi.deleteSession(sessionId)
      this.history = this.history.filter(s => s.session_id !== sessionId)
    },

    // ==================== Settings ====================

    updateSettings(newSettings) {
      this.settings = { ...this.settings, ...newSettings }
    },

    setTemperature(temperature) {
      this.settings.temperature = temperature
    },

    // ==================== Utilities ====================

    setGeneratedWorkflow(workflow) {
      this.generatedWorkflow = workflow
    },

    reset() {
      this.messages = []
      this.generatedWorkflow = null
      this.generationError = null
      this.history = []
      this.isGenerating = false
      this.isStreaming = false
      this.currentSessionId = null
      this.streamingProgress = 0
      this.streamingStage = ''
      this.lastIntent = null
      this.pendingAutoApply = false
    },

    resetSession() {
      this.messages = []
      this.generatedWorkflow = null
      this.generationError = null
      this.currentSessionId = null
      this.streamingProgress = 0
      this.streamingStage = ''
      this.isStreaming = false
      this.lastIntent = null
      this.pendingAutoApply = false
    }
  }
})
