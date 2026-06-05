/**
 * Agent API 单元测试
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

const agentApi = require('@/api/agent').default

beforeEach(() => jest.clearAllMocks())

// Agent CRUD
describe('agentApi.getList', () => {
  it('GET /agents/ 默认无参数', async () => {
    await agentApi.getList()
    expect(mockRequest.get).toHaveBeenCalledWith('/agents/', {})
  })
  it('GET /agents/ 携带参数', async () => {
    await agentApi.getList({ page: 1, search: 'gpt' })
    expect(mockRequest.get).toHaveBeenCalledWith('/agents/', { page: 1, search: 'gpt' })
  })
})

describe('agentApi.getById', () => {
  it('GET /agents/:id/', async () => {
    await agentApi.getById(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/agents/1/')
  })
})

describe('agentApi.create', () => {
  it('POST /agents/', async () => {
    const data = { name: '新Agent', system_prompt: '你是助手', model: 'gpt-4' }
    await agentApi.create(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/agents/', data)
  })
})

describe('agentApi.update', () => {
  it('PATCH /agents/:id/', async () => {
    await agentApi.update(1, { temperature: 0.5 })
    expect(mockRequest.patch).toHaveBeenCalledWith('/agents/1/', { temperature: 0.5 })
  })
})

describe('agentApi.delete', () => {
  it('DELETE /agents/:id/', async () => {
    await agentApi.delete(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/agents/1/')
  })
})

// 工具管理
describe('agentApi.getAvailableTools', () => {
  it('GET /agents/:id/tools/', async () => {
    await agentApi.getAvailableTools(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/agents/1/tools/')
  })
})

describe('agentApi.addTools', () => {
  it('POST /agents/:id/tools/', async () => {
    await agentApi.addTools(1, ['tool_a'])
    expect(mockRequest.post).toHaveBeenCalledWith('/agents/1/tools/', { tools: ['tool_a'] })
  })
})

describe('agentApi.removeTool', () => {
  it('POST /agents/:id/tools_remove/', async () => {
    await agentApi.removeTool(1, 'tool_a')
    expect(mockRequest.post).toHaveBeenCalledWith('/agents/1/tools_remove/', { tool: 'tool_a' })
  })
})

// 调试
describe('agentApi.debug', () => {
  it('POST /agents/:id/debug/', async () => {
    await agentApi.debug(1, { message: '测试', context: {} })
    expect(mockRequest.post).toHaveBeenCalledWith('/agents/1/debug/', { message: '测试', context: {} })
  })
})

describe('agentApi.getDebugHistory', () => {
  it('GET /agents/:id/debug/history/', async () => {
    await agentApi.getDebugHistory(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/agents/1/debug/history/', {})
  })
})

describe('agentApi.clearDebugHistory', () => {
  it('DELETE /agents/:id/debug/history/', async () => {
    await agentApi.clearDebugHistory(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/agents/1/debug/history/')
  })
})

// 技能
describe('agentApi.getSkills', () => {
  it('GET /agents/:id/skills/', async () => {
    await agentApi.getSkills(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/agents/1/skills/')
  })
})

describe('agentApi.updateSkills', () => {
  it('PATCH /agents/:id/update_skills/', async () => {
    await agentApi.updateSkills(1, ['skill_a'])
    expect(mockRequest.patch).toHaveBeenCalledWith('/agents/1/update_skills/', { skills: ['skill_a'] })
  })
})

// 对话
describe('agentApi.getConversations', () => {
  it('GET /agents/conversations/ 按 agentId 过滤', async () => {
    await agentApi.getConversations(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/agents/conversations/', { agent_id: 1 })
  })
})

describe('agentApi.getConversation', () => {
  it('GET /agents/conversations/:id/', async () => {
    await agentApi.getConversation(5)
    expect(mockRequest.get).toHaveBeenCalledWith('/agents/conversations/5/')
  })
})

describe('agentApi.deleteConversation', () => {
  it('DELETE /agents/conversations/:id/', async () => {
    await agentApi.deleteConversation(5)
    expect(mockRequest.delete).toHaveBeenCalledWith('/agents/conversations/5/')
  })
})

describe('agentApi.getMessages', () => {
  it('GET /agents/conversations/:id/messages/', async () => {
    await agentApi.getMessages(5)
    expect(mockRequest.get).toHaveBeenCalledWith('/agents/conversations/5/messages/')
  })
})

describe('agentApi.sendMessage', () => {
  it('POST /agents/:id/chat/', async () => {
    await agentApi.sendMessage(1, { message: '你好', conversation_id: 5 })
    expect(mockRequest.post).toHaveBeenCalledWith('/agents/1/chat/', { message: '你好', conversation_id: 5 })
  })
})

describe('agentApi.streamChat', () => {
  it('stream /agents/:id/stream_chat/', async () => {
    await agentApi.streamChat(1, { message: '你好' })
    expect(mockRequest.stream).toHaveBeenCalledWith('/agents/1/stream_chat/', { message: '你好' })
  })
})
