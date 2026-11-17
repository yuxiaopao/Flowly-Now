import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { McpClient, evalPage, login, delay, FRONTEND_URL } from './chrome_mcp_client.mjs'
if (process.env.FLOWLY_ISOLATED_QA !== '1') throw new Error('This test requires the isolated fixture backend')
const client = new McpClient()
const checks = []
async function page(fn) { return evalPage(client, fn.toString(), 45000) }
async function check(name, fn) { const result = await fn(); assert.equal(result.ok, true, `${name}: ${JSON.stringify(result)}`); checks.push(name); console.log(JSON.stringify({ name, ...result })) }
try {
  await client.initialize()
  assert(client.pageTools.has('navigate_page'))
  await login(client, { entryPath: '/api/health/' })
  await client.tool('emulate', { viewport: '1440x1000x1', prefersReducedMotion: 'reduce' })
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/applications?create=1` })
  await delay(900)
  await check('create a workflow application through the real form', () => page(async () => {
    window.__deliveryQa = { token: localStorage.getItem('access_token'), apps: [] }
    const marker = await fetch('/api/v1/__isolated-qa__/').then(response => response.json())
    if (!marker.isolated || !marker.product_fixtures) throw new Error('Refusing to mutate a non-fixture backend')
    window.__deliveryWait = async predicate => { for (let n = 0; n < 100; n++) { if (await predicate()) return; await new Promise(resolve => setTimeout(resolve, 100)) }; throw new Error('Timed out waiting for application UI') }
    window.__deliveryInput = (selector, value) => { const field = document.querySelector(selector); if (!field) throw new Error(`Missing field ${selector}`); field.value = value; field.dispatchEvent(new Event(field.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })) }
    window.__deliveryCall = async (path, options = {}, key) => {
      const result = await fetch(`/api/v1/${path}`, { ...options, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${key || window.__deliveryQa.token}`, ...(options.headers || {}) } })
      const json = await result.json(); return { status: result.status, data: json.data ?? json }
    }
    const fixture = await window.__deliveryCall('workflows/', { method: 'POST', body: JSON.stringify({
      name: `QA 独立客服流程 ${Date.now()}`, nodes: [
        { id: 'start', type: 'start', position: { x: 0, y: 0 }, data: { label: '输入', config: {} } },
        { id: 'reply', type: 'text_template', position: { x: 250, y: 0 }, data: { label: '回复', config: { template: 'Hello {{customerName}}' } } },
        { id: 'end', type: 'end', position: { x: 500, y: 0 }, data: { label: '输出', config: {} } },
      ], edges: [{ source: 'start', target: 'reply' }, { source: 'reply', target: 'end' }],
    }) })
    if (fixture.status !== 201) return { ok: false, stage: 'isolated source fixture', status: fixture.status }
    window.__deliveryQa.sourceId = fixture.data.id
    await window.__deliveryWait(() => document.querySelector('[data-testid="application-name"]'))
    window.__deliveryInput('[data-testid="application-name"]', `QA 团队交付 ${Date.now()}`)
    window.__deliveryInput('[data-testid="application-kind"]', 'workflow')
    await window.__deliveryWait(() => [...(document.querySelector('[data-testid="application-source"]')?.options || [])].some(option => option.value === fixture.data.id))
    const option = [...document.querySelector('[data-testid="application-source"]').options].find(item => item.value === fixture.data.id)
    window.__deliveryInput('[data-testid="application-source"]', option.value)
    document.querySelector('[data-testid="application-submit"]').click()
    await window.__deliveryWait(() => /^\/applications\/[0-9a-f-]+$/.test(location.pathname) && document.querySelector('#application-tab-test'))
    window.__deliveryQa.id = location.pathname.split('/').at(-1)
    window.__deliveryQa.apps.push(window.__deliveryQa.id)
    return { ok: document.body.innerText.includes('草稿已保存') }
  }))
  await check('run real draft graph with case-sensitive application input', () => page(async () => {
    document.querySelector('#application-tab-test').click()
    await window.__deliveryWait(() => document.querySelector('[data-testid="application-test-input"]'))
    window.__deliveryInput('[data-testid="application-test-input"]', '{"customerName":"Ada"}')
    document.querySelector('[data-testid="application-test"]').click()
    await window.__deliveryWait(() => document.querySelector('.delivery-trace [data-status="completed"]') || document.querySelector('.delivery-trace [data-status="failed"]'))
    const requests = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/requests/`)
    const result = requests.data.results[0]
    window.__deliveryQa.testId = result.id
    return { ok: result.status === 'completed' && result.input_data.customerName === 'Ada' && JSON.stringify(result.output_data).includes('Hello Ada'), status: result.status }
  }))
  await check('publish fixed v1 with persisted test evidence', () => page(async () => {
    document.querySelector('#application-tab-publish').click()
    await window.__deliveryWait(() => document.querySelector('[data-testid="application-publish"]') && !document.querySelector('[data-testid="application-publish"]').disabled)
    document.querySelector('[data-testid="application-publish"]').click()
    await window.__deliveryWait(() => document.querySelector('[data-testid="application-release-1"]'))
    const releases = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/releases/`)
    const release = releases.data.results[0]
    window.__deliveryQa.release1 = release.id
    return { ok: release.version === 1 && release.test_request_id === window.__deliveryQa.testId, version: release.version }
  }))
  await check('one-time scoped application key invokes only its own endpoint', () => page(async () => {
    window.__deliveryInput('[data-testid="application-key-name"]', 'QA Website integration')
    document.querySelector('[data-testid="application-create-key"]').click()
    await window.__deliveryWait(() => document.querySelector('.delivery-secret code'))
    window.__deliveryQa.key = document.querySelector('.delivery-secret code').textContent.trim()
    const result = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/invoke/`, { method: 'POST', body: '{"input_data":{"customerName":"Grace"}}' }, window.__deliveryQa.key)
    const forbidden = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/`, {}, window.__deliveryQa.key)
    const hide = [...document.querySelectorAll('.delivery-secret button')].find(button => button.textContent.includes('隐藏'))
    hide.click()
    return { ok: result.status === 200 && JSON.stringify(result.data.output_data).includes('Hello Grace') && forbidden.status === 401, invoke: result.status, management: forbidden.status }
  }))
  await check('editing the source graph leaves v1 behavior unchanged and invalidates draft test', () => page(async () => {
    const app = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/`)
    const source = await window.__deliveryCall(`workflows/${app.data.draft.workflow_id}/`)
    const node = source.data.nodes.find(item => item.node_type === 'text_template')
    if (!node) return { ok: false, stage: 'source node' }
    const changed = await window.__deliveryCall(`workflows/nodes/${node.id}/`, { method: 'PATCH', body: JSON.stringify({ config: { template: 'Changed {{customerName}}' } }) })
    const result = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/invoke/`, { method: 'POST', body: '{"input_data":{"customerName":"Grace"}}' }, window.__deliveryQa.key)
    document.querySelector('[data-testid="application-refresh"]').click()
    await window.__deliveryWait(() => document.querySelector('[data-testid="application-publish"]')?.disabled)
    return { ok: changed.status === 200 && result.status === 200 && JSON.stringify(result.data.output_data).includes('Hello Grace') && !JSON.stringify(result.data.output_data).includes('Changed Grace'), frozen: true }
  }))
  await check('test a changed graph, publish v2, then roll back to v1', () => page(async () => {
    document.querySelector('#application-tab-test').click()
    await window.__deliveryWait(() => document.querySelector('[data-testid="application-test"]')?.disabled === false)
    window.__deliveryInput('[data-testid="application-test-input"]', '{"customerName":"Ada"}')
    document.querySelector('[data-testid="application-test"]').click()
    await window.__deliveryWait(() => document.querySelector('.delivery-trace [data-status="completed"]') && document.body.innerText.includes('Changed Ada'))
    document.querySelector('#application-tab-publish').click()
    await window.__deliveryWait(() => document.querySelector('[data-testid="application-publish"]') && !document.querySelector('[data-testid="application-publish"]').disabled)
    document.querySelector('[data-testid="application-publish"]').click()
    await window.__deliveryWait(() => document.querySelector('[data-testid="application-release-2"]'))
    const current = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/invoke/`, { method: 'POST', body: '{"input_data":{"customerName":"Grace"}}' }, window.__deliveryQa.key)
    if (!JSON.stringify(current.data.output_data).includes('Changed Grace')) return { ok: false, stage: 'v2 output' }
    document.querySelector('[data-testid="application-release-1"] [data-testid="application-rollback"]').click()
    await window.__deliveryWait(() => document.querySelector('.modal-box .modal-footer button:last-child'))
    Array.from(document.querySelectorAll('.modal-box .modal-footer button:last-child')).at(-1).click()
    await window.__deliveryWait(async () => (await window.__deliveryCall(`applications/${window.__deliveryQa.id}/`)).data.active_release?.version === 1)
    const reverted = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/invoke/`, { method: 'POST', body: '{"input_data":{"customerName":"Grace"}}' }, window.__deliveryQa.key)
    return { ok: reverted.status === 200 && JSON.stringify(reverted.data.output_data).includes('Hello Grace'), rolledBack: true }
  }))
  await check('revoke key immediately and retain versioned request trace', () => page(async () => {
    await new Promise(resolve => setTimeout(resolve, 350))
    document.querySelector('[data-testid="application-revoke-key"]').click()
    await window.__deliveryWait(() => document.querySelector('.modal-box .modal-footer button:last-child'))
    Array.from(document.querySelectorAll('.modal-box .modal-footer button:last-child')).at(-1).click()
    await window.__deliveryWait(async () => { const keys = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/api-keys/`); return keys.data.results[0].revoked_at })
    const rejected = await window.__deliveryCall(`applications/${window.__deliveryQa.id}/invoke/`, { method: 'POST', body: '{"input_data":{"customerName":"Grace"}}' }, window.__deliveryQa.key)
    document.querySelector('#application-tab-requests').click()
    await window.__deliveryWait(() => document.querySelector('[data-testid^="application-request-"]'))
    document.querySelector('[data-testid^="application-request-"] button').click()
    await window.__deliveryWait(() => document.querySelector('.delivery-trace'))
    return { ok: rejected.status === 401 && document.querySelector('.delivery-trace').textContent.includes('Grace'), revoked: true }
  }))
  await mkdir('Docs/verification/ai-team-20261031', { recursive: true })
  await client.tool('take_screenshot', { filePath: 'E:/Flowly-now/Docs/verification/ai-team-20261031/application-requests.png', fullPage: true })
  console.log(JSON.stringify({ passed: checks.length, failed: 0, browser: 'chrome-devtools-mcp', scope: 'isolated persisted QA fixtures' }))
} finally { client.close() }
