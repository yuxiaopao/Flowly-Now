/**
 * NL Workflow API 单元测试
 * Tests all API endpoints with request mocking and response handling.
 */

const mockRequest = {
  get: jest.fn().mockResolvedValue({}),
  post: jest.fn().mockResolvedValue({}),
  put: jest.fn().mockResolvedValue({}),
  patch: jest.fn().mockResolvedValue({}),
  delete: jest.fn().mockResolvedValue({}),
  stream: jest.fn().mockResolvedValue({})
}

jest.mock('@/api/index', () => ({
  request: mockRequest,
  api: {},
  default: {},
  toCamelCase: (str) => str,
  toSnakeCase: (str) => str,
  toCamelCaseKeys: (obj) => obj,
  toSnakeCaseKeys: (obj) => obj
}))

const nlWorkflowApi = require('@/api/nl-workflow').default

beforeEach(() => jest.clearAllMocks())

describe('nlWorkflowApi - API Endpoint Tests', () => {
  describe('getModels', () => {
    it('GET /nl-workflow/models/ returns models list', async () => {
      const mockResponse = {
        models: [
          { model_id: 'llama3', name: 'Llama 3', provider: 'ollama' },
          { model_id: 'gpt-4', name: 'GPT-4', provider: 'openai' }
        ],
        default: 'llama3',
        count: 2
      }
      mockRequest.get.mockResolvedValue(mockResponse)

      const response = await nlWorkflowApi.getModels()

      expect(mockRequest.get).toHaveBeenCalledWith('/nl-workflow/models/')
      expect(response.models).toHaveLength(2)
      expect(response.default).toBe('llama3')
    })

    it('handles empty models list', async () => {
      mockRequest.get.mockResolvedValue({ models: [], default: null, count: 0 })

      const response = await nlWorkflowApi.getModels()

      expect(response.models).toHaveLength(0)
    })
  })

  describe('createSession', () => {
    it('POST /nl-workflow/sessions/ creates new session', async () => {
      const data = { description: '创建报告工作流', name: '每日报告' }
      await nlWorkflowApi.createSession(data)
      expect(mockRequest.post).toHaveBeenCalledWith('/nl-workflow/sessions/', data)
    })

    it('POST with model and temperature options', async () => {
      const data = { description: 'Test', model: 'llama3', temperature: 0.5 }
      await nlWorkflowApi.createSession(data)
      expect(mockRequest.post).toHaveBeenCalledWith('/nl-workflow/sessions/', data)
    })

    it('handles session_id response field', async () => {
      const mockResponse = {
        session_id: 123,
        workflow_json: { name: 'Test', nodes: [], edges: [] },
        status: 'active'
      }
      mockRequest.post.mockResolvedValue(mockResponse)

      const response = await nlWorkflowApi.createSession({ description: 'Test' })

      expect(response.session_id).toBe(123)
    })

    it('handles error response', async () => {
      const mockError = { error: 'LLM connection failed' }
      mockRequest.post.mockResolvedValue(mockError)

      const response = await nlWorkflowApi.createSession({ description: 'Test' })

      expect(response.error).toBe('LLM connection failed')
    })
  })

  describe('getSessions', () => {
    it('GET /nl-workflow/sessions/ returns list', async () => {
      await nlWorkflowApi.getSessions()
      expect(mockRequest.get).toHaveBeenCalledWith('/nl-workflow/sessions/')
    })

    it('returns array of sessions', async () => {
      const mockSessions = [
        { session_id: 1, name: 'Session 1', status: 'active' },
        { session_id: 2, name: 'Session 2', status: 'completed' }
      ]
      mockRequest.get.mockResolvedValue(mockSessions)

      const response = await nlWorkflowApi.getSessions()

      expect(response).toHaveLength(2)
    })
  })

  describe('getSession', () => {
    it('GET /nl-workflow/sessions/:id/ returns session details', async () => {
      await nlWorkflowApi.getSession(1)
      expect(mockRequest.get).toHaveBeenCalledWith('/nl-workflow/sessions/1/')
    })

    it('returns full session data including workflow_json', async () => {
      const mockSession = {
        session_id: 1,
        name: 'Test Session',
        workflow_json: { name: 'Workflow', nodes: [], edges: [] },
        messages: [],
        status: 'active'
      }
      mockRequest.get.mockResolvedValue(mockSession)

      const response = await nlWorkflowApi.getSession(1)

      expect(response.session_id).toBe(1)
      expect(response.workflow_json).toBeDefined()
    })
  })

  describe('deleteSession', () => {
    it('DELETE /nl-workflow/sessions/:id/ deletes session', async () => {
      await nlWorkflowApi.deleteSession(1)
      expect(mockRequest.delete).toHaveBeenCalledWith('/nl-workflow/sessions/1/')
    })

    it('returns success message', async () => {
      mockRequest.delete.mockResolvedValue({ message: '会话已删除' })

      const response = await nlWorkflowApi.deleteSession(1)

      expect(response.message).toBe('会话已删除')
    })
  })

  describe('sendMessage', () => {
    it('POST /nl-workflow/sessions/:id/message/ sends message', async () => {
      await nlWorkflowApi.sendMessage(1, '添加邮件步骤')
      expect(mockRequest.post).toHaveBeenCalledWith('/nl-workflow/sessions/1/message/', {
        message: '添加邮件步骤'
      })
    })

    it('includes model option', async () => {
      await nlWorkflowApi.sendMessage(1, 'Test', { model: 'llama3' })
      expect(mockRequest.post).toHaveBeenCalledWith('/nl-workflow/sessions/1/message/', {
        message: 'Test',
        model: 'llama3'
      })
    })

    it('handles workflow_json response', async () => {
      const mockResponse = {
        message: '已添加邮件节点',
        workflow_json: { name: 'Updated', nodes: [], edges: [] },
        suggestions: ['添加更多步骤']
      }
      mockRequest.post.mockResolvedValue(mockResponse)

      const response = await nlWorkflowApi.sendMessage(1, '添加邮件')

      expect(response.workflow_json).toBeDefined()
      expect(response.suggestions).toHaveLength(1)
    })
  })

  describe('confirmWorkflow', () => {
    it('POST /nl-workflow/sessions/:id/confirm/ confirms workflow', async () => {
      await nlWorkflowApi.confirmWorkflow(1)
      expect(mockRequest.post).toHaveBeenCalledWith('/nl-workflow/sessions/1/confirm/')
    })

    it('returns workflow_id on success', async () => {
      const mockResponse = {
        workflow_id: 456,
        workflow: { name: 'Saved Workflow' },
        status: 'completed'
      }
      mockRequest.post.mockResolvedValue(mockResponse)

      const response = await nlWorkflowApi.confirmWorkflow(1)

      expect(response.workflow_id).toBe(456)
    })
  })

  describe('streamGenerate', () => {
    it('POST /nl-workflow/sessions/ with responseType=stream', async () => {
      const data = { description: '流式测试', name: '流式' }
      await nlWorkflowApi.streamGenerate(data)
      expect(mockRequest.post).toHaveBeenCalledWith('/nl-workflow/sessions/', data, {
        responseType: 'stream'
      })
    })
  })

  describe('preview', () => {
    it('POST /nl-workflow/preview/ generates preview', async () => {
      await nlWorkflowApi.preview({ description: '预览测试' })
      expect(mockRequest.post).toHaveBeenCalledWith('/nl-workflow/preview/', {
        description: '预览测试'
      })
    })

    it('includes model and temperature options', async () => {
      const data = { description: 'Test', model: 'llama3', temperature: 0.5 }
      await nlWorkflowApi.preview(data)
      expect(mockRequest.post).toHaveBeenCalledWith('/nl-workflow/preview/', data)
    })

    it('handles preview response with node_count and edge_count', async () => {
      const mockResponse = {
        preview: {
          name: 'Preview Workflow',
          nodes: [{ id: 'node_1' }],
          edges: [],
          node_count: 1,
          edge_count: 0
        },
        workflow_json: { name: 'Preview Workflow', nodes: [], edges: [] }
      }
      mockRequest.post.mockResolvedValue(mockResponse)

      const response = await nlWorkflowApi.preview({ description: 'Test' })

      expect(response.preview.node_count).toBe(1)
      expect(response.preview.edge_count).toBe(0)
    })
  })
})

describe('nlWorkflowApi - Backward Compatibility Tests', () => {
  it('handles both workflow and workflow_json field names', async () => {
    // Test with workflow_json (new format)
    const responseNew = {
      session_id: 1,
      workflow_json: { name: 'New Format' },
      workflow: { name: 'New Format' }
    }
    mockRequest.post.mockResolvedValue(responseNew)

    const r1 = await nlWorkflowApi.createSession({ description: 'Test' })
    expect(r1.workflow_json).toBeDefined()
    expect(r1.workflow).toBeDefined()

    // Test with only workflow (old format)
    const responseOld = {
      session_id: 2,
      workflow: { name: 'Old Format' }
    }
    mockRequest.post.mockResolvedValue(responseOld)

    const r2 = await nlWorkflowApi.createSession({ description: 'Test' })
    expect(r2.workflow).toBeDefined()
  })

  it('handles both session_id and id field names', async () => {
    // Test with session_id
    const response1 = { session_id: 1, workflow_json: {} }
    mockRequest.post.mockResolvedValue(response1)
    const r1 = await nlWorkflowApi.createSession({ description: 'Test' })
    expect(r1.session_id || r1.id).toBe(1)

    // Test with id (alternative)
    const response2 = { id: 2, workflow_json: {} }
    mockRequest.post.mockResolvedValue(response2)
    const r2 = await nlWorkflowApi.createSession({ description: 'Test' })
    expect(r2.session_id || r2.id).toBe(2)
  })
})

describe('nlWorkflowApi - Error Handling Tests', () => {
  it('handles 400 Bad Request error', async () => {
    mockRequest.post.mockRejectedValue(new Error('Bad Request'))

    await expect(nlWorkflowApi.createSession({ description: '' }))
      .rejects.toThrow('Bad Request')
  })

  it('handles 401 Unauthorized error', async () => {
    mockRequest.get.mockRejectedValue(new Error('Unauthorized'))

    await expect(nlWorkflowApi.getSessions())
      .rejects.toThrow('Unauthorized')
  })

  it('handles 404 Not Found error', async () => {
    mockRequest.get.mockRejectedValue(new Error('Not Found'))

    await expect(nlWorkflowApi.getSession(99999))
      .rejects.toThrow('Not Found')
  })
})
