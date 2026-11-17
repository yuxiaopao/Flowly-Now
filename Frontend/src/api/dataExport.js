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

  download(id) {
    return request.get(`/data-export/${id}/download/`, {}, { responseType: 'blob' })
  },

  getBackupSettings() {
    return request.get('/data-export/backup_settings/')
  },

  saveBackupSettings(data) {
    return request.patch('/data-export/backup_settings/', data)
  },

  previewRestore(id) {
    return request.post(`/data-export/${id}/restore_preview/`)
  },

  restore(id, confirmationToken) {
    return request.post(`/data-export/${id}/restore/`, { confirm: true, confirmation_token: confirmationToken })
  },

  previewDelete() {
    return request.get('/data-export/delete_preview/')
  },

  deletePersonalData(data) {
    return request.post('/data-export/delete_personal_data/', data)
  },
}

export default dataExportApi
