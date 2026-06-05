/**
 * NL Workflow Store Tests
 * Tests for Natural Language to Workflow conversion and streaming
 */

import { setActivePinia, createPinia } from 'pinia'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import {
  mockNLModels,
  mockNLSession,
  mockNLWorkflow,
  mockNLIntentCreate,
  mockNLIntentModify,
  mockNLIntentDelete,
  mockNLIntentChat,
  mockNLSuggestions,
  mockNLHistory,
  mockNLConfirmResponse
} from './mocks/nl.mock'

// Mock API
vi.mock('@/api/nl-workflow', () => ({
  nlWorkflowApi: {
    getModels: vi.fn(),
    createSession: vi.fn(),
    getSessions: vi.fn(),
    deleteSession: vi.fn(),
    sendMessage: vi.fn(),
    confirmWorkflow: vi.fn(),
    analyzeIntent: vi.fn(),
    suggest: vi.fn(),
    preview: vi.fn()
  }
}))

describe('NL Workflow Store', () => {
  let nlStore
  let nlWorkflowApi
  let pinia

  beforeEach(async () => {
    pinia = createPinia()
    setActivePinia(pinia)

    const { useNLWorkflowStore } = await import('@/stores/nlWorkflow')
    nlStore = useNLWorkflowStore()

    nlWorkflowApi = (await import('@/api/nl-workflow')).nlWorkflowApi

    // Manual reset for setup syntax store
    nlStore.messages = []
    nlStore.generatedWorkflow = null
    nlStore.isGenerating = false
    nlStore.generationError = null
    nlStore.streamingProgress = 0
    nlStore.streamingStage = ''
    nlStore.isStreaming = false
    nlStore.lastIntent = null
    nlStore.history = []
    nlStore.currentSessionId = null
    nlStore.models = []
    nlStore.selectedModel = null
  })

  afterEach(() => {
    vi.clearAllMocks()
    pinia.state.value = { nlWorkflow: {} }
  })

  describe('Initial State', () => {
    it('should initialize with empty messages', () => {
      expect(nlStore.messages).toEqual([])
      expect(nlStore.generatedWorkflow).toBeNull()
      expect(nlStore.isGenerating).toBe(false)
      expect(nlStore.generationError).toBeNull()
    })

    it('should have correct default settings', () => {
      expect(nlStore.settings.includeDescription).toBe(true)
      expect(nlStore.settings.includeValidation).toBe(true)
      expect(nlStore.settings.temperature).toBe(0.7)
      expect(nlStore.settings.maxTokens).toBe(2048)
    })

    it('should have correct computed values', () => {
      expect(nlStore.isEmpty).toBe(true)
      expect(nlStore.messageCount).toBe(0)
      expect(nlStore.hasSession).toBe(false)
      expect(nlStore.canContinue).toBe(false)
    })
  })

  describe('Message Management', () => {
    it('should add user message', () => {
      nlStore.addUserMessage('Create a workflow')

      expect(nlStore.messages).toHaveLength(1)
      expect(nlStore.messages[0].role).toBe('user')
      expect(nlStore.messages[0].content).toBe('Create a workflow')
      expect(nlStore.messages[0].timestamp).toBeTruthy()
    })

    it('should add assistant message', () => {
      nlStore.addAssistantMessage('I will create a workflow')

      expect(nlStore.messages).toHaveLength(1)
      expect(nlStore.messages[0].role).toBe('assistant')
    })

    it('should add system message', () => {
      nlStore.addSystemMessage('You are a workflow assistant')

      expect(nlStore.messages).toHaveLength(1)
      expect(nlStore.messages[0].role).toBe('system')
    })

    it('should update last assistant message', () => {
      nlStore.addAssistantMessage('Start')
      nlStore.updateLastAssistantMessage('Updated content')

      expect(nlStore.messages[0].content).toBe('Updated content')
    })

    it('should update last assistant message with metadata', () => {
      nlStore.addAssistantMessage('Start')
      nlStore.updateLastAssistantMessage('With workflow', { workflow: mockNLWorkflow })

      expect(nlStore.messages[0].metadata.workflow).toEqual(mockNLWorkflow)
    })

    it('should clear all messages', () => {
      nlStore.addUserMessage('Test')
      nlStore.addAssistantMessage('Response')
      nlStore.generatedWorkflow = mockNLWorkflow

      nlStore.clearMessages()

      expect(nlStore.messages).toEqual([])
      expect(nlStore.generatedWorkflow).toBeNull()
      expect(nlStore.generationError).toBeNull()
    })
  })

  describe('Getters', () => {
    beforeEach(() => {
      nlStore.addUserMessage('First message')
      nlStore.addAssistantMessage('First response')
      nlStore.addUserMessage('Second message')
    })

    it('should return conversation history for API', () => {
      const history = nlStore.conversationHistory

      expect(history.length).toBeGreaterThanOrEqual(3)
      expect(history[0]).toEqual({ role: 'user', content: 'First message' })
      expect(history[1]).toEqual({ role: 'assistant', content: 'First response' })
    })

    it('should return last user message', () => {
      const lastMessage = nlStore.lastUserMessage

      expect(lastMessage.content).toBe('Second message')
    })

    it('should return message count', () => {
      expect(nlStore.messageCount).toBeGreaterThanOrEqual(3)
    })
  })

  describe('Model Management', () => {
    beforeEach(() => {
      nlWorkflowApi.getModels.mockResolvedValue(mockNLModels)
    })

    it('should load models', async () => {
      await nlStore.loadModels()

      expect(nlWorkflowApi.getModels).toHaveBeenCalled()
      expect(nlStore.models).toEqual(mockNLModels.models)
      expect(nlStore.selectedModel).toBe('gpt-4')
    })

    it('should use first model if no default', async () => {
      nlWorkflowApi.getModels.mockResolvedValue({
        models: [{ model_id: 'claude-3', name: 'Claude 3' }]
      })

      await nlStore.loadModels()

      expect(nlStore.selectedModel).toBe('claude-3')
    })

    it('should not reload models if already loaded', async () => {
      nlStore.models = mockNLModels.models

      await nlStore.loadModels()

      expect(nlWorkflowApi.getModels).not.toHaveBeenCalled()
    })

    it('should set selected model', () => {
      nlStore.setSelectedModel('gpt-3.5-turbo')

      expect(nlStore.selectedModel).toBe('gpt-3.5-turbo')
    })

    it('should handle model loading errors', async () => {
      nlWorkflowApi.getModels.mockRejectedValue(new Error('Network error'))
      vi.spyOn(console, 'error').mockImplementation(() => {})

      await nlStore.loadModels()

      expect(nlStore.generationError).toBe('加载模型列表失败')
    })
  })

  describe('Session Management', () => {
    beforeEach(() => {
      nlWorkflowApi.createSession.mockResolvedValue({
        session_id: 1,
        workflow_json: mockNLWorkflow,
        message: 'Created successfully'
      })
    })

    it('should create new session', async () => {
      nlStore.selectedModel = 'gpt-4'

      const result = await nlStore.createSession('Create a chatbot', 'My Chatbot')

      expect(nlWorkflowApi.createSession).toHaveBeenCalledWith({
        description: 'Create a chatbot',
        name: 'My Chatbot',
        model: 'gpt-4',
        temperature: 0.7
      })
      expect(nlStore.currentSessionId).toBe(1)
      expect(nlStore.generatedWorkflow).toEqual(mockNLWorkflow)
      expect(nlStore.messages.length).toBeGreaterThanOrEqual(1) // At least user message
    })

    it('should handle session creation errors', async () => {
      nlWorkflowApi.createSession.mockRejectedValue(new Error('API error'))

      await expect(nlStore.createSession('Test')).rejects.toThrow('API error')
      expect(nlStore.generationError).toBe('API error')
    })

    it('should handle session creation with error response', async () => {
      nlWorkflowApi.createSession.mockResolvedValue({
        session_id: 1,
        error: 'Generation failed'
      })

      await nlStore.createSession('Test')

      expect(nlStore.generationError).toBe('Generation failed')
    })

    it('should use session_id or id field', async () => {
      nlWorkflowApi.createSession.mockResolvedValue({
        id: 2,
        workflow_json: mockNLWorkflow
      })

      await nlStore.createSession('Test')

      expect(nlStore.currentSessionId).toBe(2)
    })
  })

  describe('Intent Classification', () => {
    beforeEach(() => {
      nlWorkflowApi.analyzeIntent.mockResolvedValue(mockNLIntentCreate)
    })

    it('should analyze create intent', async () => {
      const result = await nlStore.analyzeIntent('Create a new workflow')

      expect(nlWorkflowApi.analyzeIntent).toHaveBeenCalledWith('Create a new workflow')
      expect(result.intent).toBe('create')
      expect(nlStore.lastIntent).toEqual(mockNLIntentCreate)
    })

    it('should analyze modify intent', async () => {
      nlWorkflowApi.analyzeIntent.mockResolvedValue(mockNLIntentModify)
      
      const result = await nlStore.analyzeIntent('Modify the workflow')

      expect(result.intent).toBe('modify')
    })

    it('should analyze delete intent', async () => {
      nlWorkflowApi.analyzeIntent.mockResolvedValue(mockNLIntentDelete)
      
      const result = await nlStore.analyzeIntent('Delete this workflow')

      expect(result.intent).toBe('delete')
    })

    it('should analyze chat intent', async () => {
      nlWorkflowApi.analyzeIntent.mockResolvedValue(mockNLIntentChat)
      
      const result = await nlStore.analyzeIntent('What can you do?')

      expect(result.intent).toBe('chat')
    })

    it('should handle intent analysis errors', async () => {
      nlWorkflowApi.analyzeIntent.mockRejectedValue(new Error('API error'))

      const result = await nlStore.analyzeIntent('Test')

      expect(result.intent).toBe('unknown')
      expect(result.error).toBe('API error')
    })
  })

  describe('Suggestions', () => {
    beforeEach(() => {
      nlWorkflowApi.suggest.mockResolvedValue(mockNLSuggestions)
    })

    it('should get suggestions', async () => {
      const suggestions = await nlStore.getSuggestions({ workflow: mockNLWorkflow })

      expect(nlWorkflowApi.suggest).toHaveBeenCalledWith({ workflow: mockNLWorkflow })
      expect(suggestions).toEqual(mockNLSuggestions.suggestions)
    })

    it('should handle suggestion errors', async () => {
      nlWorkflowApi.suggest.mockRejectedValue(new Error('API error'))

      const suggestions = await nlStore.getSuggestions()

      expect(suggestions).toEqual([])
    })
  })

  describe('Workflow Confirmation', () => {
    beforeEach(() => {
      nlStore.currentSessionId = 1
      nlWorkflowApi.confirmWorkflow.mockResolvedValue(mockNLConfirmResponse)
    })

    it('should confirm and save workflow', async () => {
      const workflowId = await nlStore.confirmWorkflow()

      expect(nlWorkflowApi.confirmWorkflow).toHaveBeenCalledWith(1)
      expect(workflowId).toBe(10)
    })

    it('should reset after confirmation', async () => {
      nlStore.messages = [{ role: 'user', content: 'Test' }]
      nlStore.generatedWorkflow = mockNLWorkflow

      await nlStore.confirmWorkflow()

      expect(nlStore.messages).toEqual([])
      expect(nlStore.generatedWorkflow).toBeNull()
    })

    it('should throw error if no session', async () => {
      nlStore.currentSessionId = null

      await expect(nlStore.confirmWorkflow()).rejects.toThrow('No active session to confirm')
    })

    it('should handle confirmation errors', async () => {
      nlWorkflowApi.confirmWorkflow.mockResolvedValue({})

      await expect(nlStore.confirmWorkflow()).rejects.toThrow('Failed to save workflow')
    })
  })

  describe('History Management', () => {
    beforeEach(() => {
      nlWorkflowApi.getSessions.mockResolvedValue(mockNLHistory)
    })

    it('should load history', async () => {
      const history = await nlStore.loadHistory()

      expect(nlWorkflowApi.getSessions).toHaveBeenCalled()
      expect(nlStore.history).toEqual(mockNLHistory)
      expect(nlStore.historyLoading).toBe(false)
    })

    it('should delete session from history', async () => {
      nlStore.history = [...mockNLHistory]
      nlWorkflowApi.deleteSession.mockResolvedValue({})

      await nlStore.deleteSession(1)

      expect(nlWorkflowApi.deleteSession).toHaveBeenCalledWith(1)
      expect(nlStore.history).toHaveLength(2)
    })

    it('should handle history fetch errors', async () => {
      nlWorkflowApi.getSessions.mockRejectedValue(new Error('Network error'))

      await expect(nlStore.loadHistory()).rejects.toThrow('Network error')
      expect(nlStore.historyLoading).toBe(false)
    })
  })

  describe('Settings', () => {
    it('should update settings', () => {
      nlStore.updateSettings({ temperature: 0.9, includeDescription: false })

      expect(nlStore.settings.temperature).toBe(0.9)
      expect(nlStore.settings.includeDescription).toBe(false)
    })

    it('should set temperature', () => {
      nlStore.setTemperature(0.5)

      expect(nlStore.settings.temperature).toBe(0.5)
    })
  })

  describe('Workflow Generation', () => {
    beforeEach(() => {
      nlStore.selectedModel = 'gpt-4'
    })

    it('should set generated workflow', () => {
      nlStore.setGeneratedWorkflow(mockNLWorkflow)

      expect(nlStore.generatedWorkflow).toEqual(mockNLWorkflow)
    })
  })

  describe('Reset', () => {
    it('should reset all state', () => {
      nlStore.messages = [
        { role: 'user', content: 'Test' },
        { role: 'assistant', content: 'Response' }
      ]
      nlStore.generatedWorkflow = mockNLWorkflow
      nlStore.generationError = 'Some error'
      nlStore.isGenerating = true
      nlStore.isStreaming = true
      nlStore.currentSessionId = 1
      nlStore.streamingProgress = 50
      nlStore.streamingStage = 'Processing'
      nlStore.lastIntent = mockNLIntentCreate

      nlStore.reset()

      expect(nlStore.messages).toEqual([])
      expect(nlStore.generatedWorkflow).toBeNull()
      expect(nlStore.generationError).toBeNull()
      expect(nlStore.isGenerating).toBe(false)
      expect(nlStore.isStreaming).toBe(false)
      expect(nlStore.currentSessionId).toBeNull()
      expect(nlStore.streamingProgress).toBe(0)
      expect(nlStore.streamingStage).toBe('')
      expect(nlStore.lastIntent).toBeNull()
    })

    it('should reset session without clearing history', () => {
      nlStore.messages = [{ role: 'user', content: 'Test' }]
      nlStore.history = mockNLHistory

      nlStore.resetSession()

      expect(nlStore.messages).toEqual([])
      expect(nlStore.history).toEqual(mockNLHistory)
    })
  })

  describe('Send Message', () => {
    beforeEach(() => {
      nlStore.currentSessionId = 1
      nlWorkflowApi.sendMessage.mockResolvedValue({
        message: 'Updated workflow',
        workflow_json: mockNLWorkflow
      })
    })

    it('should send message in existing session', async () => {
      const result = await nlStore.sendMessage('Add a condition node')

      expect(nlWorkflowApi.sendMessage).toHaveBeenCalledWith(1, 'Add a condition node', {
        model: null,
        temperature: 0.7
      })
      expect(nlStore.messages.length).toBeGreaterThanOrEqual(1) // user message added
      expect(nlStore.generatedWorkflow).toEqual(mockNLWorkflow)
    })

    it('should throw if no session', async () => {
      nlStore.currentSessionId = null

      await expect(nlStore.sendMessage('Test')).rejects.toThrow('No active session')
    })

    it('should handle send message errors', async () => {
      nlWorkflowApi.sendMessage.mockRejectedValue(new Error('Send failed'))

      await expect(nlStore.sendMessage('Test')).rejects.toThrow('Send failed')
      expect(nlStore.generationError).toBe('Send failed')
    })
  })

  describe('Computed States', () => {
    it('should identify canContinue correctly', () => {
      nlStore.generatedWorkflow = null
      nlStore.isGenerating = false
      expect(nlStore.canContinue).toBe(false)

      nlStore.generatedWorkflow = mockNLWorkflow
      nlStore.isGenerating = false
      expect(nlStore.canContinue).toBe(true)

      nlStore.generatedWorkflow = mockNLWorkflow
      nlStore.isGenerating = true
      expect(nlStore.canContinue).toBe(false)
    })

    it('should identify hasSession correctly', () => {
      expect(nlStore.hasSession).toBe(false)

      nlStore.currentSessionId = 1
      expect(nlStore.hasSession).toBe(true)
    })

    it('should identify isEmpty correctly', () => {
      expect(nlStore.isEmpty).toBe(true)

      nlStore.addUserMessage('Test')
      expect(nlStore.isEmpty).toBe(false)
    })
  })
})

describe('NL Workflow Streaming Tests', () => {
  let nlStore

  beforeEach(async () => {
    const pinia = createPinia()
    setActivePinia(pinia)

    const { useNLWorkflowStore } = await import('@/stores/nlWorkflow')
    nlStore = useNLWorkflowStore()
    nlStore.reset()
  })

  it('should track streaming state', () => {
    nlStore.isStreaming = true
    nlStore.streamingProgress = 50
    nlStore.streamingStage = 'Generating nodes'

    expect(nlStore.isStreaming).toBe(true)
    expect(nlStore.streamingProgress).toBe(50)
    expect(nlStore.streamingStage).toBe('Generating nodes')
  })

  it('should update streaming progress', () => {
    nlStore.streamingProgress = 0
    nlStore.streamingStage = ''

    nlStore.streamingProgress = 25
    nlStore.streamingStage = 'Analyzing intent'

    expect(nlStore.streamingProgress).toBe(25)
    expect(nlStore.streamingStage).toBe('Analyzing intent')
  })
})
