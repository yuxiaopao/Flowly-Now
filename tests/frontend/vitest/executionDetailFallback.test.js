import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ExecutionDetailDialog from '@/components/ExecutionTimeline/ExecutionDetailDialog.vue'
import api from '@/api/index'

class SocketTransport {
  static OPEN = 1
  static instances = []
  readyState = 0
  send = vi.fn()
  constructor(url) { this.url = url; SocketTransport.instances.push(this) }
  close() { this.readyState = 3; this.onclose?.({ code: 1000 }) }
}
let wrapper
let get
beforeEach(() => {
  vi.useFakeTimers()
  vi.stubGlobal('WebSocket', SocketTransport)
  SocketTransport.instances = []
  setActivePinia(createPinia())
  get = vi.spyOn(api, 'get').mockImplementation(async url => url.endsWith('/logs/') ? [] : { id: 7, status: 'running' })
})
afterEach(() => { wrapper?.unmount(); vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

async function openDialog() {
  wrapper = mount(ExecutionDetailDialog, { props: { modelValue: true, executionId: 7 }, global: { plugins: [createPinia()], stubs: {
    ElDialog: { template: '<div><slot /><slot name="footer" /></div>' },
    NodeExecutionTimeline: true, NodeExecutionDetail: true, StreamingOutputPanel: true, ExecutionLogsPanel: true,
  } } })
  await flushPromises()
  return SocketTransport.instances.at(-1)
}

describe('execution detail polling fallback', () => {
  it('polls after an asynchronous WebSocket handshake failure and stops after closing', async () => {
    const socket = await openDialog()
    socket.onerror({})
    await flushPromises()
    await vi.advanceTimersByTimeAsync(3000)
    expect(get.mock.calls.filter(([url]) => /\/executions\/7\/$/.test(url)).length).toBeGreaterThanOrEqual(2)
    await wrapper.setProps({ modelValue: false })
    const callCount = get.mock.calls.length
    await vi.advanceTimersByTimeAsync(6000)
    expect(get.mock.calls.length).toBe(callCount)
  })
})
