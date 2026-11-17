import { describe, expect, it, vi, beforeEach } from 'vitest'
import { effectScope, reactive } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { bootstrapDesktopAgent, useDesktopAgentBridge } from '@/composables/useDesktopAgentBridge'
import { connectDesktopAgent, disconnectDesktopAgent, getDesktopAgentConfig, getDesktopAgentStatus } from '@/utils/electron'

vi.mock('@/utils/electron', () => ({
  isElectron: () => true,
  getDesktopAgentConfig: vi.fn(), getDesktopAgentStatus: vi.fn(),
  connectDesktopAgent: vi.fn(), disconnectDesktopAgent: vi.fn(),
}))
beforeEach(() => {
  vi.clearAllMocks()
  getDesktopAgentConfig.mockResolvedValue({ cloudUrl: 'http://fixture.local/', agentId: 'fixture-agent' })
  getDesktopAgentStatus.mockResolvedValue({ connected: true })
  connectDesktopAgent.mockResolvedValue({ connected: true })
})

describe('desktop agent auth synchronization', () => {
  it('forwards a refreshed token even when the agent is already connected', async () => {
    await bootstrapDesktopAgent('rotated-token')
    expect(connectDesktopAgent).toHaveBeenCalledWith({ cloudUrl: 'http://fixture.local', agentId: 'fixture-agent', apiToken: 'rotated-token' })
  })

  it('does not reconnect an old session after logout overtakes a pending configuration load', async () => {
    let resolveConfig
    getDesktopAgentConfig.mockReturnValueOnce(new Promise(resolve => { resolveConfig = resolve }))
    const scope = effectScope()
    const auth = reactive({ token: 'old-token' })
    scope.run(() => useDesktopAgentBridge(auth))
    auth.token = null
    await flushPromises()
    resolveConfig({ cloudUrl: 'http://fixture.local', agentId: 'fixture-agent' })
    await flushPromises()
    expect(disconnectDesktopAgent).toHaveBeenCalled()
    expect(connectDesktopAgent).not.toHaveBeenCalled()
    scope.stop()
  })
})
