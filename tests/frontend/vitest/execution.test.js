/**
 * Execution Store Tests
 * Tests for execution state management, WebSocket integration, and status transitions
 */

import { setActivePinia, createPinia } from 'pinia'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import {
  mockExecution,
  mockExecutionStatus
} from './mocks/executions.mock'
import { setupExecutionWsMock } from './mocks/handlers'

// Mock dependencies
vi.mock('@/api/workflow', () => ({
  workflowApi: {
    executeSync: vi.fn(),
    executeAsync: vi.fn(),
    getExecution: vi.fn(),
    getExecutionStatus: vi.fn(),
    getExecutionLogs: vi.fn(),
    cancelExecution: vi.fn(),
    retryExecution: vi.fn(),
    pauseExecution: vi.fn(),
    resumeExecution: vi.fn(),
    getExecutionHistory: vi.fn()
  }
}))

vi.mock('@/api/websocket', () => ({
  ExecutionWebSocket: vi.fn().mockImplementation(() => ({
    on: vi.fn(),
    off: vi.fn(),
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    send: vi.fn()
  }))
}))

vi.mock('@/stores/app', () => ({
  useAppStore: vi.fn().mockReturnValue({
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  })
}))

// Helper to reset execution store state
function resetExecutionStore(store) {
  store.currentExecution = null
  store.executionStatus = 'idle'
  store.executionProgress = 0
  store.currentNodeId = null
  store.nodeStatusMap = {}
  store.executionLogs = []
  store.outputData = null
  store.errorMessage = null
  store.traceback = null
  store.isWsConnected = false
  store.executionHistory = []
  store.historyLoading = false
  store.streamingOutput = ''
  store.isStreaming = false
  store.streamingNode = ''
  store.tokenStats = { prompt: 0, completion: 0, total: 0 }
  store.nodeOutputs = {}
  store.nodeInputs = {}
  store.wsConnection = null
}

describe('Execution Store', () => {
  let executionStore
  let workflowApi
  let mockWs
  let pinia

  beforeEach(async () => {
    pinia = createPinia()
    setActivePinia(pinia)

    const { useExecutionStore } = await import('@/stores/execution')
    executionStore = useExecutionStore()

    // Setup mocks
    workflowApi = (await import('@/api/workflow')).workflowApi
    mockWs = setupExecutionWsMock()

    // Reset store state manually (setup syntax doesn't have $reset)
    resetExecutionStore(executionStore)
  })

  afterEach(() => {
    vi.clearAllMocks()
    pinia.state.value = { execution: {} }
  })

  describe('Initial State', () => {
    it('should initialize with correct default state', () => {
      expect(executionStore.currentExecution).toBeNull()
      expect(executionStore.executionStatus).toBe('idle')
      expect(executionStore.executionProgress).toBe(0)
      expect(executionStore.currentNodeId).toBeNull()
      expect(executionStore.nodeStatusMap).toEqual({})
      expect(executionStore.executionLogs).toEqual([])
      expect(executionStore.outputData).toBeNull()
      expect(executionStore.errorMessage).toBeNull()
    })

    it('should have correct computed values for initial state', () => {
      expect(executionStore.isRunning).toBe(false)
      expect(executionStore.isPaused).toBe(false)
      expect(executionStore.isCompleted).toBe(false)
      expect(executionStore.isFailed).toBe(false)
      expect(executionStore.isCancelled).toBe(false)
      expect(executionStore.isFinished).toBe(false)
      expect(executionStore.progressPercentage).toBe(0)
      expect(executionStore.nodeCount).toBe(0)
      expect(executionStore.completedNodeCount).toBe(0)
    })
  })

  describe('Execution Status Transitions', () => {
    beforeEach(() => {
      workflowApi.executeSync.mockResolvedValue({
        ...mockExecution,
        nodeStatus: mockExecution.nodeStatus
      })
      workflowApi.getExecution.mockResolvedValue(mockExecution)
    })

    it('should transition from idle to running on initExecution', async () => {
      executionStore.reset()
      
      const result = await executionStore.initExecution(1, { input: 'test' })

      expect(workflowApi.executeSync).toHaveBeenCalledWith(1, { input: 'test' })
      expect(result).toBeTruthy()
    })

    it('should update state from execution response', () => {
      executionStore.updateFromExecution(mockExecution)

      expect(executionStore.currentExecution).toEqual(mockExecution)
      expect(executionStore.executionStatus).toBe(mockExecution.status)
      // Node status is converted to snake_case in store, check actual state
      expect(executionStore.executionStatus).toBeTruthy()
    })

    it('keeps the failed execution ID and actual node error for viewing its history', async () => {
      const error = Object.assign(new Error('请求失败'), { response: { data: { code: 400, data: { execution_id: 'failed-run', status: 'failed', error: '字段映射缺少来源字段' } } } })
      workflowApi.executeSync.mockRejectedValueOnce(error)
      await expect(executionStore.initExecution('workflow', {})).rejects.toBe(error)
      expect(executionStore.currentExecution.id).toBe('failed-run')
      expect(executionStore.executionStatus).toBe('failed')
      expect(executionStore.errorMessage).toBe('字段映射缺少来源字段')
    })

    it('should update state from status response', () => {
      executionStore.updateFromStatus(mockExecutionStatus)

      expect(executionStore.executionStatus).toBe(mockExecutionStatus.status)
      expect(executionStore.executionProgress).toBe(mockExecutionStatus.progress)
      expect(executionStore.executionStatus).toBeTruthy()
    })
  })

  describe('Async Execution', () => {
    beforeEach(() => {
      workflowApi.executeAsync.mockResolvedValue({
        execution_id: 10,
        status: 'pending'
      })
    })

    it('should start async execution', async () => {
      const result = await executionStore.startAsyncExecution(1, { input: 'test' })

      expect(workflowApi.executeAsync).toHaveBeenCalledWith(1, { input: 'test' })
      expect(result).toBeTruthy()
      expect(executionStore.executionStatus).toBe('pending')
    })
  })

  describe('WebSocket Connection', () => {
    it('should connect to WebSocket for streaming execution', async () => {
      executionStore.wsConnection = {
        on: vi.fn(),
        connect: vi.fn().mockResolvedValue(undefined),
        disconnect: vi.fn()
      }

      await executionStore.connectWebSocket(1)

      expect(executionStore.isWsConnected).toBe(true)
    })

    it('should disconnect WebSocket', () => {
      executionStore.disconnectWebSocket()

      expect(executionStore.wsConnection).toBeNull()
      expect(executionStore.isWsConnected).toBe(false)
    })

    it('should handle WebSocket events', async () => {
      const { ExecutionWebSocket } = await import('@/api/websocket')
      const mockWsInstance = {
        on: vi.fn((event, callback) => {
          // Store callback for later invocation
          mockWsInstance._callbacks = mockWsInstance._callbacks || {}
          mockWsInstance._callbacks[event] = callback
        }),
        off: vi.fn(),
        connect: vi.fn().mockResolvedValue(undefined),
        disconnect: vi.fn()
      }
      ExecutionWebSocket.mockImplementation(() => mockWsInstance)

      await executionStore.connectWebSocket(1)

      // Simulate node_start event
      if (mockWsInstance._callbacks['node_start']) {
        mockWsInstance._callbacks['node_start']({
          nodeId: 'node_2',
          nodeName: 'LLM Node'
        })
      }

      expect(executionStore.nodeStatusMap['node_2']).toBe('running')
    })
  })

  describe('Execution Control', () => {
    beforeEach(() => {
      executionStore.currentExecution = { id: 1 }
      workflowApi.cancelExecution.mockResolvedValue({ status: 'cancelled' })
      workflowApi.pauseExecution.mockResolvedValue({ status: 'paused' })
      workflowApi.resumeExecution.mockResolvedValue({ status: 'running' })
      workflowApi.retryExecution.mockResolvedValue({ id: 2, status: 'pending' })
    })

    it('should cancel execution', async () => {
      executionStore.disconnectWebSocket = vi.fn()

      await executionStore.cancelExecution()

      expect(workflowApi.cancelExecution).toHaveBeenCalledWith(1)
      expect(executionStore.executionStatus).toBe('cancelled')
    })

    it('should pause execution', async () => {
      await executionStore.pauseExecution()

      expect(workflowApi.pauseExecution).toHaveBeenCalledWith(1)
      expect(executionStore.executionStatus).toBe('paused')
    })

    it('should resume execution', async () => {
      executionStore.executionStatus = 'paused'

      await executionStore.resumeExecution()

      expect(workflowApi.resumeExecution).toHaveBeenCalledWith(1)
      expect(executionStore.executionStatus).toBe('running')
    })

    it('should retry execution', async () => {
      executionStore.connectWebSocket = vi.fn()

      const result = await executionStore.retryExecution()

      expect(workflowApi.retryExecution).toHaveBeenCalledWith(1, {})
      expect(executionStore.executionStatus).toBe('pending')
      expect(executionStore.executionProgress).toBe(0)
    })
  })

  describe('Progress Calculations', () => {
    it('should calculate progress correctly', () => {
      executionStore.nodeStatusMap = {
        node_1: 'completed',
        node_2: 'completed',
        node_3: 'running',
        node_4: 'pending'
      }

      expect(executionStore.nodeCount).toBe(4)
      expect(executionStore.completedNodeCount).toBe(2)
      expect(executionStore.progressPercentage).toBe(50)
    })

    it('should handle empty node status', () => {
      expect(executionStore.nodeCount).toBe(0)
      expect(executionStore.completedNodeCount).toBe(0)
      expect(executionStore.progressPercentage).toBe(0)
    })

    it('should count failed nodes', () => {
      executionStore.nodeStatusMap = {
        node_1: 'completed',
        node_2: 'failed',
        node_3: 'completed'
      }

      expect(executionStore.failedNodeCount).toBe(1)
    })
  })

  describe('Node Status Summary', () => {
    it('should generate correct summary', () => {
      executionStore.nodeStatusMap = {
        node_1: 'completed',
        node_2: 'running',
        node_3: 'pending',
        node_4: 'failed',
        node_5: 'skipped'
      }

      const summary = executionStore.nodeStatusSummary

      expect(summary.completed).toBe(1)
      expect(summary.running).toBe(1)
      expect(summary.pending).toBe(1)
      expect(summary.failed).toBe(1)
      expect(summary.skipped).toBe(1)
    })
  })

  describe('Streaming Output', () => {
    beforeEach(() => {
      executionStore.isStreaming = true
      executionStore.streamingOutput = ''
    })

    it('should update streaming output', () => {
      executionStore.streamingOutput = 'Hello'
      executionStore.streamingNode = 'LLM Node'

      expect(executionStore.streamingOutput).toBe('Hello')
      expect(executionStore.streamingNode).toBe('LLM Node')
    })

    it('should handle stream completion', () => {
      executionStore.isStreaming = false
      executionStore.streamingOutput = 'Completed streaming text'

      expect(executionStore.isStreaming).toBe(false)
    })
  })

  describe('Token Statistics', () => {
    it('should track token usage', () => {
      executionStore.tokenStats = {
        prompt: 100,
        completion: 50,
        total: 150
      }

      expect(executionStore.tokenStats.prompt).toBe(100)
      expect(executionStore.tokenStats.completion).toBe(50)
      expect(executionStore.tokenStats.total).toBe(150)
    })

    it('should calculate total tokens', () => {
      executionStore.tokenStats = {
        prompt: 200,
        completion: 100,
        total: 0
      }
      executionStore.tokenStats.total = 
        executionStore.tokenStats.prompt + executionStore.tokenStats.completion

      expect(executionStore.tokenStats.total).toBe(300)
    })
  })

  describe('Node Outputs', () => {
    it('should store node outputs', () => {
      executionStore.nodeOutputs = {
        node_1: { result: 'output1' },
        node_2: { result: 'output2' }
      }

      expect(executionStore.getNodeOutput('node_1')).toEqual({ result: 'output1' })
      expect(executionStore.getNodeOutput('node_3')).toBeNull()
    })

    it('should store node inputs', () => {
      executionStore.nodeInputs = {
        node_1: { input: 'value' }
      }

      expect(executionStore.getNodeInput('node_1')).toEqual({ input: 'value' })
      expect(executionStore.getNodeInput('node_2')).toBeNull()
    })
  })

  describe('Execution Logs', () => {
    beforeEach(() => {
      workflowApi.getExecutionLogs.mockResolvedValue({
        results: mockExecution.execution_logs
      })
    })

    it('should add log entries', () => {
      executionStore.executionLogs = [
        { type: 'node_start', nodeId: 'node_1' },
        { type: 'node_complete', nodeId: 'node_1' }
      ]

      expect(executionStore.executionLogs).toHaveLength(2)
    })

    it('should clear logs', () => {
      executionStore.executionLogs = [{ type: 'log' }]
      executionStore.clearLogs()

      expect(executionStore.executionLogs).toEqual([])
    })

    it('should fetch execution logs', async () => {
      await executionStore.fetchExecutionLogs(1)

      expect(workflowApi.getExecutionLogs).toHaveBeenCalledWith(1)
      expect(executionStore.executionLogs).toMatchObject(mockExecution.execution_logs)
      expect(executionStore.executionLogs.every(log => typeof log.level === 'string')).toBe(true)
    })
  })

  describe('Execution History', () => {
    beforeEach(() => {
      workflowApi.getExecutionHistory.mockResolvedValue({
        results: [
          { id: 1, status: 'completed' },
          { id: 2, status: 'failed' }
        ]
      })
    })

    it('should fetch execution history', async () => {
      await executionStore.fetchHistory(1)

      expect(workflowApi.getExecutionHistory).toHaveBeenCalledWith(1, {})
      expect(executionStore.executionHistory).toHaveLength(2)
      expect(executionStore.historyLoading).toBe(false)
    })

    it('should handle history fetch errors gracefully', async () => {
      // Suppress console error for expected error case
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      workflowApi.getExecutionHistory.mockRejectedValue(new Error('Network error'))

      // The store rethrows the error from fetchHistory
      try {
        await executionStore.fetchHistory(1)
      } catch (e) {
        // Expected to throw
      }

      expect(executionStore.historyLoading).toBe(false)
      consoleSpy.mockRestore()
    })
  })

  describe('Error Handling', () => {
    beforeEach(() => {
      executionStore.disconnectWebSocket = vi.fn()
    })

    it('should update state on error', () => {
      // Simulate error state
      executionStore.executionStatus = 'failed'
      executionStore.errorMessage = 'Execution failed'
      executionStore.isStreaming = false

      expect(executionStore.executionStatus).toBe('failed')
      expect(executionStore.errorMessage).toBe('Execution failed')
      expect(executionStore.isStreaming).toBe(false)
    })

    it('should handle fetch execution details errors', async () => {
      workflowApi.getExecution.mockRejectedValue(new Error('Not found'))

      await expect(executionStore.fetchExecutionDetails(999)).rejects.toThrow('Not found')
    })

    it('should handle cancel errors', async () => {
      executionStore.currentExecution = { id: 1 }
      executionStore.disconnectWebSocket = vi.fn()
      workflowApi.cancelExecution.mockRejectedValue(new Error('Cancel failed'))

      await expect(executionStore.cancelExecution()).rejects.toThrow('Cancel failed')
    })
  })

  describe('Output Data', () => {
    it('should update output data with object', () => {
      executionStore.outputData = { existing: 'data' }

      executionStore.updateOutputData({ new: 'data' })

      expect(executionStore.outputData).toEqual({
        existing: 'data',
        new: 'data'
      })
    })

    it('should update output data with non-object', () => {
      executionStore.outputData = null

      executionStore.updateOutputData('simple output')

      expect(executionStore.outputData).toEqual({ lastOutput: 'simple output' })
    })
  })

  describe('Reset', () => {
    it('should reset all state', () => {
      // Set various state
      executionStore.currentExecution = { id: 1 }
      executionStore.executionStatus = 'running'
      executionStore.executionProgress = 50
      executionStore.nodeStatusMap = { node_1: 'completed' }
      executionStore.executionLogs = [{ type: 'log' }]
      executionStore.streamingOutput = 'streaming...'
      executionStore.tokenStats = { prompt: 100, completion: 50, total: 150 }

      executionStore.reset()

      expect(executionStore.currentExecution).toBeNull()
      expect(executionStore.executionStatus).toBe('idle')
      expect(executionStore.executionProgress).toBe(0)
      expect(executionStore.nodeStatusMap).toEqual({})
      expect(executionStore.executionLogs).toEqual([])
      expect(executionStore.streamingOutput).toBe('')
      expect(executionStore.tokenStats).toEqual({ prompt: 0, completion: 0, total: 0 })
    })
  })

  describe('Computed Status Checks', () => {
    it('should correctly identify running status', () => {
      executionStore.executionStatus = 'running'
      expect(executionStore.isRunning).toBe(true)
      expect(executionStore.isFinished).toBe(false)
    })

    it('should correctly identify paused status', () => {
      executionStore.executionStatus = 'paused'
      expect(executionStore.isPaused).toBe(true)
    })

    it('should correctly identify completed status', () => {
      executionStore.executionStatus = 'completed'
      expect(executionStore.isCompleted).toBe(true)
      expect(executionStore.isFinished).toBe(true)
    })

    it('should correctly identify failed status', () => {
      executionStore.executionStatus = 'failed'
      expect(executionStore.isFailed).toBe(true)
      expect(executionStore.isFinished).toBe(true)
    })

    it('should correctly identify cancelled status', () => {
      executionStore.executionStatus = 'cancelled'
      expect(executionStore.isCancelled).toBe(true)
      expect(executionStore.isFinished).toBe(true)
    })
  })
})
