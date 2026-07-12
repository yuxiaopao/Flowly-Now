import { request } from './index'

export const dataExportApi = {
  list(params = {}) {
    return request.get('/data-export/', params)
  },

  requestExport(exportType, format = 'json', extra = {}) {
    return request.post('/data-export/request_export/', {
      export_type: exportType,
      format,
      ...extra,
    })
  },

  getDownloadUrl(id) {
    return request.get(`/data-export/${id}/download/`)
  },

  download(id) {
    return request.get(`/data-export/${id}/download/`, {}, { responseType: 'blob' })
  },
}

export default dataExportApi
