/**
 * Branding API 单元测试
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

const brandingApi = require('@/api/branding').default

beforeEach(() => jest.clearAllMocks())

// Branding Config
describe('brandingApi.getCurrentBranding', () => {
  it('GET /branding/branding/current/', async () => {
    await brandingApi.getCurrentBranding()
    expect(mockRequest.get).toHaveBeenCalledWith('/branding/branding/current/')
  })
})

describe('brandingApi.updateBranding', () => {
  it('POST /branding/branding/update_config/', async () => {
    const data = { primary_color: '#000' }
    await brandingApi.updateBranding(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/branding/branding/update_config/', data)
  })
})

describe('brandingApi.applyPreset', () => {
  it('POST /branding/branding/apply_preset/', async () => {
    await brandingApi.applyPreset(2)
    expect(mockRequest.post).toHaveBeenCalledWith('/branding/branding/apply_preset/', { preset_id: 2 })
  })
})

describe('brandingApi.getPresets', () => {
  it('GET /branding/branding/presets/', async () => {
    await brandingApi.getPresets()
    expect(mockRequest.get).toHaveBeenCalledWith('/branding/branding/presets/')
  })
})

describe('brandingApi.previewBranding', () => {
  it('POST /branding/branding/preview/', async () => {
    const data = { primary_color: '#ff0000' }
    await brandingApi.previewBranding(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/branding/branding/preview/', data)
  })
})

// Email Templates
describe('brandingApi.getEmailTemplates', () => {
  it('GET /branding/email-templates/', async () => {
    await brandingApi.getEmailTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/branding/email-templates/', {})
  })
})

describe('brandingApi.getEmailTemplate', () => {
  it('GET /branding/email-templates/:id/', async () => {
    await brandingApi.getEmailTemplate(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/branding/email-templates/1/')
  })
})

describe('brandingApi.createEmailTemplate', () => {
  it('POST /branding/email-templates/', async () => {
    const data = { name: '注册确认', subject: '确认邮箱' }
    await brandingApi.createEmailTemplate(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/branding/email-templates/', data)
  })
})

describe('brandingApi.updateEmailTemplate', () => {
  it('PATCH /branding/email-templates/:id/', async () => {
    await brandingApi.updateEmailTemplate(1, { subject: '新主题' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/branding/email-templates/1/', { subject: '新主题' })
  })
})

describe('brandingApi.deleteEmailTemplate', () => {
  it('DELETE /branding/email-templates/:id/', async () => {
    await brandingApi.deleteEmailTemplate(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/branding/email-templates/1/')
  })
})

describe('brandingApi.resetEmailTemplate', () => {
  it('POST /branding/email-templates/:id/reset_to_default/', async () => {
    await brandingApi.resetEmailTemplate(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/branding/email-templates/1/reset_to_default/')
  })
})

describe('brandingApi.sendTestEmail', () => {
  it('POST /branding/email-templates/:id/send_test/', async () => {
    await brandingApi.sendTestEmail(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/branding/email-templates/1/send_test/')
  })
})

// Custom Domains
describe('brandingApi.getCustomDomains', () => {
  it('GET /branding/domains/', async () => {
    await brandingApi.getCustomDomains()
    expect(mockRequest.get).toHaveBeenCalledWith('/branding/domains/', {})
  })
})

describe('brandingApi.createCustomDomain', () => {
  it('POST /branding/domains/', async () => {
    const data = { domain: 'app.mycompany.com' }
    await brandingApi.createCustomDomain(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/branding/domains/', data)
  })
})

describe('brandingApi.deleteCustomDomain', () => {
  it('DELETE /branding/domains/:id/', async () => {
    await brandingApi.deleteCustomDomain(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/branding/domains/1/')
  })
})

describe('brandingApi.verifyDomain', () => {
  it('POST /branding/domains/:id/verify/', async () => {
    await brandingApi.verifyDomain(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/branding/domains/1/verify/')
  })
})

describe('brandingApi.refreshSSL', () => {
  it('POST /branding/domains/:id/refresh_ssl/', async () => {
    await brandingApi.refreshSSL(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/branding/domains/1/refresh_ssl/')
  })
})

// Theme Presets
describe('brandingApi.getThemePresets', () => {
  it('GET /branding/presets/', async () => {
    await brandingApi.getThemePresets()
    expect(mockRequest.get).toHaveBeenCalledWith('/branding/presets/')
  })
})

describe('brandingApi.getThemePreset', () => {
  it('GET /branding/presets/:id/', async () => {
    await brandingApi.getThemePreset(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/branding/presets/1/')
  })
})
