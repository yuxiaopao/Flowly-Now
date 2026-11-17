import { describe, expect, it } from 'vitest'
import { mapBillingHistory, BILLING_STATUS_LABELS } from '../../../Frontend/src/utils/billingHistory'

describe('persisted billing history', () => {
  it('shows the real camelCase API number, total and currency, including zero', () => {
    expect(mapBillingHistory({ id: 7, invoiceNumber: 'INV-007', periodStart: '2026-10-01T12:00:00Z', total: '0.00', currency: 'USD', status: 'refunded' }))
      .toEqual({ id: 7, date: '2026-10-01', description: 'INV-007 账单凭证', amount: 'USD 0.00', status: 'refunded' })
    expect(BILLING_STATUS_LABELS.refunded).toBe('已退款')
  })
  it('does not infer paid or invent an amount when metadata is missing', () => {
    expect(mapBillingHistory({ id: 8 })).toMatchObject({ date: '—', description: '账单凭证', amount: '—', status: 'unknown' })
  })
  it('retains legacy snake_case response support', () => {
    expect(mapBillingHistory({ invoice_number: 'INV-008', created_at: '2026-10-31', total_amount: 99, status: 'PENDING', currency: 'CNY' }))
      .toMatchObject({ date: '2026-10-31', amount: 'CNY 99', status: 'pending' })
  })
})
