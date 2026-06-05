/**
 * Billing API 单元测试
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

const billingApi = require('@/api/billing').default

beforeEach(() => jest.clearAllMocks())

describe('billingApi.getPriceTiers', () => {
  it('GET /billing/prices/', async () => {
    await billingApi.getPriceTiers()
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/prices/', {})
  })
})

describe('billingApi.getPlans', () => {
  it('GET /billing/prices/plans/', async () => {
    await billingApi.getPlans()
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/prices/plans/')
  })
})

describe('billingApi.getMySubscription', () => {
  it('GET /billing/subscriptions/my/', async () => {
    await billingApi.getMySubscription()
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/subscriptions/my/')
  })
})

describe('billingApi.subscribe', () => {
  it('POST /billing/subscriptions/subscribe/', async () => {
    const data = { plan_id: 2, payment_method: 'card' }
    await billingApi.subscribe(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/billing/subscriptions/subscribe/', data)
  })
})

describe('billingApi.cancelSubscription', () => {
  it('POST /billing/subscriptions/cancel/', async () => {
    await billingApi.cancelSubscription()
    expect(mockRequest.post).toHaveBeenCalledWith('/billing/subscriptions/cancel/')
  })
})

describe('billingApi.reactivateSubscription', () => {
  it('POST /billing/subscriptions/reactivate/', async () => {
    await billingApi.reactivateSubscription()
    expect(mockRequest.post).toHaveBeenCalledWith('/billing/subscriptions/reactivate/')
  })
})

describe('billingApi.getUsage', () => {
  it('GET /billing/subscriptions/usage/', async () => {
    await billingApi.getUsage()
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/subscriptions/usage/')
  })
})

describe('billingApi.getUsageHistory', () => {
  it('GET /billing/usage/', async () => {
    await billingApi.getUsageHistory({ start_date: '2026-04-01' })
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/usage/', { start_date: '2026-04-01' })
  })
})

describe('billingApi.getUsageHistoryDetail', () => {
  it('GET /billing/usage/history/', async () => {
    await billingApi.getUsageHistoryDetail()
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/usage/history/', {})
  })
})

describe('billingApi.getInvoices', () => {
  it('GET /billing/invoices/', async () => {
    await billingApi.getInvoices()
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/invoices/', {})
  })
})

describe('billingApi.getInvoice', () => {
  it('GET /billing/invoices/:id/', async () => {
    await billingApi.getInvoice(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/invoices/1/')
  })
})

describe('billingApi.downloadInvoice', () => {
  it('GET /billing/invoices/:id/download/', async () => {
    await billingApi.downloadInvoice(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/invoices/1/download/')
  })
})

describe('billingApi.getPayments', () => {
  it('GET /billing/payments/', async () => {
    await billingApi.getPayments()
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/payments/', {})
  })
})

describe('billingApi.validateCoupon', () => {
  it('POST /billing/coupons/validate/', async () => {
    await billingApi.validateCoupon('SAVE20')
    expect(mockRequest.post).toHaveBeenCalledWith('/billing/coupons/validate/', { code: 'SAVE20' })
  })
})

describe('billingApi.getMyCoupons', () => {
  it('GET /billing/coupons/my/', async () => {
    await billingApi.getMyCoupons()
    expect(mockRequest.get).toHaveBeenCalledWith('/billing/coupons/my/')
  })
})
