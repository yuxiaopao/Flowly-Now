import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tenantApi } from '@/api/tenant'

export const useTenantStore = defineStore('tenant', () => {
  // State
  const tenants = ref([])
  const currentTenant = ref(null)
  const members = ref([])
  const invitations = ref([])
  const pendingInvitations = ref([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref(null)

  // Team Skills state
  const skills = ref([])
  const currentSkill = ref(null)
  const isLoadingSkills = ref(false)

  // Team Tasks state
  const tasks = ref([])
  const currentTask = ref(null)
  const isLoadingTasks = ref(false)

  // Team Activities state
  const activities = ref([])
  const isLoadingActivities = ref(false)

  // Getters
  const myTenants = computed(() => tenants.value)

  // ---- Tenants ----
  async function fetchTenants(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await tenantApi.getTenants(params)
      tenants.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTenant(id) {
    isLoading.value = true
    error.value = null
    try {
      const response = await tenantApi.getTenant(id)
      currentTenant.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createTenant(data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await tenantApi.createTenant(data)
      tenants.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateTenant(id, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await tenantApi.updateTenant(id, data)
      const index = tenants.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tenants.value[index] = { ...tenants.value[index], ...response }
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteTenant(id) {
    isLoading.value = true
    error.value = null
    try {
      await tenantApi.deleteTenant(id)
      tenants.value = tenants.value.filter(t => t.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTenantUsage(id) {
    try {
      return await tenantApi.getTenantUsage(id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ---- Members ----
  async function fetchMembers(tenantId) {
    isLoading.value = true
    try {
      const response = await tenantApi.getTenantMembers(tenantId)
      members.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function inviteMember(tenantId, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await tenantApi.inviteMember(tenantId, data)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function removeMember(tenantId, memberId) {
    try {
      await tenantApi.removeMember(tenantId, memberId)
      members.value = members.value.filter(m => m.id !== memberId)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ---- Invitations ----
  async function fetchInvitations() {
    isLoading.value = true
    try {
      const response = await tenantApi.getInvitations()
      invitations.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPendingInvitations() {
    try {
      const response = await tenantApi.getPendingInvitations()
      pendingInvitations.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function acceptInvitation(id) {
    try {
      const response = await tenantApi.acceptInvitation(id)
      pendingInvitations.value = pendingInvitations.value.filter(i => i.id !== id)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function declineInvitation(id) {
    try {
      await tenantApi.declineInvitation(id)
      pendingInvitations.value = pendingInvitations.value.filter(i => i.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function joinTenant(token) {
    try {
      const response = await tenantApi.joinTenant({ token })
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ---- Usage ----
  async function refreshUsage(tenantId) {
    try {
      return await tenantApi.refreshUsage(tenantId)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============ Team Skills ============
  async function fetchSkills(tenantId, params = {}) {
    isLoadingSkills.value = true
    try {
      const response = await tenantApi.getSkills({ tenant_id: tenantId, ...params })
      skills.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoadingSkills.value = false
    }
  }

  async function fetchSkill(id) {
    isLoadingSkills.value = true
    try {
      const response = await tenantApi.getSkill(id)
      currentSkill.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoadingSkills.value = false
    }
  }

  async function createSkill(tenantId, data) {
    isSaving.value = true
    try {
      const response = await tenantApi.createSkill(tenantId, data)
      skills.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateSkill(id, data) {
    isSaving.value = true
    try {
      const response = await tenantApi.updateSkill(id, data)
      const index = skills.value.findIndex(s => s.id === id)
      if (index !== -1) skills.value[index] = { ...skills.value[index], ...response }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteSkill(id) {
    isLoadingSkills.value = true
    try {
      await tenantApi.deleteSkill(id)
      skills.value = skills.value.filter(s => s.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoadingSkills.value = false
    }
  }

  async function assignSkill(skillId, data) {
    isSaving.value = true
    try {
      return await tenantApi.assignSkill(skillId, data)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function unassignSkill(skillId, data) {
    isSaving.value = true
    try {
      return await tenantApi.unassignSkill(skillId, data)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  // ============ Team Tasks ============
  async function fetchTasks(tenantId, params = {}) {
    isLoadingTasks.value = true
    try {
      const response = await tenantApi.getTasks({ tenant_id: tenantId, ...params })
      tasks.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoadingTasks.value = false
    }
  }

  async function fetchTask(id) {
    isLoadingTasks.value = true
    try {
      const response = await tenantApi.getTask(id)
      currentTask.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoadingTasks.value = false
    }
  }

  async function createTask(tenantId, data) {
    isSaving.value = true
    try {
      const response = await tenantApi.createTask(tenantId, data)
      tasks.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateTask(id, data) {
    isSaving.value = true
    try {
      const response = await tenantApi.updateTask(id, data)
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) tasks.value[index] = { ...tasks.value[index], ...response }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteTask(id) {
    isLoadingTasks.value = true
    try {
      await tenantApi.deleteTask(id)
      tasks.value = tasks.value.filter(t => t.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoadingTasks.value = false
    }
  }

  async function assignTaskUser(taskId, data) {
    isSaving.value = true
    try {
      return await tenantApi.assignTaskUser(taskId, data)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function unassignTaskUser(taskId, data) {
    isSaving.value = true
    try {
      return await tenantApi.unassignTaskUser(taskId, data)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function changeTaskStatus(taskId, status) {
    isSaving.value = true
    try {
      const response = await tenantApi.changeTaskStatus(taskId, { status })
      const index = tasks.value.findIndex(t => t.id === taskId)
      if (index !== -1) tasks.value[index] = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  // ============ Team Activities ============
  async function fetchActivities(tenantId, params = {}) {
    isLoadingActivities.value = true
    try {
      const response = await tenantApi.getActivities({ tenant_id: tenantId, ...params })
      activities.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoadingActivities.value = false
    }
  }

  // ---- Clear ----
  function clearStore() {
    tenants.value = []
    currentTenant.value = null
    members.value = []
    invitations.value = []
    pendingInvitations.value = []
    skills.value = []
    currentSkill.value = null
    tasks.value = []
    currentTask.value = null
    activities.value = []
    error.value = null
  }

  return {
    // State
    tenants,
    currentTenant,
    members,
    invitations,
    pendingInvitations,
    isLoading,
    isSaving,
    error,
    // Skills
    skills,
    currentSkill,
    isLoadingSkills,
    // Tasks
    tasks,
    currentTask,
    isLoadingTasks,
    // Activities
    activities,
    isLoadingActivities,

    // Getters
    myTenants,

    // Actions - Tenants
    fetchTenants,
    fetchTenant,
    createTenant,
    updateTenant,
    deleteTenant,
    fetchTenantUsage,

    // Actions - Members
    fetchMembers,
    inviteMember,
    removeMember,

    // Actions - Invitations
    fetchInvitations,
    fetchPendingInvitations,
    acceptInvitation,
    declineInvitation,
    joinTenant,

    // Actions - Usage
    refreshUsage,

    // Actions - Skills
    fetchSkills,
    fetchSkill,
    createSkill,
    updateSkill,
    deleteSkill,
    assignSkill,
    unassignSkill,

    // Actions - Tasks
    fetchTasks,
    fetchTask,
    createTask,
    updateTask,
    deleteTask,
    assignTaskUser,
    unassignTaskUser,
    changeTaskStatus,

    // Actions - Activities
    fetchActivities,

    clearStore
  }
})
