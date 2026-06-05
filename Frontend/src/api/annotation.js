/**
 * Annotation API module for managing data annotation projects.
 */

import { api } from './index'

/**
 * Annotation API endpoints
 */
export const annotationApi = {
  /**
   * List annotation projects
   * @param {Object} params - Query parameters
   * @param {string} params.status - Filter by status (draft, in_progress, completed)
   * @param {string} params.annotation_type - Filter by annotation type
   * @param {string} params.search - Search by name or dataset name
   * @param {string} params.dataset - Filter by dataset ID
   * @param {number} params.page - Page number
   * @param {number} params.pageSize - Page size
   */
  list(params = {}) {
    return api.get('/annotations/projects/', { params }).then(response => {
      // Handle DRF response format: { count, results, next, previous }
      if (response && typeof response === 'object' && 'results' in response) {
        return {
          results: response.results || [],
          count: response.count || 0
        }
      }
      return response
    })
  },

  /**
   * Get a single annotation project by ID
   * @param {string} id - Project ID
   */
  get(id) {
    return api.get(`/annotations/projects/${id}/`)
  },

  /**
   * Create a new annotation project
   * @param {Object} data - Project data
   * @param {string} data.name - Project name
   * @param {string} data.annotation_type - Annotation type
   * @param {Array} data.labels - Labels array
   * @param {string} data.dataset - Dataset ID
   * @param {boolean} data.model_assisted - Enable AI-assisted annotation
   * @param {string} data.model_id - LLM model ID (optional)
   */
  create(data) {
    return api.post('/annotations/projects/', data)
  },

  /**
   * Update an annotation project
   * @param {string} id - Project ID
   * @param {Object} data - Updated data
   */
  update(id, data) {
    return api.patch(`/annotations/projects/${id}/`, data)
  },

  /**
   * Delete an annotation project
   * @param {string} id - Project ID
   */
  delete(id) {
    return api.delete(`/annotations/projects/${id}/`)
  },

  /**
   * Get annotation items for a project
   * @param {string} projectId - Project ID
   * @param {Object} params - Query parameters
   * @param {string} params.status - Filter by status (pending, annotated, skipped)
   * @param {number} params.page - Page number
   * @param {number} params.pageSize - Page size (default 20)
   */
  getItems(projectId, params = {}) {
    return api.get(`/annotations/projects/${projectId}/items/`, { params }).then(response => {
      // Handle DRF response format: { count, results, next, previous }
      return {
        items: response.results || [],
        total: response.count || 0,
        page: response.page || 1,
        page_size: response.page_size || 20,
        total_pages: response.total_pages || 1
      }
    })
  },

  /**
   * Update an annotation item
   * @param {string} itemId - Item ID
   * @param {Object} data - Updated data
   * @param {string} data.label - The label to assign
   * @param {string} data.status - Status (pending, annotated, skipped)
   */
  updateItem(itemId, data) {
    return api.patch(`/annotations/items/${itemId}/`, data)
  },

  /**
   * Bulk update multiple annotation items
   * @param {Array<string>} itemIds - Array of item IDs
   * @param {Object} data - Update data
   * @param {string} data.label - Label to assign
   * @param {string} data.status - Status to set
   */
  bulkUpdateItems(itemIds, data) {
    return api.post('/annotations/items/bulk_update/', {
      item_ids: itemIds,
      ...data
    })
  },

  /**
   * Generate AI pre-labels for pending items
   * @param {string} projectId - Project ID
   * @param {string} modelId - Optional LLM model ID
   */
  preLabel(projectId, modelId = null) {
    return api.post(`/annotations/projects/${projectId}/pre_label/`, {
      model_id: modelId
    })
  },

  /**
   * Export annotations
   * @param {string} projectId - Project ID
   * @param {string} format - Export format (json, csv)
   */
  export(projectId, format = 'json') {
    return api.get(`/annotations/projects/${projectId}/export/?format=${format}`, {
      responseType: 'blob'
    })
  },

  /**
   * Start annotation (initialize items from dataset)
   * @param {string} projectId - Project ID
   */
  start(projectId) {
    return api.post(`/annotations/projects/${projectId}/start/`)
  },

  /**
   * Complete annotation project
   * @param {string} projectId - Project ID
   */
  complete(projectId) {
    return api.post(`/annotations/projects/${projectId}/complete/`)
  },

  /**
   * Get annotation statistics
   */
  getStats() {
    return api.get('/annotations/projects/stats/')
  }
}

/**
 * Open annotation workspace in new tab/window
 * @param {string} projectId - Project ID
 */
export function openAnnotationWorkspace(projectId) {
  const url = `/annotations/${projectId}`
  window.open(url, '_blank')
}

/**
 * Generate color from label name (for consistent label colors)
 * @param {string} label - Label name
 * @returns {string} HSL color string
 */
export function getLabelColor(label) {
  let hash = 0
  for (let i = 0; i < label.length; i++) {
    hash = label.charCodeAt(i) + ((hash << 5) - hash)
  }

  const hue = Math.abs(hash % 360)
  return `hsl(${hue}, 65%, 50%)`
}

/**
 * Generate lighter color variant for backgrounds
 * @param {string} label - Label name
 * @returns {string} HSL color string
 */
export function getLabelBgColor(label) {
  let hash = 0
  for (let i = 0; i < label.length; i++) {
    hash = label.charCodeAt(i) + ((hash << 5) - hash)
  }

  const hue = Math.abs(hash % 360)
  return `hsla(${hue}, 65%, 50%, 0.15)`
}

export default annotationApi
