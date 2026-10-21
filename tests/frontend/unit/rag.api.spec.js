/**
 * RAG API 单元测试
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

const ragApi = require('@/api/rag').default

const transport = expect.objectContaining({ preserveRequestKeys: true, preserveResponseKeys: true })
beforeEach(() => jest.clearAllMocks())

// Vector Stores
describe('ragApi.getVectorStores', () => {
  it('GET /rag/vector-stores/', async () => {
    await ragApi.getVectorStores()
    expect(mockRequest.get).toHaveBeenCalledWith('/rag/vector-stores/', {}, transport)
  })
})

describe('ragApi.getVectorStore', () => {
  it('GET /rag/vector-stores/:id/', async () => {
    await ragApi.getVectorStore(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/rag/vector-stores/1/', {}, transport)
  })
})

describe('ragApi.createVectorStore', () => {
  it('POST /rag/vector-stores/', async () => {
    const data = { name: '知识库', type: 'qdrant' }
    await ragApi.createVectorStore(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/rag/vector-stores/', data, transport)
  })
})

describe('ragApi.updateVectorStore', () => {
  it('PATCH /rag/vector-stores/:id/', async () => {
    await ragApi.updateVectorStore(1, { name: '更新' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/rag/vector-stores/1/', { name: '更新' }, transport)
  })
})

describe('ragApi.deleteVectorStore', () => {
  it('DELETE /rag/vector-stores/:id/', async () => {
    await ragApi.deleteVectorStore(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/rag/vector-stores/1/', transport)
  })
})

describe('ragApi.testVectorStoreConnection', () => {
  it('POST /rag/vector-stores/:id/test_connection/', async () => {
    await ragApi.testVectorStoreConnection(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/rag/vector-stores/1/test_connection/', {}, transport)
  })
})

describe('ragApi.createVectorStoreCollection', () => {
  it('POST /rag/vector-stores/:id/create_collection/', async () => {
    await ragApi.createVectorStoreCollection(1, { name: 'col', dimension: 1536 })
    expect(mockRequest.post).toHaveBeenCalledWith('/rag/vector-stores/1/create_collection/', { name: 'col', dimension: 1536 }, transport)
  })
})

// Collections
describe('ragApi.getCollections', () => {
  it('GET /rag/collections/', async () => {
    await ragApi.getCollections()
    expect(mockRequest.get).toHaveBeenCalledWith('/rag/collections/', {}, transport)
  })
})

describe('ragApi.createCollection', () => {
  it('POST /rag/collections/', async () => {
    const data = { name: '产品文档', vector_store: 1 }
    await ragApi.createCollection(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/rag/collections/', data, transport)
  })
})

describe('ragApi.deleteCollection', () => {
  it('DELETE /rag/collections/:id/', async () => {
    await ragApi.deleteCollection(5)
    expect(mockRequest.delete).toHaveBeenCalledWith('/rag/collections/5/', transport)
  })
})

describe('ragApi.addDocument', () => {
  it('POST /rag/collections/:id/add_document/', async () => {
    const data = { title: '文档1', content: '内容' }
    await ragApi.addDocument(5, data)
    expect(mockRequest.post).toHaveBeenCalledWith('/rag/collections/5/add_document/', data, transport)
  })
})

describe('ragApi.addUrl', () => {
  it('POST /rag/collections/:id/add_url/', async () => {
    await ragApi.addUrl(5, { url: 'https://example.com' })
    expect(mockRequest.post).toHaveBeenCalledWith('/rag/collections/5/add_url/', { url: 'https://example.com' }, transport)
  })
})

describe('ragApi.clearCollection', () => {
  it('DELETE /rag/collections/:id/clear/', async () => {
    await ragApi.clearCollection(5)
    expect(mockRequest.delete).toHaveBeenCalledWith('/rag/collections/5/clear/', transport)
  })
})

// Documents
describe('ragApi.getDocuments', () => {
  it('GET /rag/documents/', async () => {
    await ragApi.getDocuments()
    expect(mockRequest.get).toHaveBeenCalledWith('/rag/documents/', {}, transport)
  })
})

describe('ragApi.getDocument', () => {
  it('GET /rag/documents/:id/', async () => {
    await ragApi.getDocument(100)
    expect(mockRequest.get).toHaveBeenCalledWith('/rag/documents/100/', {}, transport)
  })
})

describe('ragApi.deleteDocument', () => {
  it('DELETE /rag/documents/:id/', async () => {
    await ragApi.deleteDocument(100)
    expect(mockRequest.delete).toHaveBeenCalledWith('/rag/documents/100/', transport)
  })
})

describe('ragApi.reprocessDocument', () => {
  it('POST /rag/documents/:id/reprocess/', async () => {
    await ragApi.reprocessDocument(100)
    expect(mockRequest.post).toHaveBeenCalledWith('/rag/documents/100/reprocess/', {}, transport)
  })
})

describe('ragApi.getDocumentChunks', () => {
  it('GET /rag/documents/:id/chunks/', async () => {
    await ragApi.getDocumentChunks(100)
    expect(mockRequest.get).toHaveBeenCalledWith('/rag/documents/100/chunks/', {}, transport)
  })
})

// Pipelines
describe('ragApi.getPipelines', () => {
  it('GET /rag/pipelines/', async () => {
    await ragApi.getPipelines()
    expect(mockRequest.get).toHaveBeenCalledWith('/rag/pipelines/', {}, transport)
  })
})

describe('ragApi.createPipeline', () => {
  it('POST /rag/pipelines/', async () => {
    const data = { name: '检索流水线', collection: 5 }
    await ragApi.createPipeline(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/rag/pipelines/', data, transport)
  })
})

describe('ragApi.queryPipeline', () => {
  it('POST /rag/pipelines/:id/query/', async () => {
    await ragApi.queryPipeline(1, { query: '什么是RAG?', top_k: 3 })
    expect(mockRequest.post).toHaveBeenCalledWith('/rag/pipelines/1/query/', { query: '什么是RAG?', top_k: 3 }, transport)
  })
})

describe('ragApi.retrieveFromPipeline', () => {
  it('GET /rag/pipelines/:id/retrieve/', async () => {
    await ragApi.retrieveFromPipeline(1, { query: '测试' })
    expect(mockRequest.get).toHaveBeenCalledWith('/rag/pipelines/1/retrieve/', { query: '测试' }, transport)
  })
})

describe('ragApi.deletePipeline', () => {
  it('DELETE /rag/pipelines/:id/', async () => {
    await ragApi.deletePipeline(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/rag/pipelines/1/', transport)
  })
})
