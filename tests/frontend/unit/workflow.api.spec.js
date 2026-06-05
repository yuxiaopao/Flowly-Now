/**
 * 工作流 API 单元测试
 * 测试 workflowApi 的所有方法
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

const { workflowApi } = require('@/api/workflow')

beforeEach(() => jest.clearAllMocks())

// 工作流 CRUD
describe('workflowApi.getList', () => {
  it('GET /workflows/ 默认无参数', async () => {
    await workflowApi.getList()
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/', {})
  })

  it('GET /workflows/ 携带过滤参数', async () => {
    await workflowApi.getList({ page: 2, status: 'active', search: 'test' })
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/', { page: 2, status: 'active', search: 'test' })
  })
})

describe('workflowApi.getById', () => {
  it('GET /workflows/:id/', async () => {
    await workflowApi.getById(42)
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/42/')
  })
})

describe('workflowApi.create', () => {
  it('POST /workflows/ 携带工作流数据', async () => {
    const data = { name: '新工作流', description: '描述', status: 'draft', tags: ['ai'] }
    await workflowApi.create(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/', data)
  })
})

describe('workflowApi.update', () => {
  it('PATCH /workflows/:id/', async () => {
    await workflowApi.update(5, { name: '更新名称' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/workflows/5/', { name: '更新名称' })
  })
})

describe('workflowApi.delete', () => {
  it('DELETE /workflows/:id/', async () => {
    await workflowApi.delete(7)
    expect(mockRequest.delete).toHaveBeenCalledWith('/workflows/7/')
  })
})

describe('workflowApi.duplicate', () => {
  it('POST /workflows/:id/duplicate/', async () => {
    await workflowApi.duplicate(10)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/10/duplicate/')
  })
})

describe('workflowApi.export', () => {
  it('GET /workflows/:id/export/', async () => {
    await workflowApi.export(3)
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/3/export/')
  })
})

describe('workflowApi.import', () => {
  it('POST /workflows/import/ 携带 multipart/form-data', async () => {
    const formData = new FormData()
    await workflowApi.import(formData)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/import/', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  })
})

// 节点操作
describe('workflowApi.getNodes', () => {
  it('GET /workflows/nodes/ 按 workflowId 过滤', async () => {
    await workflowApi.getNodes(5)
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/nodes/', { workflow: 5 })
  })
})

describe('workflowApi.createNode', () => {
  it('POST /workflows/nodes/ 附带 workflow ID', async () => {
    await workflowApi.createNode(5, { node_type: 'llm', position_x: 100, position_y: 200 })
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/nodes/', { node_type: 'llm', position_x: 100, position_y: 200, workflow: 5 })
  })
})

describe('workflowApi.updateNode', () => {
  it('PATCH /workflows/nodes/:id/', async () => {
    await workflowApi.updateNode(3, { position_x: 300 })
    expect(mockRequest.patch).toHaveBeenCalledWith('/workflows/nodes/3/', { position_x: 300 })
  })
})

describe('workflowApi.deleteNode', () => {
  it('DELETE /workflows/nodes/:id/', async () => {
    await workflowApi.deleteNode(8)
    expect(mockRequest.delete).toHaveBeenCalledWith('/workflows/nodes/8/')
  })
})

describe('workflowApi.saveNodePositions', () => {
  it('POST /workflows/nodes/batch_update_positions/', async () => {
    const positions = [{ id: 1, position: { x: 100, y: 200 } }]
    await workflowApi.saveNodePositions(positions)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/nodes/batch_update_positions/', { positions })
  })
})

describe('workflowApi.batchCreateNodes', () => {
  it('POST /workflows/nodes/batch_create/', async () => {
    const nodes = [{ node_type: 'start' }, { node_type: 'end' }]
    await workflowApi.batchCreateNodes(1, nodes)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/nodes/batch_create/', { workflow_id: 1, nodes })
  })
})

describe('workflowApi.getAvailableNodeTypes', () => {
  it('GET /workflows/nodes/available_types/', async () => {
    await workflowApi.getAvailableNodeTypes()
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/nodes/available_types/')
  })
})

// 连线操作
describe('workflowApi.getEdges', () => {
  it('GET /workflows/edges/ 按 workflowId 过滤', async () => {
    await workflowApi.getEdges(2)
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/edges/', { workflow: 2 })
  })
})

describe('workflowApi.createEdge', () => {
  it('POST /workflows/edges/', async () => {
    const data = { source_node: 1, target_node: 2, workflow: 5 }
    await workflowApi.createEdge(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/edges/', data)
  })
})

describe('workflowApi.updateEdge', () => {
  it('PATCH /workflows/edges/:id/', async () => {
    await workflowApi.updateEdge(10, { label: '新标签' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/workflows/edges/10/', { label: '新标签' })
  })
})

describe('workflowApi.deleteEdge', () => {
  it('DELETE /workflows/edges/:id/', async () => {
    await workflowApi.deleteEdge(10)
    expect(mockRequest.delete).toHaveBeenCalledWith('/workflows/edges/10/')
  })
})

describe('workflowApi.batchCreateEdges', () => {
  it('POST /workflows/edges/batch_create/', async () => {
    const edges = [{ source_node: 1, target_node: 2 }]
    await workflowApi.batchCreateEdges(5, edges)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/edges/batch_create/', { workflow_id: 5, edges })
  })
})

// 执行
describe('workflowApi.executeSync', () => {
  it('POST /workflows/:id/execute/ 同步模式', async () => {
    await workflowApi.executeSync(1, { key: 'value' })
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/1/execute/', { input_data: { key: 'value' }, is_async: false })
  })
})

describe('workflowApi.executeAsync', () => {
  it('POST /workflows/:id/execute/ 异步模式', async () => {
    await workflowApi.executeAsync(1, { key: 'value' })
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/1/execute/', { input_data: { key: 'value' }, is_async: true })
  })
})

describe('workflowApi.getExecution', () => {
  it('GET /workflows/executions/:id/', async () => {
    await workflowApi.getExecution(100)
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/executions/100/')
  })
})

describe('workflowApi.getExecutionHistory', () => {
  it('GET /workflows/executions/ 按 workflowId 过滤', async () => {
    await workflowApi.getExecutionHistory(3, { page: 1 })
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/executions/', { workflow: 3, page: 1 })
  })
})

describe('workflowApi.cancelExecution', () => {
  it('POST /workflows/executions/:id/cancel/', async () => {
    await workflowApi.cancelExecution(100)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/executions/100/cancel/')
  })
})

describe('workflowApi.pauseExecution', () => {
  it('POST /workflows/executions/:id/pause/', async () => {
    await workflowApi.pauseExecution(100)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/executions/100/pause/')
  })
})

describe('workflowApi.resumeExecution', () => {
  it('POST /workflows/executions/:id/resume/', async () => {
    await workflowApi.resumeExecution(100)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/executions/100/resume/')
  })
})

describe('workflowApi.getExecutionStatistics', () => {
  it('GET /workflows/executions/statistics/', async () => {
    await workflowApi.getExecutionStatistics()
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/executions/statistics/')
  })
})

// 模板
describe('workflowApi.getTemplates', () => {
  it('GET /workflows/templates/', async () => {
    await workflowApi.getTemplates()
    expect(mockRequest.get).toHaveBeenCalledWith('/workflows/templates/', {})
  })
})

describe('workflowApi.createFromTemplate', () => {
  it('POST /workflows/templates/:id/create_from_template/', async () => {
    await workflowApi.createFromTemplate(2, { name: '自定义名称' })
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/templates/2/create_from_template/', { name: '自定义名称' })
  })
})

// 验证
describe('workflowApi.validate', () => {
  it('POST /workflows/:id/validate/', async () => {
    await workflowApi.validate(5)
    expect(mockRequest.post).toHaveBeenCalledWith('/workflows/5/validate/')
  })
})
