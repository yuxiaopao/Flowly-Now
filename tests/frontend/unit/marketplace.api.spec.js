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

beforeEach(() => jest.clearAllMocks())

describe('marketplaceApi.getTemplates', () => {
  it('GET /marketplace/templates/', async () => {
    await marketplaceApi.getTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/templates/', {})
  })
  it('携带搜索参数', async () => {
    await marketplaceApi.getTemplates({ search: 'AI' })
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/templates/', { search: 'AI' })
  })
})

describe('marketplaceApi.getTemplate', () => {
  it('GET /marketplace/templates/:id/', async () => {
    await marketplaceApi.getTemplate(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/templates/1/')
  })
})

describe('marketplaceApi.createTemplate', () => {
  it('POST /marketplace/templates/', async () => {
    const data = { name: '模板', workflow_id: 5 }
    await marketplaceApi.createTemplate(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/marketplace/templates/', data)
  })
})

describe('marketplaceApi.updateTemplate', () => {
  it('PATCH /marketplace/templates/:id/', async () => {
    await marketplaceApi.updateTemplate(1, { description: '新描述' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/marketplace/templates/1/', { description: '新描述' })
  })
})

describe('marketplaceApi.deleteTemplate', () => {
  it('DELETE /marketplace/templates/:id/', async () => {
    await marketplaceApi.deleteTemplate(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/marketplace/templates/1/')
  })
})

describe('marketplaceApi.getFeaturedTemplates', () => {
  it('GET /marketplace/templates/featured/', async () => {
    await marketplaceApi.getFeaturedTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/templates/featured/')
  })
})

describe('marketplaceApi.getPopularTemplates', () => {
  it('GET /marketplace/templates/popular/', async () => {
    await marketplaceApi.getPopularTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/templates/popular/')
  })
})

describe('marketplaceApi.getRecentTemplates', () => {
  it('GET /marketplace/templates/recent/', async () => {
    await marketplaceApi.getRecentTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/templates/recent/')
  })
})

describe('marketplaceApi.getTemplatePreview', () => {
  it('GET /marketplace/templates/:id/preview/', async () => {
    await marketplaceApi.getTemplatePreview(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/templates/1/preview/')
  })
})

describe('marketplaceApi.installTemplate', () => {
  it('POST /marketplace/templates/:id/install/', async () => {
    await marketplaceApi.installTemplate(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/marketplace/templates/1/install/')
  })
})

describe('marketplaceApi.rateTemplate', () => {
  it('POST /marketplace/templates/:id/rate/', async () => {
    await marketplaceApi.rateTemplate(1, 5)
    expect(mockRequest.post).toHaveBeenCalledWith('/marketplace/templates/1/rate/', { rating: 5 })
  })
})

describe('marketplaceApi.getTemplateStats', () => {
  it('GET /marketplace/templates/:id/stats/', async () => {
    await marketplaceApi.getTemplateStats(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/templates/1/stats/')
  })
})

describe('marketplaceApi.reportTemplate', () => {
  it('POST /templates/:id/report/', async () => {
    await marketplaceApi.reportTemplate('abc-123', 'inappropriate')
    expect(mockRequest.post).toHaveBeenCalledWith('/templates/abc-123/report/', { reason: 'inappropriate' })
  })
})

describe('marketplaceApi.getCategories', () => {
  it('GET /marketplace/categories/', async () => {
    await marketplaceApi.getCategories()
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/categories/', {})
  })
})

describe('marketplaceApi.getCategory', () => {
  it('GET /marketplace/categories/:id/', async () => {
    await marketplaceApi.getCategory(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/categories/1/')
  })
})

describe('marketplaceApi.getCategoryTemplates', () => {
  it('GET /marketplace/categories/:id/templates/', async () => {
    await marketplaceApi.getCategoryTemplates(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/categories/1/templates/', {})
  })
})

describe('marketplaceApi.getMyTemplates', () => {
  it('GET /marketplace/my-templates/', async () => {
    await marketplaceApi.getMyTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/my-templates/', {})
  })
})

describe('marketplaceApi.publishTemplate', () => {
  it('POST /marketplace/my-templates/:id/publish/', async () => {
    await marketplaceApi.publishTemplate(10)
    expect(mockRequest.post).toHaveBeenCalledWith('/marketplace/my-templates/10/publish/')
  })
})

describe('marketplaceApi.unpublishTemplate', () => {
  it('POST /marketplace/my-templates/:id/unpublish/', async () => {
    await marketplaceApi.unpublishTemplate(10)
    expect(mockRequest.post).toHaveBeenCalledWith('/marketplace/my-templates/10/unpublish/')
  })
})

describe('marketplaceApi.getInstalledTemplates', () => {
  it('GET /marketplace/installed/', async () => {
    await marketplaceApi.getInstalledTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/marketplace/installed/', {})
  })
})
