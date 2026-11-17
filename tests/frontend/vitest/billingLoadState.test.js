import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import { useBillingStore } from '../../../Frontend/src/stores/billing'
const api = vi.hoisted(() => ({ getMySubscription: vi.fn() }))
vi.mock('../../../Frontend/src/api/billing', () => ({ billingApi: api }))

describe('billing subscription availability', () => {
  it('reports an unavailable subscription without inventing an active free plan', async () => {
    setActivePinia(createPinia())
    api.getMySubscription.mockRejectedValueOnce(new Error('offline'))
    const store = useBillingStore()
    await store.fetchSubscription()
    expect(store.subscription).toBeNull()
    expect(store.error).toBe('offline')
    expect(store.isLoading).toBe(false)
  })
})
