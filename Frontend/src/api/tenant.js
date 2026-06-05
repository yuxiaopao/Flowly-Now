import { request } from './index'

export const tenantApi = {
  // Tenants
  getTenants(params = {}) {
    return request.get('/tenants/', params)
  },

  getTenant(id) {
    return request.get(`/tenants/${id}/`)
  },

  createTenant(data) {
    return request.post('/tenants/', data)
  },

  updateTenant(id, data) {
    return request.patch(`/tenants/${id}/`, data)
  },

  deleteTenant(id) {
    return request.delete(`/tenants/${id}/`)
  },

  getTenantUsage(id) {
    return request.get(`/tenants/${id}/usage/`)
  },

  getTenantMembers(id) {
    return request.get(`/tenants/${id}/members/`)
  },

  inviteMember(tenantId, data) {
    return request.post(`/tenants/${tenantId}/invite/`, data)
  },

  removeMember(tenantId, memberId) {
    return request.delete(`/tenants/${tenantId}/remove_member/`, { member_id: memberId })
  },

  // Memberships
  getMyMemberships() {
    return request.get('/tenants/memberships/my_memberships/')
  },

  // Invitations
  getInvitations(params = {}) {
    return request.get('/tenants/invitations/', params)
  },

  getPendingInvitations() {
    return request.get('/tenants/invitations/pending/')
  },

  joinTenant(data) {
    return request.post('/tenants/invitations/join/', data)
  },

  acceptInvitation(id) {
    return request.post(`/tenants/invitations/${id}/accept/`)
  },

  declineInvitation(id) {
    return request.post(`/tenants/invitations/${id}/decline/`)
  },

  // Usage
  refreshUsage(tenantId) {
    return request.post('/tenants/usage/refresh/', { tenant_id: tenantId })
  },

  // ============ Team Skills ============
  getSkills(params = {}) {
    return request.get('/tenants/skills/', params)
  },

  getSkill(id) {
    return request.get(`/tenants/skills/${id}/`)
  },

  createSkill(tenantId, data) {
    return request.post('/tenants/skills/', { tenant: tenantId, ...data })
  },

  updateSkill(id, data) {
    return request.patch(`/tenants/skills/${id}/`, data)
  },

  deleteSkill(id) {
    return request.delete(`/tenants/skills/${id}/`)
  },

  assignSkill(skillId, data) {
    return request.post(`/tenants/skills/${skillId}/assign/`, data)
  },

  unassignSkill(skillId, data) {
    return request.post(`/tenants/skills/${skillId}/unassign/`, data)
  },

  // ============ Team Tasks ============
  getTasks(params = {}) {
    return request.get('/tenants/tasks/', params)
  },

  getTask(id) {
    return request.get(`/tenants/tasks/${id}/`)
  },

  createTask(tenantId, data) {
    return request.post('/tenants/tasks/', { tenant: tenantId, ...data })
  },

  updateTask(id, data) {
    return request.patch(`/tenants/tasks/${id}/`, data)
  },

  deleteTask(id) {
    return request.delete(`/tenants/tasks/${id}/`)
  },

  assignTaskUser(taskId, data) {
    return request.post(`/tenants/tasks/${taskId}/assign_user/`, data)
  },

  unassignTaskUser(taskId, data) {
    return request.post(`/tenants/tasks/${taskId}/unassign_user/`, data)
  },

  changeTaskStatus(taskId, data) {
    return request.post(`/tenants/tasks/${taskId}/change_status/`, data)
  },

  // ============ Team Activities ============
  getActivities(params = {}) {
    return request.get('/tenants/activities/', params)
  }
}

export default tenantApi
