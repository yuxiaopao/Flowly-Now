import { request } from './index'
import { AUTH } from '@/config/auth'

const USER_ENDPOINT = '/auth/user/'
const AVATAR_ENDPOINT = '/auth/user/avatar/'

// Auth API methods
export const authApi = {
  login(data) {
    return request.post(AUTH.endpoints.login, data, { skipErrorToast: true })
  },
  register(data) {
    return request.post(AUTH.endpoints.register, data, { skipErrorToast: true })
  },
  logout() {
    return request.post('/auth/logout/')
  },
  getUserInfo() {
    return request.get(USER_ENDPOINT, {}, { skipAuthRedirect: true })
  },
  updateProfile(data) {
    return request.patch(USER_ENDPOINT, data, { skipErrorToast: true })
  },
  uploadAvatar(file) {
    const data = new FormData()
    data.append('avatar', file)
    return request.post(AVATAR_ENDPOINT, data, { skipErrorToast: true })
  },
  removeAvatar() {
    return request.delete(AVATAR_ENDPOINT, { skipErrorToast: true })
  },
  changePassword(data) {
    return request.post('/auth/change-password/', data, { skipErrorToast: true })
  },
  refreshToken(refreshToken) {
    return request.post(AUTH.endpoints.refresh, { refresh: refreshToken })
  },
  requestPasswordReset(email) {
    return request.post(AUTH.endpoints.reset, { email }, { skipErrorToast: true })
  },
  resetPassword(uidb64, token, newPassword) {
    return request.post(AUTH.endpoints.confirm, {
      uidb64,
      token,
      new_password: newPassword
    }, { skipErrorToast: true })
  }
}

// Named exports for convenience
export const login = (data) => authApi.login(data)
export const register = (data) => authApi.register(data)
export const logout = () => authApi.logout()
export const getUserInfo = () => authApi.getUserInfo()
export const updateProfile = (data) => authApi.updateProfile(data)
export const changePassword = (data) => authApi.changePassword(data)
export const refreshToken = (token) => authApi.refreshToken(token)

// Password reset
export function sendResetEmail(email) {
  return authApi.requestPasswordReset(email)
}

export function resetPassword({ uid, token, password }) {
  return authApi.resetPassword(uid, token, password)
}

export default authApi
