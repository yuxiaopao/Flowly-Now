import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { AxiosError } from 'axios'
import Cookies from 'js-cookie'
import api, { requestState, sessionClient } from '@/api'
import { authSession, clearAuthSession, saveAuthSession, safeAuthRedirect } from '@/utils/authSession'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfigStore } from '@/stores/siteConfig'
import { setupRouterGuard } from '@/router/routes'
import ForgotPassword from '@/views/auth/ForgotPassword.vue'

vi.mock('@/router', () => ({ default: { currentRoute: { value: { path: '/login', fullPath: '/login' } }, replace: vi.fn() } }))

const originalAdapter = api.defaults.adapter
const rawAdapter = sessionClient.defaults.adapter
const tokens = { access: 'old-access', refresh: 'old-refresh', user: { username: '测试用户' } }
function response(config, data, status = 200) { return { config, data, status, headers: {}, statusText: '' } }
function fail(config, status) { throw new AxiosError('Request failed', 'ERR_BAD_REQUEST', config, {}, response(config, {}, status)) }

beforeEach(() => {
  setActivePinia(createPinia())
  clearAuthSession()
  localStorage.clear()
  sessionStorage.clear()
  requestState.pending = 0
})
afterEach(() => { api.defaults.adapter = originalAdapter; sessionClient.defaults.adapter = rawAdapter; vi.restoreAllMocks() })

describe('authentication HTTP and session behavior', () => {
  it('submits login without stale authorization and honors session-only persistence', async () => {
    saveAuthSession(tokens, true)
    api.defaults.adapter = async config => {
      expect(config.headers.Authorization).toBeUndefined()
      expect(JSON.parse(config.data)).toEqual({ username: 'sample', password: '  spaced pass  ' })
      return response(config, { data: tokens, code: 200 })
    }
    await useAuthStore().login({ username: 'sample', password: '  spaced pass  ', remember: false })
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(sessionStorage.getItem('access_token')).toBe(tokens.access)
    expect(Cookies.get('access_token')).toBe(tokens.access)
    expect(useAuthStore().user.username).toBe('测试用户')
  })

  it('persists remember-me credentials across reloads', async () => {
    api.defaults.adapter = async config => response(config, tokens)
    await useAuthStore().login({ username: 'sample', password: 'valid', remember: true })
    expect(localStorage.getItem('refresh_token')).toBe(tokens.refresh)
    expect(sessionStorage.getItem('refresh_token')).toBeNull()
  })

  it('clears the current tab when another tab broadcasts logout', () => {
    saveAuthSession(tokens, true)
    window.dispatchEvent(new StorageEvent('storage', { key: 'auth_logout', newValue: String(Date.now()) }))
    expect(useAuthStore().token).toBeNull()
    expect(useAuthStore().user).toBeNull()
    expect(sessionStorage.getItem('refresh_token')).toBeNull()
  })

  it('shares one refresh for simultaneous 401s and synchronizes rotated credentials', async () => {
    saveAuthSession(tokens, true)
    const refreshed = { access: 'new-access', refresh: 'new-refresh', user: { username: '新用户' } }
    let refreshCount = 0
    sessionClient.defaults.adapter = async config => {
      refreshCount++
      expect(config.baseURL).toBe(api.defaults.baseURL)
      await new Promise(resolve => setTimeout(resolve, 10))
      return response(config, { code: 200, data: refreshed })
    }
    api.defaults.adapter = async config => {
      if (config.headers.Authorization === 'Bearer old-access') fail(config, 401)
      return response(config, { ok: true })
    }
    await Promise.all([api.get('/auth/user/'), api.get('/workflows/'), api.get('/agents/')])
    expect(refreshCount).toBe(1)
    expect(useAuthStore().token).toBe(refreshed.access)
    expect(useAuthStore().refreshToken).toBe(refreshed.refresh)
    expect(localStorage.getItem('refresh_token')).toBe(refreshed.refresh)
    expect(requestState.pending).toBe(0)
  })

  it('clears Pinia, cookies and both storage areas after refresh is rejected', async () => {
    saveAuthSession(tokens, true)
    sessionClient.defaults.adapter = async config => fail(config, 401)
    api.defaults.adapter = async config => fail(config, 401)
    await expect(api.get('/auth/user/')).rejects.toBeDefined()
    expect(useAuthStore().isAuthenticated).toBe(false)
    expect(useAuthStore().user).toBeNull()
    expect(Cookies.get('access_token')).toBeUndefined()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(requestState.pending).toBe(0)
  })

  it('keeps credentials on temporary refresh outage', async () => {
    saveAuthSession(tokens, false)
    sessionClient.defaults.adapter = async config => fail(config, 503)
    api.defaults.adapter = async config => fail(config, 401)
    await expect(api.get('/auth/user/', { skipErrorToast: true })).rejects.toBeDefined()
    expect(authSession.refresh).toBe(tokens.refresh)
    expect(requestState.pending).toBe(0)
  })

  it('does not restore a session when an in-flight refresh finishes after logout', async () => {
    saveAuthSession(tokens, false)
    let finish
    sessionClient.defaults.adapter = config => new Promise(resolve => { finish = () => resolve(response(config, tokens)) })
    api.defaults.adapter = async config => fail(config, 401)
    const request = api.get('/auth/user/')
    const rejected = expect(request).rejects.toBeDefined()
    await vi.waitFor(() => expect(finish).toBeTypeOf('function'))
    clearAuthSession()
    finish()
    await rejected
    expect(authSession.access).toBeNull()
  })

  it('never retries a timed-out registration POST', async () => {
    let calls = 0
    api.defaults.adapter = async config => { calls++; throw new AxiosError('timeout', 'ECONNABORTED', config) }
    await expect(api.post('/auth/register/', {}, { skipErrorToast: true })).rejects.toBeDefined()
    expect(calls).toBe(1)
    expect(requestState.pending).toBe(0)
  })

  it('retries a safe GET once without leaving the global loading indicator active', async () => {
    let calls = 0
    api.defaults.adapter = async config => {
      if (++calls === 1) throw new AxiosError('timeout', 'ECONNABORTED', config)
      return response(config, { ok: true })
    }
    await api.get('/public/site-config/')
    expect(calls).toBe(2)
    expect(requestState.pending).toBe(0)
  })

  it('uses registration settings after the shared HTTP layer converts keys', async () => {
    api.defaults.adapter = async config => response(config, { auth: { allow_registration: false, require_terms_on_register: false, password_min_length: 12 }, site: { contact_email: 'support@example.invalid' } })
    await useSiteConfigStore().fetchPublicConfig()
    expect(useSiteConfigStore().auth).toMatchObject({ allowRegistration: false, requireTermsOnRegister: false, passwordMinLength: 12 })
    expect(useSiteConfigStore().site.contactEmail).toBe('support@example.invalid')
  })

  it.each(['https://example.com', '//example.com', '/\\example.com', '/login', '/reset-password?token=x', ['bad']])('rejects unsafe or recursive post-login redirect %s', value => {
    expect(safeAuthRedirect(value)).toBe('/home')
  })

  it('preserves a protected destination and its query', () => {
    expect(safeAuthRedirect('/workflows?tab=mine')).toBe('/workflows?tab=mine')
  })
})

it('submits a flat email from the real forgot-password form and keeps neutral delivery feedback visible', async () => {
  api.defaults.adapter = async config => {
    expect(JSON.parse(config.data)).toEqual({ email: 'sample@example.invalid' })
    return response(config, { message: '如果邮箱存在，您将收到重置链接。' })
  }
  const wrapper = mount(ForgotPassword, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } })
  await wrapper.get('input').setValue('sample@example.invalid')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  await vi.waitFor(() => expect(wrapper.text()).toContain('如果邮箱存在，您将收到重置链接。'))
  wrapper.unmount()
})

it('allows a logged-in user to open a reset link, while a failed profile check blocks protected navigation', async () => {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/login', name: 'Login', component: { template: '<div />' } },
    { path: '/reset-password', name: 'ResetPassword', meta: { layout: 'blank' }, component: { template: '<div />' } },
    { path: '/home', name: 'Dashboard', meta: { requiresAuth: true }, component: { template: '<div />' } },
  ] })
  setupRouterGuard(router)
  saveAuthSession(tokens)
  await router.push('/reset-password?uid=1&token=test')
  expect(router.currentRoute.value.name).toBe('ResetPassword')
  authSession.user = null
  api.defaults.adapter = async config => fail(config, 401)
  sessionClient.defaults.adapter = async config => fail(config, 401)
  await router.push('/home')
  expect(router.currentRoute.value.name).toBe('Login')
  expect(router.currentRoute.value.query.redirect).toBe('/home')
})
