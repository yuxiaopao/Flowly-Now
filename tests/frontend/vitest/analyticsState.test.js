import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAnalyticsStore } from '../../../Frontend/src/stores/analytics'
const api = vi.hoisted(() => Object.fromEntries(['getOverview', 'getTopWorkflows', 'getRecentExecutions', 'getApiUsage', 'getExecutionTrend'].map(key => [key, vi.fn()])))
vi.mock('../../../Frontend/src/api/analytics', () => ({ analyticsApi: api }))
beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })
describe('analytics state and date synchronization', () => {
  it('distinguishes unknown, a persisted zero, and a failed reload', async () => {
    const store = useAnalyticsStore()
    expect(store.totalExecutions).toBeNull()
    api.getOverview.mockResolvedValueOnce({ totalExecutions: 0, successRate: null }).mockRejectedValueOnce(new Error('offline'))
    await store.fetchOverview()
    expect(store.totalExecutions).toBe(0)
    await store.fetchOverview()
    expect(store.overview).toBeNull()
    expect(store.error).toBe('offline')
    expect(store.totalExecutions).toBeNull()
  })
  it('passes one filter to every actual dashboard series and table', async () => {
    for (const fn of Object.values(api)) fn.mockResolvedValue([])
    const store = useAnalyticsStore()
    const filters = { start_date: '2026-10-20T00:00:00Z', end_date: '2026-10-21T23:59:59Z' }
    await store.fetchAll(filters)
    for (const fn of Object.values(api)) expect(fn).toHaveBeenCalledWith(filters)
    expect(store.isLoading).toBe(false)
  })
  it('ignores slow responses from an older filter without clearing current loading state early', async () => {
    const store = useAnalyticsStore()
    let resolveOld, resolveNew
    api.getOverview.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve })).mockImplementationOnce(() => new Promise(resolve => { resolveNew = resolve }))
    const old = store.fetchOverview({ days: 30 })
    const current = store.fetchOverview({ days: 7 })
    resolveOld({ totalExecutions: 99 })
    await old
    expect(store.overview).toBeNull()
    expect(store.isLoading).toBe(true)
    resolveNew({ totalExecutions: 7 })
    await current
    expect(store.totalExecutions).toBe(7)
    expect(store.isLoading).toBe(false)
  })
})
