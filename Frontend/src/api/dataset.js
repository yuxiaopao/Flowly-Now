import apiClient from './index'

export default {
  list(params) {
    return apiClient.get('/training/datasets/', { params })
  },
  get(id) {
    return apiClient.get(`/training/datasets/${id}/`)
  },
  create(data) {
    return apiClient.post('/training/datasets/', data)
  },
  update(id, data) {
    return apiClient.put(`/training/datasets/${id}/`, data)
  },
  delete(id) {
    return apiClient.delete(`/training/datasets/${id}/`)
  },
  upload(formData) {
    return apiClient.post('/training/datasets/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  preview(id, page = 1) {
    return apiClient.get(`/training/datasets/${id}/preview/`, { params: { page } })
  },
  stats(id) {
    return apiClient.get(`/training/datasets/${id}/stats/`)
  },
}
