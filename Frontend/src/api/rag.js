import { request } from './index'

/**
 * @typedef {Object} RAGAPI
 * @property {function(Object=): Promise<{count:number, results: import('@/types/rag').VectorStore[]}>} getVectorStores
 * @property {function(string|number): Promise<import('@/types/rag').VectorStore>} getVectorStore
 * @property {function(import('@/types/rag').CreateVectorStoreData): Promise<import('@/types/rag').VectorStore>} createVectorStore
 * @property {function(string|number, Object): Promise<import('@/types/rag').VectorStore>} updateVectorStore
 * @property {function(string|number): Promise<void>} deleteVectorStore
 * @property {function(string|number): Promise<import('@/types/rag').VectorStoreConnectionTest>} testVectorStoreConnection
 * @property {function(string|number, Object): Promise<import('@/types/rag').VectorStore>} createVectorStoreCollection
 * @property {function(Object=): Promise<{count:number, results: import('@/types/rag').DocumentCollection[]}>} getCollections
 * @property {function(string|number): Promise<import('@/types/rag').DocumentCollection>} getCollection
 * @property {function(import('@/types/rag').CreateCollectionData): Promise<import('@/types/rag').DocumentCollection>} createCollection
 * @property {function(string|number, Object): Promise<import('@/types/rag').DocumentCollection>} updateCollection
 * @property {function(string|number): Promise<void>} deleteCollection
 * @property {function(string|number, import('@/types/rag').CreateDocumentData): Promise<import('@/types/rag').Document>} addDocument
 * @property {function(string|number, import('@/types/rag').CreateURLDocumentData): Promise<import('@/types/rag').Document>} addUrl
 * @property {function(string|number): Promise<void>} clearCollection
 * @property {function(Object=): Promise<{count:number, results: import('@/types/rag').Document[]}>} getDocuments
 * @property {function(string|number): Promise<import('@/types/rag').Document>} getDocument
 * @property {function(string|number): Promise<void>} deleteDocument
 * @property {function(string|number): Promise<import('@/types/rag').Document>} reprocessDocument
 * @property {function(string|number): Promise<import('@/types/rag').Chunk[]>} getDocumentChunks
 * @property {function(Object=): Promise<{count:number, results: import('@/types/rag').RAGPipeline[]}>} getPipelines
 * @property {function(string|number): Promise<import('@/types/rag').RAGPipeline>} getPipeline
 * @property {function(import('@/types/rag').CreatePipelineData): Promise<import('@/types/rag').RAGPipeline>} createPipeline
 * @property {function(string|number, Object): Promise<import('@/types/rag').RAGPipeline>} updatePipeline
 * @property {function(string|number): Promise<void>} deletePipeline
 * @property {function(string|number, import('@/types/rag').RAGQueryRequest): Promise<import('@/types/rag').RAGQueryResponse>} queryPipeline
 * @property {function(string|number, Object): Promise<import('@/types/rag').CollectionSearchResult>} retrieveFromPipeline
 */

/** @type {RAGAPI} */
export const ragApi = {
  // Vector Stores
  /** @param {Object=} params @returns {Promise<{count:number, results: import('@/types/rag').VectorStore[]}>} */
  getVectorStores(params = {}) {
    return request.get('/rag/vector-stores/', params)
  },

  /** @param {string|number} id @returns {Promise<import('@/types/rag').VectorStore>} */
  getVectorStore(id) {
    return request.get(`/rag/vector-stores/${id}/`)
  },

  /** @param {import('@/types/rag').CreateVectorStoreData} data @returns {Promise<import('@/types/rag').VectorStore>} */
  createVectorStore(data) {
    return request.post('/rag/vector-stores/', data)
  },

  /** @param {string|number} id @param {Object} data @returns {Promise<import('@/types/rag').VectorStore>} */
  updateVectorStore(id, data) {
    return request.patch(`/rag/vector-stores/${id}/`, data)
  },

  /** @param {string|number} id @returns {Promise<void>} */
  deleteVectorStore(id) {
    return request.delete(`/rag/vector-stores/${id}/`)
  },

  /** @param {string|number} id @returns {Promise<import('@/types/rag').VectorStoreConnectionTest>} */
  testVectorStoreConnection(id) {
    return request.post(`/rag/vector-stores/${id}/test_connection/`)
  },

  /** @param {string|number} id @param {Object} data @returns {Promise<import('@/types/rag').VectorStore>} */
  createVectorStoreCollection(id, data) {
    return request.post(`/rag/vector-stores/${id}/create_collection/`, data)
  },

  // Document Collections
  /** @param {Object=} params @returns {Promise<{count:number, results: import('@/types/rag').DocumentCollection[]}>} */
  getCollections(params = {}) {
    return request.get('/rag/collections/', params)
  },

  /** @param {string|number} id @returns {Promise<import('@/types/rag').DocumentCollection>} */
  getCollection(id) {
    return request.get(`/rag/collections/${id}/`)
  },

  /** @param {import('@/types/rag').CreateCollectionData} data @returns {Promise<import('@/types/rag').DocumentCollection>} */
  createCollection(data) {
    return request.post('/rag/collections/', data)
  },

  /** @param {string|number} id @param {Object} data @returns {Promise<import('@/types/rag').DocumentCollection>} */
  updateCollection(id, data) {
    return request.patch(`/rag/collections/${id}/`, data)
  },

  /** @param {string|number} id @returns {Promise<void>} */
  deleteCollection(id) {
    return request.delete(`/rag/collections/${id}/`)
  },

  /** @param {string|number} collectionId @param {import('@/types/rag').CreateDocumentData} data @returns {Promise<import('@/types/rag').Document>} */
  addDocument(collectionId, data) {
    return request.post(`/rag/collections/${collectionId}/add_document/`, data)
  },

  /** @param {string|number} collectionId @param {import('@/types/rag').CreateURLDocumentData} data @returns {Promise<import('@/types/rag').Document>} */
  addUrl(collectionId, data) {
    return request.post(`/rag/collections/${collectionId}/add_url/`, data)
  },

  /** @param {string|number} collectionId @returns {Promise<void>} */
  clearCollection(collectionId) {
    return request.delete(`/rag/collections/${collectionId}/clear/`)
  },

  // Documents
  /** @param {Object=} params @returns {Promise<{count:number, results: import('@/types/rag').Document[]}>} */
  getDocuments(params = {}) {
    return request.get('/rag/documents/', params)
  },

  /** @param {string|number} id @returns {Promise<import('@/types/rag').Document>} */
  getDocument(id) {
    return request.get(`/rag/documents/${id}/`)
  },

  /** @param {string|number} id @returns {Promise<void>} */
  deleteDocument(id) {
    return request.delete(`/rag/documents/${id}/`)
  },

  /** @param {string|number} id @returns {Promise<import('@/types/rag').Document>} */
  reprocessDocument(id) {
    return request.post(`/rag/documents/${id}/reprocess/`)
  },

  /** @param {string|number} id @returns {Promise<import('@/types/rag').Chunk[]>} */
  getDocumentChunks(id) {
    return request.get(`/rag/documents/${id}/chunks/`)
  },

  /** @param {string|number} collectionId @param {FormData} formData */
  uploadFile(collectionId, formData) {
    return request.post(`/rag/collections/${collectionId}/upload_file/`, formData)
  },

  /** @param {string|number} collectionId @param {{ query?: string, top_k?: number }} params */
  searchCollection(collectionId, params = {}) {
    return request.get(`/rag/collections/${collectionId}/search/`, params)
  },

  /** @param {string|number} collectionId */
  getCollectionStats(collectionId) {
    return request.get(`/rag/collections/${collectionId}/stats/`)
  },

  // RAG Pipelines
  /** @param {Object=} params @returns {Promise<{count:number, results: import('@/types/rag').RAGPipeline[]}>} */
  getPipelines(params = {}) {
    return request.get('/rag/pipelines/', params)
  },

  /** @param {string|number} id @returns {Promise<import('@/types/rag').RAGPipeline>} */
  getPipeline(id) {
    return request.get(`/rag/pipelines/${id}/`)
  },

  /** @param {import('@/types/rag').CreatePipelineData} data @returns {Promise<import('@/types/rag').RAGPipeline>} */
  createPipeline(data) {
    return request.post('/rag/pipelines/', data)
  },

  /** @param {string|number} id @param {Object} data @returns {Promise<import('@/types/rag').RAGPipeline>} */
  updatePipeline(id, data) {
    return request.patch(`/rag/pipelines/${id}/`, data)
  },

  /** @param {string|number} id @returns {Promise<void>} */
  deletePipeline(id) {
    return request.delete(`/rag/pipelines/${id}/`)
  },

  /** @param {string|number} id @param {import('@/types/rag').RAGQueryRequest} data @returns {Promise<import('@/types/rag').RAGQueryResponse>} */
  queryPipeline(id, data) {
    return request.post(`/rag/pipelines/${id}/query/`, data)
  },

  /** @param {string|number} id @param {Object} params @returns {Promise<import('@/types/rag').CollectionSearchResult>} */
  retrieveFromPipeline(id, params) {
    return request.get(`/rag/pipelines/${id}/retrieve/`, params)
  }
}

export default ragApi
