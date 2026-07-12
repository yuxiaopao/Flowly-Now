import { request } from './index'

export const notificationApi = {
  getList(params = {}) {
    return request.get('/notifications/', params)
  },

  getUnreadCount() {
    return request.get('/notifications/unread_count/')
  },

  getRecent() {
    return request.get('/notifications/recent/')
  },

  markRead(id) {
    return request.post(`/notifications/${id}/mark_read/`)
  },

  markAllRead() {
    return request.post('/notifications/mark_all_read/')
  },

  archive(id) {
    return request.post(`/notifications/${id}/archive/`)
  },

  archiveAll() {
    return request.post('/notifications/archive_all/')
  },

  deleteRead() {
    return request.post('/notifications/delete_read/')
  },

  clearAll() {
    return request.delete('/notifications/clear_all/')
  },

  getPreferences() {
    return request.get('/notification-preferences/')
  },

  updatePreferences(id, data) {
    return request.patch(`/notification-preferences/${id}/`, data)
  },
}

export default notificationApi
