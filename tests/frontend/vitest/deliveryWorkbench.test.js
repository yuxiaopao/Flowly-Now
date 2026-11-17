import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Home from '../../../Frontend/src/views/dashboard/Home.vue'

const api = vi.hoisted(() => ({ overview: vi.fn(), workflows: vi.fn() }))
vi.mock('../../../Frontend/src/api/applications', () => ({ applicationsApi: { overview: api.overview } }))
vi.mock('../../../Frontend/src/api/workflow', () => ({ getWorkflowList: api.workflows }))

let wrapper
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })
async function open() {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
  ] })
  await router.push('/home')
  wrapper = mount(Home, { global: { plugins: [router], stubs: { FlowlyBot: true } } })
  await flushPromises()
  return router
}
describe('application delivery workbench', () => {
  it.each([[0.9285714285714286, '92.9%'], [0, '0%'], [1, '100%'], [null, '—']])('formats the API success ratio %s as %s', async (successRate, expected) => {
    api.overview.mockResolvedValue({ successRate, recentApplications: [], recentRequests: [] })
    api.workflows.mockResolvedValue({ results: [] })
    await open()
    const success = wrapper.findAll('.pulse-metric').find(metric => metric.find('dt').text() === '成功率')
    expect(success.find('dd').text()).toBe(expected)
  })
  it('keeps large counts and latency readable without abbreviating the underlying figures', async () => {
    api.overview.mockResolvedValue({ applicationCount: 1234567890123, requestCount: 9876543210987,
      avgLatencyMs: 123456789.125, successRate: 0.9285714285714286,
      recentApplications: [], recentRequests: [] })
    api.workflows.mockResolvedValue({ results: [] })
    await open()
    const values = Object.fromEntries(wrapper.findAll('.pulse-metric').map(metric => [metric.find('dt').text(), metric.find('dd').text()]))
    expect(values['应用']).toBe('1,234,567,890,123')
    expect(values['请求']).toBe('9,876,543,210,987')
    expect(values['平均耗时']).toBe('123,456,789.125 ms')
    expect(values['成功率']).toBe('92.9%')
  })
  it('shows persisted releases and request deep links while keeping unknown usage unknown', async () => {
    api.overview.mockResolvedValue({ applicationCount: 1, publishedCount: 1, requestCount: 1, failedCount: 0,
      successRate: null, avgLatencyMs: null, usageComplete: false,
      recentApplications: [{ id: 'app-1', name: '客服知识助手', kind: 'knowledge', activeRelease: { version: 2 } }],
      recentRequests: [{ id: 'request-1', applicationId: 'app-1', mode: 'invoke', status: 'failed', errorMessage: '模型服务不可用', latencyMs: 52 }],
    })
    api.workflows.mockResolvedValue({ results: [{ id: 'wf-1', name: '工单分流', nodeCount: 3 }] })
    await open()
    expect(wrapper.text()).toContain('已发布 v2')
    expect(wrapper.text()).toContain('模型服务不可用')
    expect(wrapper.find('a[href="/applications/app-1?tab=requests&request=request-1"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('费用以实际返回为准')
    expect(wrapper.text()).not.toContain('0%')
    expect(wrapper.find('a[href="/workflows/wf-1/edit"]').text()).toContain('工单分流')
  })
  it('offers a concrete first application path for empty real data', async () => {
    api.overview.mockResolvedValue({ applicationCount: 0, publishedCount: 0, requestCount: 0, failedCount: 0, recentApplications: [], recentRequests: [] })
    api.workflows.mockResolvedValue({ results: [] })
    await open()
    expect(wrapper.text()).toContain('把第一个原型变成可调用的应用')
    expect(wrapper.findAll('a[href="/applications?create=1"]').length).toBeGreaterThan(0)
    expect(wrapper.text()).toContain('应用测试或接入调用后')
  })
  it('keeps build resources accessible on overview failure and recovers with retry', async () => {
    api.overview.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ applicationCount: 2, recentApplications: [], recentRequests: [] })
    api.workflows.mockResolvedValue({ results: [{ id: 'wf-2', name: '已有流程' }] })
    await open()
    expect(wrapper.find('[role="alert"]').text()).toContain('应用交付数据加载失败')
    expect(wrapper.text()).toContain('已有流程')
    expect(wrapper.find('.delivery-pulse').text()).not.toContain('0%')
    await wrapper.find('[role="alert"] button').trigger('click')
    await flushPromises()
    expect(api.overview).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })
})
