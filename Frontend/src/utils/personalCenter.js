import { PROFILE_COPY } from '@/config/personalCenter'

export function toProfileForm(user = {}) {
  return {
    username: user.username || '', email: user.email || '',
    firstName: user.firstName ?? user.first_name ?? '',
    lastName: user.lastName ?? user.last_name ?? '',
    phone: user.phone || '', bio: user.bio || '',
  }
}

export function normalizeProfile(form) {
  return Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value.trim()]))
}

export function getSettingsFieldErrors(error) {
  const data = error?.response?.data
  const errors = data?.errors || data
  if (!errors || typeof errors !== 'object' || Array.isArray(errors)) return {}
  return Object.fromEntries(Object.entries(errors)
    .filter(([, value]) => Array.isArray(value) || typeof value === 'string')
    .map(([key, value]) => [key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase()), Array.isArray(value) ? value.join('；') : value]))
}

export function getSettingsError(error, fallback = PROFILE_COPY.profileError) {
  const data = error?.response?.data
  const fields = data?.errors
  if (fields && typeof fields === 'object') {
    const message = Object.values(fields).flat().filter(value => typeof value === 'string').join('；')
    if (message) return message
  }
  return data?.detail || data?.error_message || data?.message || fallback
}
