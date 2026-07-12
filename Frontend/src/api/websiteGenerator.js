import api from './index'

export const websiteGeneratorApi = {
  list: (params) => api.get('/website-generator/', { params }),
  generate: (data) => api.post('/website-generator/generate/', data),
  get: (id) => api.get(`/website-generator/${id}/`),
  update: (id, data) => api.put(`/website-generator/${id}/`, data),
  delete: (id) => api.delete(`/website-generator/${id}/`),
  download: (id) => api.get(`/website-generator/${id}/download/`, { responseType: 'blob' }),
  deploy: (id) => api.post(`/website-generator/${id}/deploy/`),
  agentMessage: (id, data) => api.post(`/website-generator/${id}/agent/message/`, data),
  generateFromTraining: (trainingRunId, name) => api.post('/website-generator/generate/', {
    training_run_id: trainingRunId,
    name: name || `YOLO Detection - ${new Date().toLocaleDateString('zh-CN')}`,
    website_type: 'detection',
  }),
}
