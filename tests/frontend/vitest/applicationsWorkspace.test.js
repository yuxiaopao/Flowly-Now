import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { defineComponent, h } from 'vue'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import api from '@/api/index'
import { useAppStore } from '@/stores/app'
import Index from '@/views/applications/Index.vue'
import Detail from '@/views/applications/Detail.vue'
import Home from '@/views/dashboard/Home.vue'

const applicationStyles = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../../../Frontend/src/views/applications/applications.css'), 'utf8')

const originalAdapter = api.defaults.adapter
const wrappers = []
const styles = []
let application
let calls
let testFails
let listFails
let releases
let keys
const trace = { id: 'request-1', application_id: 'a', mode: 'test', status: 'completed', input_data: { Customer_ID: 'u' }, output_data: { My_Result: { keep_this: true } }, latency_ms: 42, total_tokens: null, cost: null, currency: null, created_at: '2026-10-31T10:00:00Z' }

beforeEach(() => {
  calls = []
  releases = []
  keys = []
  testFails = false
  listFails = false
  application = { id: 'a', name: '客服助手', description: '团队知识问答', kind: 'knowledge', tenant_id: null,
    draft: { collection_id: 'collection-1', system_prompt: '依据资料回答', top_k: 5, min_similarity: 0 },
    draft_fingerprint: 'f1', tested_fingerprint: null, last_test_status: null, active_release: null,
    can_edit: true, can_publish: true, status: 'draft', release_count: 0,
  }
  api.defaults.adapter = async config => {
    const payload = config.data ? JSON.parse(config.data) : undefined
    calls.push({ method: config.method, url: config.url, payload, params: config.params })
    let data
    if (config.url === '/applications/resources/') data = { results: [{ id: config.params.kind === 'workflow' ? 'flow-1' : 'collection-1', name: config.params.kind === 'workflow' ? '自动流程' : '帮助文档' }], count: 1, next: null }
    else if (config.url === '/tenants/tenants/') data = { results: [], count: 0, next: null }
    else if (config.url === '/applications/' && config.method === 'post') data = { ...application, ...payload, id: 'created' }
    else if (config.url === '/applications/') {
      if (listFails) return reject(config, 503, '应用服务暂时不可用')
      data = { results: [], count: 0, next: null }
    } else if (config.url === '/applications/a/test/') {
      if (testFails) return reject(config, 503, '知识源不可用', { ...trace, status: 'failed', error_code: 'upstream_unavailable', error_message: '知识源不可用' })
      application.tested_fingerprint = application.draft_fingerprint
      application.last_test_status = 'completed'
      data = { ...trace, input_data: payload.input_data }
    } else if (config.url === '/applications/a/publish/') {
      const release = { id: 'release-1', version: 1, configuration: structuredClone(application.draft), is_active: true, created_at: '2026-10-31T10:00:00Z', knowledge_content_policy: 'live' }
      application.active_release = release
      application.status = 'published'
      application.release_count = 1
      releases = [release]
      data = release
    } else if (config.url === '/applications/a/rollback/') {
      application.active_release = releases.find(release => release.id === payload.release_id)
      application.status = 'published'
      data = application
    } else if (config.url === '/applications/a/unpublish/') {
      application.active_release = null
      application.status = 'unpublished'
      data = application
    } else if (config.url === '/applications/a/api-keys/' && config.method === 'post') {
      const key = { id: 'key-1', name: payload.name, prefix: 'flowly_app_x', is_active: true, revoked_at: null }
      keys = [key]
      data = { ...key, api_key: 'flowly_app_once_secret' }
    } else if (config.url === '/applications/a/api-keys/key-1/revoke/') {
      keys[0].revoked_at = '2026-10-31T10:00:00Z'
      keys[0].is_active = false
      data = keys[0]
    } else if (config.url === '/applications/a/api-keys/') data = { results: keys, count: keys.length, next: null }
    else if (config.url === '/applications/a/releases/') data = { results: releases, count: releases.length, next: null }
    else if (config.url === '/applications/a/requests/request-1/') data = trace
    else if (config.url === '/applications/a/requests/') data = { results: [], count: 0, next: null }
    else if (config.url.startsWith('/applications/') && config.method === 'patch') {
      application = { ...application, ...payload, draft_fingerprint: 'f2', tested_fingerprint: null, last_test_status: null }
      data = application
    } else data = { ...application, id: config.url.split('/')[2] }
    return { status: 200, statusText: 'OK', headers: {}, config, data: { code: 200, data: structuredClone(data) } }
  }
})

function reject(config, status, message, data = null) {
  const error = new Error(message)
  error.config = config
  error.response = { status, config, data: { code: status, message, data } }
  throw error
}

afterEach(() => {
  wrappers.splice(0).forEach(wrapper => wrapper.unmount())
  styles.splice(0).forEach(style => style.remove())
  api.defaults.adapter = originalAdapter
  vi.restoreAllMocks()
})

async function open(path) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/applications', component: Index }, { path: '/applications/:id', component: Detail },
    { path: '/home', component: Home },
    { path: '/elsewhere', component: { template: '<p>Other page</p>' } },
    { path: '/knowledge/:id', component: { template: '<p>Knowledge resource</p>' } },
    { path: '/workflows/:id/edit', component: { template: '<p>Workflow resource</p>' } },
    { path: '/:pathMatch(.*)*', component: { template: '<p>Resource</p>' } },
  ] })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(defineComponent({ setup: () => () => h(RouterView) }), { attachTo: document.body, global: { plugins: [pinia, router] } })
  wrappers.push(wrapper)
  await flushPromises()
  return { wrapper, router, app: useAppStore(pinia) }
}

function button(wrapper, text) { return wrapper.findAll('button').find(item => item.text().includes(text)) }

describe('application delivery workspace', () => {
  it('keeps application playground CSS inside its page after navigating to Home and back', async () => {
    const style = document.createElement('style')
    style.textContent = applicationStyles
    styles.push(style)
    document.head.append(style)
    const { wrapper, router } = await open('/applications/a?tab=test')
    expect(getComputedStyle(wrapper.get('.applications-page .delivery-workbench').element).display).toBe('grid')
    expect(getComputedStyle(wrapper.get('textarea[aria-label="测试输入 JSON"]').element).minHeight).toBe('320px')
    await router.push('/home')
    await flushPromises()
    expect(getComputedStyle(wrapper.get('.delivery-workbench').element).display).toBe('block')
    expect(wrapper.get('.delivery-pulse').exists()).toBe(true)
    await router.push('/applications/a?tab=test')
    await flushPromises()
    expect(getComputedStyle(wrapper.get('.applications-page .delivery-workbench').element).display).toBe('grid')
  })
  it('opens inline creation from the shell action and creates a resource-bound application', async () => {
    const { wrapper, router } = await open('/applications?create=1')
    await wrapper.get('input[aria-label="应用名称"]').setValue('新知识助手')
    await wrapper.get('select[aria-label="知识库"]').setValue('collection-1')
    await wrapper.get('form[aria-label="创建应用"]').trigger('submit')
    await flushPromises()
    expect(calls.find(item => item.method === 'post' && item.url === '/applications/').payload).toMatchObject({ name: '新知识助手', kind: 'knowledge', draft: { collection_id: 'collection-1' } })
    expect(router.currentRoute.value.path).toBe('/applications/created')
  })

  it('shows load failure distinctly from an empty list and retries', async () => {
    listFails = true
    const { wrapper } = await open('/applications')
    expect(wrapper.get('[role="alert"]').text()).toContain('应用服务暂时不可用')
    expect(wrapper.text()).not.toContain('还没有应用')
    listFails = false
    await button(wrapper, '重新加载').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('还没有应用')
  })

  it('blocks navigation for dirty configuration and saves before enabling tests', async () => {
    const { wrapper, router, app } = await open('/applications/a')
    vi.spyOn(app, 'confirm').mockResolvedValue(false)
    await wrapper.get('input[aria-label="应用名称"]').setValue('未保存名称')
    await router.push('/applications/b')
    expect(router.currentRoute.value.params.id).toBe('a')
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('未保存名称')
    await button(wrapper, '测试').trigger('click')
    await flushPromises()
    expect(button(wrapper, '运行草稿测试').element.disabled).toBe(true)
    await button(wrapper, '保存草稿').trigger('click')
    await flushPromises()
    expect(button(wrapper, '运行草稿测试').element.disabled).toBe(false)
    expect(calls.find(item => item.method === 'patch').payload.name).toBe('未保存名称')
  })

  it('runs a real transport test, preserves input keys and displays unknown usage', async () => {
    const { wrapper } = await open('/applications/a?tab=test')
    await wrapper.get('textarea[aria-label="测试输入 JSON"]').setValue('{"query":"退货政策","filters":{"Customer_ID":"a"}}')
    await button(wrapper, '运行草稿测试').trigger('click')
    await flushPromises()
    expect(calls.find(item => item.url.endsWith('/test/')).payload.input_data).toEqual({ query: '退货政策', filters: { Customer_ID: 'a' } })
    expect(wrapper.text()).toContain('My_Result')
    expect(wrapper.text()).toContain('未提供')
    await button(wrapper, '发布与接入').trigger('click')
    await flushPromises()
    expect(button(wrapper, '发布新版本').element.disabled).toBe(false)
  })

  it('retains failed execution trace and input without enabling publication', async () => {
    testFails = true
    const { wrapper } = await open('/applications/a?tab=test')
    await button(wrapper, '运行草稿测试').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('request-1')
    expect(wrapper.text()).toContain('知识源不可用')
    expect(wrapper.get('textarea[aria-label="测试输入 JSON"]').element.value).toContain('query')
    await button(wrapper, '发布与接入').trigger('click')
    await flushPromises()
    expect(button(wrapper, '发布新版本').element.disabled).toBe(true)
  })

  it('publishes a tested draft and shows a one-time key until explicitly dismissed', async () => {
    application.tested_fingerprint = 'f1'
    application.last_test_status = 'completed'
    const { wrapper, app } = await open('/applications/a?tab=publish')
    vi.spyOn(app, 'confirm').mockResolvedValue(true)
    await button(wrapper, '发布新版本').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="application-release-1"]').text()).toContain('线上版本')
    await wrapper.get('input[aria-label="密钥名称"]').setValue('网站服务')
    await button(wrapper, '创建密钥').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('flowly_app_once_secret')
    await button(wrapper, '已保存，隐藏密钥').trigger('click')
    expect(wrapper.text()).not.toContain('flowly_app_once_secret')
    await button(wrapper, '撤销密钥').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('已撤销')
  })

  it('opens a deep-linked request even when it is not on the first page', async () => {
    const { wrapper } = await open('/applications/a?tab=requests&request=request-1')
    expect(wrapper.text()).toContain('request-1')
    expect(wrapper.text()).toContain('Customer_ID')
    expect(calls.some(item => item.url === '/applications/a/requests/request-1/')).toBe(true)
  })

  it('recovers an uncertain test with the same idempotency key and polls a running record', async () => {
    const base = api.defaults.adapter
    const attemptKeys = []
    let posts = 0
    api.defaults.adapter = async config => {
      if (config.url === '/applications/a/test/') {
        attemptKeys.push(config.headers.get('Idempotency-Key'))
        posts++
        if (posts === 1) { const error = new Error('request timeout'); error.code = 'ECONNABORTED'; error.config = config; throw error }
        application.tested_fingerprint = 'f1'
        application.last_test_status = 'completed'
        return { status: 202, statusText: 'Accepted', headers: {}, config, data: { ...trace, status: 'running' } }
      }
      return base(config)
    }
    const { wrapper } = await open('/applications/a?tab=test')
    await button(wrapper, '运行草稿测试').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('恢复测试请求')
    await button(wrapper, '恢复测试请求').trigger('click')
    await flushPromises()
    expect(attemptKeys).toHaveLength(2)
    expect(attemptKeys[0]).toBeTruthy()
    expect(attemptKeys[1]).toBe(attemptKeys[0])
    expect(wrapper.text()).toContain('My_Result')
    expect(calls.some(item => item.url === '/applications/a/requests/request-1/')).toBe(true)
  })

  it('rejects invalid JSON locally and keeps the entered data', async () => {
    const { wrapper } = await open('/applications/a?tab=test')
    await wrapper.get('textarea[aria-label="测试输入 JSON"]').setValue('[1,2]')
    await button(wrapper, '运行草稿测试').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('输入必须是 JSON 对象')
    expect(wrapper.get('textarea[aria-label="测试输入 JSON"]').element.value).toBe('[1,2]')
    expect(calls.some(item => item.url.endsWith('/test/'))).toBe(false)
  })

  it('shows read-only permissions without loading management keys', async () => {
    application.can_edit = false
    application.can_publish = false
    const { wrapper } = await open('/applications/a?tab=publish')
    expect(wrapper.text()).toContain('发布、回滚和密钥管理需要')
    expect(button(wrapper, '发布新版本')).toBeUndefined()
    expect(wrapper.get('input[aria-label="应用名称"]').element.disabled).toBe(true)
    expect(calls.some(item => item.url.endsWith('/api-keys/'))).toBe(false)
  })

  it('does not expose application deletion to an editor without publisher permission', async () => {
    application.can_edit = true
    application.can_publish = false
    const { wrapper } = await open('/applications/a')
    expect(wrapper.get('input[aria-label="应用名称"]').element.disabled).toBe(false)
    expect(button(wrapper, '删除应用')).toBeUndefined()
  })

  it('creates and tests a workflow application without injecting knowledge configuration', async () => {
    const created = await open('/applications?create=1')
    await created.wrapper.get('select[aria-label="应用类型"]').setValue('workflow')
    await flushPromises()
    await created.wrapper.get('input[aria-label="应用名称"]').setValue('订单自动化')
    await created.wrapper.get('select[aria-label="工作流"]').setValue('flow-1')
    await created.wrapper.get('form[aria-label="创建应用"]').trigger('submit')
    await flushPromises()
    expect(calls.find(item => item.url === '/applications/' && item.method === 'post').payload.draft).toEqual({ workflow_id: 'flow-1' })
    application.kind = 'workflow'
    application.draft = { workflow_id: 'flow-1' }
    const { wrapper } = await open('/applications/a?tab=test')
    await wrapper.get('textarea[aria-label="测试输入 JSON"]').setValue('{"Order_ID":"42","custom_data":{"snake_case":1}}')
    await button(wrapper, '运行草稿测试').trigger('click')
    await flushPromises()
    expect(calls.find(item => item.url.endsWith('/test/')).payload.input_data).toEqual({ Order_ID: '42', custom_data: { snake_case: 1 } })
    expect(wrapper.find('textarea[aria-label="系统提示词"]').exists()).toBe(false)
  })

  it('switches to a historical version and unpublishes without overwriting the draft', async () => {
    releases = [
      { id: 'release-2', version: 2, configuration: { collection_id: 'collection-1', system_prompt: 'v2' } },
      { id: 'release-1', version: 1, configuration: { collection_id: 'collection-1', system_prompt: 'v1' } },
    ]
    application.active_release = releases[0]
    application.status = 'published'
    const originalDraft = structuredClone(application.draft)
    const { wrapper, app } = await open('/applications/a?tab=publish')
    vi.spyOn(app, 'confirm').mockResolvedValue(true)
    await wrapper.get('[data-testid="application-release-1"] [data-testid="application-rollback"]').trigger('click')
    await flushPromises()
    expect(calls.find(item => item.url.endsWith('/rollback/')).payload).toEqual({ release_id: 'release-1' })
    expect(application.active_release.id).toBe('release-1')
    expect(application.draft).toEqual(originalDraft)
    await button(wrapper, '下线应用').trigger('click')
    await flushPromises()
    expect(application.active_release).toBeNull()
    expect(wrapper.text()).toContain('已下线')
  })

  it('invalidates a stale publish attempt and retains the server reason', async () => {
    application.tested_fingerprint = 'f1'
    application.last_test_status = 'completed'
    const base = api.defaults.adapter
    api.defaults.adapter = config => {
      if (config.url === '/applications/a/publish/') {
        application.draft_fingerprint = 'changed-source'
        return reject(config, 409, '源工作流已更改，请重新测试')
      }
      return base(config)
    }
    const { wrapper } = await open('/applications/a?tab=publish')
    await button(wrapper, '发布新版本').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('源工作流已更改，请重新测试')
    expect(button(wrapper, '发布新版本').element.disabled).toBe(true)
  })

  it('ignores an older application load when the same route instance switches identity', async () => {
    const base = api.defaults.adapter
    let resolveFirst
    api.defaults.adapter = config => config.url === '/applications/a/' ? new Promise(resolve => { resolveFirst = () => resolve({ status: 200, statusText: 'OK', headers: {}, config, data: { ...application, name: '旧应用' } }) }) : base(config)
    const { wrapper, router } = await open('/applications/a')
    await router.push('/applications/b')
    await flushPromises()
    resolveFirst()
    await flushPromises()
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客服助手')
    expect(router.currentRoute.value.params.id).toBe('b')
  })

  it('does not report a confirmed publication as failed when the metadata refresh loses connection', async () => {
    application.tested_fingerprint = 'f1'
    application.last_test_status = 'completed'
    const base = api.defaults.adapter
    let published = false
    api.defaults.adapter = async config => {
      if (config.url === '/applications/a/' && published) return reject(config, 503, '状态服务暂时不可用')
      const result = await base(config)
      if (config.url === '/applications/a/publish/') published = true
      return result
    }
    const { wrapper } = await open('/applications/a?tab=publish')
    await button(wrapper, '发布新版本').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('版本已发布，但最新状态读取失败')
    expect(wrapper.get('[data-testid="application-release-1"]').text()).toContain('线上版本')
  })

  it('protects a one-time secret on route changes and clears it after leaving', async () => {
    const { wrapper, router, app } = await open('/applications/a?tab=publish')
    const confirmation = vi.spyOn(app, 'confirm').mockResolvedValue(false)
    await wrapper.get('input[aria-label="密钥名称"]').setValue('服务接入')
    await button(wrapper, '创建密钥').trigger('click')
    await flushPromises()
    await router.push('/applications/b')
    expect(router.currentRoute.value.params.id).toBe('a')
    expect(wrapper.text()).toContain('flowly_app_once_secret')
    confirmation.mockResolvedValue(true)
    await router.push('/applications/b')
    await flushPromises()
    expect(wrapper.text()).not.toContain('flowly_app_once_secret')
  })

  it('links an immutable release to its own successful test evidence', async () => {
    releases = [{ id: 'release-1', version: 1, test_request_id: 'request-1', tested_at: '2026-10-31T10:00:00Z', configuration: {} }]
    const { wrapper, router } = await open('/applications/a?tab=publish')
    const link = wrapper.findAll('a').find(item => item.text().includes('查看测试证据'))
    await link.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ tab: 'requests', request: 'request-1' })
    expect(wrapper.text()).toContain('Customer_ID')
  })
})
