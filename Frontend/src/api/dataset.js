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

function datasetBase(options = {}) {
  return options.source === 'generic' ? '/datasets' : '/training/datasets'
}

export const datasetApi = {
  list(params) {
    return apiClient.get('/training/datasets/', { params })
  },
  get(id, options = {}) {
    return apiClient.get(`${datasetBase(options)}/${id}/`)
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
  preview(id, page = 1, options = {}) {
    return apiClient.get(`${datasetBase(options)}/${id}/preview/`, { params: { page } })
  },
  stats(id, options = {}) {
    return apiClient.get(`${datasetBase(options)}/${id}/stats/`)
  },
  download(id, options = {}) {
    return apiClient.get(`${datasetBase(options)}/${id}/download/`, { responseType: 'blob' })
  },
}

export default datasetApi
