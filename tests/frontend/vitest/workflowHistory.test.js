import { describe, expect, it } from 'vitest'
import { createWorkflowHistory, recordWorkflowHistory, restoreWorkflowHistory, serializeWorkflowHistory } from '@/utils/workflowHistory'

const node = (value, runtime = 'large-runtime') => ({ id: 'n1', position: { x: value, y: 0 }, data: { config: { user_key: value, _runtime: 'user-owned-config' }, _runtime: { output: runtime } }, style: { color: 'red', _runtime: { status: 'completed' } } })

describe('workflow undo budget', () => {
  it('excludes runtime payloads while preserving executable configuration', () => {
    const snapshot = serializeWorkflowHistory([node(1)], [])
    expect(snapshot).not.toContain('large-runtime')
    expect(snapshot).not.toContain('completed')
    expect(JSON.parse(snapshot).nodes[0].data.config).toEqual({ user_key: 1, _runtime: 'user-owned-config' })
  })
  it('caps entries and retained UTF-16 bytes, with a valid latest state', () => {
    let history = createWorkflowHistory()
    for (let i = 0; i < 40; i++) history = recordWorkflowHistory(history, [node(i)], [], { maxEntries: 5, maxBytes: 1200, now: i })
    expect(history.entries.length).toBeLessThanOrEqual(5)
    expect(history.totalBytes).toBeLessThanOrEqual(1200)
    expect(restoreWorkflowHistory(history, history.index, []).nodes[0].position.x).toBe(39)
    expect(history.totalBytes).toBe(history.entries.reduce((sum, entry) => sum + entry.value.length * 2, 0))
  })
  it('coalesces continuous edits without replacing the pre-edit baseline', () => {
    let history = recordWorkflowHistory(createWorkflowHistory(), [node(0)], [], { now: 0 })
    history = recordWorkflowHistory(history, [node(1)], [], { mergeKey: 'property:n1', now: 100 })
    history = recordWorkflowHistory(history, [node(2)], [], { mergeKey: 'property:n1', now: 200 })
    expect(history.entries).toHaveLength(2)
    expect(restoreWorkflowHistory(history, 0, [node(2, 'new-result')]).nodes[0]).toMatchObject({ position: { x: 0 }, data: { _runtime: { output: 'new-result' } } })
  })
  it('drops the redo branch when recording after undo', () => {
    let history = createWorkflowHistory()
    for (let i = 0; i < 3; i++) history = recordWorkflowHistory(history, [node(i)], [], { now: i })
    history = recordWorkflowHistory({ ...history, index: 0 }, [node(9)], [], { now: 4 })
    expect(history.entries).toHaveLength(2)
    expect(restoreWorkflowHistory(history, history.index, []).nodes[0].position.x).toBe(9)
  })
  it('deduplicates snapshots that only changed runtime', () => {
    let history = recordWorkflowHistory(createWorkflowHistory(), [node(1)], [])
    history = recordWorkflowHistory(history, [node(1, 'new-result')], [])
    expect(history.entries).toHaveLength(1)
  })
  it('keeps the current document usable when one snapshot exceeds the undo budget', () => {
    const history = recordWorkflowHistory(createWorkflowHistory(), [node('x'.repeat(1000))], [], { maxBytes: 10 })
    expect(history.entries).toHaveLength(1)
    expect(restoreWorkflowHistory(history, 0, []).nodes[0].position.x).toHaveLength(1000)
  })
  it('restores deleted-node runtime from one shared reference and prunes it with evicted history', () => {
    const initial = node(1)
    let history = recordWorkflowHistory(createWorkflowHistory(), [initial], [], { now: 0 })
    expect(history.runtimeByNodeId.n1.data).toBe(initial.data._runtime)
    history = recordWorkflowHistory(history, [], [], { now: 1 })
    expect(restoreWorkflowHistory(history, 0, []).nodes[0].data._runtime).toEqual(initial.data._runtime)
    history = recordWorkflowHistory(history, [{ id: 'n2', data: {} }], [], { maxEntries: 1, now: 2 })
    expect(history.runtimeByNodeId.n1).toBeUndefined()
  })
})
