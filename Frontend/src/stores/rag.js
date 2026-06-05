import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ragApi } from '@/api/rag'

export const useRAGStore = defineStore('rag', () => {
  // State
  const collections = ref([])
  const currentCollection = ref(null)
  const pipelines = ref([])
  const currentPipeline = ref(null)
  const vectorStores = ref([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref(null)

  // Query results
  const queryResults = ref([])
  const isQuerying = ref(false)

  // Getters
  const totalDocuments = computed(() =>
    collections.value.reduce((sum, c) => sum + c.document_count, 0)
  )

  const totalChunks = computed(() =>
    collections.value.reduce((sum, c) => sum + c.chunk_count, 0)
  )

  // Actions - Collections
  async function fetchCollections(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await ragApi.getCollections(params)
      collections.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchCollection(id) {
    isLoading.value = true
    error.value = null
    try {
      const response = await ragApi.getCollection(id)
      currentCollection.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createCollection(data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await ragApi.createCollection(data)
      collections.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateCollection(id, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await ragApi.updateCollection(id, data)
      const index = collections.value.findIndex(c => c.id === id)
      if (index !== -1) {
        collections.value[index] = { ...collections.value[index], ...response }
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteCollection(id) {
    isLoading.value = true
    error.value = null
    try {
      await ragApi.deleteCollection(id)
      collections.value = collections.value.filter(c => c.id !== id)
      if (currentCollection.value?.id === id) {
        currentCollection.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function addDocument(collectionId, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await ragApi.addDocument(collectionId, data)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function addUrl(collectionId, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await ragApi.addUrl(collectionId, data)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function clearCollection(id) {
    try {
      await ragApi.clearCollection(id)
      const collection = collections.value.find(c => c.id === id)
      if (collection) {
        collection.document_count = 0
        collection.chunk_count = 0
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Actions - Pipelines
  async function fetchPipelines(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await ragApi.getPipelines(params)
      pipelines.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPipeline(id) {
    isLoading.value = true
    error.value = null
    try {
      const response = await ragApi.getPipeline(id)
      currentPipeline.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createPipeline(data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await ragApi.createPipeline(data)
      pipelines.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updatePipeline(id, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await ragApi.updatePipeline(id, data)
      const index = pipelines.value.findIndex(p => p.id === id)
      if (index !== -1) {
        pipelines.value[index] = { ...pipelines.value[index], ...response }
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deletePipeline(id) {
    isLoading.value = true
    error.value = null
    try {
      await ragApi.deletePipeline(id)
      pipelines.value = pipelines.value.filter(p => p.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Actions - Query
  async function queryPipeline(pipelineId, query) {
    isQuerying.value = true
    error.value = null
    try {
      const response = await ragApi.queryPipeline(pipelineId, { query })
      queryResults.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isQuerying.value = false
    }
  }

  async function retrieveFromPipeline(pipelineId, query) {
    isQuerying.value = true
    error.value = null
    try {
      const response = await ragApi.retrieveFromPipeline(pipelineId, { query })
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isQuerying.value = false
    }
  }

  // Actions - Vector Stores
  async function fetchVectorStores(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await ragApi.getVectorStores(params)
      vectorStores.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createVectorStore(data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await ragApi.createVectorStore(data)
      vectorStores.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateVectorStore(id, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await ragApi.updateVectorStore(id, data)
      const index = vectorStores.value.findIndex(v => v.id === id)
      if (index !== -1) {
        vectorStores.value[index] = { ...vectorStores.value[index], ...response }
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteVectorStore(id) {
    isLoading.value = true
    error.value = null
    try {
      await ragApi.deleteVectorStore(id)
      vectorStores.value = vectorStores.value.filter(v => v.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function testConnection(id) {
    try {
      return await ragApi.testVectorStoreConnection(id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  function clearQueryResults() {
    queryResults.value = []
  }

  function clearStore() {
    collections.value = []
    currentCollection.value = null
    pipelines.value = []
    currentPipeline.value = null
    vectorStores.value = []
    queryResults.value = []
    error.value = null
  }

  return {
    // State
    collections,
    currentCollection,
    pipelines,
    currentPipeline,
    vectorStores,
    isLoading,
    isSaving,
    isQuerying,
    error,
    queryResults,

    // Getters
    totalDocuments,
    totalChunks,

    // Actions
    fetchCollections,
    fetchCollection,
    createCollection,
    updateCollection,
    deleteCollection,
    addDocument,
    addUrl,
    clearCollection,

    fetchPipelines,
    fetchPipeline,
    createPipeline,
    updatePipeline,
    deletePipeline,
    queryPipeline,
    retrieveFromPipeline,

    fetchVectorStores,
    createVectorStore,
    updateVectorStore,
    deleteVectorStore,
    testConnection,

    clearQueryResults,
    clearStore
  }
})
