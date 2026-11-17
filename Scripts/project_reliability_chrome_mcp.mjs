import assert from 'node:assert/strict'
import { McpClient, evalPage, login, delay, FRONTEND_URL } from './chrome_mcp_client.mjs'

if (process.env.FLOWLY_ISOLATED_QA !== '1') throw new Error('Run only against the isolated QA backend (FLOWLY_ISOLATED_QA=1)')

const client = new McpClient()
const checks = []
async function page(fn) { return evalPage(client, fn.toString(), 45000) }
async function check(name, fn) {
  const result = await fn()
  assert.equal(result.ok, true, `${name}: ${JSON.stringify(result)}`)
  checks.push({ name, ...result })
  console.log(JSON.stringify({ name, ...result }))
}

try {
  await client.initialize()
  assert(client.pageTools.has('navigate_page'), 'Chrome DevTools navigate_page must be available')
  await login(client, { entryPath: '/api/health/' })
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/workflows`, timeout: 30000 })
  await delay(1200)
  await check('create isolated workflow fixtures', () => page(async () => {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
    const run = `reliability-qa-${Date.now()}`
    window.__reliabilityQa = { ids: [], names: [], token }
    for (const suffix of ['A', 'B']) {
      const name = `${run}-${suffix}`
      const response = await fetch('/api/v1/workflows/', {
        method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, nodes: [
          { id: 'start', type: 'start', position: { x: 100, y: 100 }, data: { label: `${suffix} Start`, config: {} } },
          { id: 'end', type: 'end', position: { x: 400, y: 100 }, data: { label: `${suffix} End`, config: {} } },
        ], edges: [{ source: 'start', target: 'end' }] }),
      })
      const payload = await response.json()
      if (!response.ok) return { ok: false, status: response.status, message: payload.message }
      const workflow = payload.data || payload
      window.__reliabilityQa.ids.push(workflow.id)
      window.__reliabilityQa.names.push(name)
    }
    return { ok: window.__reliabilityQa.ids.length === 2 }
  }))
  await check('switch A to B loads the matching document', () => page(async () => {
    const router = document.querySelector('#app').__vue_app__.config.globalProperties.$router
    const qa = window.__reliabilityQa
    const waitName = async name => {
      for (let i = 0; i < 80; i++) {
        if (document.querySelector('.workflow-name-input')?.value === name) return true
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      return false
    }
    await router.push(`/workflows/${qa.ids[0]}/edit`)
    if (!await waitName(qa.names[0])) return { ok: false, stage: 'load A' }
    await router.push(`/workflows/${qa.ids[1]}/edit`)
    const loaded = await waitName(qa.names[1])
    return { ok: loaded && document.querySelectorAll('.vue-flow__node').length === 2, path: location.pathname }
  }))
  await check('unblurred edits protect refresh and show the leave confirmation', () => page(async () => {
    const input = document.querySelector('.workflow-name-input')
    input.value = `${window.__reliabilityQa.names[1]} changed`
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await new Promise(resolve => setTimeout(resolve, 50))
    const unload = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(unload)
    const router = document.querySelector('#app').__vue_app__.config.globalProperties.$router
    window.__reliabilityQa.navigation = router.push(`/workflows/${window.__reliabilityQa.ids[0]}/edit`)
    await new Promise(resolve => setTimeout(resolve, 150))
    return { ok: unload.defaultPrevented && !!document.querySelector('.modal-box'), refreshProtected: unload.defaultPrevented }
  }))
  await check('cancelling the leave dialog preserves the current document', () => page(async () => {
    const dialog = document.querySelector('.modal-box')
    const cancel = [...dialog.querySelectorAll('button')].find(button => button.textContent.includes('取消'))
    cancel.click()
    await window.__reliabilityQa.navigation
    await new Promise(resolve => setTimeout(resolve, 350))
    return { ok: location.pathname.includes(window.__reliabilityQa.ids[1]) && document.querySelector('.workflow-name-input').value.endsWith(' changed') }
  }))
  await check('confirming discard loads the requested document', () => page(async () => {
    const qa = window.__reliabilityQa
    const router = document.querySelector('#app').__vue_app__.config.globalProperties.$router
    qa.navigation = router.push(`/workflows/${qa.ids[0]}/edit`)
    await new Promise(resolve => setTimeout(resolve, 100))
    const dialog = [...document.querySelectorAll('.modal-box')].at(-1)
    const buttons = [...dialog.querySelectorAll('button')]
    buttons.find(button => button.textContent.includes('确定') || button.textContent.includes('离开')).click()
    await qa.navigation
    for (let i = 0; i < 80; i++) {
      if (document.querySelector('.workflow-name-input')?.value === qa.names[0]) return { ok: true }
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    return { ok: false }
  }))
  await check('real execution and authenticated WebSocket status round trip', () => page(async () => {
    const qa = window.__reliabilityQa
    const response = await fetch(`/api/v1/workflows/${qa.ids[0]}/execute/`, {
      method: 'POST', headers: { Authorization: `Bearer ${qa.token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ input_data: {}, is_async: false }),
    })
    const payload = await response.json()
    const data = payload.data || payload
    if (!response.ok) return { ok: false, status: response.status, message: payload.message }
    const { ExecutionWebSocket } = await import('/src/api/websocket.js')
    const socket = new ExecutionWebSocket(data.execution_id)
    try {
      await socket.connect()
      const url = new URL(socket.ws.url)
      const status = new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('status timed out')), 5000)
        socket.on('execution_status', message => { clearTimeout(timer); resolve(message) })
      })
      socket.getStatus()
      const event = await status
      return { ok: data.status === 'completed' && url.searchParams.getAll('token').length === 1 && event.status === 'completed', executionStatus: data.status }
    } finally { socket.disconnect() }
  }))
  await check('missing documents clear the old graph and expose a working retry', () => page(async () => {
    const router = document.querySelector('#app').__vue_app__.config.globalProperties.$router
    const missing = '00000000-0000-4000-8000-000000000000'
    await router.push(`/workflows/${missing}/edit`)
    const waitError = async () => {
      for (let i = 0; i < 80; i++) {
        if (document.querySelector('.el-alert--error')?.textContent.includes('重试')) return true
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      return false
    }
    if (!await waitError()) return { ok: false, stage: 'error feedback' }
    const requests = []
    const observer = new PerformanceObserver(list => requests.push(...list.getEntries()))
    observer.observe({ type: 'resource' })
    document.querySelector('.el-alert--error button').click()
    await new Promise(resolve => setTimeout(resolve, 500))
    const errorVisible = await waitError()
    observer.disconnect()
    const retryObserved = requests.some(entry => entry.name.includes(missing))
    const nodes = document.querySelectorAll('.vue-flow__node').length
    return { ok: errorVisible && retryObserved && nodes === 0, errorVisible, retryObserved, nodes }
  }))
  await check('upgraded chart runtime renders the monitoring page', () => page(async () => {
    const app = document.querySelector('#app').__vue_app__
    await app.config.globalProperties.$router.push('/monitoring')
    for (let attempt = 0; attempt < 100; attempt++) {
      const chart = document.querySelector('.trend-chart')
      const canvas = chart?.querySelector('canvas')
      if (chart?.getAttribute('_echarts_instance_') && canvas?.width > 0 && canvas?.height > 0) {
        return { ok: document.body.innerText.includes('执行监控'), chartWidth: canvas.width, chartHeight: canvas.height }
      }
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    return { ok: false, stage: 'chart initialization' }
  }))
  await check('upgraded Markdown sanitizer removes executable output in Chrome', () => page(async () => {
    const { renderMarkdown } = await import('/src/utils/markdown.js')
    const container = document.createElement('div')
    container.innerHTML = renderMarkdown('<img src="data:image/png;base64,bad" onerror="window.__qaUnsafeMarkup=true"><script>window.__qaUnsafeMarkup=true</script>\n\n**safe output**')
    document.body.append(container)
    await new Promise(resolve => setTimeout(resolve, 100))
    const ok = !window.__qaUnsafeMarkup && !container.querySelector('script,[onerror]') && container.textContent.includes('safe output')
    container.remove()
    delete window.__qaUnsafeMarkup
    return { ok }
  }))
  console.log(JSON.stringify({ passed: checks.length, failed: 0, browser: 'chrome-devtools-mcp' }))
} finally {
  try {
    await page(async () => {
      const qa = window.__reliabilityQa
      if (!qa) return
      for (const id of qa.ids) await fetch(`/api/v1/workflows/${id}/`, { method: 'DELETE', headers: { Authorization: `Bearer ${qa.token}` } })
      delete window.__reliabilityQa
    })
  } finally { client.close() }
}
