import apiClient from './index'
import { getWebSocketUrl } from '@/config'

export default {
  // Training Jobs
  list(params) {
    return apiClient.get('/training/training-jobs/', { params })
  },
  get(id) {
    return apiClient.get(`/training/training-jobs/${id}/`)
  },
  create(data) {
    return apiClient.post('/training/training-jobs/', data)
  },
  update(id, data) {
    return apiClient.patch(`/training/training-jobs/${id}/`, data)
  },
  cancel(id) {
    return apiClient.post(`/training/training-jobs/${id}/cancel/`)
  },
  retry(id) {
    return apiClient.post(`/training/training-jobs/${id}/retry/`)
  },
  download(id) {
    return apiClient.get(`/training/training-jobs/${id}/download/`, { responseType: 'blob' })
  },
  stats() {
    return apiClient.get('/training/training-jobs/stats/')
  },

  // Datasets
  listDatasets(params) {
    return apiClient.get('/training/datasets/', { params })
  },
  getDataset(id) {
    return apiClient.get(`/training/datasets/${id}/`)
  },
  uploadDataset(formData) {
    return apiClient.post('/training/datasets/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  deleteDataset(id) {
    return apiClient.delete(`/training/datasets/${id}/`)
  },
  previewDataset(id, page) {
    return apiClient.get(`/training/datasets/${id}/preview/`, { params: { page } })
  },
  statsDataset(id) {
    return apiClient.get(`/training/datasets/${id}/stats/`)
  },

  // GPU Info
  getGpuInfo() {
    return apiClient.get('/training/training-jobs/gpu-info/')
  },

  // YOLO Training Runs
  listYoloRuns(params) {
    return apiClient.get('/training/yolo-runs/', { params })
  },
  getYoloRun(id) {
    return apiClient.get(`/training/yolo-runs/${id}/`)
  },
  createYoloRun(data) {
    return apiClient.post('/training/yolo-runs/', data)
  },
  cancelYoloRun(id) {
    return apiClient.post(`/training/yolo-runs/${id}/cancel/`)
  },
  retryYoloRun(id, data) {
    return apiClient.post(`/training/yolo-runs/${id}/retry/`, data || {})
  },
  getYoloMetricsHistory(id) {
    return apiClient.get(`/training/yolo-runs/${id}/metrics_history/`)
  },
  getYoloTrainingPlots(id) {
    return apiClient.get(`/training/yolo-runs/${id}/plots/`)
  },
  getYoloPlotImage(id, name) {
    return apiClient.get(`/training/yolo-runs/${id}/plot/`, {
      params: { name },
      responseType: 'blob',
    })
  },
  downloadYoloArtifact(id, artifact = 'pt') {
    return apiClient.get(`/training/yolo-runs/${id}/download/`, {
      params: { artifact },
      responseType: 'blob'
    })
  },
  getYoloWebSocketUrl(id) {
    return getWebSocketUrl(`/ws/training/${id}/`)
  },

  getOptions() {
    return apiClient.get('/training/training-jobs/options/')
  },

  analyzeDataset(data) {
    return apiClient.post('/training/training-jobs/analyze-dataset/', data)
  },
}
