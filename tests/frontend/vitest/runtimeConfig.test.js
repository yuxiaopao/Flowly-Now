import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Cookies from 'js-cookie'

vi.mock('@/api/index', () => ({ api: { defaults: { baseURL: '' } }, request: {} }))

function page(url) {
  const location = new URL(url)
  vi.stubGlobal('window', { location })
}
function environment({ mode = 'production', api = '', ws = '', devBackend = '' } = {}) {
  vi.stubEnv('MODE', mode)
  vi.stubEnv('DEV', mode === 'development')
  vi.stubEnv('PROD', mode !== 'development')
  vi.stubEnv('VITE_API_URL', api)
  vi.stubEnv('VITE_WS_URL', ws)
  vi.stubEnv('VITE_DEV_BACKEND_URL', devBackend)
  vi.stubEnv('VITE_API_PREFIX', '/api/v1')
}
beforeEach(() => { vi.resetModules(); Cookies.remove('access_token'); localStorage.clear() })
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

describe('deployed frontend endpoint resolution', () => {
  it.each(['https://flows.example.test', 'http://flows.example.test:8080', 'http://127.0.0.1:5200'])(
    'defaults production API, streaming URLs and WebSockets to the page origin %s', async origin => {
      environment(); page(`${origin}/login`)
      const config = await import('@/config')
      expect(config.APP_CONFIG.apiBaseUrl).toBe(origin)
      expect(config.getApiBaseUrl()).toBe(`${origin}/api/v1`)
      expect(config.getPublicApiUrl('/workflows/7/stream_execute/')).toBe(`${origin}/api/v1/workflows/7/stream_execute/`)
      expect(config.getWebSocketUrl('/ws/execution/7/')).toBe(`${origin.replace(/^http/, 'ws')}/ws/execution/7/`)
    },
  )

  it('keeps production same-origin defaults after loading backend loopback runtime settings', async () => {
    environment(); page('https://flows.example.test/home')
    const config = await import('@/config')
    config.applyRuntimeConfig({ api_base_url: 'http://127.0.0.1:8000', ws_url: 'ws://localhost:8000', llm: { default_model: 'configured-model' } })
    expect(config.APP_CONFIG.apiBaseUrl).toBe('https://flows.example.test')
    expect(config.getPublicApiUrl('/sse/')).toBe('https://flows.example.test/api/v1/sse/')
    expect(config.getWebSocketUrl('/ws/agent/')).toBe('wss://flows.example.test/ws/agent/')
    expect(config.APP_CONFIG.llm.defaultModel).toBe('configured-model')
  })

  it('honors explicit cross-origin API and WS environment values over runtime defaults', async () => {
    environment({ api: 'https://api.example.test/', ws: 'wss://events.example.test/' }); page('https://flows.example.test/')
    const config = await import('@/config')
    config.applyRuntimeConfig({ api_base_url: 'http://localhost:8000', ws_url: 'ws://127.0.0.1:8000' })
    expect(config.getApiBaseUrl()).toBe('https://api.example.test/api/v1')
    expect(config.getWebSocketUrl('/ws/execution/7/')).toBe('wss://events.example.test/ws/execution/7/')
  })

  it('permits a non-loopback public runtime endpoint when no environment override is present', async () => {
    environment(); page('https://flows.example.test/')
    const config = await import('@/config')
    config.applyRuntimeConfig({ api_base_url: 'https://api.example.test', ws_url: 'wss://events.example.test' })
    expect(config.getApiBaseUrl()).toBe('https://api.example.test/api/v1')
    expect(config.getWebSocketUrl('/ws/agent/')).toBe('wss://events.example.test/ws/agent/')
  })

  it('keeps Electron file-mode cloud configuration and derives secure WebSockets from HTTPS APIs', async () => {
    environment({ mode: 'electron', api: 'https://api.example.test' }); page('file:///C:/Flowly/renderer/index.html#/home')
    const config = await import('@/config')
    expect(config.getApiBaseUrl()).toBe('https://api.example.test/api/v1')
    expect(config.getPublicApiUrl('/sse/')).toBe('https://api.example.test/api/v1/sse/')
    expect(config.getWebSocketUrl('/ws/agent/')).toBe('wss://api.example.test/ws/agent/')
  })

  it('keeps explicit development proxy routing after public runtime configuration', async () => {
    environment({ mode: 'development', devBackend: 'http://127.0.0.1:8000' }); page('http://127.0.0.1:5200/home')
    const config = await import('@/config')
    config.applyRuntimeConfig({ api_base_url: 'https://wrong.example.test', ws_url: 'wss://wrong.example.test' })
    expect(config.getApiBaseUrl()).toBe('http://127.0.0.1:5200/api/v1')
    expect(config.getPublicApiUrl('/sse/')).toBe('http://127.0.0.1:5200/api/v1/sse/')
    expect(config.getWebSocketUrl('/ws/agent/')).toBe('ws://127.0.0.1:5200/ws/agent/')
  })

  it('uses the same API entrance for the real Agent streaming request', async () => {
    environment(); page('https://flows.example.test/')
    const { createPinia, setActivePinia } = await import('pinia')
    setActivePinia(createPinia())
    const { useAgent } = await import('@/composables/useAgent')
    const agent = useAgent()
    agent.currentAgent.value = { id: 7 }
    const fetch = vi.fn().mockResolvedValue({ ok: true, body: { getReader: () => ({ read: async () => ({ done: true }), cancel: async () => {} }) } })
    vi.stubGlobal('fetch', fetch)
    await agent.sendMessageStream('fixture message')
    expect(fetch).toHaveBeenCalledWith('https://flows.example.test/api/v1/agents/7/stream_chat/', expect.any(Object))
  })

  it.each(['http://localhost.:8000', 'http://127.12.34.56:8000', 'http://[::1]:8000'])(
    'does not advertise backend loopback %s to production clients', async endpoint => {
      environment(); page('https://flows.example.test/')
      const config = await import('@/config')
      config.applyRuntimeConfig({ api_base_url: endpoint, ws_url: endpoint.replace(/^http/, 'ws') })
      expect(config.getApiBaseUrl()).toBe('https://flows.example.test/api/v1')
      expect(config.getWebSocketUrl('/ws/agent/')).toBe('wss://flows.example.test/ws/agent/')
    },
  )
})
