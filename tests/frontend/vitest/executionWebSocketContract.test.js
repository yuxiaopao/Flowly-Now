import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import Cookies from 'js-cookie'
let ExecutionWebSocket, WebSocketService, useExecutionStore


vi.mock('@/api/workflow', () => ({ workflowApi: { getExecution: vi.fn().mockResolvedValue({ id: 7, status: 'completed' }) } }))

class SocketTransport {
  static OPEN = 1
  static instances = []
  readyState = 0
  send = vi.fn()
  constructor(url) { this.url = url; SocketTransport.instances.push(this) }
  open() { this.readyState = 1; this.onopen?.({}) }
  message(payload) { this.onmessage?.({ data: JSON.stringify(payload) }) }
  close(code = 1000) { this.readyState = 3; this.onclose?.({ code }) }
}

beforeEach(async () => {
  vi.useFakeTimers()
  vi.stubGlobal('WebSocket', SocketTransport)
  SocketTransport.instances = []
  setActivePinia(createPinia())
  ;({ ExecutionWebSocket, WebSocketService } = await import('@/api/websocket'))
  ;({ useExecutionStore } = await import('@/stores/execution'))
  localStorage.clear()
  Cookies.set('access_token', 'fixture-token')
})
afterEach(() => { Cookies.remove('access_token'); vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals() })

describe('execution WebSocket transport contract', () => {
  it('sends exactly one valid token and preserves execution parameters', async () => {
    const service = new ExecutionWebSocket(7)
    const connected = service.connect()
    const socket = SocketTransport.instances.at(-1)
    const url = new URL(socket.url)
    expect(url.searchParams.getAll('token')).toEqual(['fixture-token'])
    expect(url.searchParams.get('execution_id')).toBe('7')
    socket.open()
    await connected
    service.disconnect()
  })

  it('delivers backend envelopes and snake_case metadata to the real execution store without changing output keys', async () => {
    const store = useExecutionStore()
    const connected = store.connectWebSocket(7)
    const socket = SocketTransport.instances.at(-1)
    socket.open()
    await connected
    socket.message({ type: 'node_start', data: { execution_id: 7, node_id: 'n1', node_name: 'Fixture' } })
    expect(store.nodeStatusMap.n1).toBe('running')
    socket.message({ type: 'node_output', node_id: 'n1', output: { customer_id: 42, nest: { api_key_name: 'user-field' } } })
    expect(store.nodeOutputs.n1).toEqual({ customer_id: 42, nest: { api_key_name: 'user-field' } })
    socket.message({ type: 'token_update', prompt_tokens: 2, completion_tokens: 3 })
    expect(store.tokenStats.total).toBe(5)
    store.disconnectWebSocket()
  })

  it('rejects failed handshakes so callers can start HTTP polling', async () => {
    const service = new ExecutionWebSocket(7)
    const connected = service.connect()
    const rejected = expect(connected).rejects.toThrow()
    SocketTransport.instances.at(-1).onerror({})
    await rejected
    service.disconnect()
  })

  it('rejects a handshake that closes before opening or never responds', async () => {
    const service = new ExecutionWebSocket(7)
    const closed = service.connect()
    const rejected = expect(closed).rejects.toThrow()
    SocketTransport.instances.at(-1).close(4401)
    await rejected
    service.disconnect()
    const timedOut = service.connect()
    const timeoutRejected = expect(timedOut).rejects.toThrow('超时')
    await vi.advanceTimersByTimeAsync(10000)
    await timeoutRejected
    service.disconnect()
  })

  it('applies backend status snapshots without replacing state values with objects', async () => {
    const store = useExecutionStore()
    const connected = store.connectWebSocket(7)
    const socket = SocketTransport.instances.at(-1)
    socket.open()
    await connected
    socket.message({ type: 'execution_status', data: { id: 7, status: 'running', node_status: { n1: { status: 'completed', output: { user_key: 1 } } }, output_data: { user_key: 1 } } })
    expect(store.nodeStatusMap.n1).toBe('completed')
    expect(store.nodeOutputs.n1).toEqual({ user_key: 1 })
    expect(store.outputData).toEqual({ user_key: 1 })
    store.disconnectWebSocket()
  })

  it('keeps a failed terminal status and retrieves a fresh snapshot on opening', async () => {
    const { workflowApi } = await import('@/api/workflow')
    workflowApi.getExecution.mockResolvedValueOnce({ id: 7, status: 'failed' })
    const store = useExecutionStore()
    const connected = store.connectWebSocket(7)
    const socket = SocketTransport.instances.at(-1)
    socket.open()
    await connected
    expect(socket.send.mock.calls.map(([message]) => JSON.parse(message).type)).toContain('get_status')
    socket.message({ type: 'execution_complete', data: { execution_id: 7, status: 'failed', error: 'fixture failure' } })
    expect(store.executionStatus).toBe('failed')
    store.disconnectWebSocket()
  })

  it('does not reconnect after explicit disconnect, including a queued reconnect', async () => {
    const service = new ExecutionWebSocket(7)
    const connected = service.connect()
    SocketTransport.instances.at(-1).open()
    await connected
    SocketTransport.instances.at(-1).close(1006)
    service.disconnect()
    await vi.advanceTimersByTimeAsync(10000)
    expect(SocketTransport.instances).toHaveLength(1)
  })

  it('reconnects to the original path using the current token', async () => {
    const service = new WebSocketService()
    const connected = service.connect('/ws/workflow/9/', { workflowId: 9 })
    SocketTransport.instances.at(-1).open()
    await connected
    SocketTransport.instances.at(-1).close(1006)
    Cookies.set('access_token', 'rotated-token')
    await vi.advanceTimersByTimeAsync(1000)
    const socket = SocketTransport.instances.at(-1)
    const url = new URL(socket.url)
    expect(url.pathname).toBe('/ws/workflow/9/')
    expect(url.searchParams.getAll('token')).toEqual(['rotated-token'])
    expect(url.searchParams.get('workflow_id')).toBe('9')
    socket.open()
    service.disconnect()
  })
})
