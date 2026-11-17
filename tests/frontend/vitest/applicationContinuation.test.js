import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, h, nextTick } from 'vue'
import api from '@/api/index'
import { useAppStore } from '@/stores/app'
import { authSession } from '@/utils/authSession'
import { useApplicationWorkspace } from '@/views/applications/useApplicationWorkspace'
import ApplicationReadiness from '@/views/applications/ApplicationReadiness.vue'

const originalAdapter = api.defaults.adapter
let wrapper, workspace, appStore, failLoad, deferredA
const target = (name = 'Actual resource') => ({ configuration_ready: false, connection_verified: false,
  source: { id: 'source', name }, inputs: [], checked_at: '2026-11-01T10:00:00Z',
  checks: [{ code: 'content', label: '知识内容', status: 'blocked', detail: '尚无可检索文档', repair_path: '/knowledge/source' },
    { code: 'upstream', label: '连接', status: 'not_checked', detail: '尚未发送真实请求' }] })

beforeEach(() => {
  failLoad = false; deferredA = null
  localStorage.clear(); sessionStorage.clear()
  authSession.user = { id: 1 }; authSession.access = 'fixture-only'
  api.defaults.adapter = async config => {
    let data
    if (config.url.includes('/readiness/')) {
      if (deferredA && config.url.includes('/a/')) return deferredA(config)
      data = { draft: target(config.url.includes('/b/') ? 'Resource B' : 'Actual resource'), active_release: { ...target('Pinned source'), configuration_ready: true } }
    } else {
      if (failLoad) throw new Error('offline')
      const id = config.url.split('/').filter(Boolean).at(-1)
      data = { id, name: `App ${id}`, kind: 'workflow', draft: { workflow_id: `workflow-${id}` }, description: '',
        can_edit: true, can_publish: true, draft_fingerprint: 'fp', tested_fingerprint: 'fp', last_test_status: 'completed',
        evaluation_gate: { required: true, suite_id: 'suite', ready: false, reason: '需要完整回归' } }
    }
    return { status: 200, statusText: 'OK', headers: {}, config, data: { code: 200, data } }
  }
})
afterEach(() => { wrapper?.unmount(); api.defaults.adapter = originalAdapter; vi.restoreAllMocks(); authSession.user = null; authSession.access = null })

async function openWorkspace(path = '/applications/a') {
  const pinia = createPinia(); setActivePinia(pinia)
  appStore = useAppStore(pinia)
  const Page = defineComponent({ setup() { workspace = useApplicationWorkspace(); return () => h('div') } })
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/applications/:id', component: Page }, { path: '/elsewhere', component: { template: '<div />' } },
  ] })
  await router.push(path)
  wrapper = mount(RouterView, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return router
}

describe('application input and evaluation continuation', () => {
  it('blocks navigation while a write is still synchronizing without offering to discard its result', async () => {
    const router = await openWorkspace('/applications/a?tab=evaluations')
    workspace.evaluationBusy.value = true
    const confirm = vi.spyOn(appStore, 'confirm')
    await router.replace('/applications/a?tab=test')
    expect(router.currentRoute.value.query.tab).toBe('evaluations')
    expect(confirm).not.toHaveBeenCalled()
    expect(workspace.feedback.value).toContain('同步评测')
    workspace.evaluationBusy.value = false
    await router.replace('/applications/a?tab=test')
    expect(router.currentRoute.value.query.tab).toBe('test')
  })
  it('preserves unsaved input across status refresh, failure and retry', async () => {
    await openWorkspace()
    workspace.testInput.value = '{"Customer_ID":"keep", "foo_bar":1, "fooBar":2}'
    expect(workspace.testInputDirty.value).toBe(true)
    await workspace.reload()
    expect(workspace.testInput.value).toContain('Customer_ID')
    failLoad = true
    await workspace.reload()
    expect(workspace.loadError.value).toBeTruthy()
    const refresh = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(refresh)
    expect(refresh.defaultPrevented).toBe(true)
    failLoad = false
    await workspace.load()
    expect(workspace.testInput.value).toContain('fooBar')
  })
  it('guards real route changes then clears input when explicitly discarded for another app', async () => {
    const router = await openWorkspace()
    workspace.testInput.value = '{"Customer_ID":"unsaved"}'
    const confirm = vi.spyOn(appStore, 'confirm').mockResolvedValue(false)
    await router.push('/applications/b')
    expect(router.currentRoute.value.params.id).toBe('a')
    expect(confirm.mock.calls[0][0].title).toContain('测试输入')
    expect(workspace.testInput.value).toContain('unsaved')
    confirm.mockResolvedValue(true)
    await router.push('/applications/b'); await flushPromises()
    expect(workspace.application.value.id).toBe('b')
    expect(workspace.testInput.value).toBe('{}')
  })
  it('only clears the saved-input warning after the exact current input is persisted as a case', async () => {
    await openWorkspace()
    workspace.testInput.value = '{"Customer_ID":"new"}'
    workspace.acknowledgeTestInput({ Customer_ID: 'different' })
    expect(workspace.testInputDirty.value).toBe(true)
    workspace.acknowledgeTestInput({ Customer_ID: 'new' })
    expect(workspace.testInputDirty.value).toBe(false)
  })
  it('protects evaluation edits on query-tab navigation and clears dirty state only after confirmed leave', async () => {
    const router = await openWorkspace('/applications/a?tab=evaluations')
    workspace.evaluationDirty.value = true
    const confirm = vi.spyOn(appStore, 'confirm').mockResolvedValue(false)
    await router.replace('/applications/a?tab=test')
    expect(router.currentRoute.value.query.tab).toBe('evaluations')
    confirm.mockResolvedValue(true)
    await router.replace('/applications/a?tab=test'); await nextTick()
    expect(workspace.evaluationDirty.value).toBe(false)
  })
  it('uses the server evaluation gate and never rewrites an unsaved form when metadata refreshes', async () => {
    await openWorkspace()
    expect(workspace.readyToPublish.value).toBe(false)
    workspace.form.value.name = 'Unsaved name'
    workspace.updateMetadata({ ...workspace.application.value, evaluationGate: { required: true, ready: true } })
    expect(workspace.form.value.name).toBe('Unsaved name')
    expect(workspace.dirty.value).toBe(true)
    expect(workspace.readyToPublish.value).toBe(false)
  })
  it('clears private input and results immediately when the signed-in identity changes', async () => {
    await openWorkspace()
    workspace.testInput.value = '{"private":"secret fixture"}'
    workspace.testResult.value = { outputData: { private: true } }
    authSession.user = { id: 2 }
    await nextTick()
    expect(workspace.application.value).toBeNull()
    expect(workspace.testInput.value).toBe('')
    expect(workspace.testResult.value).toBeNull()
    expect(workspace.loadError.value).toContain('身份已变化')
  })
})

describe('actual readiness metadata boundary', () => {
  async function openReadiness() {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }] })
    await router.push('/')
    const pinia = createPinia(); setActivePinia(pinia)
    wrapper = mount(ApplicationReadiness, { props: { applicationId: 'a' }, global: { plugins: [pinia, router] } })
    await flushPromises()
  }
  it('keeps draft and pinned-release evidence consistent and does not call configuration healthy', async () => {
    await openReadiness()
    expect(wrapper.text()).toContain('尚无可检索文档')
    expect(wrapper.text()).toContain('存在阻塞项')
    expect(wrapper.find('a[href="/knowledge/source"]').exists()).toBe(true)
    await wrapper.find('select').setValue('active_release')
    expect(wrapper.text()).toContain('Pinned source')
    expect(wrapper.text()).toContain('请继续运行真实测试')
  })
  it('ignores a late resource response after the app changes', async () => {
    let resolveA
    deferredA = config => new Promise(resolve => { resolveA = data => resolve({ status: 200, statusText: 'OK', headers: {}, config, data: { code: 200, data } }) })
    await openReadiness()
    await wrapper.setProps({ applicationId: 'b' }); await flushPromises()
    expect(wrapper.text()).toContain('Resource B')
    resolveA({ draft: target('Resource A stale'), active_release: null }); await flushPromises()
    expect(wrapper.text()).not.toContain('Resource A stale')
    expect(wrapper.text()).toContain('Resource B')
  })
})
