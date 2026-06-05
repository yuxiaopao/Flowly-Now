/**
 * Prompt API 单元测试
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

const promptApi = require('@/api/prompt').default

beforeEach(() => jest.clearAllMocks())

describe('promptApi.getTemplates', () => {
  it('GET /prompts/templates/', async () => {
    await promptApi.getTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/prompts/templates/', {})
  })
  it('携带参数', async () => {
    await promptApi.getTemplates({ category: 'chat' })
    expect(mockRequest.get).toHaveBeenCalledWith('/prompts/templates/', { category: 'chat' })
  })
})

describe('promptApi.getTemplate', () => {
  it('GET /prompts/templates/:id/', async () => {
    await promptApi.getTemplate(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/prompts/templates/1/')
  })
})

describe('promptApi.createTemplate', () => {
  it('POST /prompts/templates/', async () => {
    const data = { name: '新模板', content: '{{role}}' }
    await promptApi.createTemplate(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/prompts/templates/', data)
  })
})

describe('promptApi.updateTemplate', () => {
  it('PATCH /prompts/templates/:id/', async () => {
    await promptApi.updateTemplate(1, { name: '更新' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/prompts/templates/1/', { name: '更新' })
  })
})

describe('promptApi.deleteTemplate', () => {
  it('DELETE /prompts/templates/:id/', async () => {
    await promptApi.deleteTemplate(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/prompts/templates/1/')
  })
})

describe('promptApi.renderTemplate', () => {
  it('POST /prompts/templates/:id/render/', async () => {
    await promptApi.renderTemplate(1, { role: '开发者' })
    expect(mockRequest.post).toHaveBeenCalledWith('/prompts/templates/1/render/', { context: { role: '开发者' } })
  })
})

describe('promptApi.getPopular', () => {
  it('GET /prompts/templates/popular/ 默认 limit=10', async () => {
    await promptApi.getPopular()
    expect(mockRequest.get).toHaveBeenCalledWith('/prompts/templates/popular/', { limit: 10 })
  })
  it('自定义 limit', async () => {
    await promptApi.getPopular(5)
    expect(mockRequest.get).toHaveBeenCalledWith('/prompts/templates/popular/', { limit: 5 })
  })
})

describe('promptApi.getFeatured', () => {
  it('GET /prompts/templates/featured/', async () => {
    await promptApi.getFeatured()
    expect(mockRequest.get).toHaveBeenCalledWith('/prompts/templates/featured/')
  })
})

describe('promptApi.getCategories', () => {
  it('GET /prompts/templates/categories/', async () => {
    await promptApi.getCategories()
    expect(mockRequest.get).toHaveBeenCalledWith('/prompts/templates/categories/')
  })
})

describe('promptApi.duplicateTemplate', () => {
  it('POST /prompts/templates/:id/duplicate/', async () => {
    await promptApi.duplicateTemplate(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/prompts/templates/1/duplicate/')
  })
})

describe('promptApi.shareTemplate', () => {
  it('POST /prompts/templates/:id/share/', async () => {
    await promptApi.shareTemplate(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/prompts/templates/1/share/')
  })
})

describe('promptApi.unshareTemplate', () => {
  it('POST /prompts/templates/:id/unshare/', async () => {
    await promptApi.unshareTemplate(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/prompts/templates/1/unshare/')
  })
})

describe('promptApi.getVariableTypes', () => {
  it('GET /prompts/variables/types/', async () => {
    await promptApi.getVariableTypes()
    expect(mockRequest.get).toHaveBeenCalledWith('/prompts/variables/types/')
  })
})
