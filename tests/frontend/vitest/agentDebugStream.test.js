import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAgentStore } from '../../../Frontend/src/stores/agent'
import { reportedTokenUsage } from '../../../Frontend/src/config/agentDebug'

const api = vi.hoisted(() => ({ streamChat: vi.fn(), debug: vi.fn(), getById: vi.fn() }))
vi.mock('../../../Frontend/src/api/agent', () => ({ agentApi: api }))
const encoder = new TextEncoder()
function responseFor(text, split = 1) {
  const bytes = encoder.encode(text)
  return new Response(new ReadableStream({ start(controller) {
    for (let offset = 0; offset < bytes.length; offset += split) controller.enqueue(bytes.slice(offset, offset + split))
    controller.close()
  } }), { status: 200 })
}
beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })
describe('agent debugging through actual SSE readers and Pinia', () => {
  it('preserves split UTF-8 frames, updates the visible message, and reuses conversation identity', async () => {
    api.streamChat.mockImplementation(() => Promise.resolve(responseFor(': ping\r\n\r\ndata:{"type":"content","content":"中文🙂"}\r\n\r\ndata: {"type":"done","conversation_id":"conversation-1"}\r\n\r\n')))
    const store = useAgentStore()
    await store.streamChatMessage('agent-1', 'hi')
    expect(store.debugMessages[1]).toMatchObject({ role: 'assistant', content: '中文🙂', isStreaming: false })
    await store.streamChatMessage('agent-1', 'continue')
    expect(api.streamChat.mock.calls[1][1].conversation_id).toBe('conversation-1')
    expect(store.isStreaming).toBe(false)
  })
  it('surfaces stream errors and premature disconnects without claiming success', async () => {
    const store = useAgentStore()
    api.streamChat.mockResolvedValueOnce(responseFor('data: {"type":"error","error":"模型不可用"}\n\n'))
    await expect(store.streamChatMessage('agent-1', 'hi')).rejects.toThrow('模型不可用')
    expect(store.debugMessages.at(-1)).toMatchObject({ role: 'error', isStreaming: false })
    api.streamChat.mockResolvedValueOnce(responseFor('data: {"type":"content","content":"partial"}\n\n'))
    await expect(store.streamChatMessage('agent-1', 'retry')).rejects.toThrow('提前关闭')
    expect(store.isStreaming).toBe(false)
  })
  it('clearing a session aborts the reader and rejects late state from an old response', async () => {
    let resolve
    api.streamChat.mockImplementation(() => new Promise(done => { resolve = done }))
    const store = useAgentStore()
    const pending = store.streamChatMessage('agent-1', 'hi')
    const signal = api.streamChat.mock.calls[0][2].signal
    store.clearDebugSession()
    expect(signal.aborted).toBe(true)
    resolve(responseFor('data: {"type":"content","content":"old"}\n\ndata: {"type":"done","conversation_id":"old"}\n\n'))
    await pending
    expect(store.debugMessages).toEqual([])
    expect(store.currentDebugSession).toBeNull()
  })
  it('retains normal debug execution IDs and guards concurrent submissions', async () => {
    const store = useAgentStore()
    let resolve
    api.debug.mockImplementation(() => new Promise(done => { resolve = done }))
    const pending = store.sendDebugMessage('agent-1', 'hi')
    await expect(store.sendDebugMessage('agent-1', 'duplicate')).rejects.toThrow('等待')
    resolve({ executionId: 'execution-1', response: 'answer', toolCalls: [{ name: 'lookup' }] })
    await pending
    expect(store.currentDebugSession.session_id).toBe('execution-1')
    expect(store.debugMessages.at(-1).toolCalls).toEqual([{ name: 'lookup' }])
    expect(store.isLoading).toBe(false)
  })
  it('does not mistake character estimates or missing counters for reported provider usage', () => {
    expect(reportedTokenUsage({ tokenCount: 45 })).toBeNull()
    expect(reportedTokenUsage(null)).toBeNull()
    expect(reportedTokenUsage({ usage: { total_tokens: 0 } })).toBe(0)
    expect(reportedTokenUsage({ usage: { totalTokens: 45 } })).toBe(45)
  })
  it('ignores a slow Agent A load after Agent B has become current', async () => {
    const store = useAgentStore()
    let resolveA
    api.getById.mockImplementationOnce(() => new Promise(resolve => { resolveA = resolve })).mockResolvedValueOnce({ id: 'B', name: 'Agent B' })
    const slow = store.fetchAgent('A')
    await store.fetchAgent('B')
    resolveA({ id: 'A', name: 'Agent A' })
    await slow
    expect(store.currentAgent.id).toBe('B')
  })
})
