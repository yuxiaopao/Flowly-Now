/**
 * Admin API 单元测试
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

const adminApi = require('@/api/admin').default

beforeEach(() => jest.clearAllMocks())

// Users
describe('adminApi.getUsers', () => {
  it('GET /admin/users/', async () => {
    await adminApi.getUsers()
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/users/', {})
  })
  it('携带搜索参数', async () => {
    await adminApi.getUsers({ search: 'test', role: 'developer' })
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/users/', { search: 'test', role: 'developer' })
  })
})

describe('adminApi.getUser', () => {
  it('GET /admin/users/:id/', async () => {
    await adminApi.getUser(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/users/1/')
  })
})

describe('adminApi.updateUser', () => {
  it('PATCH /admin/users/:id/', async () => {
    await adminApi.updateUser(1, { role: 'admin' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/admin/users/1/', { role: 'admin' })
  })
})

describe('adminApi.deleteUser', () => {
  it('DELETE /admin/users/:id/', async () => {
    await adminApi.deleteUser(99)
    expect(mockRequest.delete).toHaveBeenCalledWith('/admin/users/99/')
  })
})

// Workflows
describe('adminApi.getAllWorkflows', () => {
  it('GET /admin/workflows/', async () => {
    await adminApi.getAllWorkflows()
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/workflows/', {})
  })
  it('携带过滤参数', async () => {
    await adminApi.getAllWorkflows({ status: 'active' })
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/workflows/', { status: 'active' })
  })
})

describe('adminApi.getWorkflow', () => {
  it('GET /admin/workflows/:id/', async () => {
    await adminApi.getWorkflow(5)
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/workflows/5/')
  })
})

// Agents
describe('adminApi.getAllAgents', () => {
  it('GET /admin/agents/', async () => {
    await adminApi.getAllAgents()
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/agents/', {})
  })
})

// Usage
describe('adminApi.getSystemUsage', () => {
  it('GET /admin/usage/', async () => {
    await adminApi.getSystemUsage()
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/usage/', {})
  })
  it('携带时间范围', async () => {
    await adminApi.getSystemUsage({ period: '30d' })
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/usage/', { period: '30d' })
  })
})

// Health
describe('adminApi.getSystemHealth', () => {
  it('GET /admin/health/', async () => {
    await adminApi.getSystemHealth()
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/health/')
  })
})

// Settings
describe('adminApi.getSystemSettings', () => {
  it('GET /admin/settings/', async () => {
    await adminApi.getSystemSettings()
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/settings/')
  })
})

describe('adminApi.updateSystemSettings', () => {
  it('PATCH /admin/settings/', async () => {
    await adminApi.updateSystemSettings({ max_executions_per_user: 200 })
    expect(mockRequest.patch).toHaveBeenCalledWith('/admin/settings/', { max_executions_per_user: 200 })
  })
})

// API Keys
describe('adminApi.getApiKeys', () => {
  it('GET /admin/api-keys/', async () => {
    await adminApi.getApiKeys()
    expect(mockRequest.get).toHaveBeenCalledWith('/admin/api-keys/', {})
  })
})

describe('adminApi.createApiKey', () => {
  it('POST /admin/api-keys/', async () => {
    const data = { name: '系统Key', scopes: ['read'] }
    await adminApi.createApiKey(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/admin/api-keys/', data)
  })
})

describe('adminApi.revokeApiKey', () => {
  it('POST /admin/api-keys/:id/revoke/', async () => {
    await adminApi.revokeApiKey(10)
    expect(mockRequest.post).toHaveBeenCalledWith('/admin/api-keys/10/revoke/')
  })
})
