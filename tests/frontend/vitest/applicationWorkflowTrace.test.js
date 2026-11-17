import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import api from '@/api/index'
import ApplicationRequestTrace from '@/views/applications/ApplicationRequestTrace.vue'

const originalAdapter = api.defaults.adapter
const request = { id: 'request-1', applicationId: 'app-1', workflowExecutionId: 'hidden-execution', status: 'completed', mode: 'evaluation', inputData: { Customer_ID: 'keep' }, outputData: { foo_bar: 1, fooBar: 2 } }
let wrapper, calls, status, failureStatus, deferred, nodeStatus
const raw = id => ({ id: `execution-${id}`, status, started_at: '2026-11-01T10:00:00Z', completed_at: null,
  nodes: [{ node_id: `source-${id}`, node_name: `Actual node ${id}`, node_type: 'subworkflow', status: nodeStatus || status, started_at: '2026-11-01T10:00:01Z', completed_at: null, error_message: status === 'failed' ? '<b>Actual error</b>' : '' }] })
beforeEach(() => {
  calls = []; status = 'running'; failureStatus = null; deferred = null; nodeStatus = null
  api.defaults.adapter = async config => {
    calls.push(config)
    const captured = structuredClone(raw(config.url.includes('request-2') ? 'two' : 'one'))
    if (deferred) await deferred
    if (failureStatus) {
      const error = new Error('Fixture unavailable'); error.config = config
      error.response = { status: failureStatus, config, data: { detail: 'Fixture denied execution access' } }
      throw error
    }
    return { status: 200, statusText: 'OK', headers: {}, config, data: captured }
  }
})
afterEach(() => { wrapper?.unmount(); wrapper = null; api.defaults.adapter = originalAdapter })
async function open(extra = {}) {
  const pinia = createPinia(); setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  await router.push('/')
  wrapper = mount(ApplicationRequestTrace, { props: { request: { ...request, ...extra } }, global: { plugins: [pinia, router] } })
  await flushPromises()
}
const toggle = () => wrapper.get('[data-testid="application-workflow-trace-toggle"]')

describe('application-scoped actual workflow execution trace', () => {
  it('reads only the application request scope and keeps request state and opaque payload separate', async () => {
    nodeStatus = 'retrying'
    await open()
    expect(calls).toHaveLength(0)
    expect(wrapper.find('a[href*="/executions/"]').exists()).toBe(false)
    await toggle().trigger('click'); await flushPromises()
    expect(calls[0].url).toBe('/applications/app-1/requests/request-1/execution/')
    expect(calls[0].preserveResponseKeys).toBe(true)
    expect(wrapper.get('[data-testid="application-workflow-trace-status"]').text()).toBe('运行中')
    expect(wrapper.get('table[aria-label="主流程节点状态"]').text()).toContain('Actual node one')
    expect(wrapper.get('table[aria-label="主流程节点状态"]').text()).toContain('重试中')
    expect(wrapper.text()).toContain('最终结果以应用请求日志为准')
    expect(wrapper.get('.delivery-state[data-status="completed"]').text()).toBe('成功')
    expect(wrapper.text()).toContain('"Customer_ID": "keep"')
    expect(wrapper.text()).toContain('"foo_bar": 1')
    expect(wrapper.text()).toContain('"fooBar": 2')
  })

  it('refreshes actual state and renders server errors as text', async () => {
    await open(); await toggle().trigger('click'); await flushPromises()
    status = 'failed'
    await wrapper.get('[data-testid="application-workflow-trace-refresh"]').trigger('click'); await flushPromises()
    expect(calls).toHaveLength(2)
    expect(wrapper.get('[data-testid="application-workflow-trace-status"]').text()).toBe('失败')
    const table = wrapper.get('table[aria-label="主流程节点状态"]')
    expect(table.text()).toContain('<b>Actual error</b>')
    expect(table.find('b').exists()).toBe(false)
  })

  it.each([403, 404])('shows scoped %s errors with a real retry', async code => {
    failureStatus = code
    await open(); await toggle().trigger('click'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain(code === 403 ? '无权查看' : '尚无可访问')
    expect(wrapper.find('table[aria-label="主流程节点状态"]').exists()).toBe(false)
    failureStatus = null
    await wrapper.get('[data-testid="application-workflow-trace-retry"]').trigger('click'); await flushPromises()
    expect(wrapper.find('table[aria-label="主流程节点状态"]').exists()).toBe(true)
    expect(calls).toHaveLength(2)
  })

  it('replaces an old successful summary with the real refresh error', async () => {
    await open(); await toggle().trigger('click'); await flushPromises()
    failureStatus = 403
    await wrapper.get('[data-testid="application-workflow-trace-refresh"]').trigger('click'); await flushPromises()
    expect(wrapper.find('[data-testid="application-workflow-trace-status"]').exists()).toBe(false)
    expect(wrapper.get('[role="alert"]').text()).toContain('无权查看')
    failureStatus = null; status = 'cancelled'
    await wrapper.get('[data-testid="application-workflow-trace-retry"]').trigger('click'); await flushPromises()
    expect(wrapper.get('[data-testid="application-workflow-trace-status"]').text()).toBe('已取消')
  })

  it('reports a malformed server response instead of manufacturing an empty success', async () => {
    api.defaults.adapter = async config => ({ status: 200, statusText: 'OK', headers: {}, config, data: { id: 'execution', status: 'completed', nodes: {} } })
    await open(); await toggle().trigger('click'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('响应格式错误')
    expect(wrapper.find('table[aria-label="主流程节点状态"]').exists()).toBe(false)
  })

  it('isolates late responses after selecting a different request and aborts the old read', async () => {
    let finishOld
    deferred = new Promise(resolve => { finishOld = resolve })
    await open(); await toggle().trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('正在加载工作流执行概要')
    const oldRead = calls[0]
    deferred = null
    await wrapper.setProps({ request: { ...request, id: 'request-2', workflowExecutionId: 'another-hidden-execution' } })
    await toggle().trigger('click'); await flushPromises()
    expect(oldRead.signal.aborted).toBe(true)
    expect(wrapper.text()).toContain('Actual node two')
    finishOld(); await flushPromises()
    expect(wrapper.text()).not.toContain('Actual node one')
    expect(wrapper.text()).toContain('Actual node two')
  })

  it('aborts the in-flight execution read on unmount', async () => {
    let finish
    deferred = new Promise(resolve => { finish = resolve })
    await open(); await toggle().trigger('click'); await flushPromises()
    wrapper.unmount()
    expect(calls[0].signal.aborted).toBe(true)
    finish(); await flushPromises(); wrapper = null
  })

  it('does not guess an application scope for an incomplete historical request', async () => {
    await open({ applicationId: undefined })
    expect(toggle().element.disabled).toBe(true)
    expect(wrapper.text()).toContain('请重新加载请求详情')
    expect(calls).toHaveLength(0)
  })
})
