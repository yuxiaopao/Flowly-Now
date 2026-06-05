import { request } from './index'

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
    return request.get('/marketplace/templates/', params).then(unwrapPaginatedResponse)
  },

  getTemplate(id) {
    return request.get(`/marketplace/templates/${id}/`)
  },

  createTemplate(data) {
    return request.post('/marketplace/templates/', data)
  },

  updateTemplate(id, data) {
    return request.patch(`/marketplace/templates/${id}/`, data)
  },

  deleteTemplate(id) {
    return request.delete(`/marketplace/templates/${id}/`)
  },

  getFeaturedTemplates(params = {}) {
    return request.get('/marketplace/templates/featured/', params).then(unwrapPaginatedResponse)
  },

  getTemplatesByCategory(params = {}) {
    return request.get('/marketplace/templates/by_category/', params).then(unwrapListResponse)
  },

  installTemplate(id) {
    return request.post(`/marketplace/templates/${id}/install/`)
  },

  rateTemplate(id, rating) {
    return request.post(`/marketplace/templates/${id}/rate/`, { rating })
  },

  getTemplateStats(id) {
    return request.get(`/marketplace/templates/${id}/stats/`)
  },

  reportTemplate(id, reason) {
    return request.post(`/marketplace/templates/${id}/report/`, { reason })
  },

  // Categories
  getCategories(params = {}) {
    return request.get('/marketplace/categories/', params)
  },

  getCategory(id) {
    return request.get(`/marketplace/categories/${id}/`)
  },

  getCategoryTemplates(id, params = {}) {
    return request.get(`/marketplace/categories/${id}/templates/`, params).then(unwrapPaginatedResponse)
  },

  // My Templates
  getMyTemplates(params = {}) {
    return request.get('/marketplace/my-templates/', params).then(unwrapPaginatedResponse)
  },

  publishTemplate(id) {
    return request.post(`/marketplace/my-templates/${id}/publish/`)
  },

  unpublishTemplate(id) {
    return request.post(`/marketplace/my-templates/${id}/unpublish/`)
  },

  getTemplateInstalls(id, params = {}) {
    return request.get(`/marketplace/my-templates/${id}/installs/`, params)
  },

  // Installed Templates
  getInstalledTemplates(params = {}) {
    return request.get('/marketplace/installed/', params).then(unwrapPaginatedResponse)
  }
}

export default marketplaceApi
