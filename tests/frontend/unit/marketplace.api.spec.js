/**
 * Marketplace API 单元测试
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

const marketplaceApi = require('@/api/marketplace').default
const { WORKFLOW_OPAQUE_KEYS } = require('@/api/workflow')
const opaqueOptions = { opaqueKeys: WORKFLOW_OPAQUE_KEYS }

beforeEach(() => jest.clearAllMocks())

describe('marketplaceApi.getTemplates', () => {
  it('GET /templates/', async () => {
    await marketplaceApi.getTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/', {}, opaqueOptions)
  })
  it('携带搜索参数', async () => {
    await marketplaceApi.getTemplates({ search: 'AI' })
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/', { search: 'AI' }, opaqueOptions)
  })
})

describe('marketplaceApi.getTemplate', () => {
  it('GET /templates/:id/', async () => {
    await marketplaceApi.getTemplate(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/1/', {}, opaqueOptions)
  })
})

describe('marketplaceApi.createTemplate', () => {
  it('POST /templates/', async () => {
    const data = { name: '模板', workflow_id: 5 }
    await marketplaceApi.createTemplate(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/templates/', data)
  })
})

describe('marketplaceApi.updateTemplate', () => {
  it('PATCH /templates/:id/', async () => {
    await marketplaceApi.updateTemplate(1, { description: '新描述' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/templates/1/', { description: '新描述' })
  })
})

describe('marketplaceApi.deleteTemplate', () => {
  it('DELETE /templates/:id/', async () => {
    await marketplaceApi.deleteTemplate(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/templates/1/')
  })
})

describe('marketplaceApi.getFeaturedTemplates', () => {
  it('GET /templates/featured/', async () => {
    await marketplaceApi.getFeaturedTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/featured/', {}, opaqueOptions)
  })
})

describe('marketplaceApi.getTemplates popular sorting', () => {
  it('GET /templates/ with sort=popular', async () => {
    await marketplaceApi.getTemplates({ sort: 'popular' })
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/', { sort: 'popular' }, opaqueOptions)
  })
})

describe('marketplaceApi.getTemplates newest sorting', () => {
  it('GET /templates/ with sort=newest', async () => {
    await marketplaceApi.getTemplates({ sort: 'newest' })
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/', { sort: 'newest' }, opaqueOptions)
  })
})

describe('marketplaceApi.getTemplate preview data', () => {
  it('GET /templates/:id/ preserves the workflow data for preview', async () => {
    const workflowData = { nodes: [{ id: 'start' }], edges: [] }
    mockRequest.get.mockResolvedValueOnce({ id: 1, workflow_data: workflowData })
    const response = await marketplaceApi.getTemplate(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/1/', {}, opaqueOptions)
    expect(response.workflow_data).toEqual(workflowData)
  })
})

describe('marketplaceApi.installTemplate', () => {
  it('POST /templates/:id/install/', async () => {
    await marketplaceApi.installTemplate(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/templates/1/install/')
  })
})

describe('marketplaceApi.rateTemplate', () => {
  it('POST /templates/:id/rate/', async () => {
    await marketplaceApi.rateTemplate(1, 5)
    expect(mockRequest.post).toHaveBeenCalledWith('/templates/1/rate/', { rating: 5 })
  })
})

describe('marketplaceApi.getTemplateStats', () => {
  it('GET /templates/:id/stats/', async () => {
    await marketplaceApi.getTemplateStats(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/1/stats/')
  })
})

describe('marketplaceApi.reportTemplate', () => {
  it('POST /templates/:id/report/', async () => {
    await marketplaceApi.reportTemplate('abc-123', 'inappropriate')
    expect(mockRequest.post).toHaveBeenCalledWith('/templates/abc-123/report/', { reason: 'inappropriate' })
  })
})

describe('marketplaceApi.getCategories', () => {
  it('GET /template-categories/', async () => {
    await marketplaceApi.getCategories()
    expect(mockRequest.get).toHaveBeenCalledWith('/template-categories/', {}, opaqueOptions)
  })
})

describe('marketplaceApi.getCategory', () => {
  it('GET /template-categories/:id/', async () => {
    await marketplaceApi.getCategory(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/template-categories/1/', {}, opaqueOptions)
  })
})

describe('marketplaceApi.getCategoryTemplates', () => {
  it('GET /templates/ with category filter', async () => {
    await marketplaceApi.getCategoryTemplates(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/', { category: 1 })
  })
})

describe('marketplaceApi.getMyTemplates', () => {
  it('GET /templates/mine/', async () => {
    await marketplaceApi.getMyTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/mine/', {})
  })
})

describe('marketplaceApi.publishTemplate', () => {
  it('PATCH /templates/:id/publish/', async () => {
    await marketplaceApi.publishTemplate(10)
    expect(mockRequest.patch).toHaveBeenCalledWith('/templates/10/publish/')
  })
})

describe('marketplaceApi.unpublishTemplate', () => {
  it('PATCH /templates/:id/unpublish/', async () => {
    await marketplaceApi.unpublishTemplate(10)
    expect(mockRequest.patch).toHaveBeenCalledWith('/templates/10/unpublish/')
  })
})

describe('marketplaceApi.getInstalledTemplates', () => {
  it('GET /templates/installed/', async () => {
    await marketplaceApi.getInstalledTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/templates/installed/', {})
  })
})
