import apiClient from './index'
import { formatFileSize } from '@/utils/formatters'

export { formatFileSize }

const FORMAT_BY_EXTENSION = {
  csv: 'csv',
  json: 'json',
  jsonl: 'jsonl',
  txt: 'text',
  tsv: 'tsv',
  parquet: 'parquet',
  xlsx: 'xlsx',
  xls: 'xlsx',
}

export function detectFormatFromFilename(filename = '') {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  return FORMAT_BY_EXTENSION[ext] || 'unknown'
}

export function createDatasetFormData(file, meta = {}) {
  const formData = new FormData()
  formData.append('file', file)
  Object.entries(meta).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      formData.append(key, value)
    }
  })
  return formData
}

export const datasetApi = {
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
  upload(formData, onUploadProgress) {
    return apiClient.post('/training/datasets/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      ...(onUploadProgress ? { onUploadProgress } : {}),
    })
  },
  preview(id, page = 1) {
    return apiClient.get(`/training/datasets/${id}/preview/`, { params: { page } })
  },
  stats(id) {
    return apiClient.get(`/training/datasets/${id}/stats/`)
  },
  download(id) {
    return apiClient.get(`/training/datasets/${id}/download/`, { responseType: 'blob' })
  },
}

export default datasetApi
