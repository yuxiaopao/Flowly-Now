/**
 * Shared CRUD Store Composable
 * Provides common CRUD operations for Pinia stores
 */

import { ref, computed } from 'vue'

/**
 * Create a CRUD store with common operations
 * @param {Object} options - Configuration options
 * @param {Function} options.api - API object with getList, getById, create, update, delete methods
 * @param {String} options.name - Store name for error messages
 * @param {Function} [options.transformResponse] - Optional response transformation
 * @param {Function} [options.transformRequest] - Optional request transformation
 * @returns {Object} CRUD state and actions
 */
export function useCRUDStore(options = {}) {
  const {
    api,
    name = 'item',
    transformResponse = (r) => r,
    transformRequest = (r) => r
  } = options

  if (!api || typeof api.getList !== 'function' || typeof api.getById !== 'function') {
    throw new Error('Invalid API object: required methods (getList, getById) are missing')
  }

  // State
  const items = ref([])
  const currentItem = ref(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref(null)

  // Getters
  const itemCount = computed(() => items.value.length)
  const hasError = computed(() => error.value !== null)

  // Actions
  async function fetchItems(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.getList(params)
      const data = response.results || response
      items.value = transformResponse(Array.isArray(data) ? data : [])
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchItem(id) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.getById(id)
      currentItem.value = transformResponse(response)
      return currentItem.value
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createItem(data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await api.create(transformRequest(data))
      items.value.unshift(transformResponse(response))
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateItem(id, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await api.update(id, transformRequest(data))
      const index = items.value.findIndex(item => item.id === id)
      if (index !== -1) {
        items.value[index] = transformResponse(response)
      }
      if (currentItem.value?.id === id) {
        currentItem.value = { ...currentItem.value, ...transformResponse(response) }
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteItem(id) {
    isSaving.value = true
    error.value = null
    try {
      await api.delete(id)
      items.value = items.value.filter(item => item.id !== id)
      if (currentItem.value?.id === id) {
        currentItem.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearStore() {
    items.value = []
    currentItem.value = null
    error.value = null
  }

  return {
    // State
    items,
    currentItem,
    isLoading,
    isSaving,
    error,
    // Getters
    itemCount,
    hasError,
    // Actions
    fetchItems,
    fetchItem,
    createItem,
    updateItem,
    deleteItem,
    clearError,
    clearStore
  }
}
