/**
 * Gateway API 单元测试
 * gateway.js 现在使用 request 封装
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

const gatewayApi = require('@/api/gateway').default

beforeEach(() => jest.clearAllMocks())

// Providers
describe('gatewayApi.getProviders', () => {
  it('GET /gateway/providers/', async () => {
    await gatewayApi.getProviders()
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/providers/')
  })
})

describe('gatewayApi.getProvider', () => {
  it('GET /gateway/providers/:id/', async () => {
    await gatewayApi.getProvider(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/providers/1/')
  })
})

// Models
describe('gatewayApi.getModels', () => {
  it('GET /gateway/models/ 无参数', async () => {
    await gatewayApi.getModels()
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/models/', {})
  })
  it('携带过滤参数', async () => {
    await gatewayApi.getModels({ provider: 'openai' })
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/models/', { provider: 'openai' })
  })
})

describe('gatewayApi.getModel', () => {
  it('GET /gateway/models/:id/', async () => {
    await gatewayApi.getModel(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/models/1/')
  })
})

describe('gatewayApi.getDefaultModels', () => {
  it('GET /gateway/models/default_models/', async () => {
    await gatewayApi.getDefaultModels()
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/models/default_models/')
  })
})

describe('gatewayApi.testModel', () => {
  it('POST /gateway/models/:id/test/', async () => {
    await gatewayApi.testModel(1, { message: '你好' })
    expect(mockRequest.post).toHaveBeenCalledWith('/gateway/models/1/test/', { message: '你好' })
  })
})

// API Keys
describe('gatewayApi.getAPIKeys', () => {
  it('GET /gateway/api-keys/', async () => {
    await gatewayApi.getAPIKeys()
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/api-keys/')
  })
})

describe('gatewayApi.createAPIKey', () => {
  it('POST /gateway/api-keys/', async () => {
    const data = { name: 'Key', provider: 'openai' }
    await gatewayApi.createAPIKey(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/gateway/api-keys/', data)
  })
})

describe('gatewayApi.updateAPIKey', () => {
  it('PUT /gateway/api-keys/:id/', async () => {
    await gatewayApi.updateAPIKey(5, { name: '更新' })
    expect(mockRequest.put).toHaveBeenCalledWith('/gateway/api-keys/5/', { name: '更新' })
  })
})

describe('gatewayApi.deleteAPIKey', () => {
  it('DELETE /gateway/api-keys/:id/', async () => {
    await gatewayApi.deleteAPIKey(5)
    expect(mockRequest.delete).toHaveBeenCalledWith('/gateway/api-keys/5/')
  })
})

describe('gatewayApi.verifyAPIKey', () => {
  it('POST /gateway/api-keys/:id/verify/', async () => {
    await gatewayApi.verifyAPIKey(5)
    expect(mockRequest.post).toHaveBeenCalledWith('/gateway/api-keys/5/verify/')
  })
})

// Logs
describe('gatewayApi.getAPILogs', () => {
  it('GET /gateway/logs/', async () => {
    await gatewayApi.getAPILogs()
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/logs/', {})
  })
})

describe('gatewayApi.getAPIAggregate', () => {
  it('GET /gateway/logs/aggregate/', async () => {
    await gatewayApi.getAPIAggregate({ group_by: 'model' })
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/logs/aggregate/', { group_by: 'model' })
  })
})

describe('gatewayApi.getRecentAPICalls', () => {
  it('GET /gateway/logs/recent/ 默认 limit=20', async () => {
    await gatewayApi.getRecentAPICalls()
    expect(mockRequest.get).toHaveBeenCalledWith('/gateway/logs/recent/', { limit: 20 })
  })
})

// Chat & Embeddings
describe('gatewayApi.gatewayChat', () => {
  it('POST /gateway/chat/', async () => {
    const data = { model: 'gpt-4', messages: [{ role: 'user', content: '你好' }] }
    await gatewayApi.gatewayChat(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/gateway/chat/', data)
  })
})

describe('gatewayApi.gatewayEmbeddings', () => {
  it('POST /gateway/embeddings/', async () => {
    const data = { model: 'text-embedding-3-small', input: '文本' }
    await gatewayApi.gatewayEmbeddings(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/gateway/embeddings/', data)
  })
})
