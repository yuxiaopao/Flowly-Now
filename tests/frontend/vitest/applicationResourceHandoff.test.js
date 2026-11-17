import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { defineComponent, h } from 'vue'
import ElementPlus from 'element-plus'
import api from '@/api/index'
import { authSession } from '@/utils/authSession'
import GlobalModal from '@/components/common/GlobalModal.vue'
import Applications from '@/views/applications/Index.vue'
import Knowledge from '@/views/knowledge/Index.vue'
import { APPLICATION_RESOURCE_HANDOFF as HANDOFF, applicationResourceHandoff as handoff } from '@/utils/applicationResourceHandoff'

const originalAdapter = api.defaults.adapter
let team
const sid = '22222222-2222-4222-8222-222222222222'
let wrapper, router, calls, collections, collectionFails, removedTeam, resourceHidden, resolveCollection, holdCollection, mismatchedTenant, appCreateFails

function signIn(user = 1, session = sid) {
  authSession.user = { id: user, username: 'fixture-user' }
  authSession.access = `eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify({ user_id: user, sid: session }))}.fixture`
}

beforeEach(() => {
  sessionStorage.clear(); localStorage.clear()
  team = '11111111-1111-4111-8111-111111111111'
  signIn()
  calls = []; collections = []
  collectionFails = false; removedTeam = false; resourceHidden = false; holdCollection = false; resolveCollection = null
  mismatchedTenant = false; appCreateFails = false
  api.defaults.adapter = async config => {
    const payload = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
    calls.push({ url: config.url, method: config.method, payload, params: config.params })
    let data
    if (config.url === '/applications/resources/') data = { results: resourceHidden ? [] : collections.filter(row => String(row.tenant || '') === String(config.params.tenant_id || '')), next: null, count: collections.length }
    else if (config.url === '/tenants/tenants/') data = { results: removedTeam ? [] : [{ id: team, name: '交付团队' }], next: null, count: removedTeam ? 0 : 1 }
    else if (config.url === `/tenants/tenants/${team}/`) {
      if (removedTeam) throw failure(config, '团队权限已失效', 404)
      data = { id: team, name: '交付团队', status: 'active' }
    }
    else if (config.url === '/rag/collections/' && config.method === 'post') {
      if (collectionFails) throw failure(config, '没有权限在该团队创建知识库', 403)
      data = { ...payload, tenant: mismatchedTenant ? null : payload.tenant, id: '33333333-3333-4333-8333-333333333333' }
      collections.push(data)
      if (holdCollection) return new Promise(resolve => { resolveCollection = () => resolve(response(config, data)) })
    } else if (config.url === '/rag/collections/') data = { results: collections, next: null, count: collections.length }
    else if (config.url === '/applications/' && config.method === 'post') {
      if (appCreateFails) throw failure(config, '当前团队不再允许创建应用', 403)
      data = { ...payload, id: 'application-created' }
    }
    else data = { results: [], next: null, count: 0 }
    return response(config, data)
  }
})

afterEach(() => {
  wrapper?.unmount(); wrapper = null
  api.defaults.adapter = originalAdapter
  authSession.user = null; authSession.access = null
  vi.restoreAllMocks()
  document.querySelectorAll('.el-overlay, .el-popper, .modal-overlay').forEach(element => element.remove())
})

function response(config, data) { return { status: 200, statusText: 'OK', headers: {}, config, data: { code: 200, data: structuredClone(data) } } }
function failure(config, message, status) { const error = new Error(message); error.config = config; error.response = { status, config, data: { code: status, message } }; return error }

async function open() {
  const pinia = createPinia(); setActivePinia(pinia)
  router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/applications', component: Applications }, { path: '/knowledge', component: Knowledge },
    { path: '/applications/:id', component: { template: '<p>应用详情</p>' } },
    { path: '/elsewhere', component: { template: '<p>其他页面</p>' } },
  ] })
  await router.push('/applications?create=1'); await router.isReady()
  wrapper = mount(defineComponent({ setup: () => () => h('div', [h(RouterView), h(GlobalModal)]) }),
    { attachTo: document.body, global: { plugins: [pinia, router, ElementPlus] } })
  await flushPromises()
}

function action(scope, text) { return scope.findAll('button, a').find(item => item.text().replace(/\s+/g, '').includes(text)) }
function collectionDialog() { return wrapper.findAllComponents({ name: 'ElDialog' }).find(item => item.props('title') === '创建文档集合') }
async function startHandoff() {
  await open()
  await wrapper.get('input[aria-label="应用名称"]').setValue('客户支持助手')
  await wrapper.get('textarea[aria-label="用途说明"]').setValue('保留这段尚未提交的用途说明')
  await wrapper.get('select[aria-label="所属空间"]').setValue(team)
  await flushPromises()
  await action(wrapper, '先创建知识库').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/knowledge')
}

describe('new application → knowledge resource → original application draft', () => {
  it('displays the verified team label when the real API uses numeric tenant IDs', async () => {
    team = 7
    await startHandoff()
    const dialog = collectionDialog()
    const select = dialog.findAllComponents({ name: 'ElSelect' }).find(item => item.props('disabled'))
    expect(select.props('modelValue')).toBe(7)
    expect(select.text()).toContain('交付团队')
    await dialog.find('input[placeholder="输入集合名称"]').setValue('数字团队知识库')
    await action(dialog, '创建').trigger('click'); await flushPromises()
    expect(calls.find(call => call.url === '/rag/collections/' && call.method === 'post').payload.tenant).toBe(7)
    expect(wrapper.get('select[aria-label="所属空间"]').element.value).toBe('7')
    expect(wrapper.get('select[aria-label="知识库"]').element.value).toBe(collections[0].id)
  })

  it('preserves the named team draft and binds the newly created same-team collection', async () => {
    await startHandoff()
    expect(document.querySelector('.modal-overlay')).toBeNull()
    expect(router.currentRoute.value.fullPath).not.toContain('客户支持助手')
    const dialog = collectionDialog()
    expect(dialog.props('modelValue')).toBe(true)
    await dialog.find('input[placeholder="输入集合名称"]').setValue('客户手册')
    await action(dialog, '创建').trigger('click'); await flushPromises()
    const createCollection = calls.find(call => call.url === '/rag/collections/' && call.method === 'post')
    expect(createCollection.payload.tenant).toBe(team)
    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客户支持助手')
    expect(wrapper.get('textarea[aria-label="用途说明"]').element.value).toContain('尚未提交')
    expect(wrapper.get('select[aria-label="所属空间"]').element.value).toBe(team)
    expect(wrapper.get('select[aria-label="知识库"]').element.value).toBe(collections[0].id)
    await wrapper.get('form[aria-label="创建应用"]').trigger('submit'); await flushPromises()
    expect(calls.find(call => call.url === '/applications/' && call.method === 'post').payload).toMatchObject({
      name: '客户支持助手', description: '保留这段尚未提交的用途说明', tenant_id: team,
      draft: { collection_id: collections[0].id },
    })
  })

  it('cancels resource creation and restores the same application without submitting anything', async () => {
    await startHandoff()
    await collectionDialog().find('input[placeholder="输入集合名称"]').setValue('尚未创建的集合')
    await action(collectionDialog(), '取消').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客户支持助手')
    expect(wrapper.get('select[aria-label="所属空间"]').element.value).toBe(team)
    expect(calls.filter(call => call.method === 'post')).toHaveLength(0)
  })

  it('keeps the collection fields and original team draft after a real HTTP permission failure, then retries', async () => {
    await startHandoff()
    collectionFails = true
    await collectionDialog().find('input[placeholder="输入集合名称"]').setValue('重试不会丢名称')
    await action(collectionDialog(), '创建').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/knowledge')
    expect(collectionDialog().text()).toContain('没有权限在该团队创建知识库')
    expect(collectionDialog().find('input[placeholder="输入集合名称"]').element.value).toBe('重试不会丢名称')
    collectionFails = false
    await action(collectionDialog(), '创建').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.get('select[aria-label="知识库"]').element.value).toBe(collections[0].id)
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客户支持助手')
  })

  it('refuses an expired handoff but restores the still-valid application draft', async () => {
    await startHandoff()
    const now = Date.now()
    vi.spyOn(Date, 'now').mockReturnValue(now + HANDOFF.handoffTtlMs + 1)
    await collectionDialog().find('input[placeholder="输入集合名称"]').setValue('过期后不提交')
    await action(collectionDialog(), '创建').trigger('click'); await flushPromises()
    expect(collectionDialog().text()).toContain('上下文已过期')
    expect(calls.some(call => call.method === 'post')).toBe(false)
    await action(collectionDialog(), '取消').trigger('click'); await flushPromises()
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客户支持助手')
    expect(wrapper.text()).toContain('应用草稿已恢复')
  })

  it('does not auto-bind a collection that the server resource contract no longer permits', async () => {
    await startHandoff()
    resourceHidden = true
    await collectionDialog().find('input[placeholder="输入集合名称"]').setValue('服务端限制的集合')
    await action(collectionDialog(), '创建').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客户支持助手')
    expect(wrapper.get('select[aria-label="知识库"]').element.value).toBe('')
    expect(wrapper.text()).toContain('不在当前空间可绑定')
  })

  it('keeps a saved form after navigation cancellation and retains the ordinary leave confirmation', async () => {
    await open()
    await wrapper.get('input[aria-label="应用名称"]').setValue('导航取消仍保留')
    router.beforeEach(to => to.path === '/knowledge' ? false : true)
    await action(wrapper, '先创建知识库').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('导航取消仍保留')
    const navigation = router.push('/elsewhere')
    await flushPromises()
    expect(document.body.textContent).toContain('放弃未创建的应用')
    const stay = [...document.querySelectorAll('button')].find(button => button.textContent.includes('继续填写'))
    stay.click(); await flushPromises(); await navigation
    expect(router.currentRoute.value.path).toBe('/applications')
  })

  it('keeps the form in place when session storage cannot safely save it', async () => {
    await open()
    await wrapper.get('input[aria-label="应用名称"]').setValue('浏览器存储失败也保留')
    vi.spyOn(sessionStorage, 'setItem').mockImplementation(() => { throw new Error('quota') })
    await action(wrapper, '先创建知识库').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.text()).toContain('无法安全暂存应用草稿')
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('浏览器存储失败也保留')
  })

  it('preserves the same session draft through a token refresh', async () => {
    await startHandoff()
    signIn(1, sid)
    await flushPromises()
    await action(collectionDialog(), '取消').trigger('click'); await flushPromises()
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客户支持助手')
  })

  it('does not restore private form data after identity changes during collection creation', async () => {
    await startHandoff()
    holdCollection = true
    await collectionDialog().find('input[placeholder="输入集合名称"]').setValue('旧身份私有集合')
    await action(collectionDialog(), '创建').trigger('click'); await flushPromises()
    expect(resolveCollection).toBeTypeOf('function')
    signIn(2, '44444444-4444-4444-8444-444444444444')
    await flushPromises()
    resolveCollection(); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/knowledge')
    expect(wrapper.text()).not.toContain('客户支持助手')
    expect(wrapper.text()).not.toContain('旧身份私有集合')
    expect(handoff.read().status).not.toBe('draft')
  })

  it('does not switch a revoked team context to personal creation', async () => {
    await startHandoff()
    await action(collectionDialog(), '取消').trigger('click'); await flushPromises()
    removedTeam = true
    await action(wrapper, '先创建知识库').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/knowledge')
    expect(calls.some(call => call.method === 'post')).toBe(false)
    expect(wrapper.text()).toContain('原团队不可用')
    expect(collectionDialog().props('modelValue')).toBe(false)
    await action(wrapper, '返回应用草稿').trigger('click'); await flushPromises()
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客户支持助手')
    expect(wrapper.get('select[aria-label="所属空间"]').element.value).toBe(team)
  })

  it('does not overwrite current input or follow external paths from an invalid context', async () => {
    await open()
    await wrapper.get('input[aria-label="应用名称"]').setValue('当前草稿不能被旧链接覆盖')
    await router.replace({ path: '/applications', query: { create: '1', [HANDOFF.queryKey]: 'https://outside.invalid/private' } })
    await flushPromises()
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('当前草稿不能被旧链接覆盖')
    expect(wrapper.text()).toContain('上下文无效')
    expect(router.currentRoute.value.path).toBe('/applications')
  })

  it('removes expired private draft contents and explicitly reports the retention limit', async () => {
    await startHandoff()
    const now = Date.now()
    vi.spyOn(Date, 'now').mockReturnValue(now + HANDOFF.draftTtlMs + 1)
    await action(collectionDialog(), '取消').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('')
    expect(wrapper.text()).toContain('保留期限')
    expect(sessionStorage.getItem(HANDOFF.storageKey)).not.toContain('客户支持助手')
    expect(sessionStorage.getItem(HANDOFF.storageKey)).not.toContain('尚未提交')
  })

  it('rejects a previous login session even when the account id is unchanged', async () => {
    await startHandoff()
    signIn(1, '55555555-5555-4555-8555-555555555555')
    await flushPromises()
    await action(wrapper, '返回应用草稿').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('')
    expect(wrapper.text()).not.toContain('客户支持助手')
  })

  it('keeps the ordinary knowledge entry independent and does not force a return or team', async () => {
    await open()
    await router.push('/knowledge'); await flushPromises()
    await action(wrapper, '新建集合').trigger('click'); await flushPromises()
    await collectionDialog().find('input[placeholder="输入集合名称"]').setValue('正常个人知识库')
    await action(collectionDialog(), '创建').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/knowledge')
    expect(calls.find(call => call.url === '/rag/collections/' && call.method === 'post').payload.tenant).toBeNull()
    expect(router.currentRoute.value.query[HANDOFF.queryKey]).toBeUndefined()
  })

  it('rejects a mismatched server resource scope without issuing a second create request', async () => {
    await startHandoff()
    mismatchedTenant = true
    await collectionDialog().find('input[placeholder="输入集合名称"]').setValue('不允许跨空间绑定')
    await action(collectionDialog(), '创建').trigger('click'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/knowledge')
    expect(collectionDialog().text()).toContain('所属空间不一致')
    await action(collectionDialog(), '返回应用草稿').trigger('click'); await flushPromises()
    expect(calls.filter(call => call.url === '/rag/collections/' && call.method === 'post')).toHaveLength(1)
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客户支持助手')
    expect(wrapper.get('select[aria-label="知识库"]').element.value).toBe('')
  })

  it('keeps the restored draft when the server denies final application creation', async () => {
    await startHandoff()
    await collectionDialog().find('input[placeholder="输入集合名称"]').setValue('可绑定的手册')
    await action(collectionDialog(), '创建').trigger('click'); await flushPromises()
    appCreateFails = true
    await wrapper.get('form[aria-label="创建应用"]').trigger('submit'); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.text()).toContain('当前团队不再允许创建应用')
    expect(wrapper.get('input[aria-label="应用名称"]').element.value).toBe('客户支持助手')
    expect(wrapper.get('select[aria-label="知识库"]').element.value).toBe(collections[0].id)
    expect(handoff.read().draft.name).toBe('客户支持助手')
  })
})
