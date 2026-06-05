/**
 * Integrations API 单元测试
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

const integrationsApi = require('@/api/integrations').default

beforeEach(() => jest.clearAllMocks())

// Webhooks
describe('integrationsApi.getWebhooks', () => {
  it('GET /integrations/webhooks/', async () => {
    await integrationsApi.getWebhooks()
    expect(mockRequest.get).toHaveBeenCalledWith('/integrations/webhooks/', {})
  })
})

describe('integrationsApi.getWebhook', () => {
  it('GET /integrations/webhooks/:id/', async () => {
    await integrationsApi.getWebhook(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/integrations/webhooks/1/')
  })
})

describe('integrationsApi.createWebhook', () => {
  it('POST /integrations/webhooks/', async () => {
    const data = { url: 'https://example.com/hook', events: ['workflow.completed'] }
    await integrationsApi.createWebhook(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/integrations/webhooks/', data)
  })
})

describe('integrationsApi.updateWebhook', () => {
  it('PATCH /integrations/webhooks/:id/', async () => {
    await integrationsApi.updateWebhook(1, { url: 'https://new.com/hook' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/integrations/webhooks/1/', { url: 'https://new.com/hook' })
  })
})

describe('integrationsApi.deleteWebhook', () => {
  it('DELETE /integrations/webhooks/:id/', async () => {
    await integrationsApi.deleteWebhook(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/integrations/webhooks/1/')
  })
})

describe('integrationsApi.testWebhook', () => {
  it('POST /integrations/webhooks/:id/test/', async () => {
    await integrationsApi.testWebhook(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/integrations/webhooks/1/test/')
  })
})

describe('integrationsApi.getWebhookDeliveries', () => {
  it('GET /integrations/webhooks/:id/deliveries/', async () => {
    await integrationsApi.getWebhookDeliveries(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/integrations/webhooks/1/deliveries/', {})
  })
})

describe('integrationsApi.getWebhookStats', () => {
  it('GET /integrations/webhooks/:id/stats/', async () => {
    await integrationsApi.getWebhookStats(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/integrations/webhooks/1/stats/')
  })
})

// Integrations
describe('integrationsApi.getIntegrations', () => {
  it('GET /integrations/integrations/', async () => {
    await integrationsApi.getIntegrations()
    expect(mockRequest.get).toHaveBeenCalledWith('/integrations/integrations/', {})
  })
})

describe('integrationsApi.createIntegration', () => {
  it('POST /integrations/integrations/', async () => {
    const data = { name: 'Slack', type: 'slack' }
    await integrationsApi.createIntegration(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/integrations/integrations/', data)
  })
})

describe('integrationsApi.updateIntegration', () => {
  it('PATCH /integrations/integrations/:id/', async () => {
    await integrationsApi.updateIntegration(5, { name: '更新' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/integrations/integrations/5/', { name: '更新' })
  })
})

describe('integrationsApi.deleteIntegration', () => {
  it('DELETE /integrations/integrations/:id/', async () => {
    await integrationsApi.deleteIntegration(5)
    expect(mockRequest.delete).toHaveBeenCalledWith('/integrations/integrations/5/')
  })
})

describe('integrationsApi.connectIntegration', () => {
  it('POST /integrations/integrations/:id/connect/', async () => {
    await integrationsApi.connectIntegration(5)
    expect(mockRequest.post).toHaveBeenCalledWith('/integrations/integrations/5/connect/')
  })
})

describe('integrationsApi.disconnectIntegration', () => {
  it('POST /integrations/integrations/:id/disconnect/', async () => {
    await integrationsApi.disconnectIntegration(5)
    expect(mockRequest.post).toHaveBeenCalledWith('/integrations/integrations/5/disconnect/')
  })
})

describe('integrationsApi.syncIntegration', () => {
  it('POST /integrations/integrations/:id/sync/', async () => {
    await integrationsApi.syncIntegration(5)
    expect(mockRequest.post).toHaveBeenCalledWith('/integrations/integrations/5/sync/')
  })
})

describe('integrationsApi.getAvailableIntegrations', () => {
  it('GET /integrations/integrations/available/', async () => {
    await integrationsApi.getAvailableIntegrations()
    expect(mockRequest.get).toHaveBeenCalledWith('/integrations/integrations/available/')
  })
})

// Templates
describe('integrationsApi.getIntegrationTemplates', () => {
  it('GET /integrations/templates/', async () => {
    await integrationsApi.getIntegrationTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/integrations/templates/', {})
  })
})

describe('integrationsApi.getTemplatesByCategory', () => {
  it('GET /integrations/templates/categories/', async () => {
    await integrationsApi.getTemplatesByCategory()
    expect(mockRequest.get).toHaveBeenCalledWith('/integrations/templates/categories/')
  })
})

describe('integrationsApi.registerWebhookReceiver', () => {
  it('POST /integrations/webhook-receiver/', async () => {
    await integrationsApi.registerWebhookReceiver('https://app.com/hook', ['push'], 'secret')
    expect(mockRequest.post).toHaveBeenCalledWith('/integrations/webhook-receiver/', {
      webhookUrl: 'https://app.com/hook',
      events: ['push'],
      secret: 'secret'
    })
  })
})
