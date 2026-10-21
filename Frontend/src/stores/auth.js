import { defineStore } from 'pinia'
import { ref, computed, toRef } from 'vue'
import authApi from '@/api/auth'
import { authSession, saveAuthSession, clearAuthSession } from '@/utils/authSession'
import { getSettingsError } from '@/utils/personalCenter'
import { normalizeAccountAvatar, persistAccountAvatar, readAccountAvatar } from '@/utils/accountAvatar'

export const useAuthStore = defineStore('auth', () => {
  const user = toRef(authSession, 'user')
  const token = toRef(authSession, 'access')
  const refreshToken = toRef(authSession, 'refresh')
  const isLoading = ref(false)
  const error = ref(null)
  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => Boolean(user.value?.isStaff || user.value?.isSuperuser))
  const userName = computed(() => user.value?.username || '')
  const userEmail = computed(() => user.value?.email || '')
  let profilePromise = null

  async function run(action) {
    isLoading.value = true
    error.value = null
    try {
      return await action()
    } catch (err) {
      error.value = getSettingsError(err, '操作失败，请检查网络后重试')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function login({ remember = false, ...credentials }) {
    return run(async () => {
      const response = await authApi.login(credentials)
      saveAuthSession(response, remember)
      return response
    })
  }

  function register(data) {
    return run(() => authApi.register(data))
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // The interceptor reports network errors; local sign-out must still finish.
    } finally {
      clearAuth()
    }
  }

  function clearAuth() {
    clearAuthSession()
    error.value = null
  }

  async function fetchUserInfo() {
    if (!token.value) return null
    if (!profilePromise) {
      profilePromise = authApi.getUserInfo().then(response => {
        if (token.value) user.value = response
        return token.value ? response : null
      }).finally(() => { profilePromise = null })
    }
    return profilePromise
  }

  function updateProfile(data) {
    return run(async () => {
      const payload = data.avatarPreferences ? { ...data, avatarPreferences: normalizeAccountAvatar({ ...readAccountAvatar(user.value), ...data.avatarPreferences }) } : data
      const response = await authApi.updateProfile(payload)
      if (data.avatarPreferences) {
        const synced = response.avatarPreferences !== undefined
        const preferences = normalizeAccountAvatar(synced ? response.avatarPreferences : { ...readAccountAvatar(user.value), ...data.avatarPreferences })
        response.avatarPreferencesPersisted = persistAccountAvatar(user.value.id, preferences)
        response.avatarPreferencesSynced = synced
        response.avatarPreferences = preferences
      }
      user.value = { ...user.value, ...response }
      return response
    })
  }

  function changePassword(data) {
    return run(async () => {
      const response = await authApi.changePassword(data)
      saveAuthSession(response)
      return response
    })
  }

  async function uploadAvatar(file) {
    const response = await authApi.uploadAvatar(file)
    const preferences = normalizeAccountAvatar(response.avatarPreferences || { ...readAccountAvatar(user.value), mode: 'image' })
    persistAccountAvatar(user.value.id, preferences)
    user.value = { ...user.value, avatar: response.avatar, avatarPreferences: preferences }
    return response
  }

  async function removeAvatar() {
    const response = await authApi.removeAvatar()
    const preferences = normalizeAccountAvatar(response.avatarPreferences || { ...readAccountAvatar(user.value), mode: 'robot' })
    persistAccountAvatar(user.value.id, preferences)
    user.value = { ...user.value, avatar: response.avatar, avatarPreferences: preferences }
    return response
  }

  return { user, token, refreshToken, isLoading, error, isAuthenticated, isAdmin,
    userName, userEmail, login, register, logout, clearAuth, fetchUserInfo,
    updateProfile, changePassword, uploadAvatar, removeAvatar }
})
