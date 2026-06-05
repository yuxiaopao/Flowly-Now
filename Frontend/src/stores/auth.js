import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import Cookies from 'js-cookie'
import authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const token = ref(Cookies.get('access_token') || localStorage.getItem('access_token'))
  const refreshToken = ref(Cookies.get('refresh_token') || localStorage.getItem('refresh_token'))
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.is_staff || false)
  const userName = computed(() => user.value?.username || '')
  const userEmail = computed(() => user.value?.email || '')

  // Actions
  async function login(credentials) {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.login(credentials)
      const { access, refresh, user: userData } = response

      // 保存 Token
      token.value = access
      refreshToken.value = refresh
      Cookies.set('access_token', access, { expires: 1 })
      Cookies.set('refresh_token', refresh, { expires: 7 })
      localStorage.setItem('access_token', access)
      localStorage.setItem('refresh_token', refresh)

      // 保存用户信息
      user.value = userData

      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function register(userData) {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.register(userData)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch (err) {
      // 忽略登出 API 错误
    } finally {
      // 清除本地状态
      clearAuth()
    }
  }

  function clearAuth() {
    user.value = null
    token.value = null
    refreshToken.value = null
    Cookies.remove('access_token')
    Cookies.remove('refresh_token')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function fetchUserInfo() {
    if (!token.value) return null

    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.getUserInfo()
      user.value = response
      return response
    } catch (err) {
      error.value = err.message
      // Token 可能过期
      if (err.response?.status === 401) {
        clearAuth()
      }
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function updateProfile(data) {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.updateProfile(data)
      user.value = { ...user.value, ...response }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function changePassword(passwords) {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.changePassword(passwords)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    user,
    token,
    refreshToken,
    isLoading,
    error,
    // Getters
    isAuthenticated,
    isAdmin,
    userName,
    userEmail,
    // Actions
    login,
    register,
    logout,
    clearAuth,
    fetchUserInfo,
    updateProfile,
    changePassword
  }
})
