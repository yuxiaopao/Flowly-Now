import { describe, expect, it, vi } from 'vitest'
import { chunkDistribution, loadRagPages, validateRagFile } from '@/utils/rag'
import { RAG_CONFIG, DOCUMENT_STATUSES } from '@/config/rag'

describe('RAG data handling', () => {
  it('loads every page and preserves server document metadata keys', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce({ results: [{ id: 'first', metadata: { businessKey: 'ops' } }], next: '/next' })
      .mockResolvedValueOnce({ results: [{ id: 'second' }], next: null })
    const rows = await loadRagPages(fetch, { collection: 'collection' })
    expect(rows).toHaveLength(2)
    expect(rows[0].metadata.businessKey).toBe('ops')
    expect(fetch.mock.calls[1][0]).toMatchObject({ collection: 'collection', page: 2 })
  })

  it('stops on an empty page instead of repeatedly requesting a malformed next link', async () => {
    const fetch = vi.fn().mockResolvedValue({ results: [], next: '/next' })
    expect(await loadRagPages(fetch)).toEqual([])
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('builds actual chunk length statistics, including empty collections', () => {
    expect(chunkDistribution([])['0-100']).toBe(0)
    expect(chunkDistribution([{ content: 'a'.repeat(99) }, { content: '文'.repeat(100) }, { content: 'x'.repeat(2000) }]))
      .toEqual({ '0-100': 1, '100-500': 1, '500-1000': 0, '1000-2000': 0, '2000+': 1 })
  })

  it('accepts supported files and rejects empty, binary and oversized uploads', () => {
    expect(validateRagFile({ name: 'Guide.PDF', size: 10 })).toBe('')
    expect(validateRagFile({ name: 'Guide.exe', size: 10 })).toBeTruthy()
    expect(validateRagFile({ name: 'Guide.md', size: 0 })).toBeTruthy()
    expect(validateRagFile({ name: 'Guide.md', size: RAG_CONFIG.maxFileBytes + 1 })).toBeTruthy()
    expect(DOCUMENT_STATUSES.completed.label).toBe('已处理')
  })
})
