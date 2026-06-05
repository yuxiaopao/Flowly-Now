// API Mock Handlers for testing
// These handlers intercept API calls and return mock data

import { vi } from 'vitest'
import {
  mockWorkflowList,
  mockWorkflow,
  mockAvailableModels,
  mockAvailableTools,
  mockAvailableNodeTypes
} from './workflows.mock'
import {
  mockExecutionList,
  mockExecution,
  mockExecutionStatistics
} from './executions.mock'
import {
  mockNLModels,
  mockNLSession,
  mockNLWorkflow,
  mockNLHistory,
  mockNLConfirmResponse
} from './nl.mock'

// Store for mock implementations
const mockHandlers = {}

// HTTP status codes
const HTTP_OK = 200
const HTTP_CREATED = 201
const HTTP_NO_CONTENT = 204
const HTTP_BAD_REQUEST = 400
const HTTP_NOT_FOUND = 404
const HTTP_SERVER_ERROR = 500

// Create mock response
function createResponse(data, status = HTTP_OK) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === HTTP_OK ? 'OK' : status === HTTP_CREATED ? 'Created' : 'Error',
    data,
    json: () => Promise.resolve(data)
  }
}

// Create error response
function createErrorResponse(message, status = HTTP_SERVER_ERROR) {
  const error = new Error(message)
  error.response = { status, data: { error: message } }
  return Promise.reject(error)
}

// Workflow API handlers
export function setupWorkflowMocks() {
  mockHandlers.workflow = {
    getList: vi.fn().mockResolvedValue(mockWorkflowList),
    getById: vi.fn().mockResolvedValue(mockWorkflow),
    create: vi.fn().mockResolvedValue(mockWorkflow),
    update: vi.fn().mockResolvedValue(mockWorkflow),
    delete: vi.fn().mockResolvedValue({ status: HTTP_NO_CONTENT }),
    duplicate: vi.fn().mockResolvedValue({ ...mockWorkflow, id: 99, name: 'Duplicate of Test Workflow' }),
    execute: vi.fn().mockResolvedValue({ execution_id: 1, status: 'pending' }),
    executeSync: vi.fn().mockResolvedValue(mockExecution),
    executeAsync: vi.fn().mockResolvedValue({ execution_id: 1, status: 'pending' }),
    getExecution: vi.fn().mockResolvedValue(mockExecution),
    getExecutionHistory: vi.fn().mockResolvedValue(mockExecutionList),
    getExecutionStatus: vi.fn().mockResolvedValue({ status: 'completed' }),
    getExecutionLogs: vi.fn().mockResolvedValue({ executionLogs: mockExecution.execution_logs }),
    cancelExecution: vi.fn().mockResolvedValue({ status: 'cancelled' }),
    retryExecution: vi.fn().mockResolvedValue({ execution_id: 2, status: 'pending' }),
    deleteExecution: vi.fn().mockResolvedValue({ status: HTTP_NO_CONTENT }),
    pauseExecution: vi.fn().mockResolvedValue({ status: 'paused' }),
    resumeExecution: vi.fn().mockResolvedValue({ status: 'running' }),
    getExecutionStatistics: vi.fn().mockResolvedValue(mockExecutionStatistics),
    getTools: vi.fn().mockResolvedValue(mockAvailableTools),
    getAvailableNodeTypes: vi.fn().mockResolvedValue({ types: mockAvailableNodeTypes }),
    validate: vi.fn().mockResolvedValue({ valid: true, errors: [], warnings: [] }),
    getTemplates: vi.fn().mockResolvedValue({ count: 0, results: [] }),
    getTemplate: vi.fn().mockRejectedValue(new Error('Template not found'))
  }
  return mockHandlers.workflow
}

// Execution WebSocket mock
export function setupExecutionWsMock() {
  const mockWs = {
    on: vi.fn(),
    off: vi.fn(),
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    send: vi.fn(),
    emit: vi.fn()
  }
  return mockWs
}

// NL Workflow API handlers
export function setupNLMocks() {
  mockHandlers.nl = {
    getModels: vi.fn().mockResolvedValue(mockNLModels),
    createSession: vi.fn().mockResolvedValue({
      session_id: 1,
      workflow_json: mockNLWorkflow,
      message: 'Workflow generated successfully'
    }),
    getSessions: vi.fn().mockResolvedValue(mockNLHistory),
    getSession: vi.fn().mockResolvedValue(mockNLSession),
    deleteSession: vi.fn().mockResolvedValue({ status: HTTP_NO_CONTENT }),
    updateSession: vi.fn().mockResolvedValue(mockNLSession),
    sendMessage: vi.fn().mockResolvedValue({
      message: 'I have updated the workflow',
      workflow_json: mockNLWorkflow
    }),
    confirmWorkflow: vi.fn().mockResolvedValue(mockNLConfirmResponse),
    analyzeIntent: vi.fn().mockResolvedValue({
      intent: 'create',
      confidence: 0.95,
      action: 'create_workflow'
    }),
    suggest: vi.fn().mockResolvedValue({
      suggestions: ['Add error handling', 'Include validation']
    }),
    preview: vi.fn().mockResolvedValue(mockNLWorkflow)
  }
  return mockHandlers.nl
}

// Stream mock for SSE
export function createMockStreamResponse(events) {
  let index = 0
  const stream = new ReadableStream({
    start(controller) {
      // Send events one by one
      const sendNext = () => {
        if (index < events.length) {
          const event = events[index]
          const data = `data: ${JSON.stringify(event)}\n\n`
          controller.enqueue(new TextEncoder().encode(data))
          index++
          setTimeout(sendNext, 50)
        } else {
          controller.close()
        }
      }
      sendNext()
    }
  })

  return {
    ok: true,
    status: 200,
    body: stream
  }
}

// Reset all mocks
export function resetMocks() {
  Object.values(mockHandlers).forEach(handler => {
    Object.values(handler).forEach(fn => {
      if (vi.isMockFunction(fn)) {
        fn.mockClear()
      }
    })
  })
}

// Export handlers for direct access
export function getMockHandlers() {
  return mockHandlers
}
