import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { McpClient, evalPage, login, delay, FRONTEND_URL } from './chrome_mcp_client.mjs'
if (process.env.FLOWLY_ISOLATED_QA !== '1') throw new Error('Run only against isolated product fixtures')
const client = new McpClient()
const checks = []
async function page(fn) { return evalPage(client, fn.toString(), 60000) }
async function check(name, fn) { const value = await fn(); assert.equal(value.ok, true, `${name}: ${JSON.stringify(value)}`); checks.push(name); console.log(JSON.stringify({ name, ...value })) }
try {
  await client.initialize()
  assert(client.pageTools.has('navigate_page'))
  await login(client, { entryPath: '/api/health/' })
  await client.tool('emulate', { viewport: '1440x1000x1', prefersReducedMotion: 'reduce' })
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/applications?create=1` })
  await delay(600)
  await check('knowledge application rejects unsupported evidence and blocks publication', () => page(async () => {
    window.__productQa = { token: localStorage.getItem('access_token') }
    const marker = await fetch('/api/v1/__isolated-qa__/').then(response => response.json())
    if (!marker.isolated || !marker.product_fixtures) throw new Error('Refusing to mutate a non-fixture backend')
    window.__productWait = async (predicate, label = 'product UI') => { for (let n = 0; n < 150; n++) { if (await predicate()) return; await new Promise(resolve => setTimeout(resolve, 100)) }; throw new Error(`Timed out waiting for ${label}`) }
    window.__productInput = (selector, value) => { const field = document.querySelector(selector); if (!field) throw new Error(`Missing field ${selector}`); field.value = value; field.dispatchEvent(new Event(field.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })) }
    window.__productCall = async (path, options = {}) => { const response = await fetch(`/api/v1/${path}`, { ...options, headers: { Authorization: `Bearer ${window.__productQa.token}`, 'Content-Type': 'application/json', ...(options.headers || {}) } }); const json = await response.json(); return { status: response.status, data: json.data ?? json } }
    window.__productRouter = document.querySelector('#app').__vue_app__.config.globalProperties.$router
    await window.__productWait(() => document.querySelector('[data-testid="application-name"]'))
    window.__productInput('[data-testid="application-name"]', '团队知识助手（隔离验证）')
    const source = document.querySelector('[data-testid="application-source"]')
    await window.__productWait(() => [...source.options].some(option => option.textContent.includes('QA Release Playbook')))
    window.__productInput('[data-testid="application-source"]', [...source.options].find(option => option.textContent.includes('QA Release Playbook')).value)
    document.querySelector('[data-testid="application-submit"]').click()
    await window.__productWait(() => document.querySelector('#application-tab-test'))
    window.__productQa.knowledgeId = location.pathname.split('/').at(-1)
    document.querySelector('#application-tab-test').click()
    await window.__productWait(() => document.querySelector('[data-testid="application-test-input"]'))
    window.__productInput('[data-testid="application-test-input"]', '{"query":"zzzz_no_evidence_1983"}')
    document.querySelector('[data-testid="application-test"]').click()
    await window.__productWait(() => document.querySelector('.delivery-trace [data-status="failed"]'))
    const request = (await window.__productCall(`applications/${window.__productQa.knowledgeId}/requests/`)).data.results[0]
    document.querySelector('#application-tab-publish').click()
    await window.__productWait(() => document.querySelector('[data-testid="application-publish"]'))
    return { ok: request.error_code === 'no_evidence' && document.querySelector('[data-testid="application-publish"]').disabled, errorCode: request.error_code }
  }))
  await check('indexed knowledge runs through local HTTP provider fixture with real citations', () => page(async () => {
    document.querySelector('#application-tab-test').click()
    await window.__productWait(() => document.querySelector('[data-testid="application-test-input"]'))
    window.__productInput('[data-testid="application-test-input"]', '{"query":"release"}')
    document.querySelector('[data-testid="application-test"]').click()
    await window.__productWait(() => document.querySelector('.delivery-trace [data-status="completed"]'))
    const request = (await window.__productCall(`applications/${window.__productQa.knowledgeId}/requests/`)).data.results[0]
    if (!request.output_data?.grounded || !request.output_data.sources?.length) return { ok: false, status: request.status, errorCode: request.error_code }
    document.querySelector('#application-tab-publish').click()
    await window.__productWait(() => document.querySelector('[data-testid="application-publish"]')?.disabled === false)
    document.querySelector('[data-testid="application-publish"]').click()
    await window.__productWait(() => document.querySelector('[data-testid="application-release-1"]'))
    return { ok: request.output_data.response.includes('[1]'), sourceCount: request.output_data.sources.length, provider: 'isolated local HTTP fixture; not model quality validation' }
  }))
  await check('project source opens its actual workflow and historical project creates a configured copy', () => page(async () => {
    const sites = (await window.__productCall('website-generator/')).data
    const rows = sites.results || sites
    const canonical = rows.find(site => site.name.includes('QA 有来源项目'))
    const historical = rows.find(site => site.name.includes('QA 历史识别项目'))
    if (!canonical || !historical) return { ok: false, stage: 'site fixtures' }
    await window.__productRouter.push(`/projects/${canonical.id}`)
    await window.__productWait(() => document.querySelector('[data-testid="site-source-workflow"]'))
    document.querySelector('[data-testid="site-source-workflow"]').click()
    await window.__productWait(() => location.pathname.includes(`/workflows/${canonical.source.workflow_id}/edit`))
    await window.__productRouter.push(`/projects/${historical.id}`)
    await window.__productWait(() => document.querySelector('[data-testid="site-rebuild-workflow"]'))
    document.querySelector('[data-testid="site-rebuild-workflow"]').click()
    await window.__productWait(() => /^\/workflows\/[0-9a-f-]+\/edit$/.test(location.pathname))
    const id = location.pathname.split('/')[2]
    const copy = (await window.__productCall(`workflows/${id}/`)).data
    const config = JSON.stringify(copy.nodes.map(node => node.config))
    window.__productQa.rebuiltWorkflowId = id
    return { ok: copy.nodes.length === 4 && copy.edges.length === 3 && config.includes(historical.id) && config.includes('qa-best.pt'), nodes: copy.nodes.length, edges: copy.edges.length }
  }))
  await check('real Editor label save preserves config keys, model manifest and UUID literals', () => page(async () => {
    const id = window.__productQa.rebuiltWorkflowId
    const original = (await window.__productCall(`workflows/${id}/`)).data
    const node = original.nodes.find(item => item.node_type === 'website_generator')
    const expected = { ...node.config, foo_bar: 1, fooBar: 2, Customer_ID: 'keep',
      literal_uuid: node.id, literal_reference: `node_outputs['${node.id}']` }
    const patched = await window.__productCall(`workflows/nodes/${node.id}/`, { method: 'PATCH', body: JSON.stringify({ config: expected }) })
    if (patched.status !== 200) return { ok: false, stage: 'config fixture' }
    await window.__productRouter.push('/workflows')
    await window.__productRouter.push(`/workflows/${id}/edit`)
    await window.__productWait(() => document.querySelector('.workflow-name-input')?.value === original.name)
    await window.__productWait(() => document.querySelector(`.vue-flow__node[data-id="${node.id}"]`))
    document.querySelector(`.vue-flow__node[data-id="${node.id}"]`).click()
    await window.__productWait(() => document.querySelector('input[placeholder="输入节点名称"]'))
    window.__productInput('input[placeholder="输入节点名称"]', 'QA 配置完整性验证节点')
    document.querySelector('input[placeholder="输入节点名称"]').blur()
    await window.__productWait(() => document.querySelector('button[aria-label="保存工作流"]')?.disabled === false)
    document.querySelector('button[aria-label="保存工作流"]').click()
    let saved
    await window.__productWait(async () => {
      const result = (await window.__productCall(`workflows/${id}/`)).data
      saved = result.nodes.find(item => item.id === node.id)
      return saved?.name === 'QA 配置完整性验证节点'
    }, 'persisted Editor label update')
    const config = saved.config
    return { ok: config.foo_bar === 1 && config.fooBar === 2 && config.Customer_ID === 'keep' &&
      config.literal_uuid === node.id && config.literal_reference === expected.literal_reference &&
      JSON.stringify(config.modelArtifactManifest) === JSON.stringify(expected.modelArtifactManifest) &&
      JSON.stringify(config.wizard) === JSON.stringify(expected.wizard), keysPreserved: true }
  }))
  await check('billing download button returns persisted printable statement content', () => page(async () => {
    const actualCreateUrl = URL.createObjectURL.bind(URL)
    URL.createObjectURL = blob => { if (blob.type.includes('html') || blob.type.includes('json')) window.__productQa.downloadBlob = blob; return actualCreateUrl(blob) }
    await window.__productRouter.push('/settings/billing')
    await window.__productWait(() => [...document.querySelectorAll('button')].some(button => button.textContent.includes('下载凭证')))
    const button = [...document.querySelectorAll('button')].find(item => item.textContent.includes('下载凭证'))
    button.click()
    await window.__productWait(() => window.__productQa.downloadBlob?.type.includes('html'))
    const content = await window.__productQa.downloadBlob.text()
    return { ok: content.includes('QA-BILL-001') && content.includes('12.00') && content.includes('非税务发票'), nativeDownloadTriggered: true }
  }))
  await check('full export is an immutable snapshot and restore cancellation changes nothing', () => page(async () => {
    await window.__productRouter.push('/settings/data-export')
    await window.__productWait(() => document.querySelector('[data-testid="export-full"] button'))
    const before = (await window.__productCall('workflows/?page_size=100')).data
    window.__productQa.beforeRestoreCount = before.count
    const selected = before.results.find(item => item.name.startsWith('QA 独立客服流程'))
    window.__productQa.oldName = selected.name
    const existingExportIds = new Set((await window.__productCall('data-export/?page_size=100')).data.results.map(item => item.id))
    document.querySelector('[data-testid="export-full"] button').click()
    await window.__productWait(() => document.querySelector('[data-testid="export-confirm"]'))
    document.querySelector('[data-testid="export-confirm"]').click()
    await window.__productWait(async () => {
      const rows = (await window.__productCall('data-export/')).data.results
      const backup = rows.find(row => row.export_type === 'full' && row.status === 'completed' && !existingExportIds.has(row.id))
      if (backup) { window.__productQa.exportId = backup.id; return true }
      return false
    }, 'completed persisted export')
    await window.__productCall(`workflows/${selected.id}/`, { method: 'PATCH', body: JSON.stringify({ name: `${selected.name} changed after snapshot` }) })
    const downloaded = await fetch(`/api/v1/data-export/${window.__productQa.exportId}/download/`, { headers: { Authorization: `Bearer ${window.__productQa.token}` } })
    const snapshot = await downloaded.json()
    const archived = snapshot.workflows.find(workflow => workflow.id === selected.id)
    if (archived?.name !== window.__productQa.oldName) return { ok: false, stage: 'snapshot mutability' }
    await window.__productWait(() => document.querySelector(`[data-testid="restore-backup-${window.__productQa.exportId}"]`))
    document.querySelector(`[data-testid="restore-backup-${window.__productQa.exportId}"]`).click()
    await window.__productWait(() => document.querySelector('[data-testid="backup-restore-confirm"]'))
    const dialog = document.querySelector('[data-testid="backup-restore-confirm"]').closest('.el-dialog')
    Array.from(dialog.querySelectorAll('button')).find(button => button.textContent.trim() === '取消').click()
    await new Promise(resolve => setTimeout(resolve, 350))
    const count = (await window.__productCall('workflows/?page_size=1')).data.count
    return { ok: count === window.__productQa.beforeRestoreCount, cancelledWithoutCopies: true }
  }))
  await check('confirmed restore creates real private draft copies while preserving originals', () => page(async () => {
    document.querySelector(`[data-testid="restore-backup-${window.__productQa.exportId}"]`).click()
    await window.__productWait(() => {
      const button = document.querySelector('[data-testid="backup-restore-confirm"]')
      return button && !button.disabled && button.closest('.el-dialog').getClientRects().length > 0
    }, 'visible restore confirmation')
    document.querySelector('[data-testid="backup-restore-confirm"]').click()
    await window.__productWait(async () => (await window.__productCall('workflows/?page_size=1')).data.count > window.__productQa.beforeRestoreCount, 'restored database copies')
    const count = (await window.__productCall('workflows/?page_size=1')).data.count
    return { ok: count > window.__productQa.beforeRestoreCount, before: window.__productQa.beforeRestoreCount, after: count }
  }))
  await check('backup scheduler configuration is explicit and saved policy survives reload', () => page(async () => {
    await new Promise(resolve => setTimeout(resolve, 350))
    const policy = (await window.__productCall('data-export/backup_settings/')).data
    const control = document.querySelector('[aria-label="启用自动备份"]')
    const honest = policy.scheduler_configured ? true : control?.getAttribute('aria-disabled') === 'true' || control?.disabled || control?.closest('.el-switch')?.classList.contains('is-disabled')
    document.querySelector('[data-testid="backup-policy-save"]').click()
    await window.__productWait(() => !document.querySelector('[data-testid="backup-policy-save"]').classList.contains('is-loading'))
    const persisted = (await window.__productCall('data-export/backup_settings/')).data
    return { ok: Boolean(honest) && persisted.enabled === policy.enabled, schedulerConfigured: Boolean(policy.scheduler_configured) }
  }))
  await mkdir('Docs/verification/ai-team-20261031', { recursive: true })
  await client.tool('take_screenshot', { filePath: 'E:/Flowly-now/Docs/verification/ai-team-20261031/personal-backup.png', fullPage: true })
  await check('analytics errors and real empty values do not masquerade as zero usage', () => page(async () => {
    await window.__productRouter.push('/analytics')
    await window.__productWait(() => document.querySelector('.analytics-scope'))
    await window.__productWait(() => !document.querySelector('.stat-card[aria-busy="true"]'))
    const values = [...document.querySelectorAll('.stat-card__value')].map(item => item.textContent.trim())
    return { ok: values.includes('—') && !values.includes('¥0.00') && document.body.innerText.includes('原日志未记录币种'), values }
  }))
  await check('four themes preserve live home data and bounded desktop layout', () => page(async () => {
    await window.__productRouter.push('/home')
    await window.__productWait(() => document.querySelector('.delivery-pulse')?.getAttribute('aria-busy') === 'false')
    const store = document.querySelector('#app').__vue_app__.config.globalProperties.$pinia._s.get('app')
    store.setSidebarCollapsed(false)
    await new Promise(resolve => setTimeout(resolve, 250))
    const overview = (await window.__productCall('applications/overview/')).data
    const success = [...document.querySelectorAll('.pulse-metric')].find(item => item.querySelector('dt').textContent.trim() === '成功率')
    const expected = overview.success_rate == null ? '—' : new Intl.NumberFormat('zh-CN', { style: 'percent', maximumFractionDigits: 1 }).format(overview.success_rate)
    if (success?.querySelector('dd').textContent.trim() !== expected) return { ok: false, stage: 'real ratio formatting', expected }
    const shell = document.querySelector('.delivery-workbench')
    const sections = ['.page-header', '.delivery-pulse', '.delivery-path', '.workbench-columns'].map(selector => shell.querySelector(selector).getBoundingClientRect())
    const flow = sections.every((rect, index) => rect.width >= shell.clientWidth * .9 && (!index || rect.top >= sections[index - 1].bottom - 1))
    if (!flow) return { ok: false, stage: 'application CSS leaked into home flow', sections: sections.map(rect => ({ top: rect.top, bottom: rect.bottom, width: rect.width })) }
    const results = []
    for (const theme of ['dark', 'light', 'pure-bw', 'high-contrast']) {
      store.setTheme(theme)
      await new Promise(resolve => setTimeout(resolve, 100))
      results.push({ theme, active: document.documentElement.dataset.theme, bounded: document.documentElement.scrollWidth <= innerWidth + 1,
        metricTextBounded: [...document.querySelectorAll('.pulse-metric dd')].every(item => item.scrollWidth <= item.clientWidth + 1) })
    }
    store.setTheme('dark')
    return { ok: results.every(item => item.active === item.theme && item.bounded && item.metricTextBounded), themes: results, realSuccessRate: expected }
  }))
  await check('frontend POST stream delivers incremental real graph events and opaque input', () => page(async () => {
    const created = await window.__productCall('workflows/', { method: 'POST', body: JSON.stringify({
      name: 'QA 浏览器实时执行', nodes: [
        { id: 'start', type: 'start', position: { x: 0, y: 0 }, data: { label: '输入', config: {} } },
        { id: 'delay', type: 'delay', position: { x: 250, y: 0 }, data: { label: '短等待', config: { duration: 300, unit: 'ms' } } },
        { id: 'end', type: 'end', position: { x: 500, y: 0 }, data: { label: '输出', config: {} } },
      ], edges: [{ source: 'start', target: 'delay' }, { source: 'delay', target: 'end' }],
    }) })
    if (created.status !== 201) return { ok: false, stage: 'stream fixture', status: created.status }
    const { streamExecuteWorkflow } = await import('/src/api/workflow.js')
    const input = { Customer_ID: 'Keep_CASE', foo_bar: 1, fooBar: 2 }
    const response = await streamExecuteWorkflow(created.data.id, input)
    if (!response.ok || !response.headers.get('content-type').includes('text/event-stream')) return { ok: false, stage: 'stream HTTP', status: response.status }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let text = '', firstAt = null, lastAt = null
    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        if (firstAt == null) firstAt = performance.now()
        lastAt = performance.now()
        text += decoder.decode(value, { stream: true })
      }
      text += decoder.decode()
    } finally { reader.releaseLock() }
    const events = text.split(/\r?\n\r?\n/).filter(frame => frame.startsWith('data:')).map(frame => JSON.parse(frame.slice(5).trim()))
    const first = events[0], last = events.at(-1)
    const persisted = (await window.__productCall(`workflows/executions/${first.execution_id}/`)).data
    return { ok: first.type === 'execution_start' && last.type === 'execution_complete' && last.status === 'completed' &&
      lastAt - firstAt >= 150 && persisted.input_data.Customer_ID === input.Customer_ID && persisted.input_data.foo_bar === 1 && persisted.input_data.fooBar === 2,
      eventCount: events.length, incrementalMilliseconds: Math.round(lastAt - firstAt), status: last.status }
  }))
  await client.tool('take_screenshot', { filePath: 'E:/Flowly-now/Docs/verification/ai-team-20261031/delivery-workbench.png', fullPage: true })
  await page(() => {
    sessionStorage.setItem('flowly_product_qa_knowledge_id', window.__productQa.knowledgeId)
    return { ok: true }
  })
  await client.tool('emulate', { viewport: '390x844x1,mobile,touch', prefersReducedMotion: 'reduce' })
  await check('mobile workspace remains bounded and keyboard navigation opens and closes', () => page(async () => {
    await new Promise(resolve => setTimeout(resolve, 250))
    const bounded = document.documentElement.scrollWidth <= innerWidth + 1
    const values = [...document.querySelectorAll('.pulse-metric dd')]
    const originals = values.map(item => item.textContent)
    let largeNumberLayout
    try {
      values[0].textContent = '1,234,567,890,123'
      values.at(-1).textContent = '123,456,789.125 ms'
      largeNumberLayout = document.documentElement.scrollWidth <= innerWidth + 1 && values.every(item => item.scrollWidth <= item.clientWidth + 1)
    } finally { values.forEach((item, index) => { item.textContent = originals[index] }) }
    document.querySelector('.mobile-menu-btn').click()
    await new Promise(resolve => setTimeout(resolve, 100))
    const open = document.querySelector('.sidebar').getAttribute('aria-modal') === 'true'
    document.querySelector('.sidebar').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await new Promise(resolve => setTimeout(resolve, 100))
    return { ok: bounded && largeNumberLayout && open && document.querySelector('.sidebar').hasAttribute('inert'), bounded, largeNumberLayoutFixture: largeNumberLayout,
      menuClosed: document.querySelector('.sidebar').hasAttribute('inert') }
  }))
  await client.tool('take_screenshot', { filePath: 'E:/Flowly-now/Docs/verification/ai-team-20261031/delivery-mobile.png', fullPage: true })
  await client.tool('emulate', { viewport: '1440x1000x1', prefersReducedMotion: 'reduce' })
  await check('personal cleanup rejects wrong password then removes only previewed personal data', () => page(async () => {
    const marker = await fetch('/api/v1/__isolated-qa__/').then(response => response.json())
    if (!marker.isolated || !marker.product_fixtures) throw new Error('Refusing to delete outside fixture backend')
    window.__productQa = { token: localStorage.getItem('access_token'), knowledgeId: sessionStorage.getItem('flowly_product_qa_knowledge_id') }
    window.__productWait = async (predicate, label = 'product UI') => { for (let n = 0; n < 150; n++) { if (await predicate()) return; await new Promise(resolve => setTimeout(resolve, 100)) }; throw new Error(`Timed out waiting for ${label}`) }
    window.__productInput = (selector, value) => { const field = document.querySelector(selector); if (!field) throw new Error(`Missing field ${selector}`); field.value = value; field.dispatchEvent(new Event(field.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })) }
    window.__productCall = async (path, options = {}) => { const response = await fetch(`/api/v1/${path}`, { ...options, headers: { Authorization: `Bearer ${window.__productQa.token}`, 'Content-Type': 'application/json', ...(options.headers || {}) } }); const json = await response.json(); return { status: response.status, data: json.data ?? json } }
    await window.__productWait(() => document.querySelector('#app')?.__vue_app__?.config.globalProperties.$router)
    window.__productRouter = document.querySelector('#app').__vue_app__.config.globalProperties.$router
    await window.__productRouter.push('/settings/data-export')
    await window.__productWait(() => document.querySelector('[data-testid="personal-data-delete-open"]'))
    const count = async path => {
      const result = await window.__productCall(path)
      if (result.status !== 200) throw new Error(`Count request failed ${path}: ${result.status}`)
      const total = result.data.count ?? result.data.results?.length ?? result.data.length
      if (!Number.isInteger(total)) throw new Error(`Invalid count response ${path}`)
      return total
    }
    const beforeWorkflows = await count('workflows/?page_size=1')
    const preservedPaths = ['applications/?page_size=100', 'billing/invoices/?page_size=100', 'data-export/?page_size=100']
    const before = await Promise.all(preservedPaths.map(count))
    const open = async () => {
      document.querySelector('[data-testid="personal-data-delete-open"]').click()
      await window.__productWait(() => document.querySelector('[aria-label="当前密码"]')?.getClientRects().length > 0)
      window.__productInput('[aria-label="清理确认文字"]', '删除个人工作流和Agent')
    }
    await open()
    window.__productInput('[aria-label="当前密码"]', 'incorrect-password')
    await window.__productWait(() => !document.querySelector('[data-testid="personal-data-delete-confirm"]').disabled)
    document.querySelector('[data-testid="personal-data-delete-confirm"]').click()
    await window.__productWait(() => document.body.innerText.includes('清理失败，请核对密码'))
    await window.__productWait(() => !document.querySelector('[data-testid="personal-data-delete-confirm"]').classList.contains('is-loading'))
    if (await count('workflows/?page_size=1') !== beforeWorkflows) return { ok: false, stage: 'wrong password changed data' }
    const dialog = document.querySelector('[data-testid="personal-data-delete-confirm"]').closest('.el-dialog')
    Array.from(dialog.querySelectorAll('button')).find(button => button.textContent.trim() === '取消').click()
    await new Promise(resolve => setTimeout(resolve, 300))
    await open()
    window.__productInput('[aria-label="当前密码"]', 'Test123456!')
    await window.__productWait(() => !document.querySelector('[data-testid="personal-data-delete-confirm"]').disabled)
    document.querySelector('[data-testid="personal-data-delete-confirm"]').click()
    await window.__productWait(async () => await count('workflows/?page_size=1') === 0, 'personal workflows deleted')
    const after = await Promise.all(preservedPaths.map(count))
    const knowledge = await window.__productCall(`applications/${window.__productQa.knowledgeId}/test/`, { method: 'POST', body: '{"input_data":{"query":"release"}}' })
    sessionStorage.removeItem('flowly_product_qa_knowledge_id')
    return { ok: beforeWorkflows > 0 && JSON.stringify(before) === JSON.stringify(after) && knowledge.status === 200 && knowledge.data.status === 'completed',
      personalWorkflowsRemoved: beforeWorkflows, preserved: ['applications', 'invoices', 'backups', 'indexed knowledge', 'authenticated account'] }
  }))
  console.log(JSON.stringify({ passed: checks.length, failed: 0, browser: 'chrome-devtools-mcp', scope: 'isolated fixtures; provider transport fixture only' }))
} finally { client.close() }
