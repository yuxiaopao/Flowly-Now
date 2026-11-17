import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { defineComponent, h } from 'vue'
import api from '@/api/index'
import GeneratedSiteDetail from '@/views/projects/GeneratedSiteDetail.vue'

const originalAdapter = api.defaults.adapter
const wrappers = []
let site
let posts
let failFirst
beforeEach(() => {
  posts = []
  failFirst = false
  site = { id: 'site-1', name: '识别站点', status: 'completed', website_type: 'detection', can_rebuild: true,
    source: { status: 'not_recorded', message: '此历史项目未记录源工作流。' }, rebuild_notice: '副本使用新目录，不复制凭据。' }
  api.defaults.adapter = async config => {
    if (config.method === 'post') {
      posts.push({ url: config.url, key: config.headers.get('Idempotency-Key'), payload: JSON.parse(config.data) })
      if (failFirst && posts.length === 1) { const error = new Error('connection lost'); error.config = config; error.code = 'ECONNABORTED'; throw error }
      return { status: 201, statusText: 'Created', headers: {}, config, data: { workflow_id: 'copied-real-workflow', source_site_id: site.id } }
    }
    return { status: 200, statusText: 'OK', headers: {}, config, data: structuredClone(site) }
  }
})
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()); api.defaults.adapter = originalAdapter })

async function open() {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/projects/:id', component: GeneratedSiteDetail },
    { path: '/workflows/:id/edit', component: { template: '<p>Actual editor route</p>' } },
    { path: '/workflows/:id', component: { template: '<p>Read-only workflow route</p>' } },
  ] })
  await router.push('/projects/site-1')
  await router.isReady()
  const wrapper = mount(defineComponent({ setup: () => () => h(RouterView) }), { attachTo: document.body, global: { plugins: [createPinia(), router] } })
  wrappers.push(wrapper)
  await flushPromises()
  return { wrapper, router }
}

describe('generated project workflow source and reconstruction', () => {
  it('opens the canonical source workflow rather than a new fixed template', async () => {
    site.source = { status: 'available', workflow_id: 'canonical-source', can_edit: true }
    const { wrapper, router } = await open()
    await wrapper.get('[data-testid="site-source-workflow"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/workflows/canonical-source/edit')
    expect(posts).toHaveLength(0)
  })

  it('creates a real authorized copy from the public site id before navigating', async () => {
    const { wrapper, router } = await open()
    expect(wrapper.text()).toContain('未记录源工作流')
    expect(wrapper.find('[data-testid="site-source-workflow"]').exists()).toBe(false)
    await wrapper.get('[data-testid="site-rebuild-workflow"]').trigger('click')
    await flushPromises()
    expect(posts).toHaveLength(1)
    expect(posts[0]).toMatchObject({ url: '/website-generator/site-1/rebuild-workflow/', payload: {} })
    expect(posts[0].key).toBeTruthy()
    expect(router.currentRoute.value.path).toBe('/workflows/copied-real-workflow/edit')
  })

  it('retries an uncertain creation with the same key and does not navigate on failure', async () => {
    failFirst = true
    const { wrapper, router } = await open()
    await wrapper.get('[data-testid="site-rebuild-workflow"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/projects/site-1')
    expect(wrapper.text()).toContain('结果未确认')
    await wrapper.get('[data-testid="site-rebuild-workflow"]').trigger('click')
    await flushPromises()
    expect(posts[1].key).toBe(posts[0].key)
    expect(router.currentRoute.value.path).toBe('/workflows/copied-real-workflow/edit')
  })

  it('hides unavailable source and copy actions for a read-only viewer', async () => {
    site.can_rebuild = false
    site.source = { status: 'unavailable', message: '源工作流已删除或当前无权访问。' }
    const { wrapper } = await open()
    expect(wrapper.find('[data-testid="site-source-workflow"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="site-rebuild-workflow"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('当前无权访问')
  })
})
