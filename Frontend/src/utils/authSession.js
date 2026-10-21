import { reactive } from 'vue'
import Cookies from 'js-cookie'
import { AUTH } from '@/config/auth'

function read(key) {
  return Cookies.get(key) || sessionStorage.getItem(key) || localStorage.getItem(key) || null
}

export const authSession = reactive({
  access: read(AUTH.accessKey),
  refresh: read(AUTH.refreshKey),
  user: null,
  revision: 0,
})

export function rememberSession() {
  return localStorage.getItem(AUTH.rememberKey) === 'true'
}

export function saveAuthSession(data, remember = rememberSession()) {
  if (!data?.access || !data?.refresh) throw new Error('登录响应不完整，请重试')
  for (const [kind, key] of [['access', AUTH.accessKey], ['refresh', AUTH.refreshKey]]) {
    localStorage.removeItem(key)
    sessionStorage.removeItem(key)
    const storage = remember ? localStorage : sessionStorage
    storage.setItem(key, data[kind])
    Cookies.set(key, data[kind], {
      path: '/', sameSite: 'Lax', secure: location.protocol === 'https:',
      ...(remember ? { expires: AUTH.cookieDays[kind] } : {}),
    })
  }
  localStorage.setItem(AUTH.rememberKey, String(remember))
  authSession.access = data.access
  authSession.refresh = data.refresh
  if (data.user) authSession.user = data.user
  authSession.revision++
}

export function clearAuthSession(broadcast = true) {
  for (const key of [AUTH.accessKey, AUTH.refreshKey]) {
    Cookies.remove(key, { path: '/' })
    localStorage.removeItem(key)
    sessionStorage.removeItem(key)
  }
  authSession.access = null
  authSession.refresh = null
  authSession.user = null
  authSession.revision++
  if (broadcast) localStorage.setItem(AUTH.logoutKey, String(Date.now()))
}

window.addEventListener('storage', event => {
  if (event.key === AUTH.logoutKey) clearAuthSession(false)
  if (event.key === AUTH.refreshKey && event.newValue) {
    authSession.access = read(AUTH.accessKey)
    authSession.refresh = read(AUTH.refreshKey)
    authSession.user = null
    authSession.revision++
  }
})

export function safeAuthRedirect(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return AUTH.routes.home
  const path = value.split(/[?#]/)[0]
  if (['/', '/register', ...Object.values(AUTH.routes).filter(route => route !== AUTH.routes.home)].includes(path)) return AUTH.routes.home
  return value
}
