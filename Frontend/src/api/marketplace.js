import { request } from './index'
import {
  getWorkflowTemplates,
  getTemplate,
  getFeaturedTemplates,
  getTemplatesByCategory,
  getTemplateCategories,
  getTemplateCategory,
} from './workflow'

function unwrapListResponse(response) {
  if (Array.isArray(response)) {
    return response
  }
  if (Array.isArray(response?.results)) {
    return response.results
  }
  return []
}

function unwrapPaginatedResponse(response) {
  if (response && typeof response === 'object' && Array.isArray(response.results)) {
    return {
      ...response,
      results: response.results,
      count: Number(response.count ?? response.results.length ?? 0),
    }
  }

  const results = unwrapListResponse(response)
  return {
    count: results.length,
    results,
  }
}

export const marketplaceApi = {
  // Workflow Templates
  getTemplates(params = {}) {
    return getWorkflowTemplates(params)
  },

  getTemplate(id) {
    return getTemplate(id)
  },

  createTemplate(data) {
    return request.post('/templates/', data)
  },

  updateTemplate(id, data) {
    return request.patch(`/templates/${id}/`, data)
  },

  deleteTemplate(id) {
    return request.delete(`/templates/${id}/`)
  },

  getFeaturedTemplates(params = {}) {
    return getFeaturedTemplates(params)
  },

  getTemplatesByCategory(params = {}) {
    return getTemplatesByCategory(params)
  },

  installTemplate(id) {
    return request.post(`/templates/${id}/install/`)
  },

  rateTemplate(id, rating) {
    return request.post(`/templates/${id}/rate/`, { rating })
  },

  getTemplateStats(id) {
    return request.get(`/templates/${id}/stats/`)
  },

  reportTemplate(id, reason) {
    return request.post(`/templates/${id}/report/`, { reason })
  },

  // Categories
  getCategories(params = {}) {
    return getTemplateCategories(params)
  },

  getCategory(id) {
    return getTemplateCategory(id)
  },

  getCategoryTemplates(id, params = {}) {
    return request.get('/templates/', { ...params, category: id }).then(unwrapPaginatedResponse)
  },

  // My Templates
  getMyTemplates(params = {}) {
    return request.get('/templates/mine/', params).then(unwrapPaginatedResponse)
  },

  publishTemplate(id) {
    return request.patch(`/templates/${id}/publish/`)
  },

  unpublishTemplate(id) {
    return request.patch(`/templates/${id}/unpublish/`)
  },

  getTemplateInstalls(id, params = {}) {
    return request.get(`/marketplace/my-templates/${id}/installs/`, params)
  },

  // Installed Templates
  getInstalledTemplates(params = {}) {
    return request.get('/templates/installed/', params).then(unwrapPaginatedResponse)
  }
}

export default marketplaceApi
