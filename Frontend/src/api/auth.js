import { request } from './index'

// Auth API methods
export const authApi = {
  login(data) {
    return request.post('/auth/login/', data)
  },
  register(data) {
    return request.post('/auth/register/', data)
  },
  logout() {
    return request.post('/auth/logout/')
  },
  getUserInfo() {
    return request.get('/auth/user/')
  },
  updateProfile(data) {
    return request.patch('/auth/user/', data)
  },
  changePassword(data) {
    return request.post('/auth/change-password/', data)
  },
  refreshToken(refreshToken) {
    return request.post('/auth/refresh/', { refresh: refreshToken })
  },
  requestPasswordReset(email) {
    return request.post('/auth/password-reset/', { email })
  },
  resetPassword(uidb64, token, newPassword) {
    return request.post('/auth/password-reset/confirm/', {
      uidb64,
      token,
      new_password: newPassword
    })
  },
  verifyEmail(key) {
    return request.post('/auth/verify-email/', { key })
  },
  resendVerificationEmail() {
    return request.post('/auth/verify-email/resend/')
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
export const verifyEmail = (key) => authApi.verifyEmail(key)
export const resendVerificationEmail = () => authApi.resendVerificationEmail()

// Password reset
export function sendResetEmail(email) {
  return authApi.requestPasswordReset(email)
}

export function resetPassword({ token, password }) {
  return authApi.resetPassword(null, null, password)
}

export default authApi
