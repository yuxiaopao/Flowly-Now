import api from './index'

export const websiteGeneratorApi = {
  generate: (data) => api.post('/website-generator/generate/', data),
  get: (id) => api.get(`/website-generator/${id}/`),
  update: (id, data) => api.put(`/website-generator/${id}/`, data),
  delete: (id) => api.delete(`/website-generator/${id}/`),
  download: (id) => api.get(`/website-generator/${id}/download/`, { responseType: 'blob' }),
  deploy: (id) => api.post(`/website-generator/${id}/deploy/`),
}
