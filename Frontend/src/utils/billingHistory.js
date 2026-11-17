export const BILLING_STATUS_LABELS = Object.freeze({ paid: '已支付', pending: '待支付', failed: '失败', refunded: '已退款' })
export const BILLING_STATUS_TONES = Object.freeze({ paid: 'success', pending: 'warning', failed: 'danger', refunded: 'info' })

export function mapBillingHistory(invoice) {
  const date = invoice.periodStart ?? invoice.period_start ?? invoice.createdAt ?? invoice.created_at
  const number = invoice.invoiceNumber ?? invoice.invoice_number
  const total = invoice.total ?? invoice.totalAmount ?? invoice.total_amount
  const currency = invoice.currency || ''
  return {
    id: invoice.id,
    date: typeof date === 'string' ? date.substring(0, 10) : '—',
    description: invoice.description || (number ? `${number} 账单凭证` : '账单凭证'),
    amount: total == null ? '—' : `${currency} ${total}`.trim(),
    status: typeof invoice.status === 'string' ? invoice.status.toLowerCase() : 'unknown',
  }
}
