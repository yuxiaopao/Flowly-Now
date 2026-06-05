/**
 * 监控 API 单元测试
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

const monitoringApi = require('@/api/monitoring').default

beforeEach(() => jest.clearAllMocks())

// Alerts
describe('monitoringApi.getAlerts', () => {
  it('GET /monitoring/alerts/', async () => {
    await monitoringApi.getAlerts()
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/alerts/', {})
  })
  it('携带过滤参数', async () => {
    await monitoringApi.getAlerts({ severity: 'critical' })
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/alerts/', { severity: 'critical' })
  })
})

describe('monitoringApi.getAlert', () => {
  it('GET /monitoring/alerts/:id/', async () => {
    await monitoringApi.getAlert(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/alerts/1/')
  })
})

describe('monitoringApi.acknowledgeAlert', () => {
  it('POST /monitoring/alerts/:id/acknowledge/', async () => {
    await monitoringApi.acknowledgeAlert(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/monitoring/alerts/1/acknowledge/')
  })
})

describe('monitoringApi.resolveAlert', () => {
  it('POST /monitoring/alerts/:id/resolve/ 携带 note', async () => {
    await monitoringApi.resolveAlert(1, '已修复')
    expect(mockRequest.post).toHaveBeenCalledWith('/monitoring/alerts/1/resolve/', { note: '已修复' })
  })
})

describe('monitoringApi.muteAlert', () => {
  it('POST /monitoring/alerts/:id/mute/', async () => {
    await monitoringApi.muteAlert(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/monitoring/alerts/1/mute/')
  })
})

describe('monitoringApi.getAlertSummary', () => {
  it('GET /monitoring/alerts/summary/', async () => {
    await monitoringApi.getAlertSummary()
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/alerts/summary/')
  })
})

// Alert Rules
describe('monitoringApi.getAlertRules', () => {
  it('GET /monitoring/rules/', async () => {
    await monitoringApi.getAlertRules()
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/rules/', {})
  })
})

describe('monitoringApi.createAlertRule', () => {
  it('POST /monitoring/rules/', async () => {
    const data = { name: '高CPU', condition: 'cpu > 90' }
    await monitoringApi.createAlertRule(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/monitoring/rules/', data)
  })
})

describe('monitoringApi.updateAlertRule', () => {
  it('PATCH /monitoring/rules/:id/', async () => {
    await monitoringApi.updateAlertRule(1, { name: '更新' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/monitoring/rules/1/', { name: '更新' })
  })
})

describe('monitoringApi.deleteAlertRule', () => {
  it('DELETE /monitoring/rules/:id/', async () => {
    await monitoringApi.deleteAlertRule(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/monitoring/rules/1/')
  })
})

// Metrics
describe('monitoringApi.getMetrics', () => {
  it('GET /monitoring/metrics/', async () => {
    await monitoringApi.getMetrics({ start: '2026-01-01' })
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/metrics/', { start: '2026-01-01' })
  })
})

describe('monitoringApi.getDashboardMetrics', () => {
  it('GET /monitoring/metrics/dashboard/', async () => {
    await monitoringApi.getDashboardMetrics()
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/metrics/dashboard/')
  })
})

describe('monitoringApi.getMetricsAggregate', () => {
  it('GET /monitoring/metrics/aggregate/', async () => {
    await monitoringApi.getMetricsAggregate({ group_by: 'hour' })
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/metrics/aggregate/', { group_by: 'hour' })
  })
})

describe('monitoringApi.exportMetrics', () => {
  it('GET /monitoring/metrics/export/', async () => {
    await monitoringApi.exportMetrics({ format: 'csv' })
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/metrics/export/', { format: 'csv' })
  })
})

// Channels
describe('monitoringApi.getChannels', () => {
  it('GET /monitoring/channels/', async () => {
    await monitoringApi.getChannels()
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/channels/', {})
  })
})

describe('monitoringApi.createChannel', () => {
  it('POST /monitoring/channels/', async () => {
    const data = { name: 'Slack', type: 'slack' }
    await monitoringApi.createChannel(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/monitoring/channels/', data)
  })
})

describe('monitoringApi.testChannel', () => {
  it('POST /monitoring/channels/:id/test/', async () => {
    await monitoringApi.testChannel(5)
    expect(mockRequest.post).toHaveBeenCalledWith('/monitoring/channels/5/test/')
  })
})

describe('monitoringApi.deleteChannel', () => {
  it('DELETE /monitoring/channels/:id/', async () => {
    await monitoringApi.deleteChannel(5)
    expect(mockRequest.delete).toHaveBeenCalledWith('/monitoring/channels/5/')
  })
})

// Execution Logs
describe('monitoringApi.getExecutionLogs', () => {
  it('GET /monitoring/logs/', async () => {
    await monitoringApi.getExecutionLogs({ level: 'error' })
    expect(mockRequest.get).toHaveBeenCalledWith('/monitoring/logs/', { level: 'error' })
  })
})
